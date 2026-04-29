import unittest
from unittest.mock import patch

from src.models import Repository
from src.reporter import _extract_content, fallback_report, generate_report, normalize_report_markdown
from src.settings import Settings


class ReporterTest(unittest.TestCase):
    def test_fallback_report_contains_core_fields(self):
        settings = Settings(
            root=None,
            run_date="2026-04-27",
            since_date="2026-04-20",
            days_back=7,
            min_stars=20,
            max_projects=10,
            github_token="",
            kimi_api_key="",
            kimi_base_url="",
            kimi_model="",
            telegram_bot_token="",
            telegram_chat_id="",
            interests={},
        )
        repositories = [
            Repository(
                full_name="owner/project",
                html_url="https://github.com/owner/project",
                description="Useful agent tool",
                stargazers_count=120,
                forks_count=20,
                language="Python",
                created_at="2026-04-25T00:00:00Z",
                updated_at="2026-04-25T00:00:00Z",
                category="AI Agent",
            )
        ]

        trend_summary = {"summary_points": ["Python 是本期出现最多的主要语言，共 1 个项目。"]}
        report = fallback_report(repositories, ["created:>=2026-04-20 stars:>20"], settings, trend_summary)

        self.assertIn("owner/project", report)
        self.assertIn("https://github.com/owner/project", report)
        self.assertIn("Star 120", report)
        self.assertIn("created:>=2026-04-20 stars:>20", report)
        self.assertIn("Python 是本期出现最多的主要语言", report)

    def test_extracts_content_from_openai_style_response(self):
        data = {"choices": [{"message": {"content": "正文"}}]}

        self.assertEqual(_extract_content(data), "正文")

    def test_extracts_content_from_list_response(self):
        data = {"choices": [{"message": {"content": [{"text": "正文"}]}}]}

        self.assertEqual(_extract_content(data), "正文")

    def test_normalizes_language_and_github_table_links_with_full_url_text(self):
        report = "| 项目 | 主要语言 | 链接 |\n| demo | 蟒蛇 | https://github.com/a/b |"

        result = normalize_report_markdown(report)

        self.assertIn("| demo | Python | [https://github.com/a/b](https://github.com/a/b) |", result)

    def test_normalizes_standalone_github_links(self):
        report = "https://github.com/a/b"

        result = normalize_report_markdown(report)

        self.assertEqual(result.strip(), "[https://github.com/a/b](https://github.com/a/b)")

    def test_keeps_existing_markdown_github_links(self):
        report = "[https://github.com/a/b](https://github.com/a/b)"

        result = normalize_report_markdown(report)

        self.assertEqual(result.strip(), "[https://github.com/a/b](https://github.com/a/b)")

    def test_rewrites_short_github_link_text_to_full_url(self):
        report = "[GitHub](https://github.com/a/b)"

        result = normalize_report_markdown(report)

        self.assertEqual(result.strip(), "[https://github.com/a/b](https://github.com/a/b)")

    def test_retries_kimi_without_readme_after_content_filter(self):
        settings = Settings(
            root=None,
            run_date="2026-04-27",
            since_date="2026-04-20",
            days_back=7,
            min_stars=20,
            max_projects=10,
            github_token="",
            kimi_api_key="key",
            kimi_base_url="https://api.example.com/v1",
            kimi_model="model",
            telegram_bot_token="",
            telegram_chat_id="",
            interests={},
        )
        repositories = [
            Repository(
                full_name="owner/project",
                html_url="https://github.com/owner/project",
                description="Useful agent tool",
                stargazers_count=120,
                forks_count=20,
                language="Python",
                created_at="2026-04-25T00:00:00Z",
                updated_at="2026-04-25T00:00:00Z",
                readme_excerpt="raw readme",
            )
        ]

        with patch(
            "src.reporter._generate_with_kimi",
            side_effect=[RuntimeError("content_filter high risk"), "Kimi 正文"],
        ) as generate:
            report, fallback_used, report_error = generate_report(repositories, [], settings, {})

        self.assertEqual(report.strip(), "Kimi 正文")
        self.assertFalse(fallback_used)
        self.assertEqual(report_error, "")
        self.assertEqual(generate.call_count, 2)
        self.assertFalse(generate.call_args_list[1].kwargs["include_readme"])


if __name__ == "__main__":
    unittest.main()
