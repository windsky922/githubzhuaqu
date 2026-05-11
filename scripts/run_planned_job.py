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
    parser.add_argument("--job-file", type=Path, default=None, help="从 JSON 文件读取 job_id。")
    args = parser.parse_args()

    job_id = args.job_id or _job_id_from_file(args.job_file)
    if args.job_file is not None and not job_id:
        print(f"无法从任务文件读取 job_id：{args.job_file}", file=sys.stderr)
        return 1
    result = run_planned_job(root=args.root, db_path=args.db, job_id=job_id or None)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if result.get("executed") and result.get("status") == "failed":
        return 1
    return 0


def _job_id_from_file(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return ""
    return str(data.get("job_id") or "")


if __name__ == "__main__":
    raise SystemExit(main())
