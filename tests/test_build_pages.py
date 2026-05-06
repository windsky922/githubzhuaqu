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
                            "description": "desc",
                            "readme_summary": "这是一个简短 README 摘要。",
                            "category": "AI Agent",
                            "language": "Python",
                            "stargazers_count": 100,
                            "star_growth": 20,
                            "sources": ["github_trending", "github_search"],
                            "trending_rank": 2,
                            "security_flags": ["未识别到许可证。"],
                            "security_score": 85,
                            "security_level": "medium",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            written = build_pages(root)

            self.assertIn(root / "docs" / "index.md", written)
            self.assertIn(root / "docs" / "projects.md", written)
            self.assertIn(root / "docs" / "explorer.html", written)
            self.assertIn(root / "docs" / "projects.json", written)
            self.assertIn(root / "docs" / "runs.json", written)
            self.assertIn(root / "docs" / "profiles.json", written)
            self.assertIn(root / "docs" / "feed.xml", written)
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
            self.assertIn("[项目筛选页](explorer.html)", index)
            self.assertIn("[历史项目索引](projects.html)", index)
            self.assertIn("[公共项目 JSON](projects.json)", index)
            self.assertIn("[公共运行 JSON](runs.json)", index)
            self.assertIn("[个性化方向 JSON](profiles.json)", index)
            self.assertIn("[RSS 订阅](feed.xml)", index)
            self.assertIn("[历史归档查询说明](archive-query.html)", index)
            self.assertIn("[数据契约说明](data-contracts.html)", index)
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
            self.assertEqual(projects_json["projects"][0]["readme_summary"], "这是一个简短 README 摘要。")
            self.assertIn("security_flags", projects_json["projects"][0])
            self.assertEqual(projects_json["projects"][0]["security_score"], 85)
            self.assertEqual(projects_json["projects"][0]["security_level"], "medium")
            runs_json = json.loads((root / "docs" / "runs.json").read_text(encoding="utf-8"))
            self.assertEqual(runs_json["schema_version"], 1)
            self.assertEqual(runs_json["count"], 1)
            self.assertEqual(runs_json["runs"][0]["run_date"], "2026-04-28")
            self.assertTrue(runs_json["runs"][0]["telegram_sent"])
            self.assertEqual(runs_json["runs"][0]["delivery_results"], [])
            self.assertEqual(runs_json["runs"][0]["top_languages"][0]["name"], "Python")
            profiles_json = json.loads((root / "docs" / "profiles.json").read_text(encoding="utf-8"))
            self.assertEqual(profiles_json["schema_version"], 1)
            self.assertEqual(profiles_json["count"], 0)
            explorer = (root / "docs" / "explorer.html").read_text(encoding="utf-8")
            self.assertIn("GitHub 热点项目筛选", explorer)
            self.assertIn('fetch("projects.json"', explorer)
            self.assertIn('fetch("profiles.json"', explorer)
            self.assertIn('id="runDate"', explorer)
            self.assertIn('id="language"', explorer)
            self.assertIn('id="profile"', explorer)
            self.assertIn('id="category"', explorer)
            self.assertIn('id="share"', explorer)
            self.assertIn("restoreFiltersFromUrl", explorer)
            self.assertIn("updateUrl", explorer)
            self.assertIn("summaryHtml", explorer)
            self.assertIn("matchesProfile", explorer)
            self.assertIn("securityText", explorer)
            self.assertIn("detailPanel", explorer)
            self.assertIn("toggleDetails", explorer)
            self.assertIn('id="profileShortcuts"', explorer)
            self.assertIn("renderProfileShortcuts", explorer)
            self.assertIn("data-profile", explorer)
            self.assertIn("README 摘要", explorer)
            self.assertIn("相似项目", explorer)
            self.assertIn("similarProjects", explorer)
            self.assertIn("similarityScore", explorer)
            self.assertIn("projectKeywords", explorer)
            feed = (root / "docs" / "feed.xml").read_text(encoding="utf-8")
            self.assertIn("<rss version=\"2.0\">", feed)
            self.assertIn("GitHub 每周热点项目周报 - 2026-04-28", feed)
            self.assertIn("weekly/2026-04-28.html", feed)
            self.assertIn("入选项目 10 个", feed)
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
            profiles_json = json.loads((root / "docs" / "profiles.json").read_text(encoding="utf-8"))
            self.assertEqual(projects_json["projects"], [])
            self.assertEqual(runs_json["runs"], [])
            self.assertEqual(profiles_json["profiles"], [])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_builds_public_profiles_json_from_config(self):
        root = Path.cwd() / f".tmp-pages-profile-test-{uuid.uuid4().hex}"
        try:
            (root / "reports").mkdir(parents=True)
            (root / "config").mkdir(parents=True)
            (root / "config" / "profiles.example.json").write_text(
                json.dumps(
                    {
                        "agent_development": {
                            "profile_label": "Agent 开发",
                            "learning_goals": ["工具调用"],
                            "preferred_languages": ["Python"],
                            "preferred_topics": ["agent"],
                            "search_topics": ["llm"],
                            "secret_note": "不应公开",
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            build_pages(root)

            profiles = json.loads((root / "docs" / "profiles.json").read_text(encoding="utf-8"))
            self.assertEqual(profiles["profiles"][0]["name"], "agent_development")
            self.assertEqual(profiles["profiles"][0]["label"], "Agent 开发")
            self.assertEqual(profiles["profiles"][0]["preferred_languages"], ["Python"])
            self.assertNotIn("secret_note", profiles["profiles"][0])
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
