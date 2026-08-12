from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import socket
import sys
import tempfile
from collections import Counter, defaultdict
from contextlib import ExitStack, contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.repository import ApiRepository
from scripts.check_blind_rag_acceptance import validate_policy


MINIMUM_BASELINE_CASES = 20
MINIMUM_METRIC_COVERAGE_RATE = 0.25
BLIND_COHORTS = frozenset({"fresh", "stale"})
ALLOWED_REQUEST_KEYS = frozenset({"q", "context"})
RUNNER_REQUEST = {"mode": "hybrid", "model": "local-hash-v1", "limit": 3, "auto_build": True}
ELIGIBILITY_LABELS = frozenset({"eligible", "unknown", "rejected"})
FRESHNESS_LABELS = frozenset({"fresh", "lagging", "stale", "unknown", "not_applicable"})
COVERAGE_LABELS = frozenset({"high", "medium", "low", "none", "unknown"})
ROUTE_LABELS = frozenset({"new_search", "resume", "refine", "clarify"})
CANDIDATE_SCOPES = frozenset({"archive", "none", "previous_candidates", "primary_candidate", "selected_candidates"})
REQUIRED_CATEGORIES = frozenset(
    {
        "unseen-readme",
        "multi-clause",
        "cross-chunk",
        "zh-negation",
        "en-negation",
        "capability-scope",
        "source-freshness",
        "freshness-required",
        "freshness-not-required",
        "no-match",
        "clarification",
        "unknown",
        "rejected",
        "comparison",
        "explanation",
        "sse",
    }
)
SNAPSHOT_DIRECTORIES = ("data/raw", "data/runs", "data/selected", "data/trends")
OFFLINE_ENVIRONMENT = (
    "KIMI_API_KEY",
    "KIMI_BASE_URL",
    "KIMI_MODEL",
    "KIMI_CANARY_ENABLED",
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "GH_SEARCH_TOKEN",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
)


class BlindBaselineError(ValueError):
    pass


class _DisabledModelClient:
    def status(self) -> dict[str, Any]:
        return {
            "provider": "disabled",
            "configured": False,
            "model": "",
            "base_url_configured": False,
            "timeout_seconds": 0,
            "max_retries": 0,
        }

    def chat(self, *_args: Any, **_kwargs: Any) -> str:
        raise AssertionError("provider_call_forbidden")

    def stream_chat(self, *_args: Any, **_kwargs: Any) -> Iterator[str]:
        raise AssertionError("provider_call_forbidden")


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _normalize_query(value: str) -> str:
    return " ".join(value.casefold().split())


