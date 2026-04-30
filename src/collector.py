from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from .models import Repository
from .security import redact_sensitive_text
from .settings import Settings


GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
GITHUB_REPO_URL = "https://api.github.com/repos"
GITHUB_TRENDING_URL = "https://github.com/trending"
README_EXCERPT_LIMIT = 2000
README_SUMMARY_MAX_SENTENCES = 3
README_SUMMARY_MAX_LENGTH = 300
DEFAULT_SEARCH_TOPICS = ["ai", "agent", "llm", "automation"]
DEFAULT_SEARCH_LANGUAGES = ["Python", "TypeScript"]


def build_queries(settings: Settings) -> list[str]:
    since = settings.since_date
    min_stars = settings.min_stars
    topics = _list_interest(settings, "search_topics", DEFAULT_SEARCH_TOPICS)
    languages = _list_interest(settings, "search_languages", _list_interest(settings, "preferred_languages", DEFAULT_SEARCH_LANGUAGES))

    queries = [f"pushed:>={since} stars:>{min_stars}"]
    queries.extend(f"topic:{topic} pushed:>={since} stars:>10" for topic in topics[:6] if topic)
    queries.extend(f"language:{language} pushed:>={since} stars:>{min_stars}" for language in languages[:6] if language)
    return queries


class _TrendingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.full_names: list[str] = []
        self._article_depth = 0
        self._heading_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "article":
            self._article_depth += 1
            return
        if tag == "h2" and self._article_depth:
            self._heading_depth += 1
            return
        if tag != "a":
            return
        if not self._article_depth or not self._heading_depth:
            return
        href = dict(attrs).get("href") or ""
        full_name = _repo_name_from_href(href)
        if full_name and full_name not in self.full_names:
            self.full_names.append(full_name)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h2" and self._heading_depth:
            self._heading_depth -= 1
        elif tag == "article" and self._article_depth:
            self._article_depth -= 1


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


def _request_html(url: str, timeout: int = 20) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/html",
            "User-Agent": "github-weekly-agent",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub Trending error {error.code}: {body}") from error


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
    repositories = [_sanitize_repository(Repository.from_github_item(item)) for item in data.get("items", [])]
    for repo in repositories:
        repo.sources = ["github_search"]
        repo.source_priority = max(repo.source_priority, 10)
    return repositories


def fetch_repository(full_name: str, settings: Settings) -> Repository:
    parts = full_name.split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid repository name: {full_name}")
    owner = urllib.parse.quote(parts[0], safe="")
    repo = urllib.parse.quote(parts[1], safe="")
    data = _request_json(f"{GITHUB_REPO_URL}/{owner}/{repo}", settings.github_token)
    return _sanitize_repository(Repository.from_github_item(data))


def collect_trending_repositories(settings: Settings) -> tuple[list[Repository], list[str], list[str], list[dict]]:
    if not _trending_enabled(settings):
        return [], [], [], []

    repositories: list[Repository] = []
    queries: list[str] = []
    errors: list[str] = []
    stats: list[dict] = []
    max_repositories = _int_interest(settings, "trending_max_repositories", 25)

    for label, url in build_trending_sources(settings):
        queries.append(label)
        source_errors = []
        source_count = 0
        try:
            names = fetch_trending_repository_names(url)
            for rank, full_name in enumerate(names[:max_repositories], start=1):
                try:
                    repo = fetch_repository(full_name, settings)
                except Exception as error:
                    source_errors.append(f"{full_name}: {error}")
                    continue
                repo.sources = ["github_trending"]
                repo.trending_rank = rank
                repo.trending_period = "weekly"
                repo.source_priority = max(repo.source_priority, 100)
                repositories.append(repo)
                source_count += 1
        except Exception as error:
            errors.append(f"{label}: {error}")
            stats.append({"source": "github_trending", "query": label, "status": "failed", "count": 0, "error": str(error)})
            continue

        errors.extend(f"{label} {error}" for error in source_errors)
        stats.append(
            {
                "source": "github_trending",
                "query": label,
                "status": "partial" if source_errors else "success",
                "count": source_count,
                "error": "; ".join(source_errors[:3]),
            }
        )
    return repositories, queries, errors, stats


def build_trending_sources(settings: Settings) -> list[tuple[str, str]]:
    sources = [("GitHub Trending weekly", f"{GITHUB_TRENDING_URL}?since=weekly")]
    languages = _list_interest(settings, "trending_languages", [])
    for language in languages[:6]:
        slug = urllib.parse.quote(str(language).strip().lower(), safe="")
        if slug:
            sources.append((f"GitHub Trending weekly language:{language}", f"{GITHUB_TRENDING_URL}/{slug}?since=weekly"))
    return sources


def fetch_trending_repository_names(url: str) -> list[str]:
    return _parse_trending_repository_names(_request_html(url))


def _parse_trending_repository_names(html: str) -> list[str]:
    parser = _TrendingParser()
    parser.feed(html)
    return parser.full_names


def _repo_name_from_href(href: str) -> str:
    path = href.split("?", 1)[0].strip("/")
    parts = path.split("/")
    if len(parts) != 2:
        return ""
    owner, repo = parts
    if not owner or not repo:
        return ""
    ignored = {
        "apps",
        "collections",
        "features",
        "login",
        "marketplace",
        "orgs",
        "settings",
        "sponsors",
        "topics",
        "trending",
        "users",
    }
    if owner in ignored:
        return ""
    return f"{owner}/{repo}"


