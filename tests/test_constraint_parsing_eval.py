import unittest
from pathlib import Path

from scripts.evaluate_constraint_parsing import evaluate, evaluate_evidence, load_cases, load_evidence_cases


class ConstraintParsingEvaluationTest(unittest.TestCase):
    def test_dataset_splits_and_deterministic_acceptance(self):
        result = evaluate(load_cases(Path("evals/constraint_parsing_cases.jsonl")))
        self.assertEqual(result["sample_count"], 100)
        self.assertEqual(result["failures"], [])
        self.assertEqual(result["splits"]["locked"]["constraint_exact_match_accuracy"], 1)
        self.assertGreaterEqual(result["splits"]["adversarial"]["constraint_exact_match_accuracy"], 0.95)
        self.assertEqual(result["metrics"]["operator_accuracy"], 1)
        self.assertEqual(result["metrics"]["clarification_accuracy"], 1)

    def test_sentence_evidence_semantics_have_no_false_eligible_result(self):
        result = evaluate_evidence(load_evidence_cases(Path("evals/constraint_evidence_cases.jsonl")))
        self.assertEqual(result["sample_count"], 36)
        self.assertEqual(result["failures"], [])
        self.assertEqual(result["metrics"]["evidence_state_accuracy"], 1)
        self.assertEqual(result["metrics"]["false_eligible_rate"], 0)
        self.assertEqual(result["metrics"]["hard_constraint_violation_rate"], 0)


if __name__ == "__main__":
    unittest.main()
