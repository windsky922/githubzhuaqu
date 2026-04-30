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
DEFAULT_SCORE_WEIGHTS = {
    "trending": 0.45,
    "star_growth": 0.25,
    "topic": 0.15,
    "freshness": 0.10,
    "community": 0.05,
}
TRENDING_TOP_RANK_LIMIT = 10
DEFAULT_MIN_TRENDING_TOP_PROJECTS = 7


def process_repositories(
    repositories: list[Repository],
    settings: Settings,
    star_history: dict[str, int] | None = None,
) -> list[Repository]:
    unique = _dedupe(repositories)
    filtered = [repo for repo in unique if _is_usable(repo, settings)]
    _score(filtered, settings, star_history or {})
    ranked = sorted(
        filtered,
        key=lambda repo: (repo.score, repo.source_priority, -repo.trending_rank, repo.star_growth, repo.stargazers_count),
        reverse=True,
    )
    return _select_with_trending_floor(ranked, settings)


def _select_with_trending_floor(ranked: list[Repository], settings: Settings) -> list[Repository]:
    max_projects = settings.max_projects
    min_trending = min(_int_interest(settings, "min_trending_top10_projects", DEFAULT_MIN_TRENDING_TOP_PROJECTS), max_projects)
    protected_trending = sorted(
        [repo for repo in ranked if 0 < repo.trending_rank <= TRENDING_TOP_RANK_LIMIT],
        key=lambda repo: repo.trending_rank,
    )[:min_trending]
    selected: list[Repository] = []
    selected_names: set[str] = set()
    for repo in protected_trending + ranked:
        if repo.full_name in selected_names:
            continue
        selected.append(repo)
        selected_names.add(repo.full_name)
        if len(selected) >= max_projects:
            break
    return selected


def _dedupe(repositories: list[Repository]) -> list[Repository]:
    by_name: dict[str, Repository] = {}
    for repo in repositories:
        if not repo.full_name:
            continue
        if repo.full_name not in by_name:
            by_name[repo.full_name] = repo
        else:
            _merge_repository_signals(by_name[repo.full_name], repo)
    return list(by_name.values())


def _merge_repository_signals(target: Repository, source: Repository) -> None:
    target.sources = sorted(set(target.sources + source.sources))
    if source.trending_rank and (not target.trending_rank or source.trending_rank < target.trending_rank):
        target.trending_rank = source.trending_rank
        target.trending_period = source.trending_period
    target.source_priority = max(target.source_priority, source.source_priority)


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
    max_trending_rank = max((repo.trending_rank for repo in repositories if repo.trending_rank > 0), default=0)
    weights = _score_weights(settings)

    for repo in repositories:
        star_score = repo.stargazers_count / max_stars if max_stars else 0
        fork_score = repo.forks_count / max_forks if max_forks else 0
        growth_score = repo.star_growth / max_growth if max_growth else 0
        trending_score = _trending_score(repo, max_trending_rank)
        topic_score = _topic_score(repo, settings)
        profile_matches = _profile_matches(repo, settings)
        freshness_score = _freshness_score(repo.pushed_at or repo.updated_at, settings.days_back)
        community_score = (star_score + fork_score) / 2
        repo.category = _category(repo)
        repo.score = round(
            weights["trending"] * trending_score
            + weights["star_growth"] * growth_score
            + weights["topic"] * topic_score
            + weights["freshness"] * freshness_score
            + weights["community"] * community_score,
            4,
        )
        repo.selection_reasons = _selection_reasons(repo, topic_score, profile_matches)


def _star_growth(repo: Repository, star_history: dict[str, int]) -> int:
    previous = star_history.get(repo.full_name)
    if previous is None:
        return 0
    return max(0, repo.stargazers_count - previous)


def _trending_score(repo: Repository, max_rank: int) -> float:
    if not repo.trending_rank or not max_rank:
        return 0
    return max(0.0, (max_rank - repo.trending_rank + 1) / max_rank)


def _score_weights(settings: Settings) -> dict[str, float]:
    configured = settings.interests.get("score_weights", {}) or {}
    weights = DEFAULT_SCORE_WEIGHTS.copy()
    for key in weights:
        try:
            value = float(configured.get(key, weights[key]))
        except (TypeError, ValueError):
            continue
        if value >= 0:
            weights[key] = value
    total = sum(weights.values())
    if total <= 0:
        return DEFAULT_SCORE_WEIGHTS.copy()
    return {key: value / total for key, value in weights.items()}


def _int_interest(settings: Settings, key: str, default: int) -> int:
    try:
        value = int(settings.interests.get(key, default))
    except (TypeError, ValueError):
        return default
    return max(0, value)


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


def _profile_matches(repo: Repository, settings: Settings) -> list[str]:
    rules = settings.interests.get("profile_match_rules") or []
    text = " ".join([repo.full_name, repo.description, repo.language, *repo.topics]).lower()
    language = repo.language.lower()
    matches = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        label = str(rule.get("label") or rule.get("name") or "").strip()
        if not label:
            continue
        preferred_languages = {str(item).lower() for item in rule.get("preferred_languages", [])}
        preferred_topics = [str(item).lower() for item in rule.get("preferred_topics", [])]
        language_matched = language in preferred_languages
        topic_matched = any(topic and topic in text for topic in preferred_topics)
        if (language_matched or topic_matched) and label not in matches:
            matches.append(label)
    return matches


def _selection_reasons(repo: Repository, topic_score: float, profile_matches: list[str]) -> list[str]:
    reasons = []
    if repo.trending_rank > 0:
        reasons.append(f"进入 GitHub Trending 周榜第 {repo.trending_rank} 位，是本期最重要的热度信号。")
    if repo.star_growth > 0:
        reasons.append(f"较上次记录新增 Star {repo.star_growth}，近期热度上升。")
    if profile_matches:
        reasons.append(f"匹配当前个性化方向：{'、'.join(profile_matches)}。")
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