def _trending_enabled(settings: Settings) -> bool:
    return settings.interests.get("enable_github_trending", True) is not False


def _list_interest(settings: Settings, key: str, default: list[str]) -> list[str]:
    if key not in settings.interests:
        return default
    value = settings.interests.get(key)
    if not isinstance(value, list):
        return default
    return value


def _int_interest(settings: Settings, key: str, default: int) -> int:
    try:
        value = int(settings.interests.get(key, default))
    except (TypeError, ValueError):
        return default
    return max(1, value)


def collect_repositories(settings: Settings) -> tuple[list[Repository], list[str], list[str], list[dict]]:
    search_queries = build_queries(settings)
    repositories, queries, errors, stats = collect_trending_repositories(settings)

    for query in search_queries:
        queries.append(query)
        try:
            results = search_repositories(query, settings)
            repositories.extend(results)
            stats.append({"source": "github_search", "query": query, "status": "success", "count": len(results), "error": ""})
        except Exception as error:  # Keep later queries useful if one query fails.
            errors.append(f"{query}: {error}")
            stats.append({"source": "github_search", "query": query, "status": "failed", "count": 0, "error": str(error)})

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
        repo.readme_summary = _readme_excerpt(readme)
        repo.readme_excerpt = repo.readme_summary
        if repo.readme_summary:
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
    summary = summarize_readme(readme, max_length=min(limit, README_SUMMARY_MAX_LENGTH))
    return summary[:limit]


def summarize_readme(readme: str, max_length: int = README_SUMMARY_MAX_LENGTH) -> str:
    cleaned = _clean_readme_for_summary(redact_sensitive_text(readme))
    sentences = _readme_sentences(cleaned)
    if not sentences:
        sentences = _readme_fragments(cleaned)
    if not sentences:
        return ""
    summary = _join_limited_sentences(sentences, max_length)
    return summary if summary else sentences[0][:max_length].rstrip()


def _clean_readme_for_summary(readme: str) -> str:
    lines = []
    in_code_block = False
    for raw_line in readme.splitlines():
        line = raw_line.strip()
        if line.startswith("```") or line.startswith("~~~"):
            in_code_block = not in_code_block
            continue
        if in_code_block or not line:
            continue
        if _skip_readme_line(line):
            continue
        lines.append(_clean_readme_line(line))
    text = " ".join(line for line in lines if line)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _skip_readme_line(line: str) -> bool:
    lowered = line.lower()
    heading_text = re.sub(r"^#{1,6}\s*", "", lowered).strip()
    if re.match(r"^#{1,6}\s+", line):
        return True
    if line.startswith(("!", "[!", "<p ", "<div ", "<img ", "<a ")):
        return True
    if line.startswith("|") and line.endswith("|"):
        return True
    if re.fullmatch(r"[-*_=\s]{3,}", line):
        return True
    if lowered.startswith(("[toc]", "table of contents", "contents")):
        return True
    if heading_text in {
        "installation",
        "install",
        "usage",
        "quick start",
        "getting started",
        "documentation",
        "docs",
        "license",
        "contributing",
        "contributors",
        "sponsors",
        "support",
        "acknowledgements",
    }:
        return True
    return False


def _clean_readme_line(line: str) -> str:
    line = re.sub(r"^#{1,6}\s*", "", line)
    line = re.sub(r"!\[[^\]]*]\([^)]*\)", "", line)
    line = re.sub(r"\[([^\]]+)]\([^)]*\)", r"\1", line)
    line = re.sub(r"`([^`]+)`", r"\1", line)
    line = re.sub(r"^[>*\-\d.)\s]+", "", line)
    return line.strip()


def _readme_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?。！？])\s+", text)
    sentences = []
    for part in parts:
        sentence = part.strip(" -:;，,")
        if _usable_readme_sentence(sentence):
            sentences.append(sentence)
        if len(sentences) >= README_SUMMARY_MAX_SENTENCES:
            break
    return sentences


def _readme_fragments(text: str) -> list[str]:
    fragments = []
    for part in re.split(r"\s{2,}|[;；]", text):
        fragment = part.strip(" -:;，,。")
        if _usable_readme_sentence(fragment):
            fragments.append(_ensure_sentence_end(fragment))
        if len(fragments) >= README_SUMMARY_MAX_SENTENCES:
            break
    return fragments


def _ensure_sentence_end(text: str) -> str:
    return text if re.search(r"[.!?。！？]$", text) else text + "。"


def _usable_readme_sentence(sentence: str) -> bool:
    if len(sentence) < 18:
        return False
    lowered = sentence.lower()
    noisy_markers = ("http://", "https://", "npm install", "pip install", "docker run", "git clone")
    if any(marker in lowered for marker in noisy_markers):
        return False
    letters = re.findall(r"[A-Za-z\u4e00-\u9fff]", sentence)
    return len(letters) >= 12


def _join_limited_sentences(sentences: list[str], max_length: int) -> str:
    selected = []
    total = 0
    for sentence in sentences:
        next_total = total + len(sentence) + (1 if selected else 0)
        if selected and next_total > max_length:
            break
        selected.append(sentence)
        total = next_total
    return " ".join(selected).strip()


def _sanitize_repository(repo: Repository) -> Repository:
    repo.description = redact_sensitive_text(repo.description)
    return repo
