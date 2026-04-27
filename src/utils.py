from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path


def date_range(days_back: int = 7) -> tuple[str, str]:
    today = datetime.now(UTC).date()
    since = today - timedelta(days=days_back)
    return today.isoformat(), since.isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def chunk_text(text: str, limit: int = 3500) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text.strip()
    while len(remaining) > limit:
        split_at = max(
            remaining.rfind("\n## ", 0, limit),
            remaining.rfind("\n\n", 0, limit),
            remaining.rfind("\n", 0, limit),
        )
        if split_at < limit // 3:
            split_at = limit
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


def clean_error(error: Exception) -> str:
    message = str(error)
    if len(message) > 500:
        return message[:500] + "..."
    return message

