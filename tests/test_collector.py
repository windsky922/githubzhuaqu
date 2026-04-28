import unittest

from src.collector import _readme_excerpt, build_queries
from src.settings import Settings


class CollectorTest(unittest.TestCase):
    def test_readme_excerpt_normalizes_whitespace_and_limits_length(self):
        readme = "# Title\n\n" + "word " * 20

        result = _readme_excerpt(readme, limit=18)

        self.assertEqual(result, "# Title word word ")
        self.assertLessEqual(len(result), 18)

    def test_queries_focus_on_weekly_activity(self):
        settings = Settings(
            root=None,
            run_date="2026-04-28",
            since_date="2026-04-21",
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

        queries = build_queries(settings)

        self.assertIn("pushed:>=2026-04-21 stars:>20", queries)
        self.assertIn("created:>=2026-04-21 stars:>10", queries)


if __name__ == "__main__":
    unittest.main()
