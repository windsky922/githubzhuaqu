from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.task_executor import TASK_TYPES, batch_execute_project_agent_tasks


def main() -> int:
    parser = argparse.ArgumentParser(description="批量执行项目级 Agent 只读任务。")
    parser.add_argument("--root", type=Path, default=ROOT, help="项目根目录。")
    parser.add_argument("--db", type=Path, default=None, help="SQLite 路径。")
    parser.add_argument("--limit", type=int, default=3, help="最多执行任务数，默认 3。")
    parser.add_argument("--priority", type=int, default=2, help="最高优先级数值，默认 2。")
    parser.add_argument("--task-type", choices=sorted(TASK_TYPES), default=None, help="仅执行指定任务类型。")
    parser.add_argument("--dry-run", action="store_true", help="只做预检查，不写入执行记录。")
    args = parser.parse_args()

    db_path = args.db or args.root / "data" / "github_weekly.sqlite"
    result = batch_execute_project_agent_tasks(
        args.root,
        db_path,
        limit=args.limit,
        priority=args.priority,
        task_type=args.task_type,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 1 if any(item.get("status") == "failed" for item in result["results"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
