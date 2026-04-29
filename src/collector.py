from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from .models import Repository
from .settings import Settings


GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
README_EXCERPT_LIMIT = 2000


def build_queries(settings: Settings) -> list[str]:
    since = settings.since_date
    min_stars = settings.min_stars
    return [
        f"pushed:>={since} stars:>{min_stars}",
        f"topic:ai pushed:>={since} stars:>{min_stars}",
        f"topic:agent pushed:>={since} stars:>10",
        f"topic:llm pushed:>={since} stars:>10",
        f"topic:automation pushed:>={since} stars:>10",
        f"language:Python pushed:>={since} stars:>{min_stars}",
        f"language:TypeScript pushed:>={since} stars:>{min_stars}",
    ]


def _request_json(url: str, token: str, timeout: int = 20) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-weekly-agent",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API error {error.code}: {body}") from error


def _request_text(url: str, token: str, timeout: int = 20) -> str:
    headers = {
        "Accept": "application/vnd.github.raw",
        "User-Agent": "github-weekly-agent",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub README API error {error.code}: {body}") from error


def search_repositories(query: str, settings: Settings) -> list[Repository]:
    params = urllib.parse.urlencode(
        {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": 30,
        }
    )
    data = _request_json(f"{GITHUB_SEARCH_URL}?{params}", settings.github_token)
    return [Repository.from_github_item(item) for item in data.get("items", [])]


def collect_repositories(settings: Settings) -> tuple[list[Repository], list[str], list[str], list[dict]]:
    queries = build_queries(settings)
    repositories: list[Repository] = []
    errors: list[str] = []
    stats: list[dict] = []

    for query in queries:
        try:
            results = search_repositories(query, settings)
            repositories.extend(results)
            stats.append({"query": query, "status": "success", "count": len(results), "error": ""})
        except Exception as error:  # Keep later queries useful if one query fails.
            errors.append(f"{query}: {error}")
            stats.append({"query": query, "status": "failed", "count": 0, "error": str(error)})

    if not repositories and errors:
        raise RuntimeError("; ".join(errors))
    return repositories, queries, errors, stats


def enrich_repositories_with_readmes(repositories: list[Repository], settings: Settings) -> int:
    fetched_count = 0
    for repo in repositories:
        try:
            readme = fetch_readme(repo.full_name, settings)
        except Exception:
            continue
        repo.readme_excerpt = _readme_excerpt(readme)
        if repo.readme_excerpt:
            fetched_count += 1
    return fetched_count


def fetch_readme(full_name: str, settings: Settings) -> str:
    parts = full_name.split("/", 1)
    if len(parts) != 2:
        return ""
    owner = urllib.parse.quote(parts[0], safe="")
    repo = urllib.parse.quote(parts[1], safe="")
    url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    return _request_text(url, settings.github_token)


def _readme_excerpt(readme: str, limit: int = README_EXCERPT_LIMIT) -> str:
    normalized = " ".join(readme.split())
    return normalized[:limit]
