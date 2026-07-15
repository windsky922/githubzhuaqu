from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.audit_public_archive_content import (
    _inspect_database,
    _report_directory,
    _require_structure_token,
    _write_report,
    GitHubArchiveApi,
    enumerate_history,
    structure_scan,
)


class FakeArchiveApi:
    def __init__(self, blobs: dict[str, bytes]) -> None:
        self.blobs = blobs

    def get(self, path: str, params: dict[str, str | int] | None = None):
        if path.endswith("/commits"):
            return [{"sha": "new"}, {"sha": "old"}] if (params or {}).get("page") == 1 else []
        if path.endswith("/git/trees/new"):
            return {"tree": [{"path": "data/github_weekly.sqlite", "type": "blob", "sha": "blob-a"}]}
        if path.endswith("/git/trees/old"):
            return {"tree": [{"path": "data/github_weekly.sqlite", "type": "blob", "sha": "blob-a"}]}
        raise AssertionError(path)

    def get_bytes(self, path: str) -> bytes:
        return self.blobs[path.rsplit("/", 1)[-1]]


def _sqlite_bytes() -> bytes:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "fixture.sqlite"
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE subscription_events (created_at TEXT, query TEXT, payload TEXT)")
        connection.execute(
            "INSERT INTO subscription_events VALUES (?, ?, ?)",
            ("2026-07-15T00:00:00Z", "archive-query-canary", "archive-secret-canary"),
        )
        connection.commit()
        connection.close()
        return path.read_bytes()


class ArchiveContentAuditTest(unittest.TestCase):
    def test_github_blob_payload_is_base64_decoded(self) -> None:
        api = GitHubArchiveApi("test")
        with patch.object(api, "get", return_value={"encoding": "base64", "content": "U1FMaXRlIGZvcm1hdCAzAA=="}):
            self.assertEqual(api.get_bytes("repos/owner/repo/git/blobs/blob-a"), b"SQLite format 3\x00")

    def test_inventory_deduplicates_blob_and_tracks_commit_bounds(self) -> None:
        inventory = enumerate_history(FakeArchiveApi({"blob-a": b""}), "owner/repo", "weekly-archive")

        self.assertEqual(inventory["history_commits_scanned"], 2)
        self.assertEqual(inventory["database_blob_count"], 1)
        self.assertEqual(
            inventory["databases"],
            [{"blob_sha": "blob-a", "paths": ["data/github_weekly.sqlite"], "occurrences": 2, "first_seen_newest": "new", "last_seen_oldest": "old"}],
        )

    def test_structure_scan_reports_only_redacted_schema_statistics(self) -> None:
        canary = _sqlite_bytes()
        summary = structure_scan(FakeArchiveApi({"blob-a": canary}), enumerate_history(FakeArchiveApi({"blob-a": canary}), "owner/repo", "weekly-archive"))

        database = summary["databases"][0]
        table = database["tables"][0]
        encoded = json.dumps(summary, ensure_ascii=False)
        self.assertTrue(database["sqlite_magic"])
        self.assertEqual(database["structure_status"], "ok")
        self.assertEqual(table["table"], "subscription_events")
        self.assertEqual(table["row_count"], 1)
        self.assertEqual(table["time_ranges"][0]["minimum"], "2026-07-15T00:00:00Z")
        self.assertIn("user_input_named_field", table["risk_categories"])
        self.assertIn("notification_or_subscription_field", table["risk_categories"])
        self.assertNotIn("archive-query-canary", encoded)
        self.assertNotIn("archive-secret-canary", encoded)

    def test_invalid_database_never_exposes_parser_error(self) -> None:
        summary = _inspect_database(b"not-a-database archive-note-canary", {"blob_sha": "blob-a", "paths": [], "occurrences": 1, "first_seen_newest": "new", "last_seen_oldest": "old"})

        self.assertEqual(summary["structure_status"], "not_sqlite")
        self.assertNotIn("archive-note-canary", json.dumps(summary))

    def test_report_directory_rejects_public_or_outside_locations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "tmp"):
                _report_directory(Path(directory), "run")

    def test_structure_scan_requires_token_before_download(self) -> None:
        previous = os.environ.pop("GITHUB_TOKEN", None)
        try:
            with self.assertRaisesRegex(RuntimeError, "未下载"):
                _require_structure_token()
        finally:
            if previous is not None:
                os.environ["GITHUB_TOKEN"] = previous

    def test_report_is_written_only_under_tmp(self) -> None:
        private_root = Path.cwd() / "tmp"
        private_root.mkdir(exist_ok=True)
        test_root = Path(tempfile.mkdtemp(prefix="archive-audit-test-", dir=private_root))
        report = _write_report({"database_blob_count": 0}, test_root)
        try:
            self.assertTrue(report.is_file())
            self.assertTrue(report.resolve().is_relative_to((Path.cwd() / "tmp").resolve()))
        finally:
            shutil.rmtree(test_root, ignore_errors=True)
