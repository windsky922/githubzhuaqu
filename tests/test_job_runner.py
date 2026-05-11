from __future__ import annotations

import os
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from src.job_runner import run_planned_job
from src.models import RunSummary
from src.storage.sqlite_store import connect, initialize, upsert_job


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
                    "request": {"profile": "agent_development", "dry_run": True, "days_back": 3},
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
                return summary

            with patch("src.job_runner.run_weekly_report", side_effect=fake_run) as run:
                result = run_planned_job(root=root, db_path=db_path, job_id="preview:abc")

            self.assertTrue(result["executed"])
            self.assertEqual(result["status"], "succeeded")
            run.assert_called_once()
            job = _read_job(db_path, "preview:abc")
            self.assertEqual(job["status"], "succeeded")
            self.assertEqual(job["run_date"], "2026-05-11")
            self.assertIn("2026-05-11.html", job["result_json"])
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


if __name__ == "__main__":
    unittest.main()
