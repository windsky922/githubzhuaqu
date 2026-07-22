"""Evaluate fixed adversarial capability-scope fixtures without a model or network."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.claim_support import compare_facts


def evaluate(path: Path) -> dict:
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not cases or len({case.get("id") for case in cases}) != len(cases):
        raise ValueError("capability scope cases must be non-empty with unique ids")
    failures = []
    false_scope_supports = 0
    for case in cases:
        result = compare_facts(claim=case["claim"], evidence=case["evidence"], quote=case["quote"])
        actual = result["semantic_support_status"] == "supported"
        expected = bool(case["expected_supported"])
        false_scope_supports += int(actual and not expected)
        if actual != expected:
            failures.append({"id": case["id"], "expected_supported": expected, "actual": result})
    return {
        "schema_version": 1,
        "sample_count": len(cases),
        "metrics": {
            "exact_accuracy": (len(cases) - len(failures)) / len(cases),
            "false_scope_support_rate": false_scope_supports / len(cases),
        },
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ROOT / "evals" / "capability_scope_cases.jsonl")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(args.cases)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 1 if result["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
