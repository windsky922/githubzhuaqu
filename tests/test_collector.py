import unittest
from unittest.mock import patch

from src.collector import _readme_excerpt, build_queries, collect_repositories
from src.models import Repository
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
        self.assertFalse(any(query.startswith("created:>=") for query in queries))

    def test_collect_repositories_returns_partial_errors(self):
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
        repository = Repository(
            full_name="owner/project",
            html_url="https://github.com/owner/project",
            description="desc",
            stargazers_count=100,
            forks_count=10,
            language="Python",
            created_at="2026-04-20T00:00:00Z",
            updated_at="2026-04-28T00:00:00Z",
            pushed_at="2026-04-28T00:00:00Z",
        )

        def fake_search(query, current_settings):
            if "topic:ai" in query:
                raise RuntimeError("rate limited")
            return [repository]

        with patch("src.collector.search_repositories", side_effect=fake_search):
            repositories, queries, errors = collect_repositories(settings)

        self.assertEqual(repositories, [repository] * (len(queries) - 1))
        self.assertEqual(len(errors), 1)
        self.assertIn("topic:ai", errors[0])
        self.assertIn("rate limited", errors[0])


if __name__ == "__main__":
    unittest.main()
