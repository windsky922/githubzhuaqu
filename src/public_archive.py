"""Field-level public projections for the weekly static archive.

The local JSON archive is the full operational source of truth.  This module
creates the narrower, rebuildable projection that may be copied to the public
``weekly-archive`` branch.  Unknown fields are deliberately discarded.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import Any


REPOSITORY_FIELDS = frozenset(
    {
        "archived",
        "category",
        "created_at",
        "description",
        "fork",
        "forks_count",
        "full_name",
        "html_url",
        "language",
        "license_name",
        "open_issues_count",
        "pushed_at",
        "quality_flags",
        "quality_level",
        "quality_score",
        "readme_summary",
        "score",
        "security_flags",
        "security_level",
        "security_score",
        "selection_reasons",
        "source_priority",
        "sources",
        "star_growth",
        "stargazers_count",
        "topics",
        "trending_period",
        "trending_rank",
        "updated_at",
    }
)
RUN_FIELDS = frozenset(
    {
        "collected_count",
        "collector_query_count",
        "collector_success_count",
        "collector_success_rate",
        "fallback_used",
        "kimi_used",
        "previously_sent_selected_count",
        "previously_sent_selected_rate",
        "readme_fetch_rate",
        "readme_fetched_count",
        "rag_freshness",
        "report_path",
        "run_date",
        "schema_version",
        "selected_count",
        "skipped_sent_count",
        "star_history_updated_count",
        "status",
        "telegram_explorer_url",
        "telegram_report_url",
        "telegram_runs_url",
        "telegram_sent",
        "trending_top10_available_count",
        "trending_top10_fulfillment_rate",
        "trending_top10_selected_count",
    }
)
RAG_FRESHNESS_FIELDS = frozenset(
    {
        "schema_version",
        "source_latest_date",
        "corpus_latest_date",
        "embedding_latest_date",
        "source_hash",
        "corpus_version",
        "corpus_hash",
        "chunk_count",
        "embedding_model",
        "embedding_hash",
        "embedding_count",
        "dimensions",
    }
)
TREND_FIELDS = frozenset(
    {
        "schema_version",
        "summary_points",
        "top_categories",
        "top_languages",
        "top_star_growth",
        "top_trending",
        "total_projects",
        "total_star_growth",
        "trending_project_count",
        "trending_selected_rate",
        "trending_top10_selected_count",
    }
)
TREND_PROJECT_FIELDS = frozenset({"category", "full_name", "html_url", "language", "star_growth", "stargazers_count"})
NAME_COUNT_FIELDS = frozenset({"count", "name"})


def project_archive_json(relative: PurePosixPath, payload: Any) -> Any:
    """Return a fail-closed public projection for one allowed data JSON file."""
    parts = relative.parts
    if len(parts) != 3 or parts[0] != "data" or parts[2] == "":
        raise ValueError("public archive JSON path is invalid")
    directory = parts[1]
    if directory in {"raw", "selected"}:
        if not isinstance(payload, list):
            raise ValueError("public repository archive JSON must be a list")
        return [_project_record(record, REPOSITORY_FIELDS) for record in payload if isinstance(record, Mapping)]
    if directory == "runs":
        if not isinstance(payload, Mapping):
            raise ValueError("public run archive JSON must be an object")
        projected = _project_record(payload, RUN_FIELDS)
        if isinstance(projected.get("rag_freshness"), Mapping):
            projected["rag_freshness"] = _project_record(projected["rag_freshness"], RAG_FRESHNESS_FIELDS)
        return projected
    if directory == "trends":
        if not isinstance(payload, Mapping):
            raise ValueError("public trend archive JSON must be an object")
        projected = _project_record(payload, TREND_FIELDS)
        for key in ("top_languages", "top_categories"):
            if isinstance(projected.get(key), list):
                projected[key] = [_project_record(item, NAME_COUNT_FIELDS) for item in projected[key] if isinstance(item, Mapping)]
        for key in ("top_star_growth", "top_trending"):
            if isinstance(projected.get(key), list):
                projected[key] = [_project_record(item, TREND_PROJECT_FIELDS) for item in projected[key] if isinstance(item, Mapping)]
        return projected
    raise ValueError("public archive JSON directory is not allowed")


def _project_record(record: Mapping[str, Any], fields: frozenset[str]) -> dict[str, Any]:
    return {key: record[key] for key in sorted(fields) if key in record}
