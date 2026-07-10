import json
import shutil
import unittest
import uuid
from pathlib import Path

from scripts.query_archive import query_archive, query_archive_page, table_output
from src.storage.sqlite_store import import_json_archive


class QueryArchiveTest(unittest.TestCase):
    def test_query_page_returns_total_and_offset(self):
        root = Path.cwd() / f".tmp-query-archive-test-{uuid.uuid4().hex}"
        try:
            _write_archive(root)
            db_path = root / "data" / "github_weekly.sqlite"
            import_json_archive(root, db_path)
            rows, total = query_archive_page(db_path=db_path, root=root, limit=1, offset=1)

            self.assertEqual(total, 2)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["full_name"], "owner/tool")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_queries_history_by_language_source_and_keyword(self):
        root = Path.cwd() / f".tmp-query-archive-test-{uuid.uuid4().hex}"
        try:
            _write_archive(root)
            db_path = root / "data" / "github_weekly.sqlite"
            import_json_archive(root, db_path)

            rows = query_archive(
                db_path=db_path,
                root=root,
                language="Python",
                source="github_trending",
                query="agent",
            )

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["full_name"], "owner/agent")
            self.assertEqual(rows[0]["sources"], ["github_trending"])
            self.assertEqual(rows[0]["security_flags"], [])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_queries_history_by_profile_and_risk(self):
        root = Path.cwd() / f".tmp-query-archive-test-{uuid.uuid4().hex}"
        try:
            _write_archive(root)
            db_path = root / "data" / "github_weekly.sqlite"
            import_json_archive(root, db_path)

            rows = query_archive(db_path=db_path, root=root, profile="developer_tools", risk="has")

            self.assertEqual([row["full_name"] for row in rows], ["owner/tool"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_table_output_has_clickable_source_url_text(self):
        rows = [
            {
                "run_date": "2026-05-03",
                "full_name": "owner/agent",
                "language": "Python",
                "category": "AI Agent",
                "quality_score": 92,
                "star_growth": 20,
                "trending_rank": 1,
                "html_url": "https://github.com/owner/agent",
            }
        ]

        output = table_output(rows)

        self.assertIn("owner/agent", output)
        self.assertIn("https://github.com/owner/agent", output)
        self.assertIn("92", output)

    def test_queries_history_by_quality_trending_and_sort(self):
        root = Path.cwd() / f".tmp-query-archive-test-{uuid.uuid4().hex}"
        try:
            _write_archive(root)
            db_path = root / "data" / "github_weekly.sqlite"
            import_json_archive(root, db_path)

            rows = query_archive(
                db_path=db_path,
                root=root,
                min_quality=80,
                trending_top=3,
                sort="quality",
            )

            self.assertEqual([row["full_name"] for row in rows], ["owner/agent"])
            self.assertEqual(rows[0]["quality_score"], 92)
            self.assertEqual(rows[0]["quality_level"], "high")
        finally:
            shutil.rmtree(root, ignore_errors=True)


def _write_archive(root: Path) -> None:
    (root / "data" / "runs").mkdir(parents=True)
    (root / "data" / "selected").mkdir(parents=True)
    (root / "data" / "trends").mkdir(parents=True)
    (root / "data" / "state").mkdir(parents=True)
    (root / "config").mkdir(parents=True)
    (root / "data" / "runs" / "2026-05-03.json").write_text(
        json.dumps({"run_date": "2026-05-03", "status": "success"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (root / "data" / "selected" / "2026-05-03.json").write_text(
        json.dumps(
            [
                {
                    "full_name": "owner/agent",
                    "html_url": "https://github.com/owner/agent",
                    "description": "agent workflow automation",
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
                    "quality_score": 92,
                    "quality_level": "high",
                    "quality_flags": [],
                },
                {
                    "full_name": "owner/tool",
                    "html_url": "https://github.com/owner/tool",
                    "description": "developer cli automation",
                    "language": "Go",
                    "stargazers_count": 50,
                    "forks_count": 5,
                    "score": 0.5,
                    "star_growth": 5,
                    "trending_rank": 0,
                    "category": "Developer Tools",
                    "sources": ["github_search"],
                    "selection_reasons": ["匹配开发者工具方向。"],
                    "security_flags": ["未识别到许可证。"],
                    "quality_score": 55,
                    "quality_level": "medium",
                    "quality_flags": ["社区信号较弱。"],
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
    (root / "data" / "state" / "sent_repos.json").write_text("[]", encoding="utf-8")
    (root / "data" / "state" / "star_history.json").write_text("[]", encoding="utf-8")
    (root / "config" / "profiles.example.json").write_text(
        json.dumps(
            {
                "developer_tools": {
                    "profile_label": "开发者工具",
                    "preferred_languages": ["Go", "Rust"],
                    "preferred_topics": ["cli", "developer-tools", "automation"],
                    "search_topics": ["cli"],
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
