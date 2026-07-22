"""Private blind-pack baseline runner.

The pack path is deliberately explicit and outside the public ``evals/`` tree.
It records only pack hash and aggregate categories; questions, labels and answers
are never copied into the repository or CI logs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from src.rag.freshness import is_time_sensitive_query


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blind-pack", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    pack = args.blind_pack.resolve()
    if "evals" in {part.lower() for part in pack.parts}:
        raise SystemExit("blind pack must not be stored under public evals/")
    rows = [json.loads(line) for line in pack.read_text(encoding="utf-8").splitlines() if line.strip()]
    categories = Counter()
    mismatches = 0
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("query"), str):
            raise SystemExit("invalid blind case")
        expected = row.get("freshness_required")
        if not isinstance(expected, bool):
            raise SystemExit("each blind case needs boolean freshness_required")
        mismatches += is_time_sensitive_query(row["query"]) != expected
        categories.update(str(item) for item in row.get("categories", []) if str(item))
    report = {
        "schema_version": 1,
        "kind": "blind_rag_baseline",
        "pack_sha256": hashlib.sha256(pack.read_bytes()).hexdigest(),
        "case_count": len(rows),
        "category_counts": dict(sorted(categories.items())),
        "freshness_required_exact_rate": 0.0 if not rows else (len(rows) - mismatches) / len(rows),
        "threshold": None,
        "note": "baseline only; frozen independent labels are required before any CI threshold",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("kind", "pack_sha256", "case_count", "freshness_required_exact_rate", "threshold")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
