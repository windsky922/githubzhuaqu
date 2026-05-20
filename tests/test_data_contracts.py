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
    "readme_summary",
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
    "security_score",
    "security_level",
    "quality_flags",
    "quality_score",
    "quality_level",
    "report_url",
}

RUN_KEYS = {
    "run_date",
    "status",
    "run_schema_version",
    "report_url",
    "selected_count",
    "collected_count",
    "previously_sent_selected_count",
    "previously_sent_selected_rate",
    "readme_fetched_count",
    "readme_fetch_rate",
    "star_history_updated_count",
    "kimi_used",
    "fallback_used",
    "telegram_sent",
    "telegram_report_url",
    "telegram_explorer_url",
    "telegram_runs_url",
    "delivery_results",
    "collector_error_count",
    "collector_failed_count",
    "collector_error_kinds",
    "collector_error_summary",
    "collector_query_count",
    "collector_success_count",
    "collector_success_rate",
    "top_languages",
    "top_categories",
    "total_star_growth",
    "trending_project_count",
    "trending_top10_available_count",
    "trending_top10_selected_count",
    "trending_top10_fulfillment_rate",
    "trending_selected_rate",
    "summary_points",
}

JOB_KEYS = {
    "job_id",
    "kind",
    "status",
    "run_date",
    "submitted_at",
    "started_at",
    "finished_at",
    "request",
    "result",
    "error",
    "report_url",
}

JOB_REQUEST_KEYS = {
    "profile",
    "sources",
    "dry_run",
    "requested_dry_run",
    "confirm_delivery",
    "delivery_allowed",
    "days_back",
    "trigger_source",
    "requested_by",
    "safety_warnings",
}

JOB_RESULT_KEYS = {
    "run_date",
    "status",
    "selected_count",
    "collected_count",
    "kimi_used",
    "fallback_used",
    "telegram_sent",
    "telegram_error",
    "report_path",
    "report_url",
    "sqlite_index_path",
    "sqlite_error",
    "error",
}

PROFILE_KEYS = {
    "name",
    "label",
    "learning_goals",
    "preferred_languages",
    "preferred_topics",
    "search_languages",
    "search_topics",
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
    "project_corpus": {
        "corpus_id",
        "run_date",
        "full_name",
        "html_url",
        "title",
        "language",
        "category",
        "sources_json",
        "search_text",
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
    "jobs": {
        "job_id",
        "kind",
        "status",
        "run_date",
        "submitted_at",
        "started_at",
        "finished_at",
        "request_json",
        "result_json",
        "error",
        "payload_json",
    },
    "job_events": {
        "event_id",
        "job_id",
        "event_type",
        "status",
        "actor",
        "created_at",
        "message",
        "payload_json",
    },
    "subscriptions": {
        "subscription_id",
        "name",
        "status",
        "profile",
        "language",
        "category",
        "query",
        "sort",
        "limit_count",
        "channels_json",
        "created_at",
        "updated_at",
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
            jobs = json.loads((root / "docs" / "jobs.json").read_text(encoding="utf-8"))
            profiles = json.loads((root / "docs" / "profiles.json").read_text(encoding="utf-8"))
            self.assertEqual(projects["schema_version"], 1)
            self.assertEqual(runs["schema_version"], 1)
            self.assertEqual(jobs["schema_version"], 1)
            self.assertEqual(profiles["schema_version"], 1)
            self.assertEqual(set(projects["projects"][0]), PROJECT_KEYS)
            self.assertEqual(set(runs["runs"][0]), RUN_KEYS)
            self.assertEqual(set(jobs["jobs"][0]), JOB_KEYS)
            self.assertEqual(set(jobs["jobs"][0]["request"]), JOB_REQUEST_KEYS)
            self.assertEqual(set(jobs["jobs"][0]["result"]), JOB_RESULT_KEYS)
            self.assertEqual(set(profiles["profiles"][0]), PROFILE_KEYS)
            self.assertIsInstance(projects["projects"][0]["selection_reasons"], list)
            self.assertIsInstance(projects["projects"][0]["security_flags"], list)
            self.assertIsInstance(projects["projects"][0]["quality_flags"], list)
            self.assertIsInstance(runs["runs"][0]["summary_points"], list)
            self.assertIsInstance(runs["runs"][0]["collector_error_kinds"], list)
            self.assertIsInstance(runs["runs"][0]["collector_error_summary"], list)
            self.assertIsInstance(profiles["profiles"][0]["preferred_topics"], list)
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
    (root / "config").mkdir(parents=True)
    (root / "reports" / "2026-05-03.md").write_text("# 周报", encoding="utf-8")
    (root / "data" / "runs" / "2026-05-03.json").write_text(
        json.dumps(
            {
                "run_date": "2026-05-03",
                "schema_version": 1,
                "status": "success",
                "selected_count": 1,
                "collected_count": 2,
                "previously_sent_selected_count": 0,
                "previously_sent_selected_rate": 0.0,
                "readme_fetched_count": 1,
                "readme_fetch_rate": 1.0,
                "star_history_updated_count": 2,
                "collector_query_count": 2,
                "collector_success_count": 1,
                "collector_success_rate": 0.5,
                "collector_stats": [
                    {"source": "github_trending", "query": "GitHub Trending weekly", "stage": "repository_detail", "status": "success", "count": 1, "error": "", "error_kind": "", "status_code": 0},
                    {"source": "github_search", "query": "topic:ai", "stage": "github_search", "status": "failed", "count": 0, "error": "GitHub API error 403: API rate limit exceeded", "error_kind": "rate_limited", "status_code": 403, "rate_limit_remaining": "0", "rate_limit_reset": "1777777777"},
                ],
                "trending_top10_available_count": 1,
                "trending_top10_selected_count": 1,
                "trending_top10_fulfillment_rate": 1.0,
                "kimi_used": True,
                "fallback_used": False,
                "telegram_sent": True,
                "telegram_report_url": "https://example.com/weekly/2026-05-03.html",
                "telegram_explorer_url": "https://example.com/explorer.html?date=2026-05-03",
                "telegram_runs_url": "https://example.com/runs.html",
                "delivery_results": [{"channel": "telegram", "sent": True, "error": "", "skipped": False}],
                "collector_errors": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / "data" / "trends" / "2026-05-03.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "top_languages": [{"name": "Python", "count": 1}],
                "top_categories": [{"name": "AI Agent", "count": 1}],
                "total_star_growth": 10,
                "trending_project_count": 1,
                "trending_top10_selected_count": 1,
                "trending_selected_rate": 1.0,
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
                    "readme_summary": "这是一个用于测试的项目摘要。",
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
                    "security_score": 100,
                    "security_level": "low",
                    "quality_flags": [],
                    "quality_score": 92,
                    "quality_level": "high",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / "config" / "profiles.example.json").write_text(
        json.dumps(
            {
                "python": {
                    "profile_label": "Python 工具与应用开发",
                    "learning_goals": ["Python 自动化"],
                    "preferred_languages": ["Python"],
                    "preferred_topics": ["python"],
                    "search_languages": ["Python"],
                    "search_topics": ["automation"],
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
