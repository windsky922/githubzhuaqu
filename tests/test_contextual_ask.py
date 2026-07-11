import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.evaluate_project_match import write_fixture
from src.api.repository import ApiRepository
from src.storage.sqlite_store import connect


class ContextualAskTest(unittest.TestCase):
    def _repository(self, root):
        write_fixture(root)
        repository = ApiRepository(root=root, db_path=root / "data" / "github_weekly.sqlite")
        repository.ensure_sqlite_index()
        return repository

    def test_short_follow_up_without_context_clarifies_without_retrieval(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = self._repository(Path(directory))
            with patch.object(repository, "_rag_explain_readonly", side_effect=AssertionError("retrieval must not run")):
                result = repository.rag_ask_contextual({"q": "继续", "mode": "hybrid"})
        self.assertEqual(result["answer_mode"], "clarification")
        self.assertTrue(result["clarification_required"])
        self.assertFalse(result["input_route"]["retrieval_performed"])
        self.assertEqual(result["recommendations"], [])
        self.assertFalse(result["answer_quality"]["applicable"])

    def test_contextual_search_does_not_persist_explanation(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = self._repository(Path(directory))
            with patch.dict(os.environ, {"KIMI_API_KEY": "", "KIMI_MODEL": ""}, clear=False):
                result = repository.rag_ask_contextual({"q": "找 Python 多 Agent 项目", "mode": "hybrid", "auto_build": True})
            connection = connect(repository.db_path)
            try:
                count = connection.execute("SELECT COUNT(*) FROM rag_explanations").fetchone()[0]
            finally:
                connection.close()
        self.assertEqual(count, 0)
        self.assertEqual(result["query"], "找 Python 多 Agent 项目")
        self.assertEqual(result["resolved_query"], "找 Python 多 Agent 项目")
        self.assertEqual(result["input_route"]["route"], "new_search")
        self.assertTrue(result["input_route"]["retrieval_performed"])
        self.assertEqual(result["source_explanation_id"], "")

    def test_resume_filters_response_to_previous_candidates(self):
        payload = {
            "q": "继续",
            "context": {
                "previous_user_goal": "多智能体编排项目",
                "candidate_repository_ids": ["eval/agent-orchestrator"],
                "primary_repository_id": "eval/agent-orchestrator",
                "mode": "hybrid",
                "resumable": True,
            },
            "mode": "hybrid",
            "auto_build": True,
        }
        with tempfile.TemporaryDirectory() as directory:
            repository = self._repository(Path(directory))
            with patch.dict(os.environ, {"KIMI_API_KEY": "", "KIMI_MODEL": ""}, clear=False):
                result = repository.rag_ask_contextual(payload)
        self.assertEqual(result["input_route"]["route"], "resume")
        self.assertEqual(result["input_route"]["candidate_scope"], "previous_candidates")
        self.assertTrue(result["recommendations"])
        self.assertEqual({item["full_name"] for item in result["recommendations"]}, {"eval/agent-orchestrator"})

    def test_stream_final_matches_normal_response(self):
        payload = {"q": "找 Python 多 Agent 项目", "mode": "hybrid", "auto_build": True, "limit": 3}
        with tempfile.TemporaryDirectory() as directory:
            repository = self._repository(Path(directory))
            with patch.dict(os.environ, {"KIMI_API_KEY": "", "KIMI_MODEL": ""}, clear=False):
                normal = repository.rag_ask_contextual(payload)
                events = list(repository.rag_ask_contextual_stream(payload))
        self.assertEqual(events[0]["event"], "meta")
        self.assertEqual(events[-1]["event"], "final")
        self.assertEqual(events[-1]["data"], normal)

    @unittest.skipUnless(importlib.util.find_spec("fastapi") and importlib.util.find_spec("httpx"), "缺少 API 测试依赖")
    def test_post_routes_are_additive_and_validate_payload(self):
        from fastapi.testclient import TestClient
        from src.api.app import create_app

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._repository(root)
            client = TestClient(create_app(root=root, db_path=root / "data" / "github_weekly.sqlite"))
            with patch.dict(os.environ, {"KIMI_API_KEY": "", "KIMI_MODEL": ""}, clear=False):
                contextual = client.post("/v1/rag/ask", json={"q": "继续"})
                stream = client.post("/v1/rag/ask/stream", json={"q": "继续"})
                legacy_get = client.get("/v1/rag/ask", params={"q": "agent workflow"})
                invalid = client.post("/v1/rag/ask", json={"q": "继续", "context": {"candidate_repository_ids": ["bad"]}})
        self.assertEqual(contextual.status_code, 200)
        self.assertEqual(contextual.json()["answer_mode"], "clarification")
        self.assertEqual(stream.status_code, 200)
        self.assertEqual([block.splitlines()[0] for block in stream.text.strip().split("\n\n")], ["event: meta", "event: final"])
        final = json.loads(stream.text.strip().split("\n\n")[-1].splitlines()[1].removeprefix("data: "))
        self.assertEqual(final, contextual.json())
        self.assertEqual(legacy_get.status_code, 200)
        self.assertNotIn("input_route", legacy_get.json())
        self.assertEqual(invalid.status_code, 422)


if __name__ == "__main__":
    unittest.main()
