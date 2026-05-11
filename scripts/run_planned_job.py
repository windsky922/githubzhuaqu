from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.job_runner import run_planned_job


def main() -> int:
    parser = argparse.ArgumentParser(description="执行 SQLite jobs 表中的 planned 周报任务。")
    parser.add_argument("--root", type=Path, default=ROOT, help="项目根目录，默认当前仓库根目录。")
    parser.add_argument("--db", type=Path, default=None, help="SQLite 派生索引路径，默认 data/github_weekly.sqlite。")
    parser.add_argument("--job-id", default="", help="指定要执行的任务编号；为空时执行最早的 planned 任务。")
    args = parser.parse_args()

    result = run_planned_job(root=args.root, db_path=args.db, job_id=args.job_id or None)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if result.get("executed") and result.get("status") == "failed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
