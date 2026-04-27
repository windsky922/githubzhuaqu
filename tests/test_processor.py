import unittest

from src.models import Repository
from src.processor import process_repositories
from src.settings import Settings


def repo(name, stars, description="desc", fork=False, archived=False, topics=None):
    return Repository(
        full_name=name,
        html_url=f"https://github.com/{name}",
        description=description,
        stargazers_count=stars,
        forks_count=10,
        language="Python",
        created_at="2026-04-25T00:00:00Z",
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
        ]

        result = process_repositories(items, settings)

        self.assertEqual([item.full_name for item in result], ["a/one", "e/five"])
        self.assertTrue(all(item.score > 0 for item in result))


if __name__ == "__main__":
    unittest.main()

