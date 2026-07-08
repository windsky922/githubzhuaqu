import unittest
from pathlib import Path

from src.llm.client import LlmClientError
from src.rag.answering import answer_rag_question


class _FakeClient:
    def __init__(self, *, configured=True, answer="模型回答", error: Exception | None = None) -> None:
        self.configured = configured
        self.answer = answer
        self.error = error
        self.calls = 0

    def status(self):
        return {
            "provider": "kimi",
            "configured": self.configured,
            "model": "moonshot-test" if self.configured else "",
            "base_url_configured": True,
            "timeout_seconds": 3,
            "max_retries": 0,
        }

    def chat(self, messages):
        self.calls += 1
        if self.error:
            raise self.error
        return self.answer


def _retrieval(contexts):
    return {
        "query": "agent workflow",
        "contexts": contexts,
        "citations": [
            {
                "index": 1,
                "full_name": "owner/agent",
                "html_url": "https://github.com/owner/agent",
                "run_date": "2026-05-09",
                "chunk_id": "chunk:1",
            }
        ][: len(contexts)],
        "retrieval": {"mode": "hybrid"},
        "prompt_context": "[1] owner/agent\nagent workflow automation",
    }


class RagAnsweringTest(unittest.TestCase):
    def test_refuses_without_evidence(self):
        client = _FakeClient()

        result = answer_rag_question(
            root=Path.cwd(),
            query="agent workflow",
            retrieval=_retrieval([]),
            client=client,
        )

        self.assertEqual(result["answer_mode"], "refusal")
        self.assertEqual(result["fallback_reason"], "no_evidence")
        self.assertEqual(client.calls, 0)

    def test_unconfigured_client_uses_rule_fallback(self):
        result = answer_rag_question(
            root=Path.cwd(),
            query="agent workflow",
            retrieval=_retrieval([_context()]),
            client=_FakeClient(configured=False),
        )

        self.assertEqual(result["answer_model"], "rule:rag-ask-v1")
        self.assertEqual(result["answer_mode"], "fallback_rule")
        self.assertIn("Kimi API 未配置", result["fallback_reason"])
        self.assertIn("owner/agent", result["answer"])
        self.assertIn("[1]", result["answer"])
        self.assertTrue(result["answer_quality"]["passed"])

    def test_llm_answer_adds_citation_when_missing(self):
        client = _FakeClient(answer="可以优先研究 owner/agent。")

        result = answer_rag_question(
            root=Path.cwd(),
            query="agent workflow",
            retrieval=_retrieval([_context()]),
            client=client,
        )

        self.assertEqual(result["answer_model"], "kimi:moonshot-test")
        self.assertEqual(result["answer_mode"], "llm")
        self.assertEqual(result["fallback_reason"], "")
        self.assertIn("[1]", result["answer"])

    def test_llm_error_uses_rule_fallback(self):
        result = answer_rag_question(
            root=Path.cwd(),
            query="agent workflow",
            retrieval=_retrieval([_context()]),
            client=_FakeClient(error=LlmClientError("timeout")),
        )

        self.assertEqual(result["answer_mode"], "fallback_rule")
        self.assertEqual(result["fallback_reason"], "timeout")
        self.assertIn("owner/agent", result["answer"])

    def test_invalid_llm_citation_uses_rule_fallback(self):
        result = answer_rag_question(
            root=Path.cwd(),
            query="agent workflow",
            retrieval=_retrieval([_context()]),
            client=_FakeClient(answer="owner/agent 适合继续研究，因为它覆盖 agent workflow 场景 [99]。"),
        )

        self.assertEqual(result["answer_model"], "rule:rag-ask-v1")
        self.assertEqual(result["answer_mode"], "fallback_rule")
        self.assertIn("llm_quality_failed", result["fallback_reason"])
        self.assertIn("invalid_citation:99", result["fallback_reason"])

    def test_unknown_repository_in_llm_answer_uses_rule_fallback(self):
        result = answer_rag_question(
            root=Path.cwd(),
            query="agent workflow",
            retrieval=_retrieval([_context()]),
            client=_FakeClient(answer="unknown/repo 比 owner/agent 更值得继续研究，因为它覆盖 agent workflow 场景 [1]。"),
        )

        self.assertEqual(result["answer_mode"], "fallback_rule")
        self.assertIn("unknown_repository:unknown/repo", result["fallback_reason"])

    def test_short_llm_answer_uses_rule_fallback(self):
        result = answer_rag_question(
            root=Path.cwd(),
            query="agent workflow",
            retrieval=_retrieval([_context()]),
            client=_FakeClient(answer="好 [1]"),
        )

        self.assertEqual(result["answer_mode"], "fallback_rule")
        self.assertIn("answer_too_short", result["fallback_reason"])

    def test_missing_prompt_file_uses_rule_fallback(self):
        result = answer_rag_question(
            root=Path.cwd() / ".missing-rag-answering-root",
            query="agent workflow",
            retrieval=_retrieval([_context()]),
            client=_FakeClient(),
        )

        self.assertEqual(result["answer_mode"], "fallback_rule")
        self.assertIn("rag_ask.md", result["fallback_reason"])
        self.assertIn("owner/agent", result["answer"])


def _context():
    return {
        "chunk_id": "chunk:1",
        "text": "owner/agent 是 agent workflow automation 项目。",
        "evidence": ["agent workflow automation"],
        "metadata": {
            "full_name": "owner/agent",
            "html_url": "https://github.com/owner/agent",
            "run_date": "2026-05-09",
            "language": "Python",
            "category": "AI Agent",
            "sources": ["github_trending"],
        },
    }


if __name__ == "__main__":
    unittest.main()
