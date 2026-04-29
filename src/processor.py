from __future__ import annotations

from datetime import UTC, datetime

from .models import Repository
from .settings import Settings


CATEGORIES = {
    "AI Agent": {"agent", "agents", "autonomous", "workflow"},
    "LLM Tooling": {"llm", "openai", "claude", "kimi", "rag", "prompt"},
    "Developer Tools": {"developer-tools", "cli", "devtools", "coding", "automation"},
    "Machine Learning": {"machine-learning", "ml", "deep-learning", "pytorch", "tensorflow"},
    "Automation": {"github-actions", "telegram", "bot", "automation"},
}


def process_repositories(
    repositories: list[Repository],
    settings: Settings,
    star_history: dict[str, int] | None = None,
) -> list[Repository]:
    unique = _dedupe(repositories)
    filtered = [repo for repo in unique if _is_usable(repo, settings)]
    _score(filtered, settings, star_history or {})
    filtered.sort(key=lambda repo: (repo.score, repo.star_growth, repo.stargazers_count), reverse=True)
    return filtered[: settings.max_projects]


def _dedupe(repositories: list[Repository]) -> list[Repository]:
    by_name: dict[str, Repository] = {}
    for repo in repositories:
        if repo.full_name and repo.full_name not in by_name:
            by_name[repo.full_name] = repo
    return list(by_name.values())


def _is_usable(repo: Repository, settings: Settings) -> bool:
    if repo.archived or repo.fork:
        return False
    if repo.stargazers_count < settings.min_stars:
        return False
    if not repo.description.strip():
        return False
    if not _active_since(repo, settings.since_date):
        return False
    text = f"{repo.full_name} {repo.description}".lower()
    excluded = settings.interests.get("exclude_keywords", [])
    return not any(keyword.lower() in text for keyword in excluded)


def _score(repositories: list[Repository], settings: Settings, star_history: dict[str, int]) -> None:
    max_stars = max((repo.stargazers_count for repo in repositories), default=1)
    max_forks = max((repo.forks_count for repo in repositories), default=1)
    for repo in repositories:
        repo.star_growth = _star_growth(repo, star_history)
    max_growth = max((repo.star_growth for repo in repositories), default=0)

    for repo in repositories:
        star_score = repo.stargazers_count / max_stars if max_stars else 0
        fork_score = repo.forks_count / max_forks if max_forks else 0
        growth_score = repo.star_growth / max_growth if max_growth else 0
        topic_score = _topic_score(repo, settings)
        freshness_score = _freshness_score(repo.pushed_at or repo.updated_at, settings.days_back)
        repo.category = _category(repo)
        repo.score = round(
            0.25 * star_score
            + 0.05 * fork_score
            + 0.20 * topic_score
            + 0.40 * growth_score
            + 0.10 * freshness_score,
            4,
        )
        repo.selection_reasons = _selection_reasons(repo, topic_score)


def _star_growth(repo: Repository, star_history: dict[str, int]) -> int:
    previous = star_history.get(repo.full_name)
    if previous is None:
        return 0
    return max(0, repo.stargazers_count - previous)


def _topic_score(repo: Repository, settings: Settings) -> float:
    preferred = {item.lower() for item in settings.interests.get("preferred_topics", [])}
    preferred_languages = {item.lower() for item in settings.interests.get("preferred_languages", [])}
    repo_terms = {topic.lower() for topic in repo.topics}
    repo_terms.add(repo.language.lower())
    repo_terms.update(repo.full_name.lower().replace("/", " ").split())
    if repo.language.lower() in preferred_languages:
        repo_terms.add(repo.language.lower())
    if not preferred:
        return 0
    hits = len(preferred.intersection(repo_terms))
    return min(1.0, hits / 3)


def _selection_reasons(repo: Repository, topic_score: float) -> list[str]:
    reasons = []
    if repo.star_growth > 0:
        reasons.append(f"较上次记录新增 Star {repo.star_growth}，近期热度上升。")
    if repo.stargazers_count > 0:
        reasons.append(f"当前累计 Star {repo.stargazers_count}，具备一定社区关注度。")
    if topic_score > 0:
        reasons.append("仓库主题、语言或名称与关注方向匹配。")
    if repo.pushed_at or repo.updated_at:
        reasons.append("最近一周仍有更新或维护活动。")
    return reasons[:4]


def _freshness_score(created_at: str, days_back: int) -> float:
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        return 0
    age_days = max(0, (datetime.now(UTC) - created).days)
    return max(0.0, 1 - age_days / max(days_back, 1))


def _active_since(repo: Repository, since_date: str) -> bool:
    active_at = repo.pushed_at or repo.updated_at
    try:
        active = datetime.fromisoformat(active_at.replace("Z", "+00:00")).date()
        since = datetime.fromisoformat(since_date).date()
    except ValueError:
        return False
    return active >= since


def _category(repo: Repository) -> str:
    text = " ".join([repo.full_name, repo.description, repo.language, *repo.topics]).lower()
    for category, keywords in CATEGORIES.items():
        if any(keyword in text for keyword in keywords):
            return category
    return "Other"
