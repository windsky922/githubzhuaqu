import shutil
import unittest
import uuid
from pathlib import Path

from scripts.backfill_rag_explanations import backfill_rag_explanations
from src.api.repository import ApiRepository
from tests.test_api import _write_fixture


class RagBackfillTest(unittest.TestCase):
    def test_backfills_missing_project_explanations(self):
        root = Path.cwd() / f".tmp-rag-backfill-test-{uuid.uuid4().hex}"
        try:
            _write_fixture(root)
            db_path = root / "data" / "github_weekly.sqlite"
            repository = ApiRepository(root=root, db_path=db_path)

            before = repository.rag_coverage(limit=10)
            self.assertGreaterEqual(before["gap_count"], 1)

            dry_run = backfill_rag_explanations(root=root, db_path=db_path, limit=1, dry_run=True)
            self.assertEqual(dry_run["processed_count"], 1)
            self.assertTrue(dry_run["processed"][0]["dry_run"])
            self.assertEqual(dry_run["processed"][0]["status"], "planned")

            result = backfill_rag_explanations(root=root, db_path=db_path, limit=1)
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["processed_count"], 1)
            self.assertTrue(result["processed"][0]["explanation_id"].startswith("ragx:"))

            full_name = result["processed"][0]["full_name"]
            explanations = repository.rag_explanations(repo=full_name, limit=5)
            self.assertGreaterEqual(explanations["count"], 1)
            self.assertIn(full_name, explanations["explanations"][0]["repositories"])
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
