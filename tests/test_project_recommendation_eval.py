import tempfile
import unittest
from pathlib import Path

from scripts.evaluate_project_match import load_cases, write_fixture
from scripts.evaluate_project_recommendations import evaluate_recommendations
from src.api.repository import ApiRepository


class ProjectRecommendationEvaluationTest(unittest.TestCase):
    def test_fixture_reports_structured_recommendation_metrics(self):
        cases = load_cases(Path("evals/project_match_cases.jsonl"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root)
            result = evaluate_recommendations(
                ApiRepository(root=root, db_path=root / "data" / "github_weekly.sqlite"),
                cases,
            )
        self.assertEqual(result["sample_count"], len(cases))
        self.assertEqual(set(result["modes"]), {"fts5", "local-hash-v1", "hybrid"})
        for metrics in result["modes"].values():
            self.assertEqual(
                set(metrics),
                {"top_1_accuracy", "recall_at_3", "mrr_at_10", "hard_constraint_violation_rate", "no_primary_rate"},
            )
            self.assertEqual(metrics["hard_constraint_violation_rate"], 0)
            self.assertTrue(all(0 <= value <= 1 for value in metrics.values()))


if __name__ == "__main__":
    unittest.main()
