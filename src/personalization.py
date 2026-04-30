from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .settings import load_interests


MERGE_LIST_KEYS = {
    "exclude_keywords",
    "preferred_languages",
    "preferred_topics",
    "search_languages",
    "search_topics",
    "trending_languages",
}


PROFILE_KEYS = ("active_profiles", "active_profile")


def load_project_profiles(root: Path) -> dict:
    custom_path = root / "config" / "profiles.json"
    if custom_path.exists():
        return load_interests(custom_path)
    return load_interests(root / "config" / "profiles.example.json")


def selected_profile_names(interests: dict, env_value: str = "") -> list[str]:
    if env_value:
        return _split_profile_names(env_value)
    for key in PROFILE_KEYS:
        names = _profile_names_from_value(interests.get(key))
        if names:
            return names
    return []


def apply_interest_profiles(interests: dict, profiles: dict, profile_names: list[str]) -> dict:
    merged = deepcopy(interests)
    errors = []
    applied = []
    for profile_name in profile_names:
        profile = profiles.get(profile_name)
        if not isinstance(profile, dict):
            errors.append(f"未找到个性化 profile：{profile_name}")
            continue
        merged = _merge_profile(merged, profile)
        applied.append(profile_name)

    if applied:
        merged["active_profiles"] = applied
        merged["active_profile"] = applied[0]
        merged["profile_labels"] = [
            str(profiles[name].get("profile_label") or name)
            for name in applied
            if isinstance(profiles.get(name), dict)
        ]
        merged["profile_match_rules"] = [
            _profile_match_rule(name, profiles[name])
            for name in applied
            if isinstance(profiles.get(name), dict)
        ]
    if errors:
        merged["profile_errors"] = errors
    return merged


def apply_interest_profile(interests: dict, profiles: dict, profile_name: str) -> dict:
    return apply_interest_profiles(interests, profiles, _split_profile_names(profile_name))


def _merge_profile(interests: dict, profile: dict) -> dict:
    merged = deepcopy(interests)
    for key, value in profile.items():
        if key in MERGE_LIST_KEYS:
            merged[key] = _merge_lists(merged.get(key, []), value)
        elif key == "score_weights" and isinstance(value, dict):
            weights = dict(merged.get("score_weights") or {})
            weights.update(value)
            merged[key] = weights
        else:
            merged[key] = deepcopy(value)
    return merged


def _merge_lists(base: object, extra: object) -> list:
    result = []
    for item in _as_list(base) + _as_list(extra):
        if item not in result:
            result.append(item)
    return result


def _as_list(value: object) -> list:
    return value if isinstance(value, list) else []


def _profile_match_rule(name: str, profile: dict) -> dict:
    return {
        "name": name,
        "label": str(profile.get("profile_label") or name),
        "preferred_topics": _as_list(profile.get("preferred_topics")),
        "preferred_languages": _as_list(profile.get("preferred_languages")),
    }


def _profile_names_from_value(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return _split_profile_names(value)
    return []


def _split_profile_names(value: str) -> list[str]:
    names = []
    for item in value.replace(";", ",").split(","):
        name = item.strip()
        if name and name not in names:
            names.append(name)
    return names
