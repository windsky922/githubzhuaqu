"""Produce atomic, public RAG freshness attestations from a weekly archive."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from src.rag.embeddings import DEFAULT_DIMENSIONS, MODEL_NAME, build_rag_embeddings
from src.storage.sqlite_store import connect, import_json_archive, initialize

SCHEMA_VERSION = 1


def refresh_rag_freshness(
    *,
    root: Path,
    db_path: Path,
    run_date: str,
    model: str = MODEL_NAME,
    dimensions: int = DEFAULT_DIMENSIONS,
) -> dict[str, Any]:
    """Rebuild derived RAG layers and attest only their complete success."""
    source = source_ready(root=root, run_date=run_date)
    corpus = corpus_ready(root=root, db_path=db_path, run_date=run_date)
    embedding = embedding_ready(
        db_path=db_path,
        run_date=run_date,
        model=model,
        dimensions=dimensions,
    )
    return finalize_attestation(
        root=root,
        run_date=run_date,
        source=source,
        corpus=corpus,
        embedding=embedding,
    )


def source_ready(*, root: Path, run_date: str) -> dict[str, Any]:
    """Validate the successful source artifacts for one weekly run."""
    payload = _load_run(root, run_date)
    if str(payload.get("status") or "") != "success":
        raise ValueError("freshness attestation requires a successful weekly run")
    paths = [root / "data" / "raw" / f"{run_date}.json", root / "data" / "selected" / f"{run_date}.json"]
    if any(not path.is_file() for path in paths):
        raise ValueError("freshness attestation requires raw and selected source artifacts")
    return {"run_date": run_date, "source_hash": _files_hash(root, paths)}


def corpus_ready(*, root: Path, db_path: Path, run_date: str) -> dict[str, Any]:
    """Rebuild corpus from public JSON and return deterministic current-run evidence."""
    import_json_archive(root, db_path)
    connection = connect(db_path)
    try:
        initialize(connection)
        rows = connection.execute(
            """
            SELECT chunk_id, corpus_id, corpus_version, cleaner_version, content_hash
            FROM rag_chunks
            WHERE run_date = ?
            ORDER BY chunk_id ASC
            """,
            (run_date,),
        ).fetchall()
    finally:
        connection.close()
    if not rows:
        raise ValueError("freshness attestation requires current-run corpus chunks")
    serialized = [dict(row) for row in rows]
    versions = {str(row["corpus_version"] or "") for row in rows}
    if len(versions) != 1 or not next(iter(versions)):
        raise ValueError("freshness attestation requires one corpus version")
    return {
        "run_date": run_date,
        "corpus_version": next(iter(versions)),
        "corpus_hash": _canonical_hash(serialized),
        "chunk_count": len(serialized),
    }


def embedding_ready(
    *,
    db_path: Path,
    run_date: str,
    model: str,
    dimensions: int,
) -> dict[str, Any]:
    """Build embeddings and prove every current-run chunk has one embedding."""
    result = build_rag_embeddings(db_path, model=model, dimensions=dimensions)
    connection = connect(db_path)
    try:
        initialize(connection)
        expected = connection.execute(
            "SELECT COUNT(*) AS count FROM rag_chunks WHERE run_date = ?",
            (run_date,),
        ).fetchone()
        rows = connection.execute(
            """
            SELECT chunk_id, corpus_id, dimensions, vector_json
            FROM rag_embeddings
            WHERE run_date = ? AND embedding_model = ?
            ORDER BY chunk_id ASC
            """,
            (run_date, model),
        ).fetchall()
    finally:
        connection.close()
    if not rows:
        raise ValueError("freshness attestation requires current-run embeddings")
    serialized = [dict(row) for row in rows]
    if len(serialized) != int(expected["count"] or 0):
        raise ValueError("freshness attestation embedding coverage is incomplete")
    return {
        "run_date": run_date,
        "embedding_model": model,
        "embedding_hash": _canonical_hash(serialized),
        "embedding_count": len(serialized),
        "dimensions": int(result.get("dimensions") or dimensions),
    }


def finalize_attestation(
    *,
    root: Path,
    run_date: str,
    source: dict[str, Any],
    corpus: dict[str, Any],
    embedding: dict[str, Any],
) -> dict[str, Any]:
    """Atomically attach one complete attestation; reject all partial inputs."""
    for stage in (source, corpus, embedding):
        if str(stage.get("run_date") or "") != run_date:
            raise ValueError("freshness attestation stages must match the source run")
    required = (
        (source, "source_hash"),
        (corpus, "corpus_version"),
        (corpus, "corpus_hash"),
        (embedding, "embedding_model"),
        (embedding, "embedding_hash"),
    )
    if any(not str(stage.get(field) or "") for stage, field in required):
        raise ValueError("freshness attestation cannot finalize incomplete stages")
    if int(corpus.get("chunk_count") or 0) < 1 or int(embedding.get("embedding_count") or 0) < 1:
        raise ValueError("freshness attestation requires non-empty corpus and embeddings")
    if int(embedding.get("dimensions") or 0) < 1:
        raise ValueError("freshness attestation requires embedding dimensions")
    payload = _load_run(root, run_date)
    attestation = {
        "schema_version": SCHEMA_VERSION,
        "source_latest_date": run_date,
        "corpus_latest_date": run_date,
        "embedding_latest_date": run_date,
        "source_hash": str(source["source_hash"]),
        "corpus_version": str(corpus["corpus_version"]),
        "corpus_hash": str(corpus["corpus_hash"]),
        "chunk_count": int(corpus.get("chunk_count") or 0),
        "embedding_model": str(embedding["embedding_model"]),
        "embedding_hash": str(embedding["embedding_hash"]),
        "embedding_count": int(embedding.get("embedding_count") or 0),
        "dimensions": int(embedding.get("dimensions") or 0),
    }
    updated = {**payload, "rag_freshness": attestation}
    path = root / "data" / "runs" / f"{run_date}.json"
    _atomic_json_write(path, updated)
    return attestation


def _load_run(root: Path, run_date: str) -> dict[str, Any]:
    path = root / "data" / "runs" / f"{run_date}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as error:
        raise ValueError("freshness attestation requires a valid run artifact") from error
    if not isinstance(payload, dict) or str(payload.get("run_date") or "") != run_date:
        raise ValueError("freshness attestation run artifact date is invalid")
    return payload


def _files_hash(root: Path, paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _canonical_hash(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
