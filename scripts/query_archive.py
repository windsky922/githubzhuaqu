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
    parser.add_argument("--query", help="按项目名、简介、方向或推荐理由关键词搜索。")
    parser.add_argument("--limit", type=int, default=20, help="最多返回项目数，默认 20。")
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
            query=args.query,
            limit=args.limit,
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
    query: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 200))
    profile_config = _load_profile(root, profile) if profile else None
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
          selections.security_flags_json
        FROM selections
        JOIN repositories ON repositories.full_name = selections.full_name
    """
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += """
        ORDER BY selections.run_date DESC, selections.position ASC
        LIMIT ?
    """
    parameters.append(max(limit * 20, 200) if profile_config else limit)

    connection = connect(db_path)
    try:
        initialize(connection)
        rows = [_row_to_project(row) for row in connection.execute(sql, parameters).fetchall()]
    finally:
        connection.close()

    if profile_config:
        rows = [row for row in rows if _matches_profile(row, profile_config)]
    return rows[:limit]


def table_output(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "没有匹配的历史项目。"
    lines = ["日期 | 项目 | 语言 | 方向 | 新增 Star | Trending | 链接", "--- | --- | --- | --- | ---: | ---: | ---"]
    for row in rows:
        trending = row["trending_rank"] if row["trending_rank"] else "-"
        lines.append(
            " | ".join(
                [
                    str(row["run_date"]),
                    str(row["full_name"]),
                    str(row["language"] or "Unknown"),
                    str(row["category"] or "Other"),
                    str(row["star_growth"]),
                    str(trending),
                    str(row["html_url"]),
                ]
            )
        )
    return "\n".join(lines)


def _row_to_project(row: sqlite3.Row) -> dict[str, Any]:
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


def _json_list(value: str) -> list[Any]:
    try:
        data = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


if __name__ == "__main__":
    raise SystemExit(main())
