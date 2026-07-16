import unittest

from src.rag.answer_quality import validate_rag_answer


class RagAnswerQualityTest(unittest.TestCase):
    def test_accepts_answer_with_known_repository_and_valid_citation(self):
        result = validate_rag_answer(
            answer="owner/agent 适合继续研究，因为证据显示它覆盖 agent workflow 场景 [1]。",
            citations=[{"index": 1, "full_name": "owner/agent"}],
            contexts=[{"metadata": {"full_name": "owner/agent"}}],
        )

        self.assertTrue(result["passed"])
        self.assertEqual(result["issues"], [])
        self.assertTrue(result["citation_validity"])
        self.assertEqual(result["evidence_relevance"], "not_applicable")
        self.assertEqual(result["claim_support"], "not_applicable")
        self.assertEqual(result["data_freshness"], "unknown")

    def test_rejects_invalid_citation_index(self):
        result = validate_rag_answer(
            answer="owner/agent 适合继续研究，因为证据显示它覆盖 agent workflow 场景 [99]。",
            citations=[{"index": 1, "full_name": "owner/agent"}],
            contexts=[{"metadata": {"full_name": "owner/agent"}}],
        )

        self.assertFalse(result["passed"])
        self.assertIn("invalid_citation:99", result["issues"])
        self.assertFalse(result["citation_validity"])

    def test_rejects_unknown_repository(self):
        result = validate_rag_answer(
            answer="unknown/repo 比 owner/agent 更值得研究，因为它覆盖更多自动化场景 [1]。",
            citations=[{"index": 1, "full_name": "owner/agent"}],
            contexts=[{"metadata": {"full_name": "owner/agent"}}],
        )

        self.assertFalse(result["passed"])
        self.assertIn("unknown_repository:unknown/repo", result["issues"])

    def test_rejects_short_answer(self):
        result = validate_rag_answer(
            answer="好 [1]",
            citations=[{"index": 1, "full_name": "owner/agent"}],
            contexts=[{"metadata": {"full_name": "owner/agent"}}],
        )

        self.assertFalse(result["passed"])
        self.assertIn("answer_too_short", result["issues"])


if __name__ == "__main__":
    unittest.main()
