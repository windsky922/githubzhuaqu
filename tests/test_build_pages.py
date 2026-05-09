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
                json.dumps(
                    {
                        "selected_count": 10,
                        "collected_count": 100,
                        "kimi_used": True,
                        "telegram_sent": True,
                        "telegram_runs_url": "https://example.com/runs.html",
                        "collector_stats": [
                            {
                                "source": "github_search",
                                "query": "topic:ai",
                                "stage": "github_search",
                                "status": "failed",
                                "count": 0,
                                "error": "GitHub API error 403: API rate limit exceeded",
                                "error_kind": "rate_limited",
                                "status_code": 403,
                                "rate_limit_remaining": "0",
                                "rate_limit_reset": "1777777777",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
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
                            "quality_flags": ["README 摘要不足"],
                            "quality_score": 82,
                            "quality_level": "high",
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
            self.assertIn(root / "docs" / "project.html", written)
            self.assertIn(root / "docs" / "runs.html", written)
            self.assertIn(root / "docs" / "projects.json", written)
            self.assertIn(root / "docs" / "runs.json", written)
            self.assertIn(root / "docs" / "profiles.json", written)
            self.assertIn(root / "docs" / "profiles.html", written)
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
            self.assertIn("[项目详情页](project.html)", index)
            self.assertIn("[运行状态面板](runs.html)", index)
            self.assertIn("[历史项目索引](projects.html)", index)
            self.assertIn("[公共项目 JSON](projects.json)", index)
            self.assertIn("[公共运行 JSON](runs.json)", index)
            self.assertIn("[个性化方向页](profiles.html)", index)
            self.assertIn("[个性化方向 JSON](profiles.json)", index)
            self.assertIn("[RSS 订阅](feed.xml)", index)
            self.assertIn("[后端 API 说明](api.html)", index)
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
            self.assertEqual(projects_json["projects"][0]["quality_flags"], ["README 摘要不足"])
            self.assertEqual(projects_json["projects"][0]["quality_score"], 82)
            self.assertEqual(projects_json["projects"][0]["quality_level"], "high")
            runs_json = json.loads((root / "docs" / "runs.json").read_text(encoding="utf-8"))
            self.assertEqual(runs_json["schema_version"], 1)
            self.assertEqual(runs_json["count"], 1)
            self.assertEqual(runs_json["runs"][0]["run_date"], "2026-04-28")
            self.assertTrue(runs_json["runs"][0]["telegram_sent"])
            self.assertEqual(runs_json["runs"][0]["delivery_results"], [])
            self.assertEqual(runs_json["runs"][0]["collector_failed_count"], 1)
            self.assertEqual(runs_json["runs"][0]["collector_error_kinds"], ["rate_limited"])
            self.assertEqual(runs_json["runs"][0]["collector_error_summary"][0]["status_code"], 403)
            self.assertEqual(runs_json["runs"][0]["telegram_runs_url"], "https://example.com/runs.html")
            self.assertEqual(runs_json["runs"][0]["top_languages"][0]["name"], "Python")
            profiles_json = json.loads((root / "docs" / "profiles.json").read_text(encoding="utf-8"))
            self.assertEqual(profiles_json["schema_version"], 1)
            self.assertEqual(profiles_json["count"], 0)
            profiles_page = (root / "docs" / "profiles.html").read_text(encoding="utf-8")
            self.assertIn("个性化方向", profiles_page)
            self.assertIn('fetch("profiles.json"', profiles_page)
            self.assertIn("查看匹配项目", profiles_page)
            self.assertIn("explorer.html?profile=", profiles_page)
            explorer = (root / "docs" / "explorer.html").read_text(encoding="utf-8")
            self.assertIn("GitHub 热点项目筛选", explorer)
            self.assertIn('fetch("/api/projects?limit=200&sort=recent"', explorer)
            self.assertIn('fetch("/api/profiles"', explorer)
            self.assertIn('fetch("projects.json"', explorer)
            self.assertIn('fetch("profiles.json"', explorer)
            self.assertIn("loadProjects", explorer)
            self.assertIn("shouldUseApi", explorer)
            self.assertIn('params.get("api") === "1"', explorer)
            self.assertIn('params.set("api", apiMode)', explorer)
            self.assertIn("来源：${source}", explorer)
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
            self.assertIn('id="qualityLevel"', explorer)
            self.assertIn("平均质量分", explorer)
            self.assertIn("质量信号", explorer)
            self.assertIn("qualityText", explorer)
            self.assertIn("quality_score", explorer)
            self.assertIn('id="profileShortcuts"', explorer)
            self.assertIn("renderProfileShortcuts", explorer)
            self.assertIn("data-profile", explorer)
            self.assertIn("README 摘要", explorer)
            self.assertIn("相似项目", explorer)
            self.assertIn("similarProjects", explorer)
            self.assertIn("similarityScore", explorer)
            self.assertIn("projectKeywords", explorer)
            self.assertIn("projectDetailUrl", explorer)
            self.assertIn('params.set("repo", repo)', explorer)
            project_page = (root / "docs" / "project.html").read_text(encoding="utf-8")
            self.assertIn("GitHub 项目详情", project_page)
            self.assertIn('fetch(`/api/projects/${encodeURIComponentOwnerRepo(repo)}`', project_page)
            self.assertIn('fetch("projects.json"', project_page)
            self.assertIn("buildStaticDetail", project_page)
            self.assertIn("历史趋势", project_page)
            self.assertIn("trendHtml", project_page)
            self.assertIn("bar-fill quality", project_page)
            self.assertIn("历史入选记录", project_page)
            self.assertIn("相似项目", project_page)
            runs_page = (root / "docs" / "runs.html").read_text(encoding="utf-8")
            self.assertIn("运行状态面板", runs_page)
            self.assertIn('fetch("runs.json"', runs_page)
            self.assertIn('id="fallback"', runs_page)
            self.assertIn("trending_top10_fulfillment_rate", runs_page)
            self.assertIn("collector_success_rate", runs_page)
            self.assertIn("telegram_explorer_url", runs_page)
            self.assertIn('id="errorKind"', runs_page)
            self.assertIn("collector_error_summary", runs_page)
            self.assertIn("errorKindLabel", runs_page)
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

    def test_builds_quality_fields_for_legacy_selected_projects(self):
        root = Path.cwd() / f".tmp-pages-quality-test-{uuid.uuid4().hex}"
        try:
            (root / "reports").mkdir(parents=True)
            (root / "data" / "selected").mkdir(parents=True)
            (root / "reports" / "2026-05-06.md").write_text("# 周报", encoding="utf-8")
            (root / "data" / "selected" / "2026-05-06.json").write_text(
                json.dumps(
                    [
                        {
                            "full_name": "owner/project",
                            "html_url": "https://github.com/owner/project",
                            "description": "short",
                            "language": "Python",
                            "stargazers_count": 50,
                            "forks_count": 0,
                            "pushed_at": "2026-05-05T00:00:00Z",
                            "readme_summary": "",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            build_pages(root)

            projects = json.loads((root / "docs" / "projects.json").read_text(encoding="utf-8"))
            item = projects["projects"][0]
            self.assertGreater(item["quality_score"], 0)
            self.assertNotEqual(item["quality_level"], "unknown")
            self.assertTrue(item["quality_flags"])
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
