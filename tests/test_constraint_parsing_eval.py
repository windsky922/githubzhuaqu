import unittest
from pathlib import Path

from scripts.evaluate_constraint_parsing import evaluate, load_cases


class ConstraintParsingEvaluationTest(unittest.TestCase):
    def test_dataset_splits_and_deterministic_acceptance(self):
        result = evaluate(load_cases(Path("evals/constraint_parsing_cases.jsonl")))
        self.assertEqual(result["sample_count"], 100)
        self.assertEqual(result["failures"], [])
        self.assertEqual(result["splits"]["locked"]["constraint_exact_match_accuracy"], 1)
        self.assertGreaterEqual(result["splits"]["adversarial"]["constraint_exact_match_accuracy"], 0.95)
        self.assertEqual(result["metrics"]["operator_accuracy"], 1)
        self.assertEqual(result["metrics"]["clarification_accuracy"], 1)


if __name__ == "__main__":
    unittest.main()
