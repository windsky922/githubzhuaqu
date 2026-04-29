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


class ReportChecksTest(unittest.TestCase):
    def test_accepts_complete_report(self):
        report = "owner/project [https://github.com/owner/project](https://github.com/owner/project)"

        errors = check_report_quality(report, [repo()])

        self.assertEqual(errors, [])

    def test_reports_missing_project_and_link(self):
        errors = check_report_quality("其他内容", [repo()])

        self.assertTrue(any("项目名称" in error for error in errors))
        self.assertTrue(any("完整 Markdown 链接" in error for error in errors))

    def test_reports_bad_language_translation(self):
        report = "owner/project 蟒蛇 [https://github.com/owner/project](https://github.com/owner/project)"

        errors = check_report_quality(report, [repo()])

        self.assertTrue(any("蟒蛇" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
