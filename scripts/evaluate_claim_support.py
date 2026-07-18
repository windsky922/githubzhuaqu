"""Evaluate deterministic structured claim-support checks with fixed fixtures."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "evals" / "claim_support_cases.jsonl"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.claim_support import compare_facts


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not cases or len({str(case.get("id") or "") for case in cases}) != len(cases):
        raise ValueError("claim_support_cases must be non-empty with unique ids")
    return cases


def evaluate(cases: list[dict[str, Any]]) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    supported_correct = 0
    rejected_correct = 0
    false_supports = 0
    for case in cases:
        result = compare_facts(claim=case.get("claim"), evidence=case.get("evidence"), quote=str(case.get("quote") or ""))
        actual = result["semantic_support_status"] == "supported"
        expected = bool(case.get("expected_supported"))
        if actual == expected:
            supported_correct += int(expected)
            rejected_correct += int(not expected)
        else:
            false_supports += int(actual and not expected)
            failures.append({"id": case.get("id"), "expected_supported": expected, "actual": result})
    count = len(cases)
    return {
        "schema_version": 1,
        "sample_count": count,
        "metrics": {
            "exact_accuracy": supported_correct / count + rejected_correct / count,
            "false_support_rate": false_supports / count,
            "supported_case_accuracy": supported_correct,
            "rejected_case_accuracy": rejected_correct / max(1, sum(not bool(case.get("expected_supported")) for case in cases)),
        },
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(load_cases(args.cases))
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if not result["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
