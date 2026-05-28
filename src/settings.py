from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    root: Path
    run_date: str
    since_date: str
    days_back: int
    min_stars: int
    max_projects: int
    github_token: str
    kimi_api_key: str
    kimi_base_url: str
    kimi_model: str
    telegram_bot_token: str
    telegram_chat_id: str
    interests: dict
    report_base_url: str = ""


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name, "")
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def load_interests(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def load_project_interests(root: Path = ROOT) -> dict:
    custom_path = root / "config" / "interests.json"
    if custom_path.exists():
        interests = load_interests(custom_path)
    else:
        interests = load_interests(root / "config" / "interests.example.json")

    from .personalization import apply_interest_profiles, load_project_profiles, selected_profile_names

    profiles = load_project_profiles(root)
    profile_names = selected_profile_names(interests, os.getenv("INTEREST_PROFILE", ""))
    interests = apply_interest_profiles(interests, profiles, profile_names)
    return apply_runtime_interest_overrides(interests)


def apply_runtime_interest_overrides(interests: dict) -> dict:
    """合并任务级偏好，不修改本地配置文件。"""
    output = dict(interests)
    languages = _list_env("INTEREST_LANGUAGE")
    topics = [*_list_env("INTEREST_CATEGORY"), *_list_env("INTEREST_QUERY")]
    if languages:
        output["preferred_languages"] = _merge_unique(output.get("preferred_languages", []), languages)
        output["search_languages"] = _merge_unique(output.get("search_languages", []), languages)
    if topics:
        output["preferred_topics"] = _merge_unique(output.get("preferred_topics", []), topics)
        output["search_topics"] = _merge_unique(output.get("search_topics", []), topics)
    return output


def _list_env(name: str) -> list[str]:
    value = os.getenv(name, "")
    for char in "，,;/|":
        value = value.replace(char, " ")
    return [item.strip() for item in value.split() if item.strip()]


def _merge_unique(existing: object, extra: list[str]) -> list[str]:
    result = []
    seen = set()
    for item in [*(existing if isinstance(existing, list) else []), *extra]:
        text = str(item).strip()
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result


def load_settings(run_date: str, since_date: str) -> Settings:
    interests = load_project_interests(ROOT)
    return Settings(
        root=ROOT,
        run_date=run_date,
        since_date=since_date,
        days_back=_int_env("DAYS_BACK", 7),
        min_stars=_int_env("MIN_STARS", int(interests.get("min_stars", 20) or 20)),
        max_projects=_int_env("MAX_PROJECTS", int(interests.get("max_projects", 10) or 10)),
        github_token=os.getenv("GH_SEARCH_TOKEN") or os.getenv("GITHUB_TOKEN", ""),
        kimi_api_key=os.getenv("KIMI_API_KEY", ""),
        kimi_base_url=os.getenv("KIMI_BASE_URL") or "https://api.moonshot.cn/v1",
        kimi_model=os.getenv("KIMI_MODEL", ""),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        interests=interests,
        report_base_url=os.getenv("REPORT_BASE_URL", ""),
    )
