import unittest

from src.models import Repository
from src.processor import process_repositories
from src.settings import Settings


def repo(name, stars, description="desc", fork=False, archived=False, topics=None, created_at="2026-04-25T00:00:00Z"):
    return Repository(
        full_name=name,
        html_url=f"https://github.com/{name}",
        description=description,
        stargazers_count=stars,
        forks_count=10,
        language="Python",
        created_at=created_at,
        updated_at="2026-04-25T00:00:00Z",
        topics=topics or ["agent"],
        fork=fork,
        archived=archived,
    )


class ProcessorTest(unittest.TestCase):
    def test_filters_dedupes_and_ranks(self):
        settings = Settings(
            root=None,
            run_date="2026-04-27",
            since_date="2026-04-20",
            days_back=7,
            min_stars=20,
            max_projects=2,
            github_token="",
            kimi_api_key="",
            kimi_base_url="",
            kimi_model="",
            telegram_bot_token="",
            telegram_chat_id="",
            interests={
                "preferred_topics": ["agent", "python"],
                "preferred_languages": ["Python"],
                "exclude_keywords": ["mirror"],
            },
        )
        items = [
            repo("a/one", 100),
            repo("a/one", 100),
            repo("b/two", 50, fork=True),
            repo("c/three", 10),
            repo("d/four", 80, description="mirror repo"),
            repo("e/five", 90),
            repo("f/old", 200, created_at="2026-04-01T00:00:00Z"),
        ]

        result = process_repositories(items, settings)

        self.assertEqual([item.full_name for item in result], ["a/one", "e/five"])
        self.assertTrue(all(item.score > 0 for item in result))

    def test_uses_star_growth_in_score(self):
        settings = Settings(
            root=None,
            run_date="2026-04-27",
            since_date="2026-04-20",
            days_back=7,
            min_stars=20,
            max_projects=2,
            github_token="",
            kimi_api_key="",
            kimi_base_url="",
            kimi_model="",
            telegram_bot_token="",
            telegram_chat_id="",
            interests={"preferred_topics": [], "preferred_languages": [], "exclude_keywords": []},
        )
        items = [
            repo("a/stable", 100, topics=[]),
            repo("b/growing", 90, topics=[]),
        ]

        result = process_repositories(items, settings, {"a/stable": 100, "b/growing": 30})

        self.assertEqual(result[0].full_name, "b/growing")
        self.assertEqual(result[0].star_growth, 60)


if __name__ == "__main__":
    unittest.main()
