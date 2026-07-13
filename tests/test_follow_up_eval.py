import unittest
from pathlib import Path

from scripts.evaluate_follow_up_routing import evaluate, load_cases


class FollowUpEvaluationTest(unittest.TestCase):
    def test_dataset_and_deterministic_metrics(self):
        cases = load_cases(Path("evals/follow_up_cases.jsonl"))
        result = evaluate(cases)
        self.assertGreaterEqual(result["sample_count"], 60)
        self.assertEqual(result["failures"], [])
        self.assertEqual(result["metrics"]["route_accuracy"], 1)
        self.assertEqual(result["metrics"]["clarification_accuracy"], 1)
        self.assertEqual(result["metrics"]["selected_candidate_index_accuracy"], 1)
        self.assertEqual(result["metrics"]["selected_repository_accuracy"], 1)
        self.assertEqual(result["metrics"]["raw_follow_up_retrieval_violation_rate"], 0)


if __name__ == "__main__":
    unittest.main()
