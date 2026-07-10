from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.storage.sqlite_store import connect, import_json_archive, initialize


def main() -> int:
    parser = argparse.ArgumentParser(description="查询 GitHub Weekly Agent 的历史项目归档。")
    parser.add_argument("--root", type=Path, default=ROOT, help="项目根目录，默认当前仓库根目录。")
    parser.add_argument(
        "--db",
        type=Path,
        default=ROOT / "data" / "github_weekly.sqlite",
        help="SQLite 派生索引路径，默认 data/github_weekly.sqlite。",
    )
    parser.add_argument("--refresh", action="store_true", help="查询前先从 JSON 归档同步 SQLite 索引。")
    parser.add_argument("--language", help="按主要语言筛选，例如 Python、Java、TypeScript。")
    parser.add_argument("--category", help="按项目方向筛选，例如 AI Agent、Developer Tools。")
    parser.add_argument("--profile", help="按 config/profiles.json 或 profiles.example.json 中的 profile 筛选。")
    parser.add_argument("--source", help="按来源筛选，例如 github_trending、github_search。")
    parser.add_argument("--risk", choices=("has", "none"), help="按风险提示筛选，has 表示有风险提示，none 表示无风险提示。")
    parser.add_argument("--quality-level", choices=("high", "medium", "low", "unknown"), help="按质量等级筛选。")
    parser.add_argument("--min-quality", type=int, help="按最低质量分筛选，范围 0 到 100。")
    parser.add_argument("--trending-top", type=int, help="只查看进入 GitHub Trending TopN 的历史项目。")
    parser.add_argument("--query", help="按项目名、简介、方向或推荐理由关键词搜索。")
    parser.add_argument("--limit", type=int, default=20, help="最多返回项目数，默认 20。")
    parser.add_argument(
        "--sort",
        choices=("recent", "position", "score", "star-growth", "trending", "quality"),
        default="recent",
        help="排序方式，默认按最新周报和入选顺序排序。",
    )
    parser.add_argument("--format", choices=("table", "json"), default="table", help="输出格式，默认 table。")
    args = parser.parse_args()

    if args.refresh or not args.db.exists():
        import_json_archive(args.root, args.db)

    try:
        rows = query_archive(
            db_path=args.db,
            root=args.root,
            language=args.language,
            category=args.category,
            profile=args.profile,
            source=args.source,
            risk=args.risk,
            quality_level=args.quality_level,
            min_quality=args.min_quality,
            trending_top=args.trending_top,
            query=args.query,
            limit=args.limit,
            sort=args.sort,
        )
    except sqlite3.Error as error:
        print(f"查询 SQLite 归档失败：{error}", file=sys.stderr)
        return 1
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print(table_output(rows))
    return 0


def query_archive(
    *,
    db_path: Path,
    root: Path = ROOT,
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
    offset: int = 0,
    sort: str = "recent",
) -> list[dict[str, Any]]:
    rows, _ = query_archive_page(
        db_path=db_path,
        root=root,
        language=language,
        category=category,
        profile=profile,
        source=source,
        risk=risk,
        quality_level=quality_level,
        min_quality=min_quality,
        trending_top=trending_top,
        query=query,
        limit=limit,
        offset=offset,
        sort=sort,
    )
    return rows


def query_archive_page(
    *,
    db_path: Path,
    root: Path = ROOT,
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
    offset: int = 0,
    sort: str = "recent",
) -> tuple[list[dict[str, Any]], int]:
    limit = max(1, min(limit, 200))
    offset = max(0, int(offset or 0))
    profile_config = _load_profile(root, profile) if profile else None
    min_quality = _bounded_quality(min_quality)
    trending_top = _bounded_positive(trending_top)
    conditions = []
    parameters: list[Any] = []

    if language:
        conditions.append("repositories.language = ?")
        parameters.append(language)
    if category:
        conditions.append("selections.category = ?")
        parameters.append(category)
    if source:
        conditions.append("selections.sources_json LIKE ?")
        parameters.append(f'%"{source}"%')
    if risk == "has":
        conditions.append("selections.security_flags_json <> '[]'")
    elif risk == "none":
        conditions.append("selections.security_flags_json = '[]'")
    if trending_top:
        conditions.append("selections.trending_rank > 0 AND selections.trending_rank <= ?")
        parameters.append(trending_top)
    if query:
        keyword = f"%{query.lower()}%"
        conditions.append(
            """(
              lower(repositories.full_name) LIKE ?
              OR lower(repositories.description) LIKE ?
              OR lower(selections.category) LIKE ?
              OR lower(selections.selection_reasons_json) LIKE ?
            )"""
        )
        parameters.extend([keyword, keyword, keyword, keyword])

    sql = """
        SELECT
          selections.run_date,
          selections.position,
          selections.full_name,
          repositories.html_url,
          repositories.description,
          repositories.language,
          selections.category,
          selections.star_growth,
          selections.trending_rank,
          selections.score,
          selections.sources_json,
          selections.selection_reasons_json,
          selections.security_flags_json,
          selections.payload_json
        FROM selections
        JOIN repositories ON repositories.full_name = selections.full_name
    """
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    needs_python_filter = bool(profile_config or quality_level or min_quality is not None or sort == "quality")

    connection = connect(db_path)
    try:
        initialize(connection)
        if needs_python_filter:
            raw_sql = sql + f" ORDER BY {_order_clause(sort)}"
            rows = [_row_to_project(row) for row in connection.execute(raw_sql, parameters).fetchall()]
            total = 0
        else:
            total_sql = "SELECT COUNT(*) " + sql[sql.index("FROM selections"):]
            total = int(connection.execute(total_sql, parameters).fetchone()[0])
            page_sql = sql + f" ORDER BY {_order_clause(sort)} LIMIT ? OFFSET ?"
            rows = [_row_to_project(row) for row in connection.execute(page_sql, [*parameters, limit, offset]).fetchall()]
    finally:
        connection.close()

    if profile_config:
        rows = [row for row in rows if _matches_profile(row, profile_config)]
    if quality_level or min_quality is not None:
        rows = [row for row in rows if _matches_quality(row, quality_level=quality_level, min_quality=min_quality)]
    rows = _sort_rows(rows, sort)
    if needs_python_filter:
        total = len(rows)
        rows = rows[offset:offset + limit]
    return rows, total


