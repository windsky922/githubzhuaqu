from __future__ import annotations

from collections import Counter
from typing import Any

from .models import Repository


def build_trend_summary(repositories: list[Repository]) -> dict[str, Any]:
    language_counts = Counter(repo.language or "Unknown" for repo in repositories)
    category_counts = Counter(repo.category or "Other" for repo in repositories)
    total_star_growth = sum(max(0, repo.star_growth) for repo in repositories)
    top_growth = sorted(
        [repo for repo in repositories if repo.star_growth > 0],
        key=lambda repo: repo.star_growth,
        reverse=True,
    )[:5]

    return {
        "total_projects": len(repositories),
        "total_star_growth": total_star_growth,
        "top_languages": _counter_items(language_counts),
        "top_categories": _counter_items(category_counts),
        "top_star_growth": [_repo_growth_item(repo) for repo in top_growth],
        "summary_points": _summary_points(language_counts, category_counts, total_star_growth, top_growth),
    }


def _counter_items(counter: Counter) -> list[dict[str, Any]]:
    return [{"name": name, "count": count} for name, count in counter.most_common()]


def _repo_growth_item(repo: Repository) -> dict[str, Any]:
    return {
        "full_name": repo.full_name,
        "html_url": repo.html_url,
        "star_growth": repo.star_growth,
        "stargazers_count": repo.stargazers_count,
        "language": repo.language,
        "category": repo.category,
    }


def _summary_points(
    language_counts: Counter,
    category_counts: Counter,
    total_star_growth: int,
    top_growth: list[Repository],
) -> list[str]:
    points = []
    if category_counts:
        category, count = category_counts.most_common(1)[0]
        points.append(f"{category} 是本期最集中的方向，共 {count} 个项目。")
    if language_counts:
        language, count = language_counts.most_common(1)[0]
        points.append(f"{language} 是本期出现最多的主要语言，共 {count} 个项目。")
    points.append(f"本期入选项目累计新增 Star {total_star_growth}。")
    if top_growth:
        leader = top_growth[0]
        points.append(f"{leader.full_name} 是本期新增 Star 最高的项目，新增 {leader.star_growth}。")
    return points
