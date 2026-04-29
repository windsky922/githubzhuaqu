import unittest
from unittest.mock import patch

from src.collector import (
    _parse_trending_repository_names,
    _readme_excerpt,
    build_queries,
    collect_repositories,
)
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
            interests={"enable_github_trending": False},
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
            interests={"enable_github_trending": False},
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
            repositories, queries, errors, stats = collect_repositories(settings)

        self.assertEqual(repositories, [repository] * (len(queries) - 1))
        self.assertEqual(len(errors), 1)
        self.assertIn("topic:ai", errors[0])
        self.assertIn("rate limited", errors[0])
        self.assertEqual(len(stats), len(queries))
        self.assertTrue(any(item["status"] == "failed" for item in stats))
        self.assertTrue(any(item["status"] == "success" and item["count"] == 1 for item in stats))

    def test_parse_trending_repository_names(self):
        html = """
        <a href="/outside/not-repository">outside</a>
        <article>
          <h2><a href="/owner/project">owner / project</a></h2>
          <a href="/inside/not-repository">inside</a>
          <a href="/owner/project/stargazers">stars</a>
          <h2><a href="/another/repo?since=weekly">another / repo</a></h2>
          <a href="/sponsors/explore">Sponsors</a>
          <a href="/apps/dependabot">Dependabot</a>
        </article>
        """

        result = _parse_trending_repository_names(html)

        self.assertEqual(result, ["owner/project", "another/repo"])

    def test_collect_repositories_prefers_trending_source(self):
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
            interests={"search_topics": [], "search_languages": []},
        )
        trending_repo = Repository(
            full_name="trend/one",
            html_url="https://github.com/trend/one",
            description="desc",
            stargazers_count=100,
            forks_count=10,
            language="Python",
            created_at="2026-04-20T00:00:00Z",
            updated_at="2026-04-28T00:00:00Z",
            pushed_at="2026-04-28T00:00:00Z",
        )

        with patch("src.collector.fetch_trending_repository_names", return_value=["trend/one"]):
            with patch("src.collector.fetch_repository", return_value=trending_repo):
                with patch("src.collector.search_repositories", return_value=[]):
                    repositories, queries, errors, stats = collect_repositories(settings)

        self.assertEqual(repositories[0].full_name, "trend/one")
        self.assertEqual(repositories[0].sources, ["github_trending"])
        self.assertEqual(repositories[0].trending_rank, 1)
        self.assertIn("GitHub Trending weekly", queries[0])
        self.assertEqual(errors, [])
        self.assertEqual(stats[0]["source"], "github_trending")


if __name__ == "__main__":
    unittest.main()