def table_output(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "没有匹配的历史项目。"
    lines = ["日期 | 项目 | 语言 | 方向 | 质量分 | 新增 Star | Trending | 链接", "--- | --- | --- | --- | ---: | ---: | ---: | ---"]
    for row in rows:
        trending = row["trending_rank"] if row["trending_rank"] else "-"
        lines.append(
            " | ".join(
                [
                    str(row["run_date"]),
                    str(row["full_name"]),
                    str(row["language"] or "Unknown"),
                    str(row["category"] or "Other"),
                    str(row.get("quality_score", 0)),
                    str(row["star_growth"]),
                    str(trending),
                    str(row["html_url"]),
                ]
            )
        )
    return "\n".join(lines)


def _row_to_project(row: sqlite3.Row) -> dict[str, Any]:
    payload = _json_object(row["payload_json"])
    return {
        "run_date": row["run_date"],
        "position": row["position"],
        "full_name": row["full_name"],
        "html_url": row["html_url"],
        "description": row["description"],
        "language": row["language"],
        "category": row["category"],
        "star_growth": row["star_growth"],
        "trending_rank": row["trending_rank"],
        "score": row["score"],
        "sources": _json_list(row["sources_json"]),
        "selection_reasons": _json_list(row["selection_reasons_json"]),
        "security_flags": _json_list(row["security_flags_json"]),
        "quality_score": _int_value(payload.get("quality_score")),
        "quality_level": str(payload.get("quality_level") or "unknown"),
        "quality_flags": payload.get("quality_flags") if isinstance(payload.get("quality_flags"), list) else [],
    }


def _load_profile(root: Path, name: str | None) -> dict[str, Any]:
    if not name:
        return {}
    profiles_path = root / "config" / "profiles.json"
    if not profiles_path.exists():
        profiles_path = root / "config" / "profiles.example.json"
    try:
        data = json.loads(profiles_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    profile = data.get(name) if isinstance(data, dict) else None
    if not isinstance(profile, dict):
        raise ValueError(f"未找到 profile：{name}")
    return profile


def _matches_profile(project: dict[str, Any], profile: dict[str, Any]) -> bool:
    preferred_languages = profile.get("preferred_languages") or []
    if project["language"] in preferred_languages:
        return True
    keywords = [
        *profile.get("preferred_topics", []),
        *profile.get("search_topics", []),
    ]
    text = " ".join(
        [
            str(project.get("full_name") or ""),
            str(project.get("description") or ""),
            str(project.get("category") or ""),
            " ".join(project.get("selection_reasons") or []),
        ]
    ).lower()
    return any(str(keyword).lower() in text for keyword in keywords if keyword)


def _matches_quality(project: dict[str, Any], *, quality_level: str | None, min_quality: int | None) -> bool:
    if quality_level and project.get("quality_level") != quality_level:
        return False
    if min_quality is not None and int(project.get("quality_score") or 0) < min_quality:
        return False
    return True


def _sort_rows(rows: list[dict[str, Any]], sort: str) -> list[dict[str, Any]]:
    if sort == "quality":
        rows = sorted(rows, key=lambda row: int(row["position"]))
        rows = sorted(rows, key=lambda row: str(row["run_date"]), reverse=True)
        return sorted(rows, key=lambda row: int(row.get("quality_score") or 0), reverse=True)
    return rows


def _order_clause(sort: str) -> str:
    mapping = {
        "recent": "selections.run_date DESC, selections.position ASC",
        "position": "selections.run_date DESC, selections.position ASC",
        "score": "selections.score DESC, selections.run_date DESC, selections.position ASC",
        "star-growth": "selections.star_growth DESC, selections.run_date DESC, selections.position ASC",
        "trending": "CASE WHEN selections.trending_rank > 0 THEN 0 ELSE 1 END, selections.trending_rank ASC, selections.run_date DESC",
        "quality": "selections.run_date DESC, selections.position ASC",
    }
    return mapping.get(sort, mapping["recent"])


def _bounded_quality(value: int | None) -> int | None:
    if value is None:
        return None
    return max(0, min(int(value), 100))


def _bounded_positive(value: int | None) -> int | None:
    if value is None:
        return None
    return max(1, int(value))


def _json_list(value: str) -> list[Any]:
    try:
        data = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _json_object(value: str) -> dict[str, Any]:
    try:
        data = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
