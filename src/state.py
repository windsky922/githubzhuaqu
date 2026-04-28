from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Repository
from .settings import Settings
from .utils import ensure_dir


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
    return [repo for repo in repositories if repo.full_name not in sent_names]


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
