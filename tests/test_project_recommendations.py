import unittest

from src.rag.project_recommendations import build_project_recommendations


class ProjectRecommendationsTest(unittest.TestCase):
    def test_groups_chunks_maps_evidence_and_orders_by_eligibility(self):
        contexts = [
            _context("owner/rejected", "chunk:r1", 10, language="Go"),
            _context("owner/eligible", "chunk:e1", 4, language="Python", source_type="readme"),
            _context("owner/eligible", "chunk:e2", 3, language="Python", source_type="description"),
            _context("owner/unknown", "chunk:u1", 9, language=""),
        ]
        citations = [
            {"index": 1, "full_name": "owner/rejected", "chunk_id": "chunk:r1"},
            {"index": 2, "full_name": "owner/eligible", "chunk_id": "chunk:e1"},
            {"index": 3, "full_name": "owner/eligible", "chunk_id": "chunk:e2"},
            {"index": 4, "full_name": "owner/unknown", "chunk_id": "chunk:u1"},
        ]

        result = build_project_recommendations(
            contexts=contexts,
            citations=citations,
            constraints={"language": "Python", "source": "github_trending"},
        )

        self.assertEqual([item["full_name"] for item in result], ["owner/eligible", "owner/unknown", "owner/rejected"])
        self.assertEqual([item["eligibility"] for item in result], ["eligible", "unknown", "rejected"])
        self.assertEqual([item["rank"] for item in result], [1, 2, 3])
        self.assertEqual(result[0]["match_score"], 0.4)
        self.assertEqual(result[0]["citation_indexes"], [2, 3])
        self.assertEqual(result[0]["evidence_chunk_ids"], ["chunk:e1", "chunk:e2"])
        self.assertEqual(result[0]["matched_requirements"], ["语言=Python", "来源=github_trending"])
        self.assertEqual(result[2]["unmet_requirements"], ["语言=Python"])
        self.assertIn("无法验证显式筛选：语言=Python", result[1]["reasons"])

    def test_all_zero_scores_preserve_first_repository_order(self):
        result = build_project_recommendations(
            contexts=[
                _context("owner/first", "chunk:1", 0),
                _context("owner/first", "chunk:2", 0),
                _context("owner/second", "chunk:3", 0),
            ],
            citations=[],
        )

        self.assertEqual([item["full_name"] for item in result], ["owner/first", "owner/second"])
        self.assertEqual([item["match_score"] for item in result], [1.0, 0.5])
        self.assertTrue(all(item["eligibility"] == "eligible" for item in result))

    def test_empty_contexts_return_no_recommendations(self):
        self.assertEqual(build_project_recommendations(contexts=[], citations=[], constraints={"language": "Python"}), [])

    def test_verified_requirements_add_unknown_state_and_evidence(self):
        result = build_project_recommendations(
            contexts=[_context("owner/project", "chunk:1", 1)],
            citations=[],
            requirements=[{"field": "deployment", "operator": "eq", "value": "local", "hard": True}],
            requirement_verification={
                "owner/project": {
                    "matched_requirements": [],
                    "unmet_requirements": [],
                    "unknown_requirements": ["部署方式=local"],
                    "evidence_chunk_ids": ["chunk:deployment"],
                }
            },
        )
        self.assertEqual(result[0]["eligibility"], "unknown")
        self.assertEqual(result[0]["unknown_requirements"], ["部署方式=local"])
        self.assertEqual(result[0]["evidence_chunk_ids"], ["chunk:1", "chunk:deployment"])


def _context(full_name, chunk_id, score, *, language="Python", source_type="identity"):
    return {
        "chunk_id": chunk_id,
        "score": score,
        "text": full_name,
        "metadata": {
            "full_name": full_name,
            "language": language,
            "category": "AI Agent",
            "sources": ["github_trending"],
            "source_type": source_type,
        },
    }


if __name__ == "__main__":
    unittest.main()
