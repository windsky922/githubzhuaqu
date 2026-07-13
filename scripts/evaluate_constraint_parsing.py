"""评估分句级硬约束解析，不调用检索或模型。"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rag.follow_up_router import normalize_intent_context, route_follow_up
from src.rag.constraint_verifier import classify_text_evidence, evidence_state_status

EXPECTED_SPLITS = {"development": 60, "locked": 20, "adversarial": 20}
EVALUATION_CONTEXT = normalize_intent_context({
    "previous_user_goal": "寻找适合团队的项目",
    "candidate_repository_ids": ["eval/agent-orchestrator", "eval/rag-platform"],
    "primary_repository_id": "eval/agent-orchestrator",
    "mode": "hybrid",
    "resumable": True,
})


class _OfflineClient:
    def status(self) -> dict[str, Any]:
        return {"configured": False, "model": ""}


def load_cases(path: Path, *, enforce_counts: bool = True) -> list[dict[str, Any]]:
    rows = []
    seen = set()
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        row = json.loads(raw)
        required = {"id", "split", "query", "expected", "expect_clarification"}
        missing = required - set(row)
        if missing:
            raise ValueError(f"line {line_number} missing: {sorted(missing)}")
        if row["id"] in seen:
            raise ValueError(f"duplicate id: {row['id']}")
        if row["split"] not in EXPECTED_SPLITS:
            raise ValueError(f"invalid split: {row['split']}")
        seen.add(row["id"])
        rows.append(row)
    counts = Counter(row["split"] for row in rows)
    if enforce_counts and (len(rows) < 100 or counts != Counter(EXPECTED_SPLITS)):
        raise ValueError(f"constraint evaluation requires exact splits {EXPECTED_SPLITS}, got {dict(counts)}")
    if not rows:
        raise ValueError("constraint evaluation cannot be empty")
    return rows


def load_evidence_cases(path: Path) -> list[dict[str, Any]]:
    rows = []
    seen = set()
    required = {"id", "field", "operator", "value", "text", "expected_state", "expected_status"}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        row = json.loads(raw)
        missing = required - set(row)
        if missing:
            raise ValueError(f"evidence line {line_number} missing: {sorted(missing)}")
        if row["id"] in seen:
            raise ValueError(f"duplicate evidence id: {row['id']}")
        seen.add(row["id"])
        rows.append(row)
    if not rows:
        raise ValueError("constraint evidence evaluation cannot be empty")
    return rows


def evaluate(cases: list[dict[str, Any]]) -> dict[str, Any]:
    items = []
    for case in cases:
        parsed = route_follow_up(
            root=PROJECT_ROOT,
            query=case["query"],
            context=EVALUATION_CONTEXT,
            client=_OfflineClient(),
        )
        expected = [_requirement(value) for value in case["expected"]]
        expected_targets = {(item["field"], str(item["value"]).casefold()): item["operator"] for item in expected}
        actual_targets = {
            (item["field"], str(item["value"]).casefold()): item["operator"]
            for item in parsed["requirements"]
        }
        target_total = max(1, len(expected_targets))
        operator_correct = (
            1
            if not expected_targets and not actual_targets
            else sum(actual_targets.get(target) == operator for target, operator in expected_targets.items())
        )
        item = {
            "id": case["id"],
            "split": case["split"],
            "constraint_exact_match": parsed["requirements"] == expected,
            "operator_score": operator_correct / target_total,
            "clarification_correct": bool(parsed["clarification_required"]) == bool(case["expect_clarification"]),
            "expected": expected,
            "actual": parsed["requirements"],
            "actual_reason": parsed["reason"],
        }
        items.append(item)
    split_metrics = {split: _metrics([item for item in items if item["split"] == split]) for split in EXPECTED_SPLITS}
    return {
        "schema_version": 2,
        "requirement_schema_version": "capability-v1",
        "sample_count": len(items),
        "metrics": _metrics(items),
        "splits": split_metrics,
        "failures": [
            item
            for item in items
            if not item["constraint_exact_match"] or item["operator_score"] != 1 or not item["clarification_correct"]
        ],
    }


def evaluate_evidence(cases: list[dict[str, Any]]) -> dict[str, Any]:
    items = []
    for case in cases:
        state = classify_text_evidence(case["field"], case["value"], case["text"])
        status = evidence_state_status(state, case.get("operator", "eq"))
        items.append({
            "id": case["id"],
            "expected_state": case["expected_state"],
            "actual_state": state,
            "expected_status": case["expected_status"],
            "actual_status": status,
        })
    total = max(1, len(items))
    non_eligible = [item for item in items if item["expected_status"] != "matched"]
    conflicts = [item for item in items if item["expected_status"] == "unmet"]
    supported = [item for item in items if item["expected_status"] == "matched"]
    metrics = {
        "evidence_state_accuracy": round(sum(item["actual_state"] == item["expected_state"] for item in items) / total, 4),
        "false_eligible_rate": round(sum(item["actual_status"] == "matched" for item in non_eligible) / max(1, len(non_eligible)), 4),
        "hard_constraint_violation_rate": round(sum(item["actual_status"] == "matched" for item in conflicts) / max(1, len(conflicts)), 4),
        "false_rejection_rate": round(sum(item["actual_status"] == "unmet" for item in supported) / max(1, len(supported)), 4),
    }
    return {
        "sample_count": len(items),
        "metrics": metrics,
        "failures": [
            item for item in items
            if item["actual_state"] != item["expected_state"] or item["actual_status"] != item["expected_status"]
        ],
    }


def _requirement(value: str) -> dict[str, Any]:
    field, operator, expected = str(value).split(":", 2)
    if field in {"offline_capable", "network_required", "external_api_required", "api_key_required"}:
        if expected not in {"true", "false"}:
            raise ValueError(f"invalid boolean capability expectation: {value}")
        expected = expected == "true"
    return {"field": field, "operator": operator, "value": expected, "hard": True}


def _metrics(items: list[dict[str, Any]]) -> dict[str, float]:
    total = max(1, len(items))
    return {
        "constraint_exact_match_accuracy": round(sum(item["constraint_exact_match"] for item in items) / total, 4),
        "operator_accuracy": round(sum(item["operator_score"] for item in items) / total, 4),
        "clarification_accuracy": round(sum(item["clarification_correct"] for item in items) / total, 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=PROJECT_ROOT / "evals" / "constraint_parsing_cases.jsonl")
    parser.add_argument("--evidence-dataset", type=Path, default=PROJECT_ROOT / "evals" / "constraint_evidence_cases.jsonl")
    parser.add_argument("--blind-dataset", type=Path, help="独立审查提供的未见样本；不要求固定数量")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(load_cases(args.dataset))
    evidence = evaluate_evidence(load_evidence_cases(args.evidence_dataset))
    result["metrics"].update(evidence["metrics"])
    result["evidence"] = evidence
    result["failures"].extend({"kind": "evidence", **item} for item in evidence["failures"])
    if args.blind_dataset:
        blind = evaluate(load_cases(args.blind_dataset, enforce_counts=False))
        result["blind"] = blind
        result["failures"].extend({"kind": "blind", **item} for item in blind["failures"])
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 1 if result["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
