import unittest

from src.models import Repository
from src.reporter import _extract_content, fallback_report
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

        report = fallback_report(repositories, ["created:>=2026-04-20 stars:>20"], settings)

        self.assertIn("owner/project", report)
        self.assertIn("https://github.com/owner/project", report)
        self.assertIn("Star 120", report)
        self.assertIn("created:>=2026-04-20 stars:>20", report)

    def test_extracts_content_from_openai_style_response(self):
        data = {"choices": [{"message": {"content": "正文"}}]}

        self.assertEqual(_extract_content(data), "正文")

    def test_extracts_content_from_list_response(self):
        data = {"choices": [{"message": {"content": [{"text": "正文"}]}}]}

        self.assertEqual(_extract_content(data), "正文")


if __name__ == "__main__":
    unittest.main()
