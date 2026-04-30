import unittest

from src.models import Repository
from src.report_checks import check_report_quality


def repo():
    return Repository(
        full_name="owner/project",
        html_url="https://github.com/owner/project",
        description="desc",
        stargazers_count=100,
        forks_count=10,
        language="Python",
        created_at="2026-04-25T00:00:00Z",
        updated_at="2026-04-28T00:00:00Z",
    )


def trending_repo():
    item = repo()
    item.sources = ["github_trending"]
    item.trending_rank = 3
    item.security_flags = ["未识别到许可证，复用代码前需要人工确认授权。"]
    return item


def complete_report(extra: str = ""):
    return (
        "## 本周总体趋势\n"
        "## 热点项目总览\n"
        "## 重点项目分析\n"
        "## 最适合用户学习的项目\n"
        "## 本周结论\n"
        "owner/project [https://github.com/owner/project](https://github.com/owner/project)\n"
        f"{extra}"
    )


class ReportChecksTest(unittest.TestCase):
    def test_accepts_complete_report(self):
        report = complete_report()

        errors = check_report_quality(report, [repo()])

        self.assertEqual(errors, [])

    def test_reports_missing_project_and_link(self):
        errors = check_report_quality("其他内容", [repo()])

        self.assertTrue(any("项目名称" in error for error in errors))
        self.assertTrue(any("完整 Markdown 链接" in error for error in errors))

    def test_reports_bad_language_translation(self):
        report = complete_report("蟒蛇")

        errors = check_report_quality(report, [repo()])

        self.assertTrue(any("蟒蛇" in error for error in errors))

    def test_reports_missing_required_sections(self):
        report = "owner/project [https://github.com/owner/project](https://github.com/owner/project)"

        errors = check_report_quality(report, [repo()])

        self.assertTrue(any("固定结构章节" in error for error in errors))
        self.assertTrue(any("本周总体趋势" in error for error in errors))

    def test_reports_unexpected_repository_links(self):
        report = complete_report("extra [https://github.com/other/project](https://github.com/other/project)")

        errors = check_report_quality(report, [repo()])

        self.assertTrue(any("非入选项目链接" in error for error in errors))
        self.assertTrue(any("other/project" in error for error in errors))

    def test_requires_trending_source_rank_and_risk_when_present(self):
        report = "owner/project [https://github.com/owner/project](https://github.com/owner/project)"

        errors = check_report_quality(report, [trending_repo()])

        self.assertTrue(any("项目来源" in error for error in errors))
        self.assertTrue(any("Trending 排名" in error for error in errors))
        self.assertTrue(any("风险提示" in error for error in errors))

    def test_accepts_trending_source_rank_and_risk(self):
        report = complete_report("GitHub Trending Trending 排名 3 风险提示：未识别到许可证。")

        errors = check_report_quality(report, [trending_repo()])

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
