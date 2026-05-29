from __future__ import annotations

import json
import math
import re
import sqlite3
from datetime import UTC, datetime
from hashlib import sha1
from pathlib import Path
from typing import Any

from src.storage.sqlite_store import connect, initialize

MODEL_NAME = "local-hash-v1"
DEFAULT_DIMENSIONS = 64
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_+\-#]+|[\u4e00-\u9fff]")


def build_rag_embeddings(db_path: Path, *, model: str = MODEL_NAME, dimensions: int = DEFAULT_DIMENSIONS) -> dict[str, Any]:
    connection = connect(db_path)
    try:
        initialize(connection)
        rows = connection.execute(
            """
            SELECT chunk_id, corpus_id, chunk_index, run_date, full_name, html_url,
                   language, category, sources_json, chunk_text, token_estimate, payload_json
            FROM rag_chunks
            ORDER BY run_date DESC, full_name ASC, chunk_index ASC
            """
        ).fetchall()
        connection.execute("DELETE FROM rag_embeddings WHERE embedding_model = ?", (model,))
        for row in rows:
            vector = hash_embedding(str(row["chunk_text"] or ""), dimensions=dimensions)
            payload = _json_object(row["payload_json"])
            payload.update(
                {
                    "chunk_index": int(row["chunk_index"] or 0),
                    "language": row["language"],
                    "category": row["category"],
                    "sources": _json_list(row["sources_json"]),
                    "token_estimate": int(row["token_estimate"] or 0),
                }
            )
            connection.execute(
                """
                INSERT INTO rag_embeddings(
                  chunk_id, corpus_id, run_date, full_name, html_url,
                  embedding_model, dimensions, vector_json, payload_json, updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id, embedding_model) DO UPDATE SET
                  corpus_id = excluded.corpus_id,
                  run_date = excluded.run_date,
                  full_name = excluded.full_name,
                  html_url = excluded.html_url,
                  dimensions = excluded.dimensions,
                  vector_json = excluded.vector_json,
                  payload_json = excluded.payload_json,
                  updated_at = excluded.updated_at
                """,
                (
                    row["chunk_id"],
                    row["corpus_id"],
                    row["run_date"],
                    row["full_name"],
                    row["html_url"],
                    model,
                    dimensions,
                    json.dumps(vector, ensure_ascii=False),
                    json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    datetime.now(UTC).isoformat(),
                ),
            )
        connection.commit()
        return {
            "model": model,
            "dimensions": dimensions,
            "chunk_count": len(rows),
            "embedding_count": _embedding_count(connection, model),
        }
    finally:
        connection.close()


def hash_embedding(text: str, *, dimensions: int = DEFAULT_DIMENSIONS) -> list[float]:
    dimensions = max(8, min(int(dimensions or DEFAULT_DIMENSIONS), 512))
    vector = [0.0] * dimensions
    for token in _tokens(text):
        digest = sha1(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    return _normalize(vector)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=False))


def vector_from_json(text: str) -> list[float]:
    try:
        data = json.loads(text or "[]")
    except json.JSONDecodeError:
        return []
    return [float(item or 0.0) for item in data] if isinstance(data, list) else []


def _tokens(text: str) -> list[str]:
    return [item.lower() for item in TOKEN_PATTERN.findall(text or "") if item.strip()]


def _normalize(vector: list[float]) -> list[float]:
    length = math.sqrt(sum(value * value for value in vector))
    if length <= 0:
        return vector
    return [round(value / length, 6) for value in vector]


def _embedding_count(connection: sqlite3.Connection, model: str) -> int:
    row = connection.execute(
        "SELECT COUNT(*) AS count FROM rag_embeddings WHERE embedding_model = ?",
        (model,),
    ).fetchone()
    return int(row["count"])


def _json_object(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _json_list(text: str) -> list[Any]:
    try:
        data = json.loads(text or "[]")
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []
