from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.api.repository import ApiRepository
from src.job_runner import run_planned_job


def _bool_value(value: str | bool | None, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _queries_from_args(repeated: list[str] | None, text: str | None) -> list[str]:
    values: list[str] = []
    for item in repeated or []:
        values.append(item)
    if text:
        values.extend(part for part in re.split(r"[,;\n]+", text) if part.strip())
    output: list[str] = []
    seen = set()
    for item in values:
        normalized = str(item or "").strip()
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        output.append(normalized)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="执行一次 RAG 检索质量评估，并写入 SQLite jobs。")
    parser.add_argument("--root", type=Path, default=ROOT, help="项目根目录，默认当前仓库根目录。")
    parser.add_argument("--db", type=Path, default=None, help="SQLite 派生索引路径，默认 data/github_weekly.sqlite。")
    parser.add_argument("--query", action="append", default=[], help="评估查询词，可重复传入。")
    parser.add_argument("--queries", default="", help="评估查询词列表，支持用逗号、分号或换行分隔。")
    parser.add_argument("--language", default="", help="可选语言过滤，例如 Python。")
    parser.add_argument("--category", default="", help="可选方向过滤，例如 AI Agent。")
    parser.add_argument("--source", default="", help="可选来源过滤，例如 github_trending。")
    parser.add_argument("--limit", type=int, default=8, help="每种检索模式最多返回多少条证据，默认 8。")
    parser.add_argument("--model", default="local-hash-v1", help="本地向量模型名，默认 local-hash-v1。")
    parser.add_argument("--auto-build", default="true", help="缺少本地 embedding 时是否自动构建，默认 true。")
    parser.add_argument("--requested-by", default="rag_evaluation_script", help="任务创建者标识。")
    args = parser.parse_args(argv)

    payload = {
        "queries": _queries_from_args(args.query, args.queries),
        "language": args.language,
        "category": args.category,
        "source": args.source,
        "limit": args.limit,
        "model": args.model,
        "auto_build": _bool_value(args.auto_build, True),
        "confirm_execution": True,
        "requested_by": args.requested_by,
        "trigger_source": "rag_search_evaluation_script",
    }
    repository = ApiRepository(root=args.root, db_path=args.db)
    plan = repository.plan_rag_search_evaluation(payload)
    runner_result = run_planned_job(root=args.root, db_path=args.db, job_id=plan.get("job_id") or None)
    result = {
        "schema_version": 1,
        "accepted": bool(plan.get("accepted")),
        "planned_job_created": bool(plan.get("planned_job_created")),
        "job_id": plan.get("job_id") or "",
        "status": runner_result.get("status") or plan.get("status") or "",
        "plan": plan,
        "runner_result": runner_result,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("accepted") and runner_result.get("status") == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
