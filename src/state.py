from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Repository
from .settings import Settings
from .utils import ensure_dir

TRENDING_DEDUP_RANK_LIMIT = 10


def load_sent_repository_names(settings: Settings) -> set[str]:
    path = _state_path(settings)
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    return _names_from_state(data)


def filter_unsent_repositories(repositories: list[Repository], sent_names: set[str]) -> list[Repository]:
    return [repo for repo in repositories if repo.full_name not in sent_names or _is_top_trending(repo)]


def _is_top_trending(repo: Repository) -> bool:
    return 0 < repo.trending_rank <= TRENDING_DEDUP_RANK_LIMIT


def write_sent_repositories(repositories: list[Repository], settings: Settings) -> str:
    path = _state_path(settings)
    ensure_dir(path.parent)
    existing = _load_state_items(settings)
    by_name = {
        str(item.get("full_name")): item
        for item in existing
        if isinstance(item, dict) and item.get("full_name")
    }
    for repo in repositories:
        if not repo.full_name:
            continue
        by_name.setdefault(
            repo.full_name,
            {
                "full_name": repo.full_name,
                "html_url": repo.html_url,
                "first_sent_at": settings.run_date,
            },
        )
    data = sorted(by_name.values(), key=lambda item: str(item.get("full_name", "")).lower())
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path.relative_to(settings.root).as_posix()


def load_star_history(settings: Settings) -> dict[str, int]:
    path = _star_history_path(settings)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, list):
        return {}
    history = {}
    for item in data:
        if not isinstance(item, dict) or not item.get("full_name"):
            continue
        try:
            history[str(item["full_name"])] = int(item.get("stargazers_count") or 0)
        except (TypeError, ValueError):
            continue
    return history


def write_star_history(repositories: list[Repository], settings: Settings) -> tuple[str, int]:
    path = _star_history_path(settings)
    ensure_dir(path.parent)
    existing = _load_star_history_items(settings)
    by_name = {
        str(item.get("full_name")): item
        for item in existing
        if isinstance(item, dict) and item.get("full_name")
    }
    updated_names = set()
    for repo in repositories:
        if not repo.full_name:
            continue
        by_name[repo.full_name] = {
            "full_name": repo.full_name,
            "html_url": repo.html_url,
            "stargazers_count": repo.stargazers_count,
            "last_seen_at": settings.run_date,
        }
        updated_names.add(repo.full_name)
    data = sorted(by_name.values(), key=lambda item: str(item.get("full_name", "")).lower())
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path.relative_to(settings.root).as_posix(), len(updated_names)


def _load_state_items(settings: Settings) -> list[dict[str, Any]]:
    path = _state_path(settings)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    items = []
    for item in data:
        if isinstance(item, str):
            items.append({"full_name": item, "html_url": "", "first_sent_at": ""})
        elif isinstance(item, dict):
            items.append(item)
    return items


def _load_star_history_items(settings: Settings) -> list[dict[str, Any]]:
    path = _star_history_path(settings)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _names_from_state(data: Any) -> set[str]:
    if not isinstance(data, list):
        return set()
    names = set()
    for item in data:
        if isinstance(item, str):
            names.add(item)
        elif isinstance(item, dict) and item.get("full_name"):
            names.add(str(item["full_name"]))
    return names


def _state_path(settings: Settings) -> Path:
    return settings.root / "data" / "state" / "sent_repos.json"


def _star_history_path(settings: Settings) -> Path:
    return settings.root / "data" / "state" / "star_history.json"
