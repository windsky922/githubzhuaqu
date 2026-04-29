from __future__ import annotations

from .models import Repository


def check_report_quality(report: str, repositories: list[Repository]) -> list[str]:
    errors = []
    if "蟒蛇" in report:
        errors.append("报告中仍包含不合适的技术语言翻译：蟒蛇")
    for repo in repositories:
        if repo.full_name and repo.full_name not in report:
            errors.append(f"报告缺少项目名称：{repo.full_name}")
        expected_link = f"[{repo.html_url}]({repo.html_url})"
        if repo.html_url and expected_link not in report:
            errors.append(f"报告缺少完整 Markdown 链接：{repo.html_url}")
    return errors
