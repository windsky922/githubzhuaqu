from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.api.repository import ApiRepository


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 RAG 诊断与覆盖缺口，并按需创建 RAG 维护 planned 任务。")
    parser.add_argument("--root", type=Path, default=ROOT, help="项目根目录，默认当前仓库根目录。")
    parser.add_argument("--db", type=Path, default=None, help="SQLite 派生索引路径，默认 data/github_weekly.sqlite。")
    parser.add_argument("--limit", type=int, default=10, help="计划回填项目数量，默认 10。")
    parser.add_argument("--evaluation-limit", type=int, default=None, help="健康状态下检索评估样本数量，默认复用 --limit。")
    parser.add_argument("--coverage-limit", type=int, default=100, help="诊断和覆盖缺口检查数量，默认 100。")
    parser.add_argument("--min-gap-count", type=int, default=1, help="达到多少缺口才创建任务，默认 1。")
    parser.add_argument("--execute", action="store_true", help="创建真实写库任务；默认只创建 dry-run 任务。")
    parser.add_argument(
        "--confirm-execution",
        action="store_true",
        help="确认允许真实写库，必须和 --execute 同时使用才会生效。",
    )
    parser.add_argument("--requested-by", default="maintenance_script", help="任务创建者标识。")
    args = parser.parse_args()

    repository = ApiRepository(root=args.root, db_path=args.db)
    payload = {
        "limit": args.limit,
        "evaluation_limit": args.evaluation_limit,
        "coverage_limit": args.coverage_limit,
        "min_gap_count": args.min_gap_count,
        "dry_run": not args.execute,
        "confirm_execution": args.confirm_execution,
        "requested_by": args.requested_by,
        "trigger_source": "rag_maintenance_script",
    }
    result = repository.plan_rag_maintenance(payload)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
