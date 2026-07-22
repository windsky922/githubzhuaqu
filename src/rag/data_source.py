"""Resolve the RAG archive source without falling back to checkout data."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from src.rag.freshness import archive_freshness


def resolve_verified_weekly_source(*, app_root: Path, explicit_root: Path | None = None) -> dict[str, Any]:
    """Return a verified weekly snapshot, or a closed ``unknown`` selection.

    Production must opt in with ``GITHUB_WEEKLY_SNAPSHOT_ROOT``.  A root passed
    directly by a test/development app is explicit and never silently replaced
    with the checkout's ``main/data`` tree.
    """
    configured = os.getenv("GITHUB_WEEKLY_SNAPSHOT_ROOT", "").strip()
    candidate = explicit_root or (Path(configured) if configured else None)
    kind = "explicit_local" if explicit_root else "weekly_snapshot"
    if candidate is None:
        return _unavailable("missing_verified_weekly_snapshot")
    candidate = candidate.resolve()
    freshness = archive_freshness(candidate)
    valid = (
        freshness.get("data_freshness") in {"fresh", "lagging", "stale"}
        and bool(freshness.get("source_latest_date"))
        and bool(freshness.get("corpus_latest_date"))
        and bool(freshness.get("embedding_latest_date"))
    )
    if not valid:
        return _unavailable("invalid_weekly_freshness_attestation", freshness=freshness, explicit_local=explicit_root is not None)
    return {
        "available": True,
        "kind": kind,
        "root": candidate,
        "source_id": f"{kind}:{candidate.name}:{freshness.get('source_latest_date')}",
        "run_date": freshness.get("source_latest_date") or "",
        "attestation": freshness,
        "reason": "",
    }


def _unavailable(reason: str, *, freshness: dict[str, Any] | None = None, explicit_local: bool = False) -> dict[str, Any]:
    return {
        "available": False,
        "kind": "unknown",
        "root": None,
        "source_id": "unknown",
        "run_date": "",
        "attestation": freshness or {"data_freshness": "unknown", "reasons": [reason]},
        "reason": reason,
        "explicit_local": explicit_local,
    }
