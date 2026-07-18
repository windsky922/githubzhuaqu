from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any


DEFAULT_STALE_AFTER_DAYS = 8
_DATE_FIELDS = ("source_latest_date", "corpus_latest_date", "embedding_latest_date")


def archive_freshness(
    root: Path,
    *,
    as_of: date | str | None = None,
    stale_after_days: int = DEFAULT_STALE_AFTER_DAYS,
) -> dict[str, Any]:
    """Read only public run artifacts; never infer freshness from runtime SQLite."""
    current = _parse_date(as_of) or date.today()
    reasons: list[str] = []
    source_dates: list[date] = []
    corpus_dates: list[date] = []
    embedding_dates: list[date] = []
    runs_dir = root / "data" / "runs"

    if not runs_dir.is_dir():
        reasons.append("missing_source_runs")
    else:
        for path in sorted(runs_dir.glob("*.json")):
            file_date = _parse_date(path.stem)
            payload = _read_object(path)
            payload_date = _parse_date(payload.get("run_date")) if payload else None
            if not file_date or not payload_date or file_date != payload_date:
                reasons.append("invalid_source_run")
                continue
            source_dates.append(payload_date)
            attestation = payload.get("rag_freshness")
            if not isinstance(attestation, dict):
                continue
            source_attested = _parse_date(attestation.get("source_latest_date"))
            corpus_attested = _parse_date(attestation.get("corpus_latest_date"))
            embedding_attested = _parse_date(attestation.get("embedding_latest_date"))
            if source_attested and source_attested != payload_date:
                reasons.append("invalid_freshness_attestation")
                continue
            if corpus_attested:
                corpus_dates.append(corpus_attested)
            if embedding_attested:
                embedding_dates.append(embedding_attested)

    values = {
        "source_latest_date": _latest_iso(source_dates),
        "corpus_latest_date": _latest_iso(corpus_dates),
        "embedding_latest_date": _latest_iso(embedding_dates),
    }
    parsed = {key: _parse_date(value) for key, value in values.items()}
    if not parsed["source_latest_date"]:
        reasons.append("missing_source_latest_date")
    if not parsed["corpus_latest_date"]:
        reasons.append("missing_corpus_latest_date")
    if not parsed["embedding_latest_date"]:
        reasons.append("missing_embedding_latest_date")
    if parsed["source_latest_date"] and parsed["corpus_latest_date"] and parsed["corpus_latest_date"] < parsed["source_latest_date"]:
        reasons.append("corpus_behind_source")
    if parsed["corpus_latest_date"] and parsed["embedding_latest_date"] and parsed["embedding_latest_date"] < parsed["corpus_latest_date"]:
        reasons.append("embedding_behind_corpus")

    ages = [(current - value).days for value in parsed.values() if value]
    stale_days = max(ages) if ages else None
    if any(age < 0 for age in ages):
        reasons.append("future_attestation_date")
    if stale_days is not None and stale_days > stale_after_days:
        reasons.append("stale_age")

    if any(reason.startswith("missing_") or reason.startswith("invalid_") or reason == "future_attestation_date" for reason in reasons):
        status = "unknown"
    elif "corpus_behind_source" in reasons or "embedding_behind_corpus" in reasons:
        status = "lagging"
    elif "stale_age" in reasons:
        status = "stale"
    else:
        status = "fresh"
    return {
        **values,
        "stale_days": stale_days,
        "data_freshness": status,
        "as_of": current.isoformat(),
        "stale_after_days": stale_after_days,
        "reasons": sorted(set(reasons)),
    }


def is_time_sensitive_query(query: str) -> bool:
    normalized = str(query or "").lower()
    markers = ("最新", "当前", "近期", "最近", "现状", "本周", "本月", "今天", "latest", "current", "recent", "today")
    return any(marker in normalized for marker in markers)


def normalize_freshness(value: Any) -> dict[str, Any]:
    freshness = value if isinstance(value, dict) else {}
    result = {key: str(freshness.get(key) or "") for key in _DATE_FIELDS}
    status = str(freshness.get("data_freshness") or "unknown")
    result.update(
        {
            "stale_days": freshness.get("stale_days") if isinstance(freshness.get("stale_days"), int) else None,
            "data_freshness": status if status in {"fresh", "lagging", "stale", "unknown"} else "unknown",
            "as_of": str(freshness.get("as_of") or ""),
            "stale_after_days": freshness.get("stale_after_days") if isinstance(freshness.get("stale_after_days"), int) else DEFAULT_STALE_AFTER_DAYS,
            "reasons": [str(item) for item in freshness.get("reasons", []) if str(item)] if isinstance(freshness.get("reasons"), list) else [],
        }
    )
    return result


def _read_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value or ""))
    except ValueError:
        return None


def _latest_iso(values: list[date]) -> str:
    return max(values).isoformat() if values else ""
