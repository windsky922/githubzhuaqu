import json
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.evaluate_project_match import write_fixture
from src.api.repository import ApiRepository
from src.llm.client import LlmClientError
from src.rag.corpus_enrichment import enrich_rag_corpus
from src.storage.sqlite_store import connect


class _Client:
    def __init__(self, answer="", configured=True, error=None):
        self.answer = answer
        self.configured = configured
        self.calls = 0
        self.error = error

    def status(self):
        return {"configured": self.configured, "model": "moonshot-test" if self.configured else ""}

    def chat(self, messages):
        self.calls += 1
        if self.error:
            raise self.error
        return self.answer


class RagCorpusEnrichmentTest(unittest.TestCase):
    def _fixture(self, root):
        write_fixture(root)
        repository = ApiRepository(root=root, db_path=root / "data" / "github_weekly.sqlite")
        repository.ensure_sqlite_index()
        return repository

    def test_validates_evidence_applies_chunk_and_uses_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = self._fixture(root)
            client = _Client(json.dumps({
                "deployment": {"value": "", "evidence": ""},
                "tech_stack": {"value": ["Python"], "evidence": "Python"},
                "license": {"value": "MIT", "evidence": "不存在的证据"},
                "maintenance_status": {"value": "", "evidence": ""},
                "limitations": {"value": [], "evidence": ""},
            }, ensure_ascii=False))
            first = enrich_rag_corpus(db_path=repository.db_path, root=Path.cwd(), limit=1, client=client)
            second = enrich_rag_corpus(db_path=repository.db_path, root=Path.cwd(), limit=1, client=client)
            connection = connect(repository.db_path)
            try:
                chunk = connection.execute("SELECT source_type, chunk_text FROM rag_chunks WHERE source_type='model_enrichment'").fetchone()
                stored = connection.execute("SELECT structured_json, evidence_json FROM rag_corpus_enrichments WHERE status='succeeded'").fetchone()
            finally:
                connection.close()
        self.assertEqual(first["processed_count"], 1)
        self.assertEqual(second["cached_count"], 1)
        self.assertEqual(client.calls, 1)
        self.assertEqual(chunk["source_type"], "model_enrichment")
        self.assertIn("Python", chunk["chunk_text"])
        self.assertNotIn("MIT", stored["structured_json"])

    def test_unconfigured_and_invalid_json_fail_safely(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = self._fixture(root)
            skipped = enrich_rag_corpus(db_path=repository.db_path, root=Path.cwd(), client=_Client(configured=False))
            failed = enrich_rag_corpus(db_path=repository.db_path, root=Path.cwd(), limit=1, replace=True, client=_Client("not-json"))
            timeout = enrich_rag_corpus(
                db_path=repository.db_path,
                root=Path.cwd(),
                limit=1,
                replace=True,
                client=_Client(error=LlmClientError("timeout")),
            )
        self.assertFalse(skipped["configured"])
        self.assertEqual(skipped["processed_count"], 0)
        self.assertEqual(failed["failed_count"], 1)
        self.assertEqual(timeout["failed_count"], 1)

    def test_plan_defaults_to_dry_run_and_requires_execution_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = self._fixture(root)
            plan = repository.plan_rag_corpus_enrichment({"limit": 2, "requested_by": "test"})
            check = repository.job_execution_check(plan["job_id"])
        self.assertEqual(plan["job"]["kind"], "rag_corpus_enrichment")
        self.assertTrue(plan["request"]["dry_run"])
        self.assertTrue(check["executable"])

    @unittest.skipUnless(importlib.util.find_spec("fastapi") and importlib.util.find_spec("httpx"), "缺少 API 测试依赖")
    def test_plan_route_is_additive_and_defaults_to_dry_run(self):
        from fastapi.testclient import TestClient
        from src.api.app import create_app

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._fixture(root)
            client = TestClient(create_app(root=root, db_path=root / "data" / "github_weekly.sqlite"))
            with patch.dict("os.environ", {"ADMIN_API_TOKEN": "test"}, clear=False):
                response = client.post(
                    "/v1/rag/corpus-enrichment-plan",
                    json={"limit": 1, "requested_by": "test"},
                    headers={"X-Admin-Token": "test"},
                )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["job"]["kind"], "rag_corpus_enrichment")
        self.assertTrue(response.json()["request"]["dry_run"])


if __name__ == "__main__":
    unittest.main()
