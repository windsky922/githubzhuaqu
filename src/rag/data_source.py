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


def resolve_local_archive_source(*, app_root: Path) -> dict[str, Any]:
    """Describe the checkout archive for explicit local-only fallback.

    This intentionally does not treat an unattested checkout as a verified
    weekly snapshot.  It is only selected by ``GITHUB_WEEKLY_DATA_MODE=local``.
    """
    root = app_root.resolve()
    sqlite_path = root / "data" / "github_weekly.sqlite"
    json_root = root / "data"
    run_dates = sorted(
        (path.stem for path in (json_root / "runs").glob("*.json") if path.stem),
        reverse=True,
    ) if (json_root / "runs").is_dir() else []
    run_date = run_dates[0] if run_dates else ""
    kind = "local_archive_sqlite" if sqlite_path.is_file() else "local_archive_json"
    available = sqlite_path.is_file() or (json_root / "selected").is_dir()
    return {
        "available": available,
        "kind": kind,
        "root": root if available else None,
        "source_id": f"{kind}:{root.name}:{run_date or 'unknown'}",
        "run_date": run_date,
        "attestation": {
            "data_freshness": "stale" if run_date else "unknown",
            "source_latest_date": run_date,
            "corpus_latest_date": "",
            "embedding_latest_date": "",
            "stale_days": None,
            "stale_after_days": 30,
            "reasons": ["local_archive_history_only"],
        },
        "reason": "" if available else "missing_local_archive",
        "explicit_local": True,
        "history_only": True,
        "read_only": True,
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
