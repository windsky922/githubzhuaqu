from __future__ import annotations

import os
import json
import shutil
import unittest
import uuid
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.create_planned_job import _truthy
from scripts.plan_dev_context_index import _truthy as _dev_context_truthy
from scripts.plan_dev_context_index import main as plan_dev_context_index_main
from scripts.run_planned_job import _job_id_from_file, main as run_planned_job_script_main
from src.job_runner import run_planned_job
from src.models import RunSummary
from src.storage.sqlite_store import connect, initialize, upsert_job
from tests.test_api import _write_fixture


class JobRunnerTest(unittest.TestCase):
    def test_runs_planned_dry_run_job_and_marks_succeeded(self) -> None:
        root = Path.cwd() / f".tmp-job-runner-{uuid.uuid4().hex}"
        try:
            db_path = root / "data" / "github_weekly.sqlite"
            _write_job(
                db_path,
                {
                    "job_id": "preview:abc",
                    "kind": "weekly_report",
                    "status": "planned",
                    "submitted_at": "2026-05-11T00:00:00Z",
                    "request": {
                        "profile": "agent_development",
                        "language": "Python",
                        "category": "AI Agent",
                        "query": "workflow",
                        "limit": 8,
                        "subscription_id": "sub:test",
                        "subscription_name": "Agent 开发订阅",
                        "dry_run": True,
                        "days_back": 3,
                    },
                },
            )
            summary = RunSummary(
                run_date="2026-05-11",
                status="success",
                selected_count=8,
                collected_count=30,
                report_path="reports/2026-05-11.md",
                telegram_report_url="https://example.com/weekly/2026-05-11.html",
            )

            def fake_run(**kwargs):
                self.assertEqual(kwargs["days_back"], 3)
                self.assertTrue(kwargs["skip_telegram_send"])
                self.assertEqual(os.getenv("INTEREST_PROFILE"), "agent_development")
                self.assertEqual(os.getenv("INTEREST_LANGUAGE"), "Python")
                self.assertEqual(os.getenv("INTEREST_CATEGORY"), "AI Agent")
                self.assertEqual(os.getenv("INTEREST_QUERY"), "workflow")
                self.assertEqual(os.getenv("MAX_PROJECTS"), "8")
                return summary

            with patch("src.job_runner.run_weekly_report", side_effect=fake_run) as run:
                result = run_planned_job(root=root, db_path=db_path, job_id="preview:abc")

            self.assertTrue(result["executed"])
            self.assertEqual(result["status"], "succeeded")
            self.assertEqual(result["result"]["request_context"]["subscription_id"], "sub:test")
            self.assertEqual(result["result"]["request_context"]["language"], "Python")
            self.assertEqual(result["result"]["request_context"]["limit"], 8)
            run.assert_called_once()
            job = _read_job(db_path, "preview:abc")
            self.assertEqual(job["status"], "succeeded")
            self.assertEqual(job["run_date"], "2026-05-11")
            self.assertIn("2026-05-11.html", job["result_json"])
            event_types = _read_job_event_types(db_path, "preview:abc")
            self.assertIn("runner_started", event_types)
            self.assertIn("runner_finished", event_types)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_marks_job_failed_when_runner_raises(self) -> None:
        root = Path.cwd() / f".tmp-job-runner-{uuid.uuid4().hex}"
        try:
            db_path = root / "data" / "github_weekly.sqlite"
            _write_job(
                db_path,
                {
                    "job_id": "preview:failed",
                    "kind": "weekly_report",
                    "status": "planned",
                    "submitted_at": "2026-05-11T00:00:00Z",
                    "request": {"dry_run": True},
                },
            )

            with patch("src.job_runner.run_weekly_report", side_effect=RuntimeError("boom")):
                result = run_planned_job(root=root, db_path=db_path, job_id="preview:failed")

            self.assertTrue(result["executed"])
            self.assertEqual(result["status"], "failed")
            job = _read_job(db_path, "preview:failed")
            self.assertEqual(job["status"], "failed")
            self.assertEqual(job["error"], "boom")
            event_types = _read_job_event_types(db_path, "preview:failed")
            self.assertIn("runner_started", event_types)
            self.assertIn("runner_failed", event_types)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_runs_planned_rag_search_evaluation_job(self) -> None:
        root = Path.cwd() / f".tmp-job-runner-rag-eval-{uuid.uuid4().hex}"
        try:
            _write_fixture(root)
            db_path = root / "data" / "github_weekly.sqlite"
            _write_job(
                db_path,
                {
                    "job_id": "rag-search-eval-plan:test",
                    "kind": "rag_search_evaluation",
                    "status": "planned",
                    "submitted_at": "2026-05-11T00:00:00Z",
                    "request": {
                        "queries": ["agent workflow", "python automation"],
                        "language": "Python",
                        "limit": 5,
                        "model": "local-hash-v1",
                        "auto_build": True,
                        "confirm_execution": True,
                    },
                },
            )

            result = run_planned_job(root=root, db_path=db_path, job_id="rag-search-eval-plan:test")

            self.assertTrue(result["executed"])
            self.assertEqual(result["status"], "succeeded")
            self.assertEqual(result["result"]["sample_count"], 2)
            self.assertIn("hybrid", result["result"]["aggregate"]["modes"])
            self.assertEqual(result["result"]["request_context"]["language"], "Python")
            self.assertEqual(result["result"]["request_context"]["queries"], ["agent workflow", "python automation"])
            job = _read_job(db_path, "rag-search-eval-plan:test")
            self.assertEqual(job["status"], "succeeded")
            job_result = json.loads(job["result_json"])
            self.assertEqual(job_result["sample_count"], 2)
            self.assertIn("runner_finished", _read_job_event_types(db_path, "rag-search-eval-plan:test"))
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_runs_planned_dev_context_index_job(self) -> None:
        root = Path.cwd() / f".tmp-job-runner-dev-context-{uuid.uuid4().hex}"
        try:
            _write_fixture(root)
            db_path = root / "data" / "github_weekly.sqlite"
            _write_job(
                db_path,
                {
                    "job_id": "dev-context-index-plan:test",
                    "kind": "dev_context_index",
                    "status": "planned",
                    "submitted_at": "2026-06-17T00:00:00Z",
                    "request": {
                        "run_checks": False,
                        "replace": False,
                        "max_command_chars": 120000,
                        "confirm_execution": True,
                        "requested_by": "test",
                        "trigger_source": "test",
                    },
                },
            )

            result = run_planned_job(root=root, db_path=db_path, job_id="dev-context-index-plan:test")

            self.assertTrue(result["executed"])
            self.assertEqual(result["status"], "succeeded")
            self.assertTrue(result["result"]["run_id"].startswith("dev-context:"))
            self.assertGreater(result["result"]["chunk_count"], 0)
            self.assertEqual(result["result"]["embedding_count"], result["result"]["chunk_count"])
            self.assertFalse(result["result"]["run_checks"])
            job = _read_job(db_path, "dev-context-index-plan:test")
            self.assertEqual(job["status"], "succeeded")
            job_result = json.loads(job["result_json"])
            self.assertEqual(job_result["run_id"], result["result"]["run_id"])
            self.assertIn("runner_finished", _read_job_event_types(db_path, "dev-context-index-plan:test"))
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_returns_not_found_when_no_planned_job_exists(self) -> None:
        root = Path.cwd() / f".tmp-job-runner-{uuid.uuid4().hex}"
        try:
            result = run_planned_job(root=root, db_path=root / "data" / "github_weekly.sqlite")
            self.assertFalse(result["executed"])
            self.assertEqual(result["status"], "not_found")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_job_file_helper_reads_created_job_id(self) -> None:
        root = Path.cwd() / f".tmp-job-runner-{uuid.uuid4().hex}"
        try:
            root.mkdir(parents=True)
            path = root / "job.json"
            path.write_text(json.dumps({"job_id": "preview:file"}), encoding="utf-8")
            self.assertEqual(_job_id_from_file(path), "preview:file")
            self.assertEqual(_job_id_from_file(root / "missing.json"), "")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_create_planned_job_truthy_parser(self) -> None:
        self.assertTrue(_truthy("true"))
        self.assertTrue(_truthy("1"))
        self.assertFalse(_truthy("false"))
        self.assertTrue(_dev_context_truthy("yes"))
        self.assertFalse(_dev_context_truthy("off"))

    def test_run_planned_job_script_rejects_invalid_job_file(self) -> None:
        root = Path.cwd() / f".tmp-job-runner-{uuid.uuid4().hex}"
        try:
            root.mkdir(parents=True)
            bad_file = root / "bad.json"
            bad_file.write_text("{}", encoding="utf-8")
            with patch("sys.argv", ["run_planned_job.py", "--job-file", str(bad_file)]):
                with redirect_stderr(StringIO()):
                    self.assertEqual(run_planned_job_script_main(), 1)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_plan_dev_context_index_script_writes_job_file(self) -> None:
        root = Path.cwd() / f".tmp-dev-context-plan-script-{uuid.uuid4().hex}"
        try:
            _write_fixture(root)
            output = root / "dev-context-job.json"
            with patch(
                "sys.argv",
                [
                    "plan_dev_context_index.py",
                    "--root",
                    str(root),
                    "--run-checks",
                    "false",
                    "--requested-by",
                    "test",
                    "--output",
                    str(output),
                ],
            ):
                with redirect_stdout(StringIO()):
                    self.assertEqual(plan_dev_context_index_main(), 0)

            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(data["planned_job_created"])
            self.assertTrue(data["job_id"].startswith("dev-context-index-plan:"))
            self.assertEqual(data["job"]["kind"], "dev_context_index")
            self.assertFalse(data["request"]["run_checks"])
        finally:
            shutil.rmtree(root, ignore_errors=True)


def _write_job(db_path: Path, data: dict) -> None:
    connection = connect(db_path)
    try:
        initialize(connection)
        upsert_job(connection, data)
        connection.commit()
    finally:
        connection.close()


def _read_job(db_path: Path, job_id: str):
    connection = connect(db_path)
    try:
        return connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    finally:
        connection.close()


def _read_job_event_types(db_path: Path, job_id: str) -> list[str]:
    connection = connect(db_path)
    try:
        rows = connection.execute(
            "SELECT event_type FROM job_events WHERE job_id = ? ORDER BY created_at ASC",
            (job_id,),
        ).fetchall()
        return [str(row["event_type"]) for row in rows]
    finally:
        connection.close()


if __name__ == "__main__":
    unittest.main()
