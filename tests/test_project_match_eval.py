import json
import tempfile
import unittest
from pathlib import Path

from scripts.evaluate_project_match import evaluate, load_cases, write_fixture
from src.api.repository import ApiRepository


class ProjectMatchEvaluationTest(unittest.TestCase):
    def test_dataset_has_unique_valid_chinese_cases(self):
        cases = load_cases(Path("evals/project_match_cases.jsonl"))
        self.assertGreaterEqual(len(cases), 50)
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        self.assertTrue(all(any("\u4e00" <= char <= "\u9fff" for char in case["query"]) for case in cases))

    def test_fixture_baseline_reports_all_required_metrics(self):
        cases = load_cases(Path("evals/project_match_cases.jsonl"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root)
            result = evaluate(ApiRepository(root=root, db_path=root / "data" / "github_weekly.sqlite"), cases)
        self.assertEqual(result["sample_count"], len(cases))
        self.assertEqual(set(result["modes"]), {"fts5", "local-hash-v1", "hybrid"})
        for metrics in result["modes"].values():
            self.assertEqual(
                set(metrics),
                {
                    "recall_at_3",
                    "recall_at_10",
                    "mrr_at_10",
                    "hard_constraint_violation_rate",
                    "zero_hit_rate",
                    "clarification_accuracy",
                },
            )
            self.assertTrue(all(0 <= value <= 1 for value in metrics.values()))


if __name__ == "__main__":
    unittest.main()
