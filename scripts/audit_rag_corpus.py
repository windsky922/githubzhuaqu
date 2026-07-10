from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.corpus_audit import audit_rag_corpus


def main() -> int:
    parser = argparse.ArgumentParser(description="只读审计 RAG 清洗后语料噪声和版本")
    parser.add_argument("--db-path", default="data/github_weekly.sqlite")
    args = parser.parse_args()
    result = audit_rag_corpus(Path(args.db_path))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
