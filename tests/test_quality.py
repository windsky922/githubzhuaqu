import unittest
from datetime import UTC, datetime, timedelta

from src.models import Repository
from src.quality import apply_quality_signals, quality_flags, quality_level, quality_score


def repo(**overrides):
    recent_time = (datetime.now(UTC) - timedelta(days=1)).isoformat().replace("+00:00", "Z")
    values = {
        "full_name": "owner/project",
        "html_url": "https://github.com/owner/project",
        "description": "A practical toolkit with clear positioning and active maintenance.",
        "stargazers_count": 500,
        "forks_count": 40,
        "language": "Python",
        "created_at": "2026-04-01T00:00:00Z",
        "updated_at": recent_time,
        "pushed_at": recent_time,
        "topics": ["agent", "automation"],
        "license_name": "MIT",
        "readme_summary": "该项目提供清晰的安装方式、使用示例和核心功能说明。",
    }
    values.update(overrides)
    return Repository(**values)


class QualityTest(unittest.TestCase):
    def test_high_quality_repository_has_no_flags(self):
        item = repo()

        self.assertEqual(quality_flags(item), [])
        self.assertEqual(quality_score([]), 100)
        self.assertEqual(quality_level(100), "high")

    def test_flags_incomplete_metadata(self):
        item = repo(
            description="short",
            forks_count=0,
            stargazers_count=50,
            topics=[],
            license_name="",
            readme_summary="",
        )

        flags = quality_flags(item)

        self.assertTrue(any("README" in flag for flag in flags))
        self.assertTrue(any("简介" in flag for flag in flags))
        self.assertTrue(any("许可证" in flag for flag in flags))
        self.assertTrue(any("社区复用" in flag for flag in flags))
        self.assertEqual(quality_level(quality_score(flags)), "low")

    def test_apply_quality_signals_updates_repository(self):
        item = repo(readme_summary="")

        apply_quality_signals([item])

        self.assertLess(item.quality_score, 100)
        self.assertEqual(item.quality_level, "high")
        self.assertTrue(item.quality_flags)


if __name__ == "__main__":
    unittest.main()
