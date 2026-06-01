from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.api.repository import ApiRepository


def backfill_rag_explanations(
    *,
    root: Path = ROOT,
    db_path: Path | None = None,
    limit: int = 10,
    rag_limit: int = 8,
    mode: str = "fts5",
    model: str = "local-hash-v1",
    auto_build: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    repository = ApiRepository(root=root, db_path=db_path)
    return repository.backfill_rag_explanations(
        limit=limit,
        rag_limit=rag_limit,
        mode=mode,
        model=model,
        auto_build=auto_build,
        dry_run=dry_run,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="为缺少解释历史的项目批量生成规则版 RAG 解释。")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--db-path", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--rag-limit", type=int, default=8)
    parser.add_argument("--mode", choices=["fts5", "vector"], default="fts5")
    parser.add_argument("--model", default="local-hash-v1")
    parser.add_argument("--auto-build", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = backfill_rag_explanations(
        root=args.root,
        db_path=args.db_path,
        limit=args.limit,
        rag_limit=args.rag_limit,
        mode=args.mode,
        model=args.model,
        auto_build=args.auto_build,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