def _subject_commitment(subjects: list[dict[str, Any]]) -> str:
    payload = json.dumps(subjects, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_metric_coverage(cases: list[dict[str, Any]]) -> None:
    minimum = math.ceil(len(cases) * MINIMUM_METRIC_COVERAGE_RATE)
    if sum(bool(case["expected"]["relevant_repository_ids"]) for case in cases) < minimum:
        raise BlindBaselineError("blind_pack_recall_labels_missing")
    if sum(bool(case["expected"]["candidate_eligibility"]) for case in cases) < minimum:
        raise BlindBaselineError("blind_pack_eligibility_labels_missing")
    if sum(isinstance(case["expected"].get("quality_passed"), bool) for case in cases) < minimum:
        raise BlindBaselineError("blind_pack_answer_quality_labels_missing")


def _execution_manifest_sha256() -> str:
    files = [
        Path(__file__).resolve(),
        (PROJECT_ROOT / "scripts" / "check_blind_rag_acceptance.py").resolve(),
        (PROJECT_ROOT / "requirements.txt").resolve(),
        (PROJECT_ROOT / "src" / "storage" / "schema.sql").resolve(),
    ]
    files.extend(sorted((PROJECT_ROOT / "src").rglob("*.py")))
    files.extend(sorted(path for path in (PROJECT_ROOT / "prompts").rglob("*") if path.is_file()))
    digest = hashlib.sha256()
    for path in sorted(set(files), key=lambda item: item.relative_to(PROJECT_ROOT).as_posix()):
        relative = path.relative_to(PROJECT_ROOT).as_posix().encode("utf-8")
        payload = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def _load_frozen_policy(path: Path) -> tuple[str, datetime, bytes]:
    if path.is_symlink():
        raise BlindBaselineError("blind_policy_invalid")
    resolved = path.resolve()
    if _is_within(resolved, PROJECT_ROOT) or not resolved.is_file():
        raise BlindBaselineError("blind_policy_invalid")
    try:
        payload = resolved.read_bytes()
        value = json.loads(payload.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise BlindBaselineError("blind_policy_invalid") from error
    if not isinstance(value, dict):
        raise BlindBaselineError("blind_policy_invalid")
    try:
        validate_policy(value)
        frozen_at = datetime.fromisoformat(value["frozen_at"])
    except (TypeError, ValueError) as error:
        raise BlindBaselineError("blind_policy_invalid") from error
    return hashlib.sha256(payload).hexdigest(), frozen_at, payload


def _validate_cohort(cases: list[dict[str, Any]], cohort: str) -> None:
    if cohort not in BLIND_COHORTS:
        raise BlindBaselineError("blind_cohort_invalid")
    source_labels = {
        case["expected"]["data_freshness"]
        for case in cases
        if "source-freshness" in case["categories"]
    }
    if source_labels != {cohort}:
        raise BlindBaselineError("blind_cohort_freshness_mismatch")


def _load_blind_pack(path: Path, *, minimum_cases: int) -> tuple[list[dict[str, Any]], str]:
    if path.is_symlink():
        raise BlindBaselineError("blind_pack_invalid")
    resolved = path.resolve()
    if _is_within(resolved, PROJECT_ROOT):
        raise BlindBaselineError("blind_pack_must_be_outside_repository")
    if not resolved.is_file() or resolved.is_symlink():
        raise BlindBaselineError("blind_pack_invalid")

    payload = resolved.read_bytes()
    try:
        text = payload.decode("utf-8")
    except UnicodeError as error:
        raise BlindBaselineError("blind_pack_encoding_invalid") from error
    cases: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    queries: set[str] = set()
    evaluation_dates: set[str] = set()
    categories: set[str] = set()
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        if not raw_line.strip():
            continue
        try:
            case = json.loads(raw_line)
        except json.JSONDecodeError as error:
            raise BlindBaselineError(f"blind_pack_json_invalid_line_{line_number}") from error
        _validate_case(case, line_number)
        identifier = case["id"]
        normalized_query = _normalize_query(case["request"]["q"])
        if identifier in identifiers:
            raise BlindBaselineError(f"blind_pack_duplicate_id_line_{line_number}")
        if normalized_query in queries:
            raise BlindBaselineError(f"blind_pack_duplicate_query_line_{line_number}")
        identifiers.add(identifier)
        queries.add(normalized_query)
        evaluation_dates.add(case["evaluation_date"])
        categories.update(case["categories"])
        cases.append(case)

    if len(cases) < minimum_cases:
        raise BlindBaselineError("blind_pack_insufficient_cases")
    if len(evaluation_dates) != 1:
        raise BlindBaselineError("blind_pack_evaluation_date_mismatch")
    if not REQUIRED_CATEGORIES.issubset(categories):
        raise BlindBaselineError("blind_pack_category_coverage_incomplete")
    _validate_metric_coverage(cases)
    return cases, hashlib.sha256(payload).hexdigest()


def load_blind_cases(path: Path, *, minimum_cases: int = MINIMUM_BASELINE_CASES) -> list[dict[str, Any]]:
    return _load_blind_pack(path, minimum_cases=minimum_cases)[0]


def _validate_case(case: Any, line_number: int) -> None:
    if not isinstance(case, dict) or case.get("schema_version") != 2:
        raise BlindBaselineError(f"blind_pack_schema_invalid_line_{line_number}")
    if not isinstance(case.get("id"), str) or not case["id"].strip():
        raise BlindBaselineError(f"blind_pack_id_invalid_line_{line_number}")
    try:
        date.fromisoformat(case.get("evaluation_date"))
    except (TypeError, ValueError) as error:
        raise BlindBaselineError(f"blind_pack_evaluation_date_invalid_line_{line_number}") from error

    request = case.get("request")
    if not isinstance(request, dict) or not isinstance(request.get("q"), str) or not request["q"].strip():
        raise BlindBaselineError(f"blind_pack_request_invalid_line_{line_number}")
    if not set(request).issubset(ALLOWED_REQUEST_KEYS) or (
        "context" in request and not isinstance(request["context"], dict)
    ):
        raise BlindBaselineError(f"blind_pack_request_fields_invalid_line_{line_number}")
    expected = case.get("expected")
    if not isinstance(expected, dict):
        raise BlindBaselineError(f"blind_pack_expected_invalid_line_{line_number}")
    freshness_required = expected.get("freshness_required")
    if not isinstance(expected.get("answer_mode"), str) or (
        freshness_required is not None and not isinstance(freshness_required, bool)
    ):
        raise BlindBaselineError(f"blind_pack_expected_contract_invalid_line_{line_number}")
    if expected.get("data_freshness") not in FRESHNESS_LABELS or expected.get("evidence_coverage") not in COVERAGE_LABELS:
        raise BlindBaselineError(f"blind_pack_expected_state_invalid_line_{line_number}")

    input_route = expected.get("input_route")
    if not isinstance(input_route, dict):
        raise BlindBaselineError(f"blind_pack_expected_route_invalid_line_{line_number}")
    if input_route.get("route") not in ROUTE_LABELS or input_route.get("candidate_scope") not in CANDIDATE_SCOPES:
        raise BlindBaselineError(f"blind_pack_expected_route_invalid_line_{line_number}")
    if not isinstance(input_route.get("clarification_required"), bool):
        raise BlindBaselineError(f"blind_pack_expected_route_invalid_line_{line_number}")
    selected_ids = input_route.get("selected_repository_ids")
    requirements = input_route.get("requirements")
    if not isinstance(selected_ids, list) or any(not isinstance(value, str) or not value for value in selected_ids):
        raise BlindBaselineError(f"blind_pack_expected_route_invalid_line_{line_number}")
    if not isinstance(requirements, list) or any(not isinstance(value, dict) for value in requirements):
        raise BlindBaselineError(f"blind_pack_expected_route_invalid_line_{line_number}")

    for field in ("acceptable_primary_ids", "relevant_repository_ids"):
        values = expected.get(field)
        if not isinstance(values, list) or any(not isinstance(value, str) or not value for value in values):
            raise BlindBaselineError(f"blind_pack_expected_labels_invalid_line_{line_number}")
        if len(values) != len(set(values)):
            raise BlindBaselineError(f"blind_pack_expected_labels_invalid_line_{line_number}")
    eligibility = expected.get("candidate_eligibility")
    if not isinstance(eligibility, dict) or any(
        not isinstance(repository_id, str) or not repository_id or label not in ELIGIBILITY_LABELS
        for repository_id, label in eligibility.items()
    ):
        raise BlindBaselineError(f"blind_pack_eligibility_labels_invalid_line_{line_number}")
    if expected.get("quality_passed") is not None and not isinstance(expected.get("quality_passed"), bool):
        raise BlindBaselineError(f"blind_pack_quality_label_invalid_line_{line_number}")

    categories = case.get("categories")
    if (
        not isinstance(categories, list)
        or not categories
        or len(categories) != len(set(categories))
        or any(category not in REQUIRED_CATEGORIES for category in categories)
    ):
        raise BlindBaselineError(f"blind_pack_categories_invalid_line_{line_number}")

    category_set = set(categories)
    acceptable_primary = expected["acceptable_primary_ids"]
    if any(eligibility.get(repository_id) != "eligible" for repository_id in acceptable_primary):
        raise BlindBaselineError(f"blind_pack_primary_labels_inconsistent_line_{line_number}")
    invalid_category_contract = (
        ("freshness-required" in category_set and freshness_required is not True)
        or ("freshness-not-required" in category_set and freshness_required is not False)
        or {"freshness-required", "freshness-not-required"}.issubset(category_set)
        or ("source-freshness" in category_set and expected["data_freshness"] == "not_applicable")
        or (
            "clarification" in category_set
            and (input_route["route"] != "clarify" or input_route["clarification_required"] is not True)
        )
        or ("no-match" in category_set and (expected["answer_mode"] != "no_match" or bool(acceptable_primary)))
        or ("unknown" in category_set and "unknown" not in eligibility.values())
        or ("rejected" in category_set and "rejected" not in eligibility.values())
    )
    if invalid_category_contract:
        raise BlindBaselineError(f"blind_pack_category_contract_invalid_line_{line_number}")


def snapshot_tree_sha256(root: Path) -> str:
    if root.is_symlink():
        raise BlindBaselineError("snapshot_root_invalid")
    resolved = root.resolve()
    if _is_within(resolved, PROJECT_ROOT) or not resolved.is_dir() or resolved.is_symlink():
        raise BlindBaselineError("snapshot_root_invalid")
    files: list[Path] = []
    for directory in SNAPSHOT_DIRECTORIES:
        base = resolved / directory
        if not base.exists():
            continue
        if base.is_symlink() or not base.is_dir():
            raise BlindBaselineError("snapshot_tree_invalid")
        for candidate in base.rglob("*"):
            if candidate.is_symlink():
                raise BlindBaselineError("snapshot_tree_invalid")
            if candidate.is_file() and candidate.suffix.lower() == ".json":
                files.append(candidate)
    if not files:
        raise BlindBaselineError("snapshot_tree_empty")

    digest = hashlib.sha256()
    for candidate in sorted(files, key=lambda value: value.relative_to(resolved).as_posix()):
        relative = candidate.relative_to(resolved).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        payload = candidate.read_bytes()
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def validate_output_path(output: Path, *, pack: Path, snapshot_root: Path) -> Path:
    if output.is_symlink():
        raise BlindBaselineError("blind_output_invalid")
    resolved = output.resolve()
    if resolved == pack.resolve():
        raise BlindBaselineError("blind_output_conflicts_with_pack")
    if _is_within(resolved, snapshot_root.resolve()):
        raise BlindBaselineError("blind_output_inside_snapshot")
    if _is_within(resolved, PROJECT_ROOT):
        raise BlindBaselineError("blind_output_must_be_outside_repository")
    return resolved


@contextmanager
def offline_snapshot_environment(snapshot_root: Path, evaluation_date: date) -> Iterator[_DisabledModelClient]:
    old_values = {name: os.environ.get(name) for name in (*OFFLINE_ENVIRONMENT, "GITHUB_WEEKLY_SNAPSHOT_ROOT")}
    for name in OFFLINE_ENVIRONMENT:
        os.environ[name] = ""
    os.environ["GITHUB_WEEKLY_SNAPSHOT_ROOT"] = str(snapshot_root.resolve())

    class _FrozenDate(date):
        @classmethod
        def today(cls) -> date:
            return cls(evaluation_date.year, evaluation_date.month, evaluation_date.day)

    client = _DisabledModelClient()

    def deny_network(*_args: Any, **_kwargs: Any) -> None:
        raise BlindBaselineError("blind_network_disabled")

    try:
        with ExitStack() as stack:
            stack.enter_context(patch("src.rag.freshness.date", _FrozenDate))
            stack.enter_context(patch("src.rag.answering.KimiChatClient", return_value=client))
            stack.enter_context(patch("socket.create_connection", deny_network))
            stack.enter_context(patch("socket.getaddrinfo", deny_network))
            for method in ("connect", "connect_ex", "sendto", "sendmsg"):
                if hasattr(socket.socket, method):
                    stack.enter_context(patch.object(socket.socket, method, deny_network))
            yield client
    finally:
        for name, value in old_values.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _recommendations(response: dict[str, Any]) -> list[dict[str, Any]]:
    value = response.get("recommendations")
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _confirmed_primary(response: dict[str, Any]) -> str | None:
    quality = response.get("answer_quality") if isinstance(response.get("answer_quality"), dict) else {}
    if quality.get("passed") is not True:
        return None
    if response.get("freshness_required") and quality.get("data_freshness") != "fresh":
        return None
    for recommendation in _recommendations(response):
        if recommendation.get("eligibility") == "eligible" and recommendation.get("current_eligible") is True:
            return str(recommendation.get("full_name") or "") or None
    return None


def _valid_stream_contract(events: list[dict[str, Any]]) -> bool:
    names = [event.get("event") for event in events]
    return bool(names) and names[0] == "meta" and names[-1] == "final" and names.count("final") == 1 and all(
        name == "delta" for name in names[1:-1]
    )


def _rate(values: list[bool | float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def evaluate_blind_cases(
    repository: ApiRepository,
    cases: list[dict[str, Any]],
    *,
    model_client: _DisabledModelClient | None = None,
    subject_collector: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    client = model_client or _DisabledModelClient()
    checks: dict[str, list[bool | float]] = defaultdict(list)
    failures: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    coverage: dict[str, list[bool]] = defaultdict(list)
    hard_violations: list[bool] = []
    subjects: list[dict[str, Any]] = []

    for case in cases:
        request = {**case["request"], **RUNNER_REQUEST}
        expected = case["expected"]
        categories.update(case["categories"])
        response = repository.rag_ask_contextual(request, router_client=client)
        events = list(repository.rag_ask_contextual_stream(request, router_client=client))
        final = events[-1].get("data") if events and isinstance(events[-1].get("data"), dict) else {}
        recommendations = _recommendations(response)
        returned = [str(item.get("full_name") or "") for item in recommendations]
        primary = _confirmed_primary(response)
        subjects.append({"case_id": case["id"], "primary_repository_id": primary})
        acceptable_primary = expected["acceptable_primary_ids"]
        relevant = expected["relevant_repository_ids"]
        eligibility_labels = expected["candidate_eligibility"]

        route = response.get("input_route") if isinstance(response.get("input_route"), dict) else {}
        expected_route = expected["input_route"]
        actual_route = {
            "route": route.get("route"),
            "candidate_scope": route.get("candidate_scope"),
            "clarification_required": bool(response.get("clarification_required")),
            "selected_repository_ids": route.get("selected_repository_ids") or [],
            "requirements": route.get("requirements") or [],
        }
        actual_freshness = response.get("freshness") if isinstance(response.get("freshness"), dict) else {}
        raw_coverage = str(response.get("evidence_coverage") or "unknown")
        coverage_label = raw_coverage if raw_coverage in COVERAGE_LABELS else "unknown"
        case_checks = {
            "answer_mode": response.get("answer_mode") == expected["answer_mode"],
            "freshness_required": response.get("freshness_required") == expected["freshness_required"],
            "data_freshness": (actual_freshness.get("data_freshness") or "not_applicable") == expected["data_freshness"],
            "evidence_coverage": coverage_label == expected["evidence_coverage"],
            "input_route": actual_route == expected_route,
            "primary": primary in acceptable_primary if acceptable_primary else primary is None,
            "sse_final_parity": response == final,
            "stream_contract": _valid_stream_contract(events),
        }
        if relevant:
            relevant_set = set(relevant)
            recall_at_3 = len(relevant_set.intersection(returned[:3])) / len(relevant_set)
            checks["recall_at_3"].append(recall_at_3)
            if recall_at_3 < 1.0:
                failures["recall_at_3"] += 1
        if expected.get("quality_passed") is not None:
            quality = response.get("answer_quality") if isinstance(response.get("answer_quality"), dict) else {}
            case_checks["quality_gate"] = quality.get("passed") is expected["quality_passed"]
        returned_eligibility = {
            str(recommendation.get("full_name") or ""): recommendation.get("eligibility")
            for recommendation in recommendations
        }
        for repository_id, label in eligibility_labels.items():
            passed = returned_eligibility.get(repository_id) == label
            checks["candidate_eligibility"].append(passed)
            if not passed:
                failures["candidate_eligibility"] += 1

        hard_violation = primary is not None and eligibility_labels.get(primary) == "rejected"
        hard_violations.append(hard_violation)
        if hard_violation:
            failures["hard_constraint_violation"] += 1
        for name, passed in case_checks.items():
            checks[name].append(passed)
            if not passed:
                failures[name] += 1
        coverage[coverage_label].append(case_checks["primary"])

    if subject_collector is not None:
        subject_collector.extend(subjects)
    emitted_primary_count = sum(subject["primary_repository_id"] is not None for subject in subjects)
    metric_numerators = {
        "answer_mode_accuracy": sum(checks["answer_mode"]),
        "freshness_required_exact_rate": sum(checks["freshness_required"]),
        "data_freshness_exact_rate": sum(checks["data_freshness"]),
        "evidence_coverage_exact_rate": sum(checks["evidence_coverage"]),
        "input_route_exact_rate": sum(checks["input_route"]),
        "primary_accuracy": sum(checks["primary"]),
        "recall_at_3": sum(checks["recall_at_3"]),
        "candidate_eligibility_accuracy": sum(checks["candidate_eligibility"]),
        "quality_gate_accuracy": sum(checks["quality_gate"]),
        "hard_constraint_violation_rate": sum(hard_violations),
        "sse_final_parity_rate": sum(checks["sse_final_parity"]),
        "stream_contract_rate": sum(checks["stream_contract"]),
        "top_1_coverage_rate": emitted_primary_count,
    }
    return {
        "case_count": len(cases),
        "top_1_subject_count": len(subjects),
        "top_1_emitted_count": emitted_primary_count,
        "top_1_subjects_sha256": _subject_commitment(subjects),
        "category_counts": dict(sorted(categories.items())),
        "metrics": {
            "answer_mode_accuracy": _rate(checks["answer_mode"]),
            "freshness_required_exact_rate": _rate(checks["freshness_required"]),
            "data_freshness_exact_rate": _rate(checks["data_freshness"]),
            "evidence_coverage_exact_rate": _rate(checks["evidence_coverage"]),
            "input_route_exact_rate": _rate(checks["input_route"]),
            "primary_accuracy": _rate(checks["primary"]),
            "recall_at_3": _rate(checks["recall_at_3"]),
            "candidate_eligibility_accuracy": _rate(checks["candidate_eligibility"]),
            "quality_gate_accuracy": _rate(checks["quality_gate"]),
            "hard_constraint_violation_rate": _rate(hard_violations),
            "sse_final_parity_rate": _rate(checks["sse_final_parity"]),
            "stream_contract_rate": _rate(checks["stream_contract"]),
            "top_1_coverage_rate": round(emitted_primary_count / len(subjects), 4) if subjects else None,
        },
        "metric_denominators": {
            "answer_mode_accuracy": len(checks["answer_mode"]),
            "freshness_required_exact_rate": len(checks["freshness_required"]),
            "data_freshness_exact_rate": len(checks["data_freshness"]),
            "evidence_coverage_exact_rate": len(checks["evidence_coverage"]),
            "input_route_exact_rate": len(checks["input_route"]),
            "primary_accuracy": len(checks["primary"]),
            "recall_at_3": len(checks["recall_at_3"]),
            "candidate_eligibility_accuracy": len(checks["candidate_eligibility"]),
            "quality_gate_accuracy": len(checks["quality_gate"]),
            "hard_constraint_violation_rate": len(hard_violations),
            "sse_final_parity_rate": len(checks["sse_final_parity"]),
            "stream_contract_rate": len(checks["stream_contract"]),
            "top_1_coverage_rate": len(subjects),
        },
        "metric_numerators": metric_numerators,
        "coverage_buckets": {
            name: {"case_count": len(values), "primary_accuracy": _rate(values)}
            for name, values in sorted(coverage.items())
        },
        "failure_category_counts": dict(sorted(failures.items())),
    }


def build_judgment_template(report: dict[str, Any], subjects: list[dict[str, Any]]) -> dict[str, Any]:
    if _subject_commitment(subjects) != report.get("top_1_subjects_sha256"):
        raise BlindBaselineError("blind_judgment_subject_mismatch")
    return {
        "schema_version": 1,
        "kind": "blind_top_1_human_judgments",
        "cohort": report["cohort"],
        "pack_sha256": report["pack_sha256"],
        "snapshot_sha256": report["snapshot_sha256"],
        "top_1_subjects_sha256": report["top_1_subjects_sha256"],
        "rubric_version": "top-1-acceptance-v1",
        "review_protocol": "independent-blind-v1",
        "status": "draft",
        "reviewer_count": 0,
        "reviewer_set_sha256": "",
        "frozen_at": "",
        "subjects": [
            {**subject, "judgment": "pending"}
            for subject in subjects
        ],
    }


def run_baseline(
    *,
    pack: Path,
    snapshot_root: Path,
    cohort: str,
    policy: Path,
    subject_collector: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    policy_hash, policy_frozen_at, policy_payload = _load_frozen_policy(policy)
    execution_hash = _execution_manifest_sha256()
    baseline_started_at = datetime.now(timezone.utc)
    if policy_frozen_at > baseline_started_at:
        raise BlindBaselineError("blind_policy_not_precommitted")
    cases, pack_hash = _load_blind_pack(pack, minimum_cases=MINIMUM_BASELINE_CASES)
    _validate_cohort(cases, cohort)
    snapshot_hash = snapshot_tree_sha256(snapshot_root)
    evaluation_date = date.fromisoformat(cases[0]["evaluation_date"])
    try:
        with tempfile.TemporaryDirectory(prefix="blind-rag-") as directory:
            db_path = Path(directory) / "blind.sqlite"
            with offline_snapshot_environment(snapshot_root, evaluation_date) as client:
                repository = ApiRepository(db_path=db_path)
                evaluation_kwargs: dict[str, Any] = {"model_client": client}
                if subject_collector is not None:
                    evaluation_kwargs["subject_collector"] = subject_collector
                result = evaluate_blind_cases(repository, cases, **evaluation_kwargs)
    finally:
        try:
            current_pack_hash = hashlib.sha256(pack.resolve().read_bytes()).hexdigest()
        except OSError:
            current_pack_hash = ""
        if current_pack_hash != pack_hash:
            raise BlindBaselineError("blind_pack_mutated_during_baseline")
        if snapshot_tree_sha256(snapshot_root) != snapshot_hash:
            raise BlindBaselineError("snapshot_mutated_during_baseline")
        if policy.resolve().read_bytes() != policy_payload:
            raise BlindBaselineError("blind_policy_mutated_during_baseline")
        if _execution_manifest_sha256() != execution_hash:
            raise BlindBaselineError("blind_execution_manifest_mutated_during_baseline")
    return {
        "schema_version": 4,
        "kind": "blind_rag_full_chain_baseline",
        "cohort": cohort,
        "pack_sha256": pack_hash,
        "snapshot_sha256": snapshot_hash,
        "runner_sha256": execution_hash,
        "policy_sha256": policy_hash,
        "baseline_started_at": baseline_started_at.isoformat(),
        "evaluation_date": evaluation_date.isoformat(),
        **result,
        "threshold": None,
        "note": "baseline only; private frozen labels were not used as CI thresholds",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="运行私有冻结样本的完整 RAG blind baseline")
    parser.add_argument("--blind-pack", required=True, type=Path)
    parser.add_argument("--snapshot-root", required=True, type=Path)
    parser.add_argument("--cohort", required=True, choices=sorted(BLIND_COHORTS))
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--judgment-template", type=Path)
    args = parser.parse_args()
    try:
        output = validate_output_path(args.output, pack=args.blind_pack, snapshot_root=args.snapshot_root)
        judgment_output = (
            validate_output_path(args.judgment_template, pack=args.blind_pack, snapshot_root=args.snapshot_root)
            if args.judgment_template
            else None
        )
        if judgment_output == output:
            raise BlindBaselineError("blind_output_conflict")
        subjects: list[dict[str, Any]] | None = [] if judgment_output else None
        report = run_baseline(
            pack=args.blind_pack,
            snapshot_root=args.snapshot_root,
            cohort=args.cohort,
            policy=args.policy,
            subject_collector=subjects,
        )
        output = validate_output_path(output, pack=args.blind_pack, snapshot_root=args.snapshot_root)
        template = build_judgment_template(report, subjects or []) if judgment_output else None
        writes: list[tuple[Path, dict[str, Any]]] = [(output, report)]
        if judgment_output and template:
            judgment_output = validate_output_path(
                judgment_output,
                pack=args.blind_pack,
                snapshot_root=args.snapshot_root,
            )
            writes.append((judgment_output, template))
        created: list[Path] = []
        try:
            for target, payload in writes:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("x", encoding="utf-8") as handle:
                    created.append(target)
                    handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        except Exception:
            for target in created:
                target.unlink(missing_ok=True)
            raise
    except (OSError, UnicodeError):
        raise SystemExit("blind_baseline_io_error") from None
    except BlindBaselineError as error:
        raise SystemExit(str(error)) from None
    except ValueError:
        raise SystemExit("blind_baseline_runtime_error") from None
    except Exception:
        raise SystemExit("blind_baseline_runtime_error") from None
    print(
        json.dumps(
            {
                "kind": report["kind"],
                "cohort": report["cohort"],
                "pack_sha256": report["pack_sha256"],
                "snapshot_sha256": report["snapshot_sha256"],
                "runner_sha256": report["runner_sha256"],
                "policy_sha256": report["policy_sha256"],
                "evaluation_date": report["evaluation_date"],
                "case_count": report["case_count"],
                "metrics": report["metrics"],
                "failure_category_counts": report["failure_category_counts"],
                "top_1_subject_count": report["top_1_subject_count"],
                "top_1_emitted_count": report["top_1_emitted_count"],
                "threshold": report["threshold"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
