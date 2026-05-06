from __future__ import annotations

from datetime import UTC, datetime

from .models import Repository


def apply_quality_signals(repositories: list[Repository]) -> None:
    for repo in repositories:
        repo.quality_flags = quality_flags(repo)
        repo.quality_score = quality_score(repo.quality_flags)
        repo.quality_level = quality_level(repo.quality_score)


def quality_flags(repo: Repository) -> list[str]:
    flags = []
    if not _readme_text(repo):
        flags.append("README 摘要不足，后续理解项目价值时需要打开仓库人工确认。")
    if len(repo.description.strip()) < 30:
        flags.append("仓库简介较短，项目定位信息有限。")
    if not repo.license_name:
        flags.append("许可证元数据缺失，复用代码前需要确认授权。")
    if not repo.topics:
        flags.append("仓库主题标签较少，垂直方向判断可能不够稳定。")
    if repo.forks_count == 0 and repo.stargazers_count < 100:
        flags.append("社区复用信号偏弱，需要结合 README 和提交历史判断成熟度。")
    if _days_since(repo.pushed_at or repo.updated_at) > 30:
        flags.append("最近维护时间超过 30 天，建议关注维护连续性。")
    return _dedupe(flags)


def quality_score(flags: list[str]) -> int:
    score = 100
    for flag in flags:
        score -= _flag_penalty(flag)
    return max(0, min(100, score))


def quality_level(score: int) -> str:
    if score >= 80:
        return "high"
    if score >= 60:
        return "medium"
    if score > 0:
        return "low"
    return "unknown"


def _flag_penalty(flag: str) -> int:
    if "README" in flag:
        return 18
    if "许可证" in flag:
        return 12
    if "维护时间" in flag:
        return 18
    if "社区复用" in flag:
        return 10
    if "简介" in flag or "主题标签" in flag:
        return 8
    return 8


def _readme_text(repo: Repository) -> str:
    return (repo.readme_summary or repo.readme_excerpt or "").strip()


def _days_since(value: str) -> int:
    if not value:
        return 999
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return 999
    return max(0, (datetime.now(UTC) - timestamp).days)


def _dedupe(items: list[str]) -> list[str]:
    result = []
    for item in items:
        if item not in result:
            result.append(item)
    return result
