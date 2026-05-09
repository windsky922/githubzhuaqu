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

