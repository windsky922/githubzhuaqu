from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.embeddings import DEFAULT_DIMENSIONS, MODEL_NAME
from src.rag.freshness_attestation import refresh_rag_freshness


def main() -> int:
    parser = argparse.ArgumentParser(description="重建派生 RAG 层并原子写入 freshness attestation。")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--db-path", type=Path, default=None)
    parser.add_argument("--run-date", required=True)
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--dimensions", type=int, default=DEFAULT_DIMENSIONS)
    args = parser.parse_args()
    root = args.root.resolve()
    database = args.db_path or root / "data" / "github_weekly.sqlite"
    result = refresh_rag_freshness(
        root=root,
        db_path=database,
        run_date=args.run_date,
        model=args.model,
        dimensions=args.dimensions,
    )
    print(json.dumps({"status": "ok", "run_date": args.run_date, "rag_freshness": result}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
