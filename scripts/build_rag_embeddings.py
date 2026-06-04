from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.embeddings import DEFAULT_DIMENSIONS, MODEL_NAME, build_rag_embeddings


def main() -> int:
    parser = argparse.ArgumentParser(description="构建本地 RAG embedding 索引。")
    parser.add_argument("--db-path", default=str(ROOT / "data" / "github_weekly.sqlite"), help="SQLite 数据库路径。")
    parser.add_argument("--model", default=MODEL_NAME, help="embedding 模型标识，默认 local-hash-v1。")
    parser.add_argument("--dimensions", type=int, default=DEFAULT_DIMENSIONS, help="向量维度。")
    args = parser.parse_args()

    result = build_rag_embeddings(Path(args.db_path), model=args.model, dimensions=args.dimensions)
    print(json.dumps({"status": "ok", **result}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
