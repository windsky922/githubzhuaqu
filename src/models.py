from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Repository:
    full_name: str
    html_url: str
    description: str
    stargazers_count: int
    forks_count: int
    language: str
    created_at: str
    updated_at: str
    pushed_at: str = ""
    topics: list[str] = field(default_factory=list)
    archived: bool = False
    fork: bool = False
    open_issues_count: int = 0
    license_name: str = ""
    readme_excerpt: str = ""
    star_growth: int = 0
    score: float = 0.0
    category: str = "Other"

    @classmethod
    def from_github_item(cls, item: dict[str, Any]) -> "Repository":
        license_data = item.get("license") or {}
        return cls(
            full_name=str(item.get("full_name") or ""),
            html_url=str(item.get("html_url") or ""),
            description=str(item.get("description") or ""),
            stargazers_count=int(item.get("stargazers_count") or 0),
            forks_count=int(item.get("forks_count") or 0),
            language=str(item.get("language") or "Unknown"),
            created_at=str(item.get("created_at") or ""),
            updated_at=str(item.get("updated_at") or ""),
            pushed_at=str(item.get("pushed_at") or item.get("updated_at") or ""),
            topics=list(item.get("topics") or []),
            archived=bool(item.get("archived") or False),
            fork=bool(item.get("fork") or False),
            open_issues_count=int(item.get("open_issues_count") or 0),
            license_name=str(license_data.get("spdx_id") or license_data.get("name") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunSummary:
    run_date: str
    status: str = "started"
    queries: list[str] = field(default_factory=list)
    collected_count: int = 0
    selected_count: int = 0
    skipped_sent_count: int = 0
    readme_fetched_count: int = 0
    star_history_updated_count: int = 0
    report_path: str = ""
    run_summary_path: str = ""
    state_path: str = ""
    star_history_path: str = ""
    kimi_used: bool = False
    fallback_used: bool = False
    report_error: str = ""
    telegram_sent: bool = False
    telegram_error: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
