import json
import shutil
import unittest
import uuid
from pathlib import Path

from scripts.build_pages import build_pages
from src.storage.sqlite_store import connect, initialize


PROJECT_KEYS = {
    "run_date",
    "full_name",
    "html_url",
    "description",
    "category",
    "language",
    "stargazers_count",
    "forks_count",
    "star_growth",
    "score",
    "sources",
    "trending_rank",
    "selection_reasons",
    "security_flags",
    "report_url",
}

RUN_KEYS = {
    "run_date",
    "status",
    "report_url",
    "selected_count",
    "collected_count",
    "previously_sent_selected_count",
    "readme_fetched_count",
    "star_history_updated_count",
    "kimi_used",
    "fallback_used",
    "telegram_sent",
    "telegram_report_url",
    "collector_error_count",
    "top_languages",
    "top_categories",
    "total_star_growth",
    "trending_project_count",
    "summary_points",
}

SQLITE_COLUMNS = {
    "runs": {
        "run_date",
        "status",
        "collected_count",
        "selected_count",
        "previously_sent_selected_count",
        "kimi_used",
        "fallback_used",
        "telegram_sent",
        "report_path",
        "telegram_report_url",
        "payload_json",
    },
    "repositories": {
        "full_name",
        "html_url",
        "description",
        "language",
        "stargazers_count",
        "forks_count",
        "license_name",
        "archived",
        "fork",
        "pushed_at",
        "payload_json",
    },
    "selections": {
        "run_date",
        "full_name",
        "position",
        "score",
        "star_growth",
        "trending_rank",
        "category",
        "sources_json",
        "selection_reasons_json",
        "security_flags_json",
        "payload_json",
    },
    "trend_summaries": {
        "run_date",
        "total_projects",
        "trending_project_count",
        "total_star_growth",
        "payload_json",
    },
    "sent_repositories": {
        "full_name",
        "html_url",
        "first_sent_at",
        "payload_json",
    },
    "star_history": {
        "full_name",
        "html_url",
        "stargazers_count",
        "last_seen_at",
        "payload_json",
    },
    "migration_meta": {
        "key",
        "value",
    },
}


class DataContractsTest(unittest.TestCase):
    def test_public_json_contracts_are_stable(self):
        root = Path.cwd() / f".tmp-contract-test-{uuid.uuid4().hex}"
        try:
            _write_public_json_fixture(root)

            build_pages(root)

            projects = json.loads((root / "docs" / "projects.json").read_text(encoding="utf-8"))
            runs = json.loads((root / "docs" / "runs.json").read_text(encoding="utf-8"))
            self.assertEqual(projects["schema_version"], 1)
            self.assertEqual(runs["schema_version"], 1)
            self.assertEqual(set(projects["projects"][0]), PROJECT_KEYS)
            self.assertEqual(set(runs["runs"][0]), RUN_KEYS)
            self.assertIsInstance(projects["projects"][0]["selection_reasons"], list)
            self.assertIsInstance(projects["projects"][0]["security_flags"], list)
            self.assertIsInstance(runs["runs"][0]["summary_points"], list)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_sqlite_schema_contract_is_stable(self):
        root = Path.cwd() / f".tmp-contract-test-{uuid.uuid4().hex}"
        try:
            db_path = root / "data" / "github_weekly.sqlite"
            connection = connect(db_path)
            try:
                initialize(connection)
                for table, expected_columns in SQLITE_COLUMNS.items():
                    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
                    actual_columns = {row["name"] for row in rows}
                    self.assertEqual(actual_columns, expected_columns, table)
            finally:
                connection.close()
        finally:
            shutil.rmtree(root, ignore_errors=True)


def _write_public_json_fixture(root: Path) -> None:
    (root / "reports").mkdir(parents=True)
    (root / "data" / "runs").mkdir(parents=True)
    (root / "data" / "trends").mkdir(parents=True)
    (root / "data" / "selected").mkdir(parents=True)
    (root / "reports" / "2026-05-03.md").write_text("# 周报", encoding="utf-8")
    (root / "data" / "runs" / "2026-05-03.json").write_text(
        json.dumps(
            {
                "run_date": "2026-05-03",
                "status": "success",
                "selected_count": 1,
                "collected_count": 2,
                "previously_sent_selected_count": 0,
                "readme_fetched_count": 1,
                "star_history_updated_count": 2,
                "kimi_used": True,
                "fallback_used": False,
                "telegram_sent": True,
                "telegram_report_url": "https://example.com/weekly/2026-05-03.html",
                "collector_errors": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / "data" / "trends" / "2026-05-03.json").write_text(
        json.dumps(
            {
                "top_languages": [{"name": "Python", "count": 1}],
                "top_categories": [{"name": "AI Agent", "count": 1}],
                "total_star_growth": 10,
                "trending_project_count": 1,
                "summary_points": ["Python 是本期主要语言。"],
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
                    "category": "AI Agent",
                    "language": "Python",
                    "stargazers_count": 100,
                    "forks_count": 10,
                    "star_growth": 10,
                    "score": 0.9,
                    "sources": ["github_trending"],
                    "trending_rank": 1,
                    "selection_reasons": ["进入 GitHub Trending 周榜第 1 位。"],
                    "security_flags": [],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
