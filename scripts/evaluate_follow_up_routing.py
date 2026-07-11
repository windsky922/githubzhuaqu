"""Evaluate deterministic follow-up routing without calling retrieval or a real model."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rag.follow_up_router import normalize_intent_context, route_follow_up


class _OfflineClient:
    def status(self) -> dict[str, Any]:
        return {"configured": False, "model": ""}


def load_cases(path: Path) -> list[dict[str, Any]]:
    rows = []
    seen = set()
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        row = json.loads(raw)
        required = {"id", "query", "context", "expected_route", "expected_scope", "expected_requirements", "expect_clarification"}
        missing = required - set(row)
        if missing:
            raise ValueError(f"line {line_number} missing: {sorted(missing)}")
        if row["id"] in seen:
            raise ValueError(f"duplicate id: {row['id']}")
        seen.add(row["id"])
        rows.append(row)
    if len(rows) < 40:
        raise ValueError("follow-up evaluation requires at least 40 cases")
    return rows


def evaluate(cases: list[dict[str, Any]], *, root: Path = PROJECT_ROOT) -> dict[str, Any]:
    items = []
    for case in cases:
        context = normalize_intent_context(case.get("context"))
        result = route_follow_up(root=root, query=case["query"], context=context, client=_OfflineClient())
        expected_fragment = str(case.get("expected_resolved_contains") or "")
        rewrite_correct = (
            not result["resolved_query"] if case["expected_route"] == "clarify"
            else expected_fragment in result["resolved_query"]
        )
        raw_violation = bool(
            case.get("must_not_retrieve_raw_input")
            and result["route"] != "clarify"
            and result["resolved_query"].strip() == str(case["query"]).strip()
        )
        items.append({
            "id": case["id"],
            "route_correct": result["route"] == case["expected_route"],
            "clarification_correct": bool(result["clarification_required"]) == bool(case["expect_clarification"]),
            "rewrite_correct": bool(rewrite_correct),
            "scope_correct": result["candidate_scope"] == case["expected_scope"],
            "constraints_correct": result["requirements"] == case["expected_requirements"],
            "raw_follow_up_retrieval_violation": raw_violation,
        })
    total = max(1, len(items))
    return {
        "schema_version": 1,
        "sample_count": len(items),
        "metrics": {
            "route_accuracy": _rate(items, "route_correct", total),
            "clarification_accuracy": _rate(items, "clarification_correct", total),
            "rewrite_accuracy": _rate(items, "rewrite_correct", total),
            "candidate_scope_accuracy": _rate(items, "scope_correct", total),
            "constraint_exact_match_accuracy": _rate(items, "constraints_correct", total),
            "raw_follow_up_retrieval_violation_rate": round(sum(item["raw_follow_up_retrieval_violation"] for item in items) / total, 4),
        },
        "failures": [item for item in items if not all(value for key, value in item.items() if key not in {"id", "raw_follow_up_retrieval_violation"}) or item["raw_follow_up_retrieval_violation"]],
    }


def _rate(items: list[dict[str, Any]], key: str, total: int) -> float:
    return round(sum(bool(item[key]) for item in items) / total, 4)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=PROJECT_ROOT / "evals" / "follow_up_cases.jsonl")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(load_cases(args.dataset))
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 1 if result["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
