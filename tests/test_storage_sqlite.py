import json
import shutil
import sqlite3
import unittest
import uuid
from pathlib import Path

from scripts.verify_migration import _json_counts
from src.storage.sqlite_store import connect, import_json_archive, table_count


class SqliteStorageTest(unittest.TestCase):
    def test_imports_json_archive_into_sqlite(self):
        root = Path.cwd() / f".tmp-sqlite-test-{uuid.uuid4().hex}"
        try:
            _write_sample_archive(root)
            db_path = root / "data" / "github_weekly.sqlite"

            counts = import_json_archive(root, db_path)

            self.assertEqual(counts["runs"], 1)
            self.assertEqual(counts["selections"], 2)
            self.assertEqual(counts["trend_summaries"], 1)
            self.assertEqual(counts["sent_repositories"], 1)
            self.assertEqual(counts["star_history"], 2)
            with connect(db_path) as connection:
                self.assertEqual(table_count(connection, "runs"), 1)
                self.assertEqual(table_count(connection, "selections"), 2)
                self.assertEqual(table_count(connection, "repositories"), 2)
                row = connection.execute(
                    "SELECT full_name, language, stargazers_count FROM repositories WHERE full_name = ?",
                    ("owner/project",),
                ).fetchone()
                self.assertEqual(row["language"], "Python")
                self.assertEqual(row["stargazers_count"], 100)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_import_is_idempotent(self):
        root = Path.cwd() / f".tmp-sqlite-test-{uuid.uuid4().hex}"
        try:
            _write_sample_archive(root)
            db_path = root / "data" / "github_weekly.sqlite"

            import_json_archive(root, db_path)
            import_json_archive(root, db_path)

            with connect(db_path) as connection:
                self.assertEqual(table_count(connection, "runs"), 1)
                self.assertEqual(table_count(connection, "selections"), 2)
                self.assertEqual(table_count(connection, "star_history"), 2)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_json_counts_match_imported_tables(self):
        root = Path.cwd() / f".tmp-sqlite-test-{uuid.uuid4().hex}"
        try:
            _write_sample_archive(root)
            db_path = root / "data" / "github_weekly.sqlite"
            import_json_archive(root, db_path)

            expected = _json_counts(root)
            with connect(db_path) as connection:
                actual = {table: table_count(connection, table) for table in expected}

            self.assertEqual(actual, expected)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_rejects_unknown_table_count_name(self):
        with sqlite3.connect(":memory:") as connection:
            with self.assertRaises(ValueError):
                table_count(connection, "unknown")


def _write_sample_archive(root: Path) -> None:
    (root / "data" / "runs").mkdir(parents=True)
    (root / "data" / "selected").mkdir(parents=True)
    (root / "data" / "trends").mkdir(parents=True)
    (root / "data" / "state").mkdir(parents=True)

    (root / "data" / "runs" / "2026-05-03.json").write_text(
        json.dumps(
            {
                "run_date": "2026-05-03",
                "status": "success",
                "collected_count": 10,
                "selected_count": 2,
                "previously_sent_selected_count": 1,
                "kimi_used": True,
                "fallback_used": False,
                "telegram_sent": True,
                "report_path": "reports/2026-05-03.md",
                "telegram_report_url": "https://example.com/weekly/2026-05-03.html",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / "data" / "selected" / "2026-05-03.json").write_text(
        json.dumps(
            [
                {
                    "full_name": "owner/project",
                    "html_url": "https://github.com/owner/project",
                    "description": "desc",
                    "language": "Python",
                    "stargazers_count": 100,
                    "forks_count": 10,
                    "score": 0.8,
                    "star_growth": 20,
                    "trending_rank": 1,
                    "category": "AI Agent",
                    "sources": ["github_trending"],
                    "selection_reasons": ["进入 GitHub Trending 周榜第 1 位。"],
                    "security_flags": [],
                },
                {
                    "full_name": "owner/tool",
                    "html_url": "https://github.com/owner/tool",
                    "description": "tool",
                    "language": "TypeScript",
                    "stargazers_count": 50,
                    "forks_count": 5,
                    "score": 0.5,
                    "star_growth": 5,
                    "trending_rank": 0,
                    "category": "Developer Tools",
                    "sources": ["github_search"],
                    "selection_reasons": [],
                    "security_flags": ["未识别到许可证。"],
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / "data" / "trends" / "2026-05-03.json").write_text(
        json.dumps({"total_projects": 2, "trending_project_count": 1, "total_star_growth": 25}, ensure_ascii=False),
        encoding="utf-8",
    )
    (root / "data" / "state" / "sent_repos.json").write_text(
        json.dumps([{"full_name": "owner/project", "html_url": "https://github.com/owner/project"}], ensure_ascii=False),
        encoding="utf-8",
    )
    (root / "data" / "state" / "star_history.json").write_text(
        json.dumps(
            [
                {"full_name": "owner/project", "html_url": "https://github.com/owner/project", "stargazers_count": 100},
                {"full_name": "owner/tool", "html_url": "https://github.com/owner/tool", "stargazers_count": 50},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
