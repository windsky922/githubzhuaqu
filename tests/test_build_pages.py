import json
import shutil
import unittest
import uuid
from pathlib import Path

from scripts.build_pages import build_pages


class BuildPagesTest(unittest.TestCase):
    def test_builds_index_and_weekly_report_pages(self):
        root = Path.cwd() / f".tmp-pages-test-{uuid.uuid4().hex}"
        try:
            (root / "reports").mkdir(parents=True)
            (root / "data" / "runs").mkdir(parents=True)
            (root / "data" / "trends").mkdir(parents=True)
            (root / "data" / "selected").mkdir(parents=True)
            (root / "reports" / "2026-04-28.md").write_text("# 周报", encoding="utf-8")
            (root / "data" / "runs" / "2026-04-28.json").write_text(
                json.dumps({"selected_count": 10, "collected_count": 100, "kimi_used": True, "telegram_sent": True}),
                encoding="utf-8",
            )
            (root / "data" / "trends" / "2026-04-28.json").write_text(
                json.dumps(
                    {
                        "summary_points": ["Python 是本期主要语言。"],
                        "top_languages": [{"name": "Python", "count": 8}],
                        "top_categories": [{"name": "AI Agent", "count": 4}],
                        "total_star_growth": 20,
                        "trending_project_count": 1,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (root / "data" / "selected" / "2026-04-28.json").write_text(
                json.dumps(
                    [
                        {
                            "full_name": "owner/project",
                            "html_url": "https://github.com/owner/project",
                            "category": "AI Agent",
                            "language": "Python",
                            "stargazers_count": 100,
                            "star_growth": 20,
                            "sources": ["github_trending", "github_search"],
                            "trending_rank": 2,
                            "security_flags": ["未识别到许可证。"],
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            written = build_pages(root)

            self.assertIn(root / "docs" / "index.md", written)
            self.assertIn(root / "docs" / "projects.md", written)
            self.assertIn(root / "docs" / "projects.json", written)
            self.assertIn(root / "docs" / "runs.json", written)
            self.assertEqual((root / "docs" / "weekly" / "2026-04-28.md").read_text(encoding="utf-8"), "# 周报")
            index = (root / "docs" / "index.md").read_text(encoding="utf-8")
            self.assertIn("[2026-04-28](weekly/2026-04-28.html)", index)
            self.assertIn("10 个项目", index)
            self.assertIn("最新运行摘要", index)
            self.assertIn("采集候选：100 个", index)
            self.assertIn("Python 是本期主要语言。", index)
            self.assertIn("主语言 Python", index)
            self.assertIn("主方向 AI Agent", index)
            self.assertIn("新增 Star 20", index)
            self.assertIn("Trending 项目 1", index)
            self.assertIn("[历史项目索引](projects.html)", index)
            self.assertIn("[公共项目 JSON](projects.json)", index)
            self.assertIn("[公共运行 JSON](runs.json)", index)
            self.assertIn("[未来更新规划](future-plan.html)", index)
            projects = (root / "docs" / "projects.md").read_text(encoding="utf-8")
            self.assertIn("owner/project", projects)
            self.assertIn("GitHub Trending + GitHub Search", projects)
            self.assertIn("| 2 |", projects)
            self.assertIn("AI Agent", projects)
            self.assertIn("[https://github.com/owner/project](https://github.com/owner/project)", projects)
            projects_json = json.loads((root / "docs" / "projects.json").read_text(encoding="utf-8"))
            self.assertEqual(projects_json["schema_version"], 1)
            self.assertEqual(projects_json["count"], 1)
            self.assertEqual(projects_json["projects"][0]["full_name"], "owner/project")
            self.assertEqual(projects_json["projects"][0]["report_url"], "weekly/2026-04-28.html")
            self.assertIn("security_flags", projects_json["projects"][0])
            runs_json = json.loads((root / "docs" / "runs.json").read_text(encoding="utf-8"))
            self.assertEqual(runs_json["schema_version"], 1)
            self.assertEqual(runs_json["count"], 1)
            self.assertEqual(runs_json["runs"][0]["run_date"], "2026-04-28")
            self.assertTrue(runs_json["runs"][0]["telegram_sent"])
            self.assertEqual(runs_json["runs"][0]["top_languages"][0]["name"], "Python")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_builds_empty_projects_table_with_complete_columns(self):
        root = Path.cwd() / f".tmp-pages-empty-test-{uuid.uuid4().hex}"
        try:
            (root / "reports").mkdir(parents=True)

            build_pages(root)

            projects = (root / "docs" / "projects.md").read_text(encoding="utf-8")
            self.assertIn("| - | 暂无项目 | - | - | - | - | 0 | 0 | 0 | - |", projects)
            self.assertIn("[周报归档首页](index.html)", projects)
            projects_json = json.loads((root / "docs" / "projects.json").read_text(encoding="utf-8"))
            runs_json = json.loads((root / "docs" / "runs.json").read_text(encoding="utf-8"))
            self.assertEqual(projects_json["projects"], [])
            self.assertEqual(runs_json["runs"], [])
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
