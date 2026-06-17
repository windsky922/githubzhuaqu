from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.api.repository import ApiRepository


def main() -> int:
    parser = argparse.ArgumentParser(description="创建开发上下文索引 planned 任务。")
    parser.add_argument("--root", type=Path, default=ROOT, help="项目根目录，默认当前仓库根目录。")
    parser.add_argument("--db", type=Path, default=None, help="SQLite 派生索引路径，默认 data/github_weekly.sqlite。")
    parser.add_argument("--run-checks", default="false", help="是否在索引时运行测试和安全检查，默认 false。")
    parser.add_argument("--replace", default="false", help="是否清空并重建开发上下文索引，默认 false。")
    parser.add_argument("--max-command-chars", type=int, default=120000, help="命令输出最多采集字符数。")
    parser.add_argument("--trigger-source", default="dev_context_index_script", help="任务触发来源。")
    parser.add_argument("--requested-by", default="", help="任务创建者。")
    parser.add_argument("--output", type=Path, default=None, help="把任务创建结果写入 JSON 文件。")
    args = parser.parse_args()

    repository = ApiRepository(root=args.root, db_path=args.db)
    result = repository.plan_dev_context_index(
        {
            "run_checks": _truthy(args.run_checks),
            "replace": _truthy(args.replace),
            "max_command_chars": args.max_command_chars,
            "trigger_source": args.trigger_source.strip() or "dev_context_index_script",
            "requested_by": args.requested_by.strip() or os.getenv("GITHUB_ACTOR", "") or "dev_context_index_script",
        }
    )
    text = json.dumps(result, ensure_ascii=False, sort_keys=True)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0


def _truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


if __name__ == "__main__":
    raise SystemExit(main())
