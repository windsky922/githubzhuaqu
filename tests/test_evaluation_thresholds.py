from __future__ import annotations

import unittest
from pathlib import Path

from scripts.check_evaluation_thresholds import check_results, load_config, verify_fixture_hashes


class EvaluationThresholdTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config(Path("config/evaluation-thresholds.json"))

    def test_fixture_hashes_and_frozen_baseline_are_accepted(self) -> None:
        self.assertEqual(len(verify_fixture_hashes(self.config)), 6)
        results = {
            "project_match": {"modes": {"local-hash-v1": {"recall_at_3": 0.9231, "recall_at_10": 0.9231, "mrr_at_10": 0.8878, "clarification_accuracy": 1.0, "hard_constraint_violation_rate": 0.0, "zero_hit_rate": 0.0769}, "hybrid": {"recall_at_3": 0.9231, "recall_at_10": 0.9231, "mrr_at_10": 0.8878, "clarification_accuracy": 1.0, "hard_constraint_violation_rate": 0.0, "zero_hit_rate": 0.0769}}},
            "project_recommendations": {"modes": {"local-hash-v1": {"top_1_accuracy": 0.8654, "recall_at_3": 0.9231, "mrr_at_10": 0.8878, "hard_constraint_violation_rate": 0.0, "no_primary_rate": 0.0769}, "hybrid": {"top_1_accuracy": 0.8654, "recall_at_3": 0.9231, "mrr_at_10": 0.8878, "hard_constraint_violation_rate": 0.0, "no_primary_rate": 0.0769}}},
            "follow_up_routing": {"metrics": {"route_accuracy": 1.0, "clarification_accuracy": 1.0, "rewrite_accuracy": 1.0, "candidate_scope_accuracy": 1.0, "constraint_exact_match_accuracy": 1.0, "raw_follow_up_retrieval_violation_rate": 0.0}},
            "constraint_parsing": {"metrics": {"constraint_exact_match_accuracy": 1.0, "operator_accuracy": 1.0, "clarification_accuracy": 1.0, "evidence_state_accuracy": 1.0, "false_eligible_rate": 0.0, "hard_constraint_violation_rate": 0.0, "false_rejection_rate": 0.0}},
            "claim_support": {"metrics": {"exact_accuracy": 1.0, "rejected_case_accuracy": 1.0, "false_support_rate": 0.0, "false_fact_anchor_rate": 0.0}},
            "capability_scope": {"metrics": {"exact_accuracy": 1.0, "false_scope_support_rate": 0.0}},
        }
        self.assertEqual(check_results(self.config, results), [])

    def test_regression_is_rejected(self) -> None:
        results = {"project_match": {"modes": {"local-hash-v1": {"recall_at_3": 0.0, "hard_constraint_violation_rate": 0.0}}}}
        violations = check_results(self.config, results)
        self.assertTrue(any(item.get("metric") == "modes.local-hash-v1.recall_at_3" for item in violations))
        self.assertTrue(any(item.get("reason") == "missing_result" for item in violations))

    def test_ci_runs_all_fixed_evaluators_and_threshold_checker(self) -> None:
        workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
        for script in (
            "evaluate_project_match.py",
            "evaluate_project_recommendations.py",
            "evaluate_follow_up_routing.py",
            "evaluate_constraint_parsing.py",
            "evaluate_claim_support.py",
            "evaluate_capability_scope.py",
            "check_evaluation_thresholds.py",
        ):
            self.assertIn(script, workflow)
        self.assertIn("fixed-evaluation-results-${{ github.sha }}", workflow)
