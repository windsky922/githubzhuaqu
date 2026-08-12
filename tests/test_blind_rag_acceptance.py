from __future__ import annotations

import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts.check_blind_rag_acceptance import (
    BlindAcceptanceError,
    PROJECT_ROOT,
    _private_path,
    _subject_commitment,
    check_acceptance,
    main,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _subjects(cohort: str, *, emitted: int = 10) -> list[dict]:
    return [
        {
            "case_id": f"{cohort}-case-{index}",
            "primary_repository_id": f"private/{cohort}-{index}" if index < emitted else None,
        }
        for index in range(20)
    ]


def _baseline(cohort: str, *, emitted: int = 10, metric: float = 1.0) -> tuple[dict, list[dict]]:
    subjects = _subjects(cohort, emitted=emitted)
    metrics = {
        "recall_at_3": metric,
        "input_route_exact_rate": metric,
        "quality_gate_accuracy": metric,
        "hard_constraint_violation_rate": 0.0,
        "data_freshness_exact_rate": metric,
        "top_1_coverage_rate": round(emitted / len(subjects), 4),
    }
    return (
        {
            "schema_version": 4,
            "kind": "blind_rag_full_chain_baseline",
            "cohort": cohort,
            "pack_sha256": _sha(f"{cohort}-pack"),
            "snapshot_sha256": _sha(f"{cohort}-snapshot"),
            "runner_sha256": _sha("runner"),
            "policy_sha256": _sha("policy"),
            "baseline_started_at": "2026-08-12T09:00:00+08:00",
            "evaluation_date": "2026-08-12",
            "case_count": len(subjects),
            "top_1_subject_count": len(subjects),
            "top_1_emitted_count": emitted,
            "top_1_subjects_sha256": _subject_commitment(subjects),
            "metrics": metrics,
            "metric_denominators": {name: len(subjects) for name in metrics},
            "metric_numerators": {
                name: (0 if name == "hard_constraint_violation_rate" else metrics[name] * len(subjects))
                for name in metrics
            },
            "threshold": None,
        },
        subjects,
    )


def _judgments(baseline: dict, subjects: list[dict], *, accepted: int = 8) -> dict:
    judged = 0
    rows = []
    for subject in subjects:
        if subject["primary_repository_id"] is None:
            judgment = "not_applicable"
        else:
            judgment = "accept" if judged < accepted else "reject"
            judged += 1
        rows.append({**subject, "judgment": judgment})
    return {
        "schema_version": 1,
        "kind": "blind_top_1_human_judgments",
        "cohort": baseline["cohort"],
        "pack_sha256": baseline["pack_sha256"],
        "snapshot_sha256": baseline["snapshot_sha256"],
        "top_1_subjects_sha256": baseline["top_1_subjects_sha256"],
        "rubric_version": "top-1-acceptance-v1",
        "review_protocol": "independent-blind-v1",
        "status": "frozen",
        "reviewer_count": 1,
        "reviewer_set_sha256": _sha("independent-reviewer"),
        "frozen_at": "2026-08-12T12:00:00+08:00",
        "subjects": rows,
    }


def _policy(*, minimum_top_1_acceptance: float = 0.8, minimum_data_freshness_accuracy: float = 0.9) -> dict:
    return {
        "schema_version": 1,
        "kind": "blind_rag_acceptance_policy",
        "policy_id": "p1-d-private-v1",
        "status": "frozen",
        "frozen_at": "2026-08-12T08:00:00+08:00",
        "thresholds": {
            "minimum_candidate_recall": 0.9,
            "minimum_data_freshness_accuracy": minimum_data_freshness_accuracy,
            "minimum_top_1_acceptance": minimum_top_1_acceptance,
            "minimum_top_1_coverage": 0.5,
            "minimum_route_accuracy": 0.9,
            "minimum_answer_quality": 0.9,
            "maximum_hard_constraint_violation": 0.0,
        },
    }


def _commitments() -> dict[str, str]:
    return {
        "fresh_baseline_sha256": _sha("fresh-baseline"),
        "fresh_judgments_sha256": _sha("fresh-judgments"),
        "policy_sha256": _sha("policy"),
        "runner_sha256": _sha("runner"),
        "stale_baseline_sha256": _sha("stale-baseline"),
        "stale_judgments_sha256": _sha("stale-judgments"),
    }


def _check(*, policy: dict | None = None, fresh_emitted: int = 10, stale_emitted: int = 10) -> dict:
    fresh, fresh_subjects = _baseline("fresh", emitted=fresh_emitted)
    stale, stale_subjects = _baseline("stale", emitted=stale_emitted)
    return check_acceptance(
        fresh_baseline=fresh,
        stale_baseline=stale,
        fresh_judgments=_judgments(fresh, fresh_subjects, accepted=8),
        stale_judgments=_judgments(stale, stale_subjects, accepted=8),
        policy=policy or _policy(),
        commitments=_commitments(),
    )


class BlindRagAcceptanceTest(unittest.TestCase):
    def test_complete_pair_reports_required_metrics_without_private_subjects(self):
        summary = _check()
        self.assertFalse(summary["accepted"])
        self.assertTrue(summary["policy_passed"])
        self.assertEqual(summary["verification_level"], "self_attested")
        self.assertEqual(summary["acceptance_status"], "independent_attestation_required")
        self.assertFalse(summary["independent_evidence_verified"])
        self.assertTrue(summary["evidence_complete"])
        self.assertEqual(summary["case_count"], 40)
        self.assertEqual(summary["judged_top_1_count"], 20)
        self.assertEqual(
            set(summary["metrics"]),
            {
                "candidate_recall",
                "top_1_acceptance",
                "top_1_coverage",
                "route_accuracy",
                "answer_quality",
                "hard_constraint_violation",
                "data_freshness_accuracy",
            },
        )
        self.assertEqual(summary["metrics"]["top_1_acceptance"], 0.8)
        rendered = json.dumps(summary, ensure_ascii=False)
        for secret in ("fresh-case-0", "private/fresh-0", "independent-reviewer"):
            self.assertNotIn(secret, rendered)

    def test_complete_evidence_below_frozen_policy_is_not_accepted(self):
        summary = _check(policy=_policy(minimum_top_1_acceptance=0.9))
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["policy_passed"])
        self.assertTrue(summary["evidence_complete"])
        self.assertEqual(summary["violations"], [{"metric": "top_1_acceptance", "code": "top_1_acceptance_policy_violation"}])

    def test_data_freshness_is_a_policy_gate(self):
        fresh, fresh_subjects = _baseline("fresh")
        stale, stale_subjects = _baseline("stale")
        for baseline in (fresh, stale):
            baseline["metrics"]["data_freshness_exact_rate"] = 0.0
            baseline["metric_numerators"]["data_freshness_exact_rate"] = 0
        summary = check_acceptance(
            fresh_baseline=fresh,
            stale_baseline=stale,
            fresh_judgments=_judgments(fresh, fresh_subjects),
            stale_judgments=_judgments(stale, stale_subjects),
            policy=_policy(),
            commitments=_commitments(),
        )
        self.assertFalse(summary["policy_passed"])
        self.assertEqual(
            summary["violations"],
            [{"metric": "data_freshness_accuracy", "code": "data_freshness_accuracy_policy_violation"}],
        )

    def test_policy_must_be_frozen_before_human_judgments(self):
        policy = _policy()
        policy["frozen_at"] = "2026-08-12T13:00:00+08:00"
        with self.assertRaisesRegex(BlindAcceptanceError, "policy_not_precommitted"):
            _check(policy=policy)

    def test_fresh_and_stale_must_use_distinct_pack_and_snapshot(self):
        fresh, fresh_subjects = _baseline("fresh")
        stale, stale_subjects = _baseline("stale")
        stale["pack_sha256"] = fresh["pack_sha256"]
        with self.assertRaisesRegex(BlindAcceptanceError, "fresh_stale_pair_invalid"):
            check_acceptance(
                fresh_baseline=fresh,
                stale_baseline=stale,
                fresh_judgments=_judgments(fresh, fresh_subjects),
                stale_judgments=_judgments(stale, stale_subjects),
                policy=_policy(),
                commitments={},
            )

    def test_pending_or_changed_human_subjects_fail_closed(self):
        fresh, fresh_subjects = _baseline("fresh")
        stale, stale_subjects = _baseline("stale")
        pending = _judgments(fresh, fresh_subjects)
        pending["subjects"][0]["judgment"] = "pending"
        with self.assertRaisesRegex(BlindAcceptanceError, "human_judgment_incomplete"):
            check_acceptance(
                fresh_baseline=fresh,
                stale_baseline=stale,
                fresh_judgments=pending,
                stale_judgments=_judgments(stale, stale_subjects),
                policy=_policy(),
                commitments={},
            )

        changed = _judgments(fresh, fresh_subjects)
        changed["subjects"][0]["primary_repository_id"] = "private/changed"
        with self.assertRaisesRegex(BlindAcceptanceError, "human_judgment_primary_mismatch"):
            check_acceptance(
                fresh_baseline=fresh,
                stale_baseline=stale,
                fresh_judgments=changed,
                stale_judgments=_judgments(stale, stale_subjects),
                policy=_policy(),
                commitments={},
            )

    def test_zero_metric_denominator_and_no_emitted_top_1_fail_closed(self):
        fresh, fresh_subjects = _baseline("fresh")
        stale, stale_subjects = _baseline("stale")
        fresh["metric_denominators"]["recall_at_3"] = 0
        with self.assertRaisesRegex(BlindAcceptanceError, "blind_metric_missing"):
            check_acceptance(
                fresh_baseline=fresh,
                stale_baseline=stale,
                fresh_judgments=_judgments(fresh, fresh_subjects),
                stale_judgments=_judgments(stale, stale_subjects),
                policy=_policy(),
                commitments={},
            )

        with self.assertRaisesRegex(BlindAcceptanceError, "human_judgment_no_top_1"):
            _check(fresh_emitted=0, stale_emitted=0)

    def test_metric_denominators_counts_and_dates_fail_closed(self):
        fresh, fresh_subjects = _baseline("fresh")
        stale, stale_subjects = _baseline("stale")
        cases = (
            ("oversized", "blind_metric_missing", lambda value: value["metric_denominators"].__setitem__("recall_at_3", 21)),
            ("full-sample", "blind_metric_missing", lambda value: value["metric_denominators"].__setitem__("input_route_exact_rate", 19)),
            ("rounded-hard", "blind_metric_inconsistent", lambda value: value["metric_numerators"].__setitem__("hard_constraint_violation_rate", 1)),
            ("subject-type", "blind_baseline_count_invalid", lambda value: value.__setitem__("top_1_subject_count", 20.0)),
            ("date", "blind_baseline_date_invalid", lambda value: value.__setitem__("evaluation_date", "not-a-date")),
        )
        for name, code, mutate in cases:
            changed = json.loads(json.dumps(fresh))
            mutate(changed)
            with self.subTest(name=name), self.assertRaisesRegex(BlindAcceptanceError, code):
                check_acceptance(
                    fresh_baseline=changed,
                    stale_baseline=stale,
                    fresh_judgments=_judgments(fresh, fresh_subjects),
                    stale_judgments=_judgments(stale, stale_subjects),
                    policy=_policy(),
                    commitments=_commitments(),
                )

    def test_inputs_and_outputs_must_stay_outside_repository(self):
        with self.assertRaisesRegex(BlindAcceptanceError, "private_path"):
            _private_path(PROJECT_ROOT / "README.md", code="private_path")
        with tempfile.TemporaryDirectory() as directory:
            external = Path(directory) / "future.json"
            self.assertEqual(
                _private_path(external, code="private_path", require_file=False),
                external.resolve(),
            )

    def test_cli_exit_codes_distinguish_pass_policy_failure_and_incomplete_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fresh, fresh_subjects = _baseline("fresh")
            stale, stale_subjects = _baseline("stale")
            paths = {
                "fresh_baseline": root / "fresh-baseline.json",
                "stale_baseline": root / "stale-baseline.json",
                "fresh_judgments": root / "fresh-judgments.json",
                "stale_judgments": root / "stale-judgments.json",
                "policy": root / "policy.json",
            }
            payloads = {
                "fresh_baseline": fresh,
                "stale_baseline": stale,
                "fresh_judgments": _judgments(fresh, fresh_subjects),
                "stale_judgments": _judgments(stale, stale_subjects),
                "policy": _policy(),
            }

            def write_inputs() -> None:
                policy_payload = json.dumps(payloads["policy"])
                policy_sha = hashlib.sha256(policy_payload.encode("utf-8")).hexdigest()
                payloads["fresh_baseline"]["policy_sha256"] = policy_sha
                payloads["stale_baseline"]["policy_sha256"] = policy_sha
                for name, path in paths.items():
                    rendered = policy_payload if name == "policy" else json.dumps(payloads[name])
                    path.write_text(rendered, encoding="utf-8")

            write_inputs()

            def run_cli(output: Path) -> tuple[int, str]:
                argv = ["check_blind_rag_acceptance.py"]
                for name, path in paths.items():
                    argv.extend([f"--{name.replace('_', '-')}", str(path)])
                argv.extend(["--output", str(output)])
                stream = io.StringIO()
                with patch.object(sys, "argv", argv), redirect_stdout(stream):
                    code = main()
                return code, stream.getvalue()

            passed_output = root / "passed.json"
            code, stdout = run_cli(passed_output)
            self.assertEqual(code, 0)
            self.assertTrue(passed_output.is_file())
            self.assertNotIn("private/fresh-0", stdout)
            passed_payload = json.loads(passed_output.read_text(encoding="utf-8"))
            self.assertFalse(passed_payload["accepted"])
            self.assertTrue(passed_payload["policy_passed"])
            self.assertEqual(passed_payload["verification_level"], "self_attested")
            self.assertNotIn("private/fresh-0", json.dumps(passed_payload))

            payloads["policy"] = _policy(minimum_top_1_acceptance=0.9)
            write_inputs()
            failed_output = root / "failed.json"
            code, _ = run_cli(failed_output)
            self.assertEqual(code, 1)
            self.assertTrue(failed_output.is_file())

            payloads["fresh_judgments"]["subjects"][0]["judgment"] = "pending"
            paths["fresh_judgments"].write_text(json.dumps(payloads["fresh_judgments"]), encoding="utf-8")
            incomplete_output = root / "incomplete.json"
            code, stdout = run_cli(incomplete_output)
            self.assertEqual(code, 2)
            self.assertFalse(incomplete_output.exists())
            self.assertIn("human_judgment_incomplete", stdout)


if __name__ == "__main__":
    unittest.main()
