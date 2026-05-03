from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.storage.sqlite_store import connect, initialize, table_count


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 SQLite 派生索引与 JSON 归档的基础计数。")
    parser.add_argument("--root", type=Path, default=ROOT, help="项目根目录，默认当前仓库根目录。")
    parser.add_argument(
        "--db",
        type=Path,
        default=ROOT / "data" / "github_weekly.sqlite",
        help="SQLite 文件路径，默认 data/github_weekly.sqlite。",
    )
    args = parser.parse_args()

    expected = _json_counts(args.root)
    try:
        with connect(args.db) as connection:
            initialize(connection)
            actual = {table: table_count(connection, table) for table in expected}
    except sqlite3.Error as error:
        print(f"SQLite 校验失败：{error}", file=sys.stderr)
        return 1

    failures = []
    for table, expected_count in expected.items():
        actual_count = actual.get(table, 0)
        status = "OK" if actual_count == expected_count else "MISMATCH"
        print(f"{table}: json={expected_count} sqlite={actual_count} {status}")
        if actual_count != expected_count:
            failures.append(table)
    if failures:
        print(f"迁移校验未通过：{', '.join(failures)}", file=sys.stderr)
        return 1
    print("迁移校验通过。")
    return 0


def _json_counts(root: Path) -> dict[str, int]:
    return {
        "runs": len(_json_files(root / "data" / "runs")),
        "selections": sum(len(_read_json_list(path)) for path in _json_files(root / "data" / "selected")),
        "trend_summaries": len(_json_files(root / "data" / "trends")),
        "sent_repositories": len(_read_json_list(root / "data" / "state" / "sent_repos.json")),
        "star_history": len(_read_json_list(root / "data" / "state" / "star_history.json")),
    }


def _json_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(item for item in path.glob("*.json") if item.is_file())


def _read_json_list(path: Path) -> list[object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


if __name__ == "__main__":
    raise SystemExit(main())
