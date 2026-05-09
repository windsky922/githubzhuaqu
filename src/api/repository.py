from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.query_archive import query_archive
from src.storage.sqlite_store import import_json_archive

ROOT = Path(__file__).resolve().parents[2]


class ApiRepository:
    """面向后端 API 的只读归档访问层。"""

    def __init__(self, root: Path = ROOT, db_path: Path | None = None) -> None:
        self.root = root
        self.db_path = db_path or root / "data" / "github_weekly.sqlite"

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "root": str(self.root),
            "sqlite_exists": self.db_path.exists(),
            "reports_exists": (self.root / "reports").exists(),
            "docs_exists": (self.root / "docs").exists(),
        }

    def projects(
        self,
        *,
        language: str | None = None,
        category: str | None = None,
        profile: str | None = None,
        source: str | None = None,
        risk: str | None = None,
        quality_level: str | None = None,
        min_quality: int | None = None,
        trending_top: int | None = None,
        query: str | None = None,
        limit: int = 20,
        sort: str = "recent",
    ) -> dict[str, Any]:
        self.ensure_sqlite_index()
        rows = query_archive(
            db_path=self.db_path,
            root=self.root,
            language=_blank_to_none(language),
            category=_blank_to_none(category),
            profile=_blank_to_none(profile),
            source=_blank_to_none(source),
            risk=_blank_to_none(risk),
            quality_level=_blank_to_none(quality_level),
            min_quality=min_quality,
            trending_top=trending_top,
            query=_blank_to_none(query),
            limit=limit,
            sort=sort,
        )
        return {
            "schema_version": 1,
            "count": len(rows),
            "projects": rows,
        }

    def project_detail(self, full_name: str) -> dict[str, Any]:
        self.ensure_sqlite_index()
        normalized = _normalize_full_name(full_name)
        history = [
            project
            for project in query_archive(
                db_path=self.db_path,
                root=self.root,
                query=normalized,
                limit=200,
                sort="recent",
            )
            if str(project.get("full_name") or "").lower() == normalized.lower()
        ]
        if not history:
            return {
                "schema_version": 1,
                "found": False,
                "full_name": normalized,
                "history_count": 0,
                "history": [],
                "similar_projects": [],
            }

        history = sorted(history, key=lambda project: str(project.get("run_date") or ""), reverse=True)
        latest = history[0]
        return {
            "schema_version": 1,
            "found": True,
            "full_name": latest.get("full_name") or normalized,
            "html_url": latest.get("html_url") or "",
            "description": latest.get("description") or "",
            "language": latest.get("language") or "",
            "category": latest.get("category") or "",
            "latest_run_date": latest.get("run_date") or "",
            "first_run_date": history[-1].get("run_date") or "",
            "history_count": len(history),
            "total_star_growth": sum(_int_value(project.get("star_growth")) for project in history),
            "best_trending_rank": _best_trending_rank(history),
            "sources": _unique_strings(source for project in history for source in project.get("sources") or []),
            "security_flags": _unique_strings(flag for project in history for flag in project.get("security_flags") or []),
            "quality_flags": _unique_strings(flag for project in history for flag in project.get("quality_flags") or []),
            "best_quality_score": max((_int_value(project.get("quality_score")) for project in history), default=0),
            "latest_quality_score": _int_value(latest.get("quality_score")),
            "latest_quality_level": latest.get("quality_level") or "unknown",
            "history": history,
            "similar_projects": self._similar_projects(latest, normalized),
        }

    def runs(self) -> dict[str, Any]:
        return _read_json_object(self.root / "docs" / "runs.json", {"schema_version": 1, "count": 0, "runs": []})

    def profiles(self) -> dict[str, Any]:
        return _read_json_object(
            self.root / "docs" / "profiles.json",
            {"schema_version": 1, "count": 0, "profiles": []},
        )

    def latest_weekly(self) -> dict[str, Any]:
        reports = sorted((self.root / "reports").glob("*.md"), key=lambda path: path.stem, reverse=True)
        reports = [path for path in reports if path.name != ".gitkeep"]
        if not reports:
            return {
                "schema_version": 1,
                "run_date": "",
                "report_url": "",
                "markdown": "",
                "run_summary": {},
            }
        latest = reports[0]
        return {
            "schema_version": 1,
            "run_date": latest.stem,
            "report_url": f"weekly/{latest.stem}.html",
            "markdown": latest.read_text(encoding="utf-8"),
            "run_summary": _read_json_object(self.root / "data" / "runs" / f"{latest.stem}.json", {}),
        }

    def ensure_sqlite_index(self) -> None:
        if not self.db_path.exists():
            import_json_archive(self.root, self.db_path)

    def _similar_projects(self, base: dict[str, Any], full_name: str) -> list[dict[str, Any]]:
        candidates = query_archive(db_path=self.db_path, root=self.root, limit=200, sort="recent")
        scored = []
        seen = set()
        for candidate in candidates:
            candidate_name = str(candidate.get("full_name") or "")
            if not candidate_name or candidate_name.lower() == full_name.lower() or candidate_name in seen:
                continue
            seen.add(candidate_name)
            score = _similarity_score(base, candidate)
            if score <= 0:
                continue
            scored.append((score, candidate))
        scored.sort(
            key=lambda item: (
                item[0],
                _int_value(item[1].get("star_growth")),
                -_rank_value(item[1].get("trending_rank")),
                str(item[1].get("run_date") or ""),
            ),
            reverse=True,
        )
        return [
            {
                "full_name": project.get("full_name") or "",
                "html_url": project.get("html_url") or "",
                "description": project.get("description") or "",
                "language": project.get("language") or "",
                "category": project.get("category") or "",
                "run_date": project.get("run_date") or "",
                "star_growth": _int_value(project.get("star_growth")),
                "trending_rank": _int_value(project.get("trending_rank")),
                "similarity_score": score,
            }
            for score, project in scored[:5]
        ]


def _read_json_object(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default
    return data if isinstance(data, dict) else default


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _normalize_full_name(value: str) -> str:
    return value.strip().strip("/")


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _best_trending_rank(projects: list[dict[str, Any]]) -> int:
    ranks = [_int_value(project.get("trending_rank")) for project in projects]
    ranks = [rank for rank in ranks if rank > 0]
    return min(ranks) if ranks else 0


def _unique_strings(values: Any) -> list[str]:
    output = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            output.append(text)
    return output


def _similarity_score(base: dict[str, Any], candidate: dict[str, Any]) -> int:
    score = 0
    if base.get("language") and base.get("language") == candidate.get("language"):
        score += 4
    if base.get("category") and base.get("category") == candidate.get("category"):
        score += 5
    score += len(set(base.get("sources") or []) & set(candidate.get("sources") or []))
    score += min(4, len(_project_keywords(base) & _project_keywords(candidate)))
    return score


def _project_keywords(project: dict[str, Any]) -> set[str]:
    text = " ".join(
        [
            str(project.get("full_name") or ""),
            str(project.get("description") or ""),
            str(project.get("category") or ""),
            " ".join(str(reason) for reason in project.get("selection_reasons") or []),
        ]
    ).lower()
    return {part for part in text.replace("/", " ").replace("-", " ").replace("_", " ").split() if len(part) >= 3}


def _rank_value(value: Any) -> int:
    rank = _int_value(value)
    return rank if rank > 0 else 9999

