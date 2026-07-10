from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any


PATTERNS = {
    "html_tags": re.compile(r"<[^>]+>"),
    "markdown_images": re.compile(r"!\[[^\]]*\]\([^)]*\)"),
    "badge_urls": re.compile(r"shields\.io|img\.shields|trendshift", re.IGNORECASE),
    "html_attributes": re.compile(r"\b(?:href|src|width|height)\s*=", re.IGNORECASE),
}


def audit_rag_corpus(db_path: Path) -> dict[str, Any]:
    connection = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute("SELECT corpus_id, chunk_text FROM rag_chunks ORDER BY corpus_id, chunk_id").fetchall()
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(project_corpus)").fetchall()}
        versions = []
        if {"corpus_version", "cleaner_version"}.issubset(columns):
            versions = [dict(row) for row in connection.execute(
                "SELECT corpus_version, cleaner_version, COUNT(*) AS count FROM project_corpus GROUP BY corpus_version, cleaner_version"
            ).fetchall()]
    finally:
        connection.close()
    counts = {name: 0 for name in PATTERNS}
    duplicates = 0
    seen_by_corpus: dict[str, set[str]] = {}
    for row in rows:
        text = str(row["chunk_text"] or "")
        for name, pattern in PATTERNS.items():
            counts[name] += len(pattern.findall(text))
        seen = seen_by_corpus.setdefault(str(row["corpus_id"]), set())
        key = text.casefold().strip()
        if key in seen:
            duplicates += 1
        elif key:
            seen.add(key)
    return {
        "schema_version": 1,
        "chunk_count": len(rows),
        "noise_counts": counts,
        "duplicate_chunks_within_corpus": duplicates,
        "versions": versions,
        "passed": not any(counts.values()) and duplicates == 0,
    }
