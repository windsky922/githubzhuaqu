"""Check paired private blind evidence and policy without claiming independent acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BASELINE_SCHEMA_VERSION = 4
JUDGMENT_SCHEMA_VERSION = 1
POLICY_SCHEMA_VERSION = 1
MINIMUM_CASES = 20
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_METRICS = {
    "candidate_recall": "recall_at_3",
    "route_accuracy": "input_route_exact_rate",
    "answer_quality": "quality_gate_accuracy",
    "hard_constraint_violation": "hard_constraint_violation_rate",
    "data_freshness_accuracy": "data_freshness_exact_rate",
}
POLICY_FIELDS = {
    "minimum_candidate_recall",
    "minimum_data_freshness_accuracy",
    "minimum_top_1_acceptance",
    "minimum_top_1_coverage",
    "minimum_route_accuracy",
    "minimum_answer_quality",
    "maximum_hard_constraint_violation",
}
FULL_SAMPLE_METRICS = {
    "data_freshness_exact_rate",
    "hard_constraint_violation_rate",
    "input_route_exact_rate",
    "top_1_coverage_rate",
}
COMMITMENT_FIELDS = {
    "fresh_baseline_sha256",
    "fresh_judgments_sha256",
    "policy_sha256",
    "runner_sha256",
    "stale_baseline_sha256",
    "stale_judgments_sha256",
}


class BlindAcceptanceError(ValueError):
    pass


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _private_path(path: Path, *, code: str, require_file: bool = True) -> Path:
    if path.is_symlink():
        raise BlindAcceptanceError(code)
    resolved = path.resolve()
    if _is_within(resolved, PROJECT_ROOT):
        raise BlindAcceptanceError(code)
    if require_file and (not resolved.is_file() or resolved.is_symlink()):
        raise BlindAcceptanceError(code)
    return resolved


def _load_private_json(path: Path, *, code: str) -> tuple[dict[str, Any], str]:
    resolved = _private_path(path, code=code)
    try:
        payload = resolved.read_bytes()
        value = json.loads(payload.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise BlindAcceptanceError(code) from error
    if not isinstance(value, dict):
        raise BlindAcceptanceError(code)
    return value, hashlib.sha256(payload).hexdigest()


def _is_rate(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and 0 <= value <= 1


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _frozen_time(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        raise BlindAcceptanceError("blind_frozen_time_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise BlindAcceptanceError("blind_frozen_time_invalid") from error
    if parsed.tzinfo is None:
        raise BlindAcceptanceError("blind_frozen_time_invalid")
    return parsed


def _subject_commitment(subjects: list[dict[str, Any]]) -> str:
    normalized = [
        {"case_id": subject["case_id"], "primary_repository_id": subject["primary_repository_id"]}
        for subject in subjects
    ]
    payload = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_baseline(value: dict[str, Any], *, cohort: str) -> dict[str, Any]:
    if (
        value.get("schema_version") != BASELINE_SCHEMA_VERSION
        or value.get("kind") != "blind_rag_full_chain_baseline"
        or value.get("cohort") != cohort
        or value.get("threshold") is not None
    ):
        raise BlindAcceptanceError("blind_baseline_contract_invalid")
    for field in ("pack_sha256", "snapshot_sha256", "runner_sha256", "policy_sha256", "top_1_subjects_sha256"):
        if not _is_sha256(value.get(field)):
            raise BlindAcceptanceError("blind_baseline_hash_invalid")
    baseline_started_at = _frozen_time(value.get("baseline_started_at"))
    try:
        date.fromisoformat(value.get("evaluation_date"))
    except (TypeError, ValueError) as error:
        raise BlindAcceptanceError("blind_baseline_date_invalid") from error
    case_count = value.get("case_count")
    subject_count = value.get("top_1_subject_count")
    emitted_count = value.get("top_1_emitted_count")
    if (
        isinstance(case_count, bool)
        or not isinstance(case_count, int)
        or case_count < MINIMUM_CASES
        or isinstance(subject_count, bool)
        or not isinstance(subject_count, int)
        or subject_count != case_count
        or isinstance(emitted_count, bool)
        or not isinstance(emitted_count, int)
        or not 0 <= emitted_count <= subject_count
    ):
        raise BlindAcceptanceError("blind_baseline_count_invalid")
    metrics = value.get("metrics")
    denominators = value.get("metric_denominators")
    numerators = value.get("metric_numerators")
    if not isinstance(metrics, dict) or not isinstance(denominators, dict) or not isinstance(numerators, dict):
        raise BlindAcceptanceError("blind_metric_missing")
    for metric in (*REQUIRED_METRICS.values(), "top_1_coverage_rate"):
        denominator = denominators.get(metric)
        numerator = numerators.get(metric)
        if (
            not _is_rate(metrics.get(metric))
            or isinstance(denominator, bool)
            or not isinstance(denominator, int)
            or denominator <= 0
            or denominator > case_count
            or (metric in FULL_SAMPLE_METRICS and denominator != case_count)
            or isinstance(numerator, bool)
            or not isinstance(numerator, (int, float))
            or not math.isfinite(float(numerator))
            or not 0 <= float(numerator) <= denominator
        ):
            raise BlindAcceptanceError("blind_metric_missing")
        expected_rate = round(float(numerator) / denominator, 4)
        if abs(float(metrics[metric]) - expected_rate) > 0.0001:
            raise BlindAcceptanceError("blind_metric_inconsistent")
    if not isinstance(numerators["hard_constraint_violation_rate"], int):
        raise BlindAcceptanceError("blind_metric_inconsistent")
    expected_coverage = round(emitted_count / subject_count, 4)
    if abs(float(metrics["top_1_coverage_rate"]) - expected_coverage) > 0.0001:
        raise BlindAcceptanceError("blind_top_1_coverage_mismatch")
    return value


def validate_judgments(
    value: dict[str, Any],
    *,
    baseline: dict[str, Any],
    cohort: str,
) -> dict[str, int]:
    if (
        value.get("schema_version") != JUDGMENT_SCHEMA_VERSION
        or value.get("kind") != "blind_top_1_human_judgments"
        or value.get("cohort") != cohort
        or value.get("rubric_version") != "top-1-acceptance-v1"
        or value.get("review_protocol") != "independent-blind-v1"
    ):
        raise BlindAcceptanceError("human_judgment_contract_invalid")
    if value.get("status") != "frozen":
        raise BlindAcceptanceError("human_judgment_incomplete")
    reviewer_count = value.get("reviewer_count")
    if isinstance(reviewer_count, bool) or not isinstance(reviewer_count, int) or reviewer_count < 1:
        raise BlindAcceptanceError("human_judgment_incomplete")
    if not _is_sha256(value.get("reviewer_set_sha256")):
        raise BlindAcceptanceError("human_judgment_incomplete")
    _frozen_time(value.get("frozen_at"))
    for field in ("pack_sha256", "snapshot_sha256", "top_1_subjects_sha256"):
        if value.get(field) != baseline.get(field):
            raise BlindAcceptanceError("human_judgment_hash_mismatch")
    subjects = value.get("subjects")
    if not isinstance(subjects, list) or len(subjects) != baseline["top_1_subject_count"]:
        raise BlindAcceptanceError("human_judgment_incomplete")
    seen: set[str] = set()
    accepted = rejected = emitted = 0
    for subject in subjects:
        if not isinstance(subject, dict) or set(subject) != {"case_id", "primary_repository_id", "judgment"}:
            raise BlindAcceptanceError("human_judgment_contract_invalid")
        case_id = subject.get("case_id")
        primary = subject.get("primary_repository_id")
        judgment = subject.get("judgment")
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise BlindAcceptanceError("human_judgment_incomplete")
        seen.add(case_id)
        if primary is None:
            if judgment != "not_applicable":
                raise BlindAcceptanceError("human_judgment_incomplete")
            continue
        if not isinstance(primary, str) or not primary or judgment not in {"accept", "reject"}:
            raise BlindAcceptanceError("human_judgment_incomplete")
        emitted += 1
        accepted += judgment == "accept"
        rejected += judgment == "reject"
    if emitted != baseline["top_1_emitted_count"]:
        raise BlindAcceptanceError("human_judgment_primary_mismatch")
    if _subject_commitment(subjects) != baseline["top_1_subjects_sha256"]:
        raise BlindAcceptanceError("human_judgment_primary_mismatch")
    return {"accepted": accepted, "rejected": rejected, "emitted": emitted, "total": len(subjects)}


def validate_policy(value: dict[str, Any]) -> dict[str, float]:
    if (
        value.get("schema_version") != POLICY_SCHEMA_VERSION
        or value.get("kind") != "blind_rag_acceptance_policy"
        or value.get("status") != "frozen"
        or not isinstance(value.get("policy_id"), str)
        or not value["policy_id"]
    ):
        raise BlindAcceptanceError("blind_policy_invalid")
    _frozen_time(value.get("frozen_at"))
    thresholds = value.get("thresholds")
    if not isinstance(thresholds, dict) or set(thresholds) != POLICY_FIELDS:
        raise BlindAcceptanceError("blind_policy_invalid")
    if any(not _is_rate(thresholds[field]) for field in POLICY_FIELDS):
        raise BlindAcceptanceError("blind_policy_invalid")
    return {field: float(thresholds[field]) for field in sorted(POLICY_FIELDS)}


def _weighted_metric(baselines: list[dict[str, Any]], metric: str) -> float:
    denominator = sum(int(item["metric_denominators"][metric]) for item in baselines)
    numerator = sum(float(item["metric_numerators"][metric]) for item in baselines)
    return numerator / denominator


def check_acceptance(
    *,
    fresh_baseline: dict[str, Any],
    stale_baseline: dict[str, Any],
    fresh_judgments: dict[str, Any],
    stale_judgments: dict[str, Any],
    policy: dict[str, Any],
    commitments: dict[str, str],
) -> dict[str, Any]:
    fresh = validate_baseline(fresh_baseline, cohort="fresh")
    stale = validate_baseline(stale_baseline, cohort="stale")
    if fresh["pack_sha256"] == stale["pack_sha256"] or fresh["snapshot_sha256"] == stale["snapshot_sha256"]:
        raise BlindAcceptanceError("blind_fresh_stale_pair_invalid")
    if fresh["runner_sha256"] != stale["runner_sha256"]:
        raise BlindAcceptanceError("blind_runner_mismatch")
    if fresh["policy_sha256"] != stale["policy_sha256"]:
        raise BlindAcceptanceError("blind_policy_mismatch")
    fresh_counts = validate_judgments(fresh_judgments, baseline=fresh, cohort="fresh")
    stale_counts = validate_judgments(stale_judgments, baseline=stale, cohort="stale")
    thresholds = validate_policy(policy)
    policy_frozen_at = _frozen_time(policy["frozen_at"])
    if commitments.get("policy_sha256") != fresh["policy_sha256"]:
        raise BlindAcceptanceError("blind_policy_hash_mismatch")
    if any(
        not (
            policy_frozen_at <= _frozen_time(baseline["baseline_started_at"])
            <= _frozen_time(judgments["frozen_at"])
        )
        for baseline, judgments in ((fresh, fresh_judgments), (stale, stale_judgments))
    ):
        raise BlindAcceptanceError("blind_policy_not_precommitted")
    judged = fresh_counts["emitted"] + stale_counts["emitted"]
    if judged <= 0:
        raise BlindAcceptanceError("human_judgment_no_top_1")
    accepted = fresh_counts["accepted"] + stale_counts["accepted"]
    baselines = [fresh, stale]
    if set(commitments) != COMMITMENT_FIELDS or any(not _is_sha256(commitments[field]) for field in COMMITMENT_FIELDS):
        raise BlindAcceptanceError("blind_commitment_invalid")
    if commitments["runner_sha256"] != fresh["runner_sha256"]:
        raise BlindAcceptanceError("blind_runner_mismatch")
    raw_metrics = {
        "candidate_recall": _weighted_metric(baselines, "recall_at_3"),
        "top_1_acceptance": accepted / judged,
        "top_1_coverage": judged / (fresh_counts["total"] + stale_counts["total"]),
        "route_accuracy": _weighted_metric(baselines, "input_route_exact_rate"),
        "answer_quality": _weighted_metric(baselines, "quality_gate_accuracy"),
        "hard_constraint_violation": _weighted_metric(baselines, "hard_constraint_violation_rate"),
        "data_freshness_accuracy": _weighted_metric(baselines, "data_freshness_exact_rate"),
    }
    metrics = {name: round(value, 4) for name, value in raw_metrics.items()}
    comparisons = (
        ("candidate_recall", "minimum_candidate_recall", lambda actual, expected: actual < expected),
        (
            "data_freshness_accuracy",
            "minimum_data_freshness_accuracy",
            lambda actual, expected: actual < expected,
        ),
        ("top_1_acceptance", "minimum_top_1_acceptance", lambda actual, expected: actual < expected),
        ("top_1_coverage", "minimum_top_1_coverage", lambda actual, expected: actual < expected),
        ("route_accuracy", "minimum_route_accuracy", lambda actual, expected: actual < expected),
        ("answer_quality", "minimum_answer_quality", lambda actual, expected: actual < expected),
        (
            "hard_constraint_violation",
            "maximum_hard_constraint_violation",
            lambda actual, expected: actual > expected,
        ),
    )
    violations = [
        {"metric": metric, "code": f"{metric}_policy_violation"}
        for metric, threshold, failed in comparisons
        if failed(raw_metrics[metric], thresholds[threshold])
    ]
    policy_passed = not violations
    return {
        "schema_version": 1,
        "kind": "blind_rag_acceptance",
        "accepted": False,
        "policy_passed": policy_passed,
        "verification_level": "self_attested",
        "acceptance_status": "independent_attestation_required",
        "independent_evidence_verified": False,
        "evidence_complete": True,
        "case_count": fresh["case_count"] + stale["case_count"],
        "judged_top_1_count": judged,
        "metrics": metrics,
        "thresholds": thresholds,
        "violations": violations,
        "commitments": commitments,
        "cohorts": {
            "fresh": {
                "pack_sha256": fresh["pack_sha256"],
                "snapshot_sha256": fresh["snapshot_sha256"],
                "case_count": fresh["case_count"],
                "top_1_emitted_count": fresh["top_1_emitted_count"],
            },
            "stale": {
                "pack_sha256": stale["pack_sha256"],
                "snapshot_sha256": stale["snapshot_sha256"],
                "case_count": stale["case_count"],
                "top_1_emitted_count": stale["top_1_emitted_count"],
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fresh-baseline", required=True, type=Path)
    parser.add_argument("--stale-baseline", required=True, type=Path)
    parser.add_argument("--fresh-judgments", required=True, type=Path)
    parser.add_argument("--stale-judgments", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        fresh_baseline, fresh_baseline_sha = _load_private_json(args.fresh_baseline, code="blind_fresh_baseline_invalid")
        stale_baseline, stale_baseline_sha = _load_private_json(args.stale_baseline, code="blind_stale_baseline_invalid")
        fresh_judgments, fresh_judgments_sha = _load_private_json(args.fresh_judgments, code="human_fresh_judgments_invalid")
        stale_judgments, stale_judgments_sha = _load_private_json(args.stale_judgments, code="human_stale_judgments_invalid")
        policy, policy_sha = _load_private_json(args.policy, code="blind_policy_invalid")
        inputs = {
            path.resolve()
            for path in (
                args.fresh_baseline,
                args.stale_baseline,
                args.fresh_judgments,
                args.stale_judgments,
                args.policy,
            )
        }
        if len(inputs) != 5:
            raise BlindAcceptanceError("blind_acceptance_inputs_conflict")
        output = _private_path(args.output, code="blind_acceptance_output_invalid", require_file=False)
        if output in inputs:
            raise BlindAcceptanceError("blind_acceptance_output_invalid")
        summary = check_acceptance(
            fresh_baseline=fresh_baseline,
            stale_baseline=stale_baseline,
            fresh_judgments=fresh_judgments,
            stale_judgments=stale_judgments,
            policy=policy,
            commitments={
                "fresh_baseline_sha256": fresh_baseline_sha,
                "stale_baseline_sha256": stale_baseline_sha,
                "fresh_judgments_sha256": fresh_judgments_sha,
                "stale_judgments_sha256": stale_judgments_sha,
                "policy_sha256": policy_sha,
                "runner_sha256": fresh_baseline.get("runner_sha256", ""),
            },
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    except BlindAcceptanceError as error:
        print(json.dumps({"accepted": False, "policy_passed": False, "evidence_complete": False, "code": str(error)}))
        return 2
    except (OSError, UnicodeError):
        print(json.dumps({"accepted": False, "policy_passed": False, "evidence_complete": False, "code": "blind_acceptance_io_error"}))
        return 2
    except Exception:
        print(json.dumps({"accepted": False, "policy_passed": False, "evidence_complete": False, "code": "blind_acceptance_runtime_error"}))
        return 2
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if summary["policy_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
