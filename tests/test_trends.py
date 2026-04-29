import unittest

from src.models import Repository
from src.trends import build_trend_summary


def repo(name, language, category, growth, trending_rank=0):
    return Repository(
        full_name=name,
        html_url=f"https://github.com/{name}",
        description="desc",
        stargazers_count=100 + growth,
        forks_count=10,
        language=language,
        created_at="2026-04-20T00:00:00Z",
        updated_at="2026-04-27T00:00:00Z",
        pushed_at="2026-04-27T00:00:00Z",
        category=category,
        star_growth=growth,
        trending_rank=trending_rank,
    )


class TrendsTest(unittest.TestCase):
    def test_builds_trend_summary(self):
        summary = build_trend_summary(
            [
                repo("a/one", "Python", "AI Agent", 20, 2),
                repo("b/two", "Python", "AI Agent", 5),
                repo("c/three", "TypeScript", "LLM Tooling", 0, 1),
            ]
        )

        self.assertEqual(summary["total_projects"], 3)
        self.assertEqual(summary["trending_project_count"], 2)
        self.assertEqual(summary["total_star_growth"], 25)
        self.assertEqual(summary["top_languages"][0], {"name": "Python", "count": 2})
        self.assertEqual(summary["top_categories"][0], {"name": "AI Agent", "count": 2})
        self.assertEqual(summary["top_trending"][0]["full_name"], "c/three")
        self.assertEqual(summary["top_trending"][0]["trending_rank"], 1)
        self.assertEqual(summary["top_star_growth"][0]["full_name"], "a/one")
        self.assertTrue(summary["summary_points"])


if __name__ == "__main__":
    unittest.main()
