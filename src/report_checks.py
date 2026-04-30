from __future__ import annotations

import re

from .models import Repository


GITHUB_REPOSITORY_LINK_PATTERN = re.compile(r"https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)")


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
        errors.extend(_source_errors(report, repo))
        errors.extend(_trending_errors(report, repo))
        errors.extend(_security_errors(report, repo))
    errors.extend(_unexpected_repository_errors(report, repositories))
    return errors


def _unexpected_repository_errors(report: str, repositories: list[Repository]) -> list[str]:
    expected = {repo.full_name.lower() for repo in repositories if repo.full_name}
    found = {match.group(1).lower() for match in GITHUB_REPOSITORY_LINK_PATTERN.finditer(report)}
    unexpected = sorted(found - expected)
    return [f"报告包含非入选项目链接：{name}" for name in unexpected]


def _source_errors(report: str, repo: Repository) -> list[str]:
    labels = {
        "github_trending": "GitHub Trending",
        "github_search": "GitHub Search",
    }
    errors = []
    for source in repo.sources:
        label = labels.get(source, source)
        if label and label not in report:
            errors.append(f"报告缺少项目来源：{repo.full_name} {label}")
    return errors


def _trending_errors(report: str, repo: Repository) -> list[str]:
    if repo.trending_rank <= 0:
        return []
    if "Trending" not in report or str(repo.trending_rank) not in report:
        return [f"报告缺少 Trending 排名：{repo.full_name} #{repo.trending_rank}"]
    return []


def _security_errors(report: str, repo: Repository) -> list[str]:
    if not repo.security_flags:
        return []
    if "风险" not in report and not any(flag in report for flag in repo.security_flags):
        return [f"报告缺少风险提示：{repo.full_name}"]
    return []
