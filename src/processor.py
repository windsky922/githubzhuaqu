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


def process_repositories(repositories: list[Repository], settings: Settings) -> list[Repository]:
    unique = _dedupe(repositories)
    filtered = [repo for repo in unique if _is_usable(repo, settings)]
    _score(filtered, settings)
    filtered.sort(key=lambda repo: repo.score, reverse=True)
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
    text = f"{repo.full_name} {repo.description}".lower()
    excluded = settings.interests.get("exclude_keywords", [])
    return not any(keyword.lower() in text for keyword in excluded)


def _score(repositories: list[Repository], settings: Settings) -> None:
    max_stars = max((repo.stargazers_count for repo in repositories), default=1)
    max_forks = max((repo.forks_count for repo in repositories), default=1)

    for repo in repositories:
        star_score = repo.stargazers_count / max_stars if max_stars else 0
        fork_score = repo.forks_count / max_forks if max_forks else 0
        topic_score = _topic_score(repo, settings)
        freshness_score = _freshness_score(repo.created_at, settings.days_back)
        repo.category = _category(repo)
        repo.score = round(
            0.45 * star_score
            + 0.20 * fork_score
            + 0.25 * topic_score
            + 0.10 * freshness_score,
            4,
        )


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


def _freshness_score(created_at: str, days_back: int) -> float:
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        return 0
    age_days = max(0, (datetime.now(UTC) - created).days)
    return max(0.0, 1 - age_days / max(days_back, 1))


def _category(repo: Repository) -> str:
    text = " ".join([repo.full_name, repo.description, repo.language, *repo.topics]).lower()
    for category, keywords in CATEGORIES.items():
        if any(keyword in text for keyword in keywords):
            return category
    return "Other"

