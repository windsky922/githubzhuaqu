from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.storage.sqlite_store import import_json_archive


def main() -> int:
    parser = argparse.ArgumentParser(description="将现有 JSON 归档导入 SQLite 派生索引。")
    parser.add_argument("--root", type=Path, default=ROOT, help="项目根目录，默认当前仓库根目录。")
    parser.add_argument(
        "--db",
        type=Path,
        default=ROOT / "data" / "github_weekly.sqlite",
        help="SQLite 文件路径，默认 data/github_weekly.sqlite。",
    )
    args = parser.parse_args()

    counts = import_json_archive(args.root, args.db)
    print(f"sqlite_db={args.db}")
    for key, value in counts.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
