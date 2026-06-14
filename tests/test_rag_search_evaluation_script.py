from __future__ import annotations

import shutil
import unittest
import uuid
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from scripts import run_rag_search_evaluation
from src.api.repository import ApiRepository
from tests.test_api import _write_fixture


class RagSearchEvaluationScriptTest(unittest.TestCase):
    def test_script_persists_rag_search_evaluation_job(self) -> None:
        root = Path.cwd() / f".tmp-rag-evaluation-script-{uuid.uuid4().hex}"
        try:
            _write_fixture(root)
            db_path = root / "data" / "github_weekly.sqlite"

            output = StringIO()
            with redirect_stdout(output):
                exit_code = run_rag_search_evaluation.main(
                    [
                        "--root",
                        str(root),
                        "--db",
                        str(db_path),
                        "--query",
                        "agent workflow",
                        "--query",
                        "python automation",
                        "--language",
                        "Python",
                        "--limit",
                        "5",
                        "--auto-build",
                        "true",
                        "--requested-by",
                        "unit-test",
                    ]
                )

            repository = ApiRepository(root=root, db_path=db_path)
            jobs = repository.jobs(kind="rag_search_evaluation", status="succeeded", limit=5)
            self.assertEqual(exit_code, 0)
            self.assertIn('"status": "succeeded"', output.getvalue())
            self.assertEqual(jobs["count"], 1)
            self.assertEqual(jobs["jobs"][0]["kind"], "rag_search_evaluation")
            self.assertEqual(jobs["jobs"][0]["request"]["requested_by"], "unit-test")
            self.assertEqual(jobs["jobs"][0]["result"]["sample_count"], 2)
            events = repository.job_events(jobs["jobs"][0]["job_id"])
            self.assertIn("runner_finished", [event["event_type"] for event in events["events"]])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_queries_from_args_deduplicates_multiple_sources(self) -> None:
        queries = run_rag_search_evaluation._queries_from_args(
            ["Agent Workflow", "agent workflow"],
            "python automation; rag search\npython automation",
        )

        self.assertEqual(queries, ["Agent Workflow", "python automation", "rag search"])


if __name__ == "__main__":
    unittest.main()
