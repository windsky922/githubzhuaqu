import unittest

from src.models import Repository
from src.processor import process_repositories
from src.settings import Settings


def repo(
    name,
    stars,
    description="desc",
    fork=False,
    archived=False,
    topics=None,
    created_at="2026-04-25T00:00:00Z",
    updated_at="2026-04-25T00:00:00Z",
    pushed_at="2026-04-25T00:00:00Z",
):
    return Repository(
        full_name=name,
        html_url=f"https://github.com/{name}",
        description=description,
        stargazers_count=stars,
        forks_count=10,
        language="Python",
        created_at=created_at,
        updated_at=updated_at,
        pushed_at=pushed_at,
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
            repo("f/inactive", 200, updated_at="2026-04-01T00:00:00Z", pushed_at="2026-04-01T00:00:00Z"),
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

    def test_star_growth_is_primary_hotness_signal(self):
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
            repo("a/huge-stable", 10000, topics=[]),
            repo("b/smaller-growing", 1000, topics=[]),
        ]

        result = process_repositories(items, settings, {"a/huge-stable": 10000, "b/smaller-growing": 100})

        self.assertEqual(result[0].full_name, "b/smaller-growing")

    def test_trending_rank_is_primary_hotness_signal(self):
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
        trending = repo("a/trending", 500, topics=[])
        growing = repo("b/growing", 10000, topics=[])
        trending.trending_rank = 1
        trending.sources = ["github_trending"]
        trending.source_priority = 100

        result = process_repositories([growing, trending], settings, {"b/growing": 1000})

        self.assertEqual(result[0].full_name, "a/trending")
        self.assertTrue(any("GitHub Trending 周榜" in reason for reason in result[0].selection_reasons))

    def test_keeps_at_least_seven_trending_top_ten_projects(self):
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
            interests={"preferred_topics": [], "preferred_languages": [], "exclude_keywords": []},
        )
        items = []
        for rank in range(1, 11):
            item = repo(f"trend/{rank}", 100 + rank, topics=[])
            item.trending_rank = rank
            item.sources = ["github_trending"]
            item.source_priority = 100
            items.append(item)
        for index in range(1, 11):
            items.append(repo(f"search/{index}", 10000 + index, topics=[]))

        result = process_repositories(items, settings, {f"search/{index}": 100 for index in range(1, 11)})

        trending_top_ten_count = len([item for item in result if 0 < item.trending_rank <= 10])
        self.assertGreaterEqual(trending_top_ten_count, 7)

    def test_adds_selection_reasons(self):
        settings = Settings(
            root=None,
            run_date="2026-04-27",
            since_date="2026-04-20",
            days_back=7,
            min_stars=20,
            max_projects=1,
            github_token="",
            kimi_api_key="",
            kimi_base_url="",
            kimi_model="",
            telegram_bot_token="",
            telegram_chat_id="",
            interests={"preferred_topics": ["agent"], "preferred_languages": ["Python"], "exclude_keywords": []},
        )
        items = [repo("a/reasoned", 100)]

        result = process_repositories(items, settings, {"a/reasoned": 80})

        self.assertTrue(result[0].selection_reasons)
        self.assertTrue(any("新增 Star 20" in reason for reason in result[0].selection_reasons))

    def test_keeps_old_project_when_active_this_week(self):
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
        items = [repo("a/old-active", 100, created_at="2020-01-01T00:00:00Z")]

        result = process_repositories(items, settings)

        self.assertEqual([item.full_name for item in result], ["a/old-active"])


if __name__ == "__main__":
    unittest.main()
