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
    parser = argparse.ArgumentParser(description="创建一个 planned 周报任务。")
    parser.add_argument("--root", type=Path, default=ROOT, help="项目根目录，默认当前仓库根目录。")
    parser.add_argument("--db", type=Path, default=None, help="SQLite 派生索引路径，默认 data/github_weekly.sqlite。")
    parser.add_argument("--profile", default="", help="个性化 profile，例如 agent_development。")
    parser.add_argument("--days-back", type=int, default=7, help="回看天数，默认 7。")
    parser.add_argument("--dry-run", default="true", help="true 时执行主流程会跳过内置 Telegram 推送。")
    parser.add_argument("--output", type=Path, default=None, help="把任务创建结果写入 JSON 文件。")
    args = parser.parse_args()

    payload = {
        "profile": args.profile.strip(),
        "days_back": args.days_back,
        "dry_run": _truthy(args.dry_run),
    }
    repository = ApiRepository(root=args.root, db_path=args.db)
    result = repository.trigger_run_preview(payload)
    text = json.dumps(result, ensure_ascii=False, sort_keys=True)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0


def _truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


if __name__ == "__main__":
    raise SystemExit(main())
