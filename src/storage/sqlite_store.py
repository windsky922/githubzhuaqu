from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from hashlib import sha1
from pathlib import Path
from typing import Any

from src.rag.corpus_cleaner import CLEANER_VERSION, CORPUS_VERSION, clean_external_text, clean_internal_text, content_hash


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    _ensure_rag_explanation_columns(connection)
    _ensure_corpus_version_columns(connection)
    connection.commit()


def _ensure_rag_explanation_columns(connection: sqlite3.Connection) -> None:
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(rag_explanations)").fetchall()}
    for name, definition in {
        "quality_score": "INTEGER NOT NULL DEFAULT 0",
        "quality_level": "TEXT NOT NULL DEFAULT ''",
        "quality_json": "TEXT NOT NULL DEFAULT '{}'",
    }.items():
        if name not in columns:
            connection.execute(f"ALTER TABLE rag_explanations ADD COLUMN {name} {definition}")


def _ensure_corpus_version_columns(connection: sqlite3.Connection) -> None:
    definitions = {
        "project_corpus": {
            "corpus_version": "TEXT NOT NULL DEFAULT 'legacy-v0'",
            "cleaner_version": "TEXT NOT NULL DEFAULT 'legacy-v0'",
            "content_hash": "TEXT NOT NULL DEFAULT ''",
            "noise_json": "TEXT NOT NULL DEFAULT '{}'",
            "source_manifest_json": "TEXT NOT NULL DEFAULT '[]'",
            "structured_json": "TEXT NOT NULL DEFAULT '{}'",
        },
        "rag_chunks": {
            "corpus_version": "TEXT NOT NULL DEFAULT 'legacy-v0'",
            "cleaner_version": "TEXT NOT NULL DEFAULT 'legacy-v0'",
            "content_hash": "TEXT NOT NULL DEFAULT ''",
            "is_untrusted": "INTEGER NOT NULL DEFAULT 0",
            "source_type": "TEXT NOT NULL DEFAULT 'legacy'",
        },
    }
    for table, columns in definitions.items():
        existing = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}
        for name, definition in columns.items():
            if name not in existing:
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_rag_chunks_source_type ON rag_chunks(source_type)")


def import_json_archive(root: Path, db_path: Path) -> dict[str, int]:
    connection = connect(db_path)
    try:
        initialize(connection)
        selection_count = import_selections(connection, root)
        corpus_count = rebuild_project_corpus(connection)
        created_agent_task_count = sync_project_agent_tasks(connection)
        if created_agent_task_count:
            corpus_count = rebuild_project_corpus(connection)
        counts = {
            "runs": import_runs(connection, root),
            "selections": selection_count,
            "project_corpus": corpus_count,
            "project_corpus_fts": corpus_count,
            "project_agent_tasks": table_count(connection, "project_agent_tasks"),
            "project_agent_task_runs": table_count(connection, "project_agent_task_runs"),
            "subscription_events": table_count(connection, "subscription_events"),
            "notification_candidates": table_count(connection, "notification_candidates"),
            "notification_deliveries": table_count(connection, "notification_deliveries"),
            "rag_chunks": table_count(connection, "rag_chunks"),
            "rag_chunks_fts": table_count(connection, "rag_chunks_fts"),
            "rag_embeddings": table_count(connection, "rag_embeddings"),
            "rag_explanations": table_count(connection, "rag_explanations"),
            "dev_corpus": table_count(connection, "dev_corpus"),
            "dev_chunks": table_count(connection, "dev_chunks"),
            "dev_chunks_fts": table_count(connection, "dev_chunks_fts"),
            "dev_embeddings": table_count(connection, "dev_embeddings"),
            "dev_runs": table_count(connection, "dev_runs"),
            "trend_summaries": import_trend_summaries(connection, root),
            "sent_repositories": import_sent_repositories(connection, root),
            "star_history": import_star_history(connection, root),
            "jobs": import_jobs_from_runs(connection, root),
        }
        connection.execute(
            """
            INSERT INTO migration_meta(key, value)
            VALUES('last_import_counts', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (_json_text(counts),),
        )
        connection.commit()
        return counts
    finally:
        connection.close()


def import_runs(connection: sqlite3.Connection, root: Path) -> int:
    count = 0
    for path in _json_files(root / "data" / "runs"):
        data = _read_json_object(path)
        if not data:
            continue
        upsert_run(connection, data)
        count += 1
    return count


def import_jobs_from_runs(connection: sqlite3.Connection, root: Path) -> int:
    count = 0
    for path in _json_files(root / "data" / "runs"):
        data = _read_json_object(path)
        if not data:
            continue
        upsert_job_from_run(connection, data)
        count += 1
    return count


def import_selections(connection: sqlite3.Connection, root: Path) -> int:
    count = 0
    for path in _json_files(root / "data" / "selected"):
        data = _read_json_list(path)
        run_date = path.stem
        for position, item in enumerate(data, start=1):
            if not isinstance(item, dict) or not item.get("full_name"):
                continue
            upsert_repository(connection, item)
            upsert_selection(connection, run_date, position, item)
            count += 1
    return count


def import_trend_summaries(connection: sqlite3.Connection, root: Path) -> int:
    count = 0
    for path in _json_files(root / "data" / "trends"):
        data = _read_json_object(path)
        if not data:
            continue
        upsert_trend_summary(connection, path.stem, data)
        count += 1
    return count


def import_sent_repositories(connection: sqlite3.Connection, root: Path) -> int:
    count = 0
    for item in _read_json_list(root / "data" / "state" / "sent_repos.json"):
        if isinstance(item, str):
            item = {"full_name": item, "html_url": "", "first_sent_at": ""}
        if not isinstance(item, dict) or not item.get("full_name"):
            continue
        connection.execute(
            """
            INSERT INTO sent_repositories(full_name, html_url, first_sent_at, payload_json)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(full_name) DO UPDATE SET
              html_url = excluded.html_url,
              first_sent_at = excluded.first_sent_at,
              payload_json = excluded.payload_json
            """,
            (
                str(item.get("full_name") or ""),
                str(item.get("html_url") or ""),
                str(item.get("first_sent_at") or ""),
                _json_text(item),
            ),
        )
        count += 1
    return count


def import_star_history(connection: sqlite3.Connection, root: Path) -> int:
    count = 0
    for item in _read_json_list(root / "data" / "state" / "star_history.json"):
        if not isinstance(item, dict) or not item.get("full_name"):
            continue
        connection.execute(
            """
            INSERT INTO star_history(full_name, html_url, stargazers_count, last_seen_at, payload_json)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(full_name) DO UPDATE SET
              html_url = excluded.html_url,
              stargazers_count = excluded.stargazers_count,
              last_seen_at = excluded.last_seen_at,
              payload_json = excluded.payload_json
            """,
            (
                str(item.get("full_name") or ""),
                str(item.get("html_url") or ""),
                _int_value(item.get("stargazers_count")),
                str(item.get("last_seen_at") or ""),
                _json_text(item),
            ),
        )
        count += 1
    return count


def upsert_run(connection: sqlite3.Connection, data: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO runs(
          run_date, status, collected_count, selected_count, previously_sent_selected_count,
          kimi_used, fallback_used, telegram_sent, report_path, telegram_report_url, payload_json
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_date) DO UPDATE SET
          status = excluded.status,
          collected_count = excluded.collected_count,
          selected_count = excluded.selected_count,
          previously_sent_selected_count = excluded.previously_sent_selected_count,
          kimi_used = excluded.kimi_used,
          fallback_used = excluded.fallback_used,
          telegram_sent = excluded.telegram_sent,
          report_path = excluded.report_path,
          telegram_report_url = excluded.telegram_report_url,
          payload_json = excluded.payload_json
        """,
        (
            str(data.get("run_date") or ""),
            str(data.get("status") or ""),
            _int_value(data.get("collected_count")),
            _int_value(data.get("selected_count")),
            _int_value(data.get("previously_sent_selected_count")),
            int(bool(data.get("kimi_used"))),
            int(bool(data.get("fallback_used"))),
            int(bool(data.get("telegram_sent"))),
            str(data.get("report_path") or ""),
            str(data.get("telegram_report_url") or ""),
            _json_text(data),
        ),
    )


def upsert_repository(connection: sqlite3.Connection, data: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO repositories(
          full_name, html_url, description, language, stargazers_count,
          forks_count, license_name, archived, fork, pushed_at, payload_json
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(full_name) DO UPDATE SET
          html_url = excluded.html_url,
          description = excluded.description,
          language = excluded.language,
          stargazers_count = excluded.stargazers_count,
          forks_count = excluded.forks_count,
          license_name = excluded.license_name,
          archived = excluded.archived,
          fork = excluded.fork,
          pushed_at = excluded.pushed_at,
          payload_json = excluded.payload_json
        """,
        (
            str(data.get("full_name") or ""),
            str(data.get("html_url") or ""),
            str(data.get("description") or ""),
            str(data.get("language") or ""),
            _int_value(data.get("stargazers_count")),
            _int_value(data.get("forks_count")),
            str(data.get("license_name") or ""),
            int(bool(data.get("archived"))),
            int(bool(data.get("fork"))),
            str(data.get("pushed_at") or data.get("updated_at") or ""),
            _json_text(data),
        ),
    )


def upsert_selection(connection: sqlite3.Connection, run_date: str, position: int, data: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO selections(
          run_date, full_name, position, score, star_growth, trending_rank, category,
          sources_json, selection_reasons_json, security_flags_json, payload_json
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_date, full_name) DO UPDATE SET
          position = excluded.position,
          score = excluded.score,
          star_growth = excluded.star_growth,
          trending_rank = excluded.trending_rank,
          category = excluded.category,
          sources_json = excluded.sources_json,
          selection_reasons_json = excluded.selection_reasons_json,
          security_flags_json = excluded.security_flags_json,
          payload_json = excluded.payload_json
        """,
        (
            run_date,
            str(data.get("full_name") or ""),
            position,
            _float_value(data.get("score")),
            _int_value(data.get("star_growth")),
            _int_value(data.get("trending_rank")),
            str(data.get("category") or "Other"),
            _json_text(data.get("sources") or []),
            _json_text(data.get("selection_reasons") or []),
            _json_text(data.get("security_flags") or []),
            _json_text(data),
        ),
    )


def upsert_trend_summary(connection: sqlite3.Connection, run_date: str, data: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO trend_summaries(run_date, total_projects, trending_project_count, total_star_growth, payload_json)
        VALUES(?, ?, ?, ?, ?)
        ON CONFLICT(run_date) DO UPDATE SET
          total_projects = excluded.total_projects,
          trending_project_count = excluded.trending_project_count,
          total_star_growth = excluded.total_star_growth,
          payload_json = excluded.payload_json
        """,
        (
            run_date,
            _int_value(data.get("total_projects")),
            _int_value(data.get("trending_project_count")),
            _int_value(data.get("total_star_growth")),
            _json_text(data),
        ),
    )


def rebuild_project_corpus(connection: sqlite3.Connection) -> int:
    connection.execute("DELETE FROM rag_chunks")
    connection.execute("DELETE FROM rag_chunks_fts")
    connection.execute("DELETE FROM rag_embeddings")
    connection.execute("DELETE FROM project_corpus")
    connection.execute("DELETE FROM project_corpus_fts")
    rows = connection.execute(
        """
        SELECT
          s.run_date,
          s.full_name,
          s.category,
          s.sources_json,
          s.selection_reasons_json,
          s.security_flags_json,
          s.payload_json AS selection_payload_json,
          r.html_url,
          r.description,
          r.language,
          r.payload_json AS repository_payload_json
        FROM selections s
        LEFT JOIN repositories r ON r.full_name = s.full_name
        ORDER BY s.run_date DESC, s.position ASC
        """
    ).fetchall()
    for row in rows:
        upsert_project_corpus(connection, row)
    return len(rows)


def upsert_project_corpus(connection: sqlite3.Connection, row: sqlite3.Row) -> None:
    selection_payload = _json_object(row["selection_payload_json"])
    repository_payload = _json_object(row["repository_payload_json"])
    full_name = str(row["full_name"] or "")
    run_date = str(row["run_date"] or "")
    title = str(selection_payload.get("name") or full_name)
    html_url = str(row["html_url"] or selection_payload.get("html_url") or repository_payload.get("html_url") or "")
    language = str(row["language"] or selection_payload.get("language") or repository_payload.get("language") or "")
    category = str(row["category"] or selection_payload.get("category") or "Other")
    sources = _json_list(row["sources_json"])
    selection_reasons = _json_list(row["selection_reasons_json"])
    security_flags = _json_list(row["security_flags_json"])
    quality_flags = _list_value(selection_payload.get("quality_flags"))
    project_profile = _project_profile(
        full_name=full_name,
        description=str(row["description"] or selection_payload.get("description") or ""),
        readme_summary=str(selection_payload.get("readme_summary") or selection_payload.get("readme_excerpt") or ""),
        language=language,
        category=category,
        selection_reasons=selection_reasons,
        security_flags=security_flags,
        quality_flags=quality_flags,
        quality_score=_int_value(selection_payload.get("quality_score")),
        quality_level=str(selection_payload.get("quality_level") or ""),
        star_growth=_int_value(selection_payload.get("star_growth")),
        trending_rank=_int_value(selection_payload.get("trending_rank")),
    )
    agent_tasks = [
        {
            "task_id": task["task_id"],
            "task_type": task["task_type"],
            "priority": _int_value(task["priority"]),
            "status": task["status"],
            "reason": task["reason"],
            "result_summary": task["result_summary"],
            "updated_at": task["updated_at"],
        }
        for task in connection.execute(
            """
            SELECT task_id, task_type, priority, status, reason, result_summary, updated_at
            FROM project_agent_tasks
            WHERE LOWER(full_name) = LOWER(?)
            ORDER BY updated_at DESC, priority ASC, task_id DESC
            LIMIT 20
            """,
            (full_name,),
        ).fetchall()
    ]
    agent_task_runs = [
        {
            "run_id": run["run_id"],
            "task_id": run["task_id"],
            "task_type": run["task_type"],
            "status": run["status"],
            "started_at": run["started_at"],
            "finished_at": run["finished_at"],
            "result": _json_object(run["result_json"]),
            "error": run["error"],
        }
        for run in connection.execute(
            """
            SELECT r.run_id, r.task_id, r.status, r.started_at, r.finished_at,
                   r.result_json, r.error, t.task_type
            FROM project_agent_task_runs r
            JOIN project_agent_tasks t ON t.task_id = r.task_id
            WHERE LOWER(t.full_name) = LOWER(?)
            ORDER BY r.started_at DESC, r.run_id DESC
            LIMIT 20
            """,
            (full_name,),
        ).fetchall()
    ]
    external_sources = [
        ("repository_description", str(row["description"] or "")),
        ("selection_description", str(selection_payload.get("description") or "")),
        ("readme", str(selection_payload.get("readme_summary") or selection_payload.get("readme_excerpt") or "")),
    ]
    cleaned_external = [(name, clean_external_text(text)) for name, text in external_sources if text]
    text_parts = [
        full_name,
        title,
        *(item.text for _, item in cleaned_external),
        category,
        language,
        " ".join(str(item) for item in sources if item),
        " ".join(str(item) for item in selection_reasons if item),
        " ".join(str(item) for item in security_flags if item),
        " ".join(str(item) for item in _list_value(selection_payload.get("topics")) if item),
        _project_profile_text(project_profile),
        _project_agent_task_memory_text(agent_tasks),
        _project_agent_run_memory_text(agent_task_runs),
    ]
    noise = {
        key: sum(item.noise.get(key, 0) for _, item in cleaned_external)
        for key in (
            "raw_chars", "html_tags", "html_attributes", "markdown_images", "badge_lines",
            "duplicate_lines", "prompt_injection_lines", "cleaned_chars",
        )
    }
    source_manifest = [
        {
            "source_type": name,
            "content_hash": item.content_hash,
            "cleaned_chars": len(item.text),
            "is_untrusted": item.is_untrusted,
        }
        for name, item in cleaned_external
    ]
    structured = {
        "deployment": "",
        "tech_stack": _list_value(selection_payload.get("topics")) + ([language] if language else []),
        "license": "",
        "maintenance_status": "",
        "limitations": [str(item) for item in [*security_flags, *quality_flags] if item],
    }
    chunk_sources = [
        ("identity", clean_internal_text(" ".join([full_name, title, language, category]))),
        ("description", "\n".join(item.text for name, item in cleaned_external if "description" in name)),
        ("readme", "\n".join(item.text for name, item in cleaned_external if name == "readme")),
        ("selection_reason", clean_internal_text("\n".join(str(item) for item in selection_reasons if item))),
        ("project_profile", clean_internal_text(_project_profile_text(project_profile))),
        ("risk", clean_internal_text("\n".join(str(item) for item in [*security_flags, *quality_flags] if item))),
        ("agent_memory", clean_internal_text("\n".join([_project_agent_task_memory_text(agent_tasks), _project_agent_run_memory_text(agent_task_runs)]))),
    ]
    payload = {
        "run_date": run_date,
        "full_name": full_name,
        "html_url": html_url,
        "language": language,
        "category": category,
        "sources": sources,
        "quality_level": selection_payload.get("quality_level") or "",
        "quality_score": _int_value(selection_payload.get("quality_score")),
        "trending_rank": _int_value(selection_payload.get("trending_rank")),
        "star_growth": _int_value(selection_payload.get("star_growth")),
        "project_profile": project_profile,
        "agent_tasks": agent_tasks,
        "agent_task_runs": agent_task_runs,
        "corpus_version": CORPUS_VERSION,
        "cleaner_version": CLEANER_VERSION,
    }
    corpus_id = sha1(f"{run_date}:{full_name}".encode("utf-8")).hexdigest()
    search_text = _clean_text(" ".join(clean_internal_text(part) for part in text_parts if part))
    search_hash = content_hash(search_text)
    is_untrusted = any(item.is_untrusted for _, item in cleaned_external)
    connection.execute(
        """
        INSERT INTO project_corpus(
          corpus_id, run_date, full_name, html_url, title, language, category,
          sources_json, search_text, corpus_version, cleaner_version, content_hash,
          noise_json, source_manifest_json, structured_json, payload_json
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(corpus_id) DO UPDATE SET
          run_date = excluded.run_date,
          full_name = excluded.full_name,
          html_url = excluded.html_url,
          title = excluded.title,
          language = excluded.language,
          category = excluded.category,
          sources_json = excluded.sources_json,
          search_text = excluded.search_text,
          corpus_version = excluded.corpus_version,
          cleaner_version = excluded.cleaner_version,
          content_hash = excluded.content_hash,
          noise_json = excluded.noise_json,
          source_manifest_json = excluded.source_manifest_json,
          structured_json = excluded.structured_json,
          payload_json = excluded.payload_json
        """,
        (
            corpus_id,
            run_date,
            full_name,
            html_url,
            title,
            language,
            category,
            _json_text(sources),
            search_text,
            CORPUS_VERSION,
            CLEANER_VERSION,
            search_hash,
            _json_text(noise),
            _json_text(source_manifest),
            _json_text(structured),
            _json_text(payload),
        ),
    )
    connection.execute("DELETE FROM project_corpus_fts WHERE corpus_id = ?", (corpus_id,))
    connection.execute(
        """
        INSERT INTO project_corpus_fts(corpus_id, full_name, title, language, category, search_text)
        VALUES(?, ?, ?, ?, ?, ?)
        """,
        (
            corpus_id,
            full_name,
            title,
            language,
            category,
            search_text,
        ),
    )
    upsert_rag_chunks(
        connection,
        corpus_id=corpus_id,
        run_date=run_date,
        full_name=full_name,
        html_url=html_url,
        language=language,
        category=category,
        sources=sources,
        search_text=search_text,
        payload=payload,
        is_untrusted=is_untrusted,
        chunk_sources=chunk_sources,
    )


def upsert_rag_chunks(
    connection: sqlite3.Connection,
    *,
    corpus_id: str,
    run_date: str,
    full_name: str,
    html_url: str,
    language: str,
    category: str,
    sources: list[Any],
    search_text: str,
    payload: dict[str, Any],
    is_untrusted: bool = False,
    chunk_sources: list[tuple[str, str]] | None = None,
) -> None:
    connection.execute(
        "DELETE FROM rag_chunks_fts WHERE chunk_id IN (SELECT chunk_id FROM rag_chunks WHERE corpus_id = ?)",
        (corpus_id,),
    )
    connection.execute("DELETE FROM rag_chunks WHERE corpus_id = ?", (corpus_id,))
    source_chunks = chunk_sources or [("legacy", search_text)]
    seen_chunks: set[str] = set()
    chunk_index = 0
    for source_type, source_text in source_chunks:
      for chunk_text in _chunk_text(source_text):
        key = chunk_text.casefold().strip()
        if not key or key in seen_chunks:
            continue
        seen_chunks.add(key)
        chunk_index += 1
        index = chunk_index
        chunk_id = sha1(f"{corpus_id}:{source_type}:{content_hash(chunk_text)}:{index}".encode("utf-8")).hexdigest()
        chunk_payload = {
            **payload,
            "corpus_id": corpus_id,
            "chunk_index": index,
            "token_estimate": _token_estimate(chunk_text),
            "source_type": source_type,
        }
        connection.execute(
            """
            INSERT INTO rag_chunks(
              chunk_id, corpus_id, chunk_index, run_date, full_name, html_url,
              language, category, sources_json, chunk_text, token_estimate,
              corpus_version, cleaner_version, content_hash, is_untrusted, source_type, payload_json
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chunk_id) DO UPDATE SET
              corpus_id = excluded.corpus_id,
              chunk_index = excluded.chunk_index,
              run_date = excluded.run_date,
              full_name = excluded.full_name,
              html_url = excluded.html_url,
              language = excluded.language,
              category = excluded.category,
              sources_json = excluded.sources_json,
              chunk_text = excluded.chunk_text,
              token_estimate = excluded.token_estimate,
              corpus_version = excluded.corpus_version,
              cleaner_version = excluded.cleaner_version,
              content_hash = excluded.content_hash,
              is_untrusted = excluded.is_untrusted,
              source_type = excluded.source_type,
              payload_json = excluded.payload_json
            """,
            (
                chunk_id,
                corpus_id,
                index,
                run_date,
                full_name,
                html_url,
                language,
                category,
                _json_text(sources),
                chunk_text,
                _token_estimate(chunk_text),
                CORPUS_VERSION,
                CLEANER_VERSION,
                content_hash(chunk_text),
                int(is_untrusted),
                source_type,
                _json_text(chunk_payload),
            ),
        )
        connection.execute("DELETE FROM rag_chunks_fts WHERE chunk_id = ?", (chunk_id,))
        connection.execute(
            """
            INSERT INTO rag_chunks_fts(chunk_id, full_name, language, category, chunk_text)
            VALUES(?, ?, ?, ?, ?)
            """,
            (chunk_id, full_name, language, category, chunk_text),
        )


def upsert_job_from_run(connection: sqlite3.Connection, data: dict[str, Any]) -> None:
    run_date = str(data.get("run_date") or "")
    if not run_date:
        return
    failed = bool(data.get("error") or data.get("report_error") or data.get("sqlite_error"))
    status = "failed" if str(data.get("status") or "") == "failed" or failed else "succeeded"
    result = {
        "selected_count": _int_value(data.get("selected_count")),
        "collected_count": _int_value(data.get("collected_count")),
        "kimi_used": bool(data.get("kimi_used")),
        "telegram_sent": bool(data.get("telegram_sent")),
        "report_url": str(data.get("report_url") or data.get("telegram_report_url") or ""),
        "report_path": str(data.get("report_path") or ""),
    }
    upsert_job(
        connection,
        {
            "job_id": f"run:{run_date}",
            "kind": "weekly_report",
            "status": status,
            "run_date": run_date,
            "submitted_at": run_date,
            "started_at": "",
            "finished_at": run_date,
            "request": {},
            "result": result,
            "error": str(data.get("error") or data.get("report_error") or data.get("sqlite_error") or ""),
            "payload": data,
        },
    )


def upsert_job(connection: sqlite3.Connection, data: dict[str, Any]) -> None:
    payload = data.get("payload")
    if not isinstance(payload, dict):
        payload = data
    connection.execute(
        """
        INSERT INTO jobs(
          job_id, kind, status, run_date, submitted_at, started_at, finished_at,
          request_json, result_json, error, payload_json
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(job_id) DO UPDATE SET
          kind = excluded.kind,
          status = excluded.status,
          run_date = excluded.run_date,
          submitted_at = excluded.submitted_at,
          started_at = excluded.started_at,
          finished_at = excluded.finished_at,
          request_json = excluded.request_json,
          result_json = excluded.result_json,
          error = excluded.error,
          payload_json = excluded.payload_json
        """,
        (
            str(data.get("job_id") or ""),
            str(data.get("kind") or "weekly_report"),
            str(data.get("status") or "planned"),
            str(data.get("run_date") or ""),
            str(data.get("submitted_at") or ""),
            str(data.get("started_at") or ""),
            str(data.get("finished_at") or ""),
            _json_text(data.get("request") or {}),
            _json_text(data.get("result") or {}),
            str(data.get("error") or ""),
            _json_text(payload),
        ),
    )


def insert_job_event(connection: sqlite3.Connection, data: dict[str, Any]) -> None:
    payload = data.get("payload")
    if not isinstance(payload, dict):
        payload = data
    event_id = str(data.get("event_id") or "")
    if not event_id:
        event_id = _event_id(data)
    connection.execute(
        """
        INSERT INTO job_events(event_id, job_id, event_type, status, actor, created_at, message, payload_json)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(event_id) DO UPDATE SET
          job_id = excluded.job_id,
          event_type = excluded.event_type,
          status = excluded.status,
          actor = excluded.actor,
          created_at = excluded.created_at,
          message = excluded.message,
          payload_json = excluded.payload_json
        """,
        (
            event_id,
            str(data.get("job_id") or ""),
            str(data.get("event_type") or ""),
            str(data.get("status") or ""),
            str(data.get("actor") or ""),
            str(data.get("created_at") or ""),
            str(data.get("message") or ""),
            _json_text(payload),
        ),
    )


def upsert_project_agent_task(connection: sqlite3.Connection, data: dict[str, Any]) -> None:
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else data
    connection.execute(
        """
        INSERT INTO project_agent_tasks(
          task_id, full_name, profile, task_type, priority, status, reason,
          result_summary, source, dedupe_key, created_at, updated_at,
          started_at, finished_at, payload_json
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(task_id) DO UPDATE SET
          full_name = excluded.full_name,
          profile = excluded.profile,
          task_type = excluded.task_type,
          priority = excluded.priority,
          status = excluded.status,
          reason = excluded.reason,
          result_summary = excluded.result_summary,
          source = excluded.source,
          dedupe_key = excluded.dedupe_key,
          updated_at = excluded.updated_at,
          started_at = excluded.started_at,
          finished_at = excluded.finished_at,
          payload_json = excluded.payload_json
        """,
        (
            str(data.get("task_id") or ""),
            str(data.get("full_name") or ""),
            str(data.get("profile") or ""),
            str(data.get("task_type") or "observe"),
            max(1, min(_int_value(data.get("priority")) or 3, 5)),
            str(data.get("status") or "planned"),
            str(data.get("reason") or ""),
            str(data.get("result_summary") or ""),
            str(data.get("source") or ""),
            str(data.get("dedupe_key") or ""),
            str(data.get("created_at") or ""),
            str(data.get("updated_at") or ""),
            str(data.get("started_at") or ""),
            str(data.get("finished_at") or ""),
            _json_text(payload),
        ),
    )


def upsert_project_agent_task_run(connection: sqlite3.Connection, data: dict[str, Any]) -> None:
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else data.get("payload_json")
    connection.execute(
        """
        INSERT INTO project_agent_task_runs(
          run_id, task_id, status, started_at, finished_at, input_json,
          evidence_json, citations_json, result_json, error, payload_json
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
          task_id = excluded.task_id,
          status = excluded.status,
          started_at = excluded.started_at,
          finished_at = excluded.finished_at,
          input_json = excluded.input_json,
          evidence_json = excluded.evidence_json,
          citations_json = excluded.citations_json,
          result_json = excluded.result_json,
          error = excluded.error,
          payload_json = excluded.payload_json
        """,
        (
            str(data.get("run_id") or ""),
            str(data.get("task_id") or ""),
            str(data.get("status") or "running"),
            str(data.get("started_at") or ""),
            str(data.get("finished_at") or ""),
            _json_text(data.get("input") if isinstance(data.get("input"), dict) else data.get("input_json")),
            _json_text(data.get("evidence") if isinstance(data.get("evidence"), list) else data.get("evidence_json")),
            _json_text(data.get("citations") if isinstance(data.get("citations"), list) else data.get("citations_json")),
            _json_text(data.get("result") if isinstance(data.get("result"), dict) else data.get("result_json")),
            str(data.get("error") or ""),
            _json_text(payload),
        ),
    )


def upsert_subscription_event(connection: sqlite3.Connection, data: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO subscription_events(
          event_id, event_type, full_name, source_run_id, severity, status, title,
          summary, evidence_json, citations_json, dedupe_key, detected_at, updated_at, payload_json
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(event_id) DO UPDATE SET
          event_type = excluded.event_type,
          full_name = excluded.full_name,
          source_run_id = excluded.source_run_id,
          severity = excluded.severity,
          status = excluded.status,
          title = excluded.title,
          summary = excluded.summary,
          evidence_json = excluded.evidence_json,
          citations_json = excluded.citations_json,
          dedupe_key = excluded.dedupe_key,
          updated_at = excluded.updated_at,
          payload_json = excluded.payload_json
        """,
        (
            str(data.get("event_id") or ""), str(data.get("event_type") or ""),
            str(data.get("full_name") or ""), str(data.get("source_run_id") or ""),
            str(data.get("severity") or "info"), str(data.get("status") or "detected"),
            str(data.get("title") or ""), str(data.get("summary") or ""),
            _json_text(data.get("evidence") if isinstance(data.get("evidence"), list) else data.get("evidence_json")),
            _json_text(data.get("citations") if isinstance(data.get("citations"), list) else data.get("citations_json")),
            str(data.get("dedupe_key") or ""), str(data.get("detected_at") or ""),
            str(data.get("updated_at") or ""),
            _json_text(data.get("payload") if isinstance(data.get("payload"), dict) else data.get("payload_json")),
        ),
    )


def upsert_notification_candidate(connection: sqlite3.Connection, data: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO notification_candidates(
          candidate_id, subscription_id, event_id, full_name, status, channels_json,
          title, message, dedupe_key, created_at, updated_at, payload_json
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(candidate_id) DO UPDATE SET
          subscription_id = excluded.subscription_id,
          event_id = excluded.event_id,
          full_name = excluded.full_name,
          status = excluded.status,
          channels_json = excluded.channels_json,
          title = excluded.title,
          message = excluded.message,
          dedupe_key = excluded.dedupe_key,
          updated_at = excluded.updated_at,
          payload_json = excluded.payload_json
        """,
        (
            str(data.get("candidate_id") or ""), str(data.get("subscription_id") or ""),
            str(data.get("event_id") or ""), str(data.get("full_name") or ""),
            str(data.get("status") or "pending"),
            _json_text(data.get("channels") if isinstance(data.get("channels"), list) else data.get("channels_json")),
            str(data.get("title") or ""), str(data.get("message") or ""),
            str(data.get("dedupe_key") or ""), str(data.get("created_at") or ""),
            str(data.get("updated_at") or ""),
            _json_text(data.get("payload") if isinstance(data.get("payload"), dict) else data.get("payload_json")),
        ),
    )


def upsert_notification_delivery(connection: sqlite3.Connection, data: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO notification_deliveries(
          delivery_id, candidate_id, subscription_id, event_id, channel, status,
          attempt_count, started_at, finished_at, error, response_json, dedupe_key, payload_json
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(delivery_id) DO UPDATE SET
          candidate_id = excluded.candidate_id,
          subscription_id = excluded.subscription_id,
          event_id = excluded.event_id,
          channel = excluded.channel,
          status = excluded.status,
          attempt_count = excluded.attempt_count,
          started_at = excluded.started_at,
          finished_at = excluded.finished_at,
          error = excluded.error,
          response_json = excluded.response_json,
          dedupe_key = excluded.dedupe_key,
          payload_json = excluded.payload_json
        """,
        (
            str(data.get("delivery_id") or ""), str(data.get("candidate_id") or ""),
            str(data.get("subscription_id") or ""), str(data.get("event_id") or ""),
            str(data.get("channel") or ""), str(data.get("status") or "planned"),
            _int_value(data.get("attempt_count")), str(data.get("started_at") or ""),
            str(data.get("finished_at") or ""), str(data.get("error") or ""),
            _json_text(data.get("response") if isinstance(data.get("response"), dict) else data.get("response_json")),
            str(data.get("dedupe_key") or ""),
            _json_text(data.get("payload") if isinstance(data.get("payload"), dict) else data.get("payload_json")),
        ),
    )


def sync_project_agent_tasks(connection: sqlite3.Connection, limit: int = 20) -> int:
    rows = connection.execute(
        """
        WITH ranked AS (
          SELECT full_name, run_date, payload_json,
                 CAST(json_extract(payload_json, '$.quality_score') AS INTEGER) AS quality_score,
                 CAST(json_extract(payload_json, '$.trending_rank') AS INTEGER) AS trending_rank,
                 CAST(json_extract(payload_json, '$.star_growth') AS INTEGER) AS star_growth,
                 ROW_NUMBER() OVER (
                   PARTITION BY LOWER(full_name)
                   ORDER BY run_date DESC, corpus_id DESC
                 ) AS row_number
          FROM project_corpus
        )
        SELECT full_name, run_date, payload_json
        FROM ranked
        WHERE row_number = 1
          AND (quality_score >= 60 OR trending_rank BETWEEN 1 AND 20 OR star_growth > 0)
        ORDER BY run_date DESC, quality_score DESC, star_growth DESC, full_name ASC
        LIMIT ?
        """,
        (max(1, min(_int_value(limit) or 20, 100)),),
    ).fetchall()
    created = 0
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    for row in rows:
        payload = _json_object(row["payload_json"])
        profile = payload.get("project_profile") if isinstance(payload.get("project_profile"), dict) else {}
        quality_score = _int_value(payload.get("quality_score"))
        risks = _list_value(profile.get("risks"))
        if risks:
            task_type = "review_risk"
            priority = 1
            reason = f"项目档案记录了 {len(risks)} 个风险点，需要复查风险变化。"
        elif quality_score >= 80:
            task_type = "deep_analysis"
            priority = 2
            reason = "项目质量信号较强，建议补充深度分析并验证落地价值。"
        else:
            task_type = "continue_tracking"
            priority = 3
            reason = str(profile.get("tracking_reason") or "项目已进入周榜，建议持续观察趋势和版本变化。")
        full_name = str(row["full_name"] or "")
        run_date = str(row["run_date"] or "")
        dedupe_key = f"weekly:{run_date}:{full_name.lower()}:{task_type}"
        task_id = "agent-task:" + sha1(dedupe_key.encode("utf-8")).hexdigest()[:16]
        exists = connection.execute(
            "SELECT 1 FROM project_agent_tasks WHERE dedupe_key = ?",
            (dedupe_key,),
        ).fetchone()
        if exists:
            continue
        upsert_project_agent_task(
            connection,
            {
                "task_id": task_id,
                "full_name": full_name,
                "profile": "",
                "task_type": task_type,
                "priority": priority,
                "status": "planned",
                "reason": reason,
                "result_summary": "",
                "source": "weekly_sync",
                "dedupe_key": dedupe_key,
                "created_at": now,
                "updated_at": now,
                "started_at": "",
                "finished_at": "",
                "payload": {
                    "run_date": run_date,
                    "project_profile": profile,
                    "subscription_action": "notify" if priority <= 2 else "watch",
                },
            },
        )
        created += 1
    connection.commit()
    return created


def _project_agent_task_memory_text(tasks: list[dict[str, Any]]) -> str:
    if not tasks:
        return ""
    lines = ["Agent 任务记忆"]
    for task in tasks:
        line = (
            f"{task.get('task_type') or 'observe'} | 状态 {task.get('status') or 'planned'} | "
            f"优先级 {task.get('priority') or 3} | 原因 {task.get('reason') or '未记录'}"
        )
        if task.get("result_summary"):
            line += f" | 执行结果 {task['result_summary']}"
        lines.append(line)
    return "\n".join(lines)


def _project_agent_run_memory_text(runs: list[dict[str, Any]]) -> str:
    if not runs:
        return ""
    lines = ["Agent 执行记忆"]
    for run in runs:
        result = run.get("result") if isinstance(run.get("result"), dict) else {}
        line = (
            f"{run.get('task_type') or 'observe'} | 状态 {run.get('status') or 'unknown'} | "
            f"决策 {result.get('decision') or '未形成'} | 摘要 {result.get('execution_summary') or run.get('error') or '未记录'}"
        )
        lines.append(line)
    return "\n".join(lines)


def table_count(connection: sqlite3.Connection, table_name: str) -> int:
    if table_name not in {
        "runs",
        "repositories",
        "selections",
        "project_corpus",
        "project_corpus_fts",
        "rag_chunks",
        "rag_chunks_fts",
        "rag_embeddings",
        "rag_explanations",
        "project_feedback",
        "project_agent_tasks",
        "project_agent_task_runs",
        "subscription_events",
        "notification_candidates",
        "notification_deliveries",
        "dev_corpus",
        "dev_chunks",
        "dev_chunks_fts",
        "dev_embeddings",
        "dev_runs",
        "trend_summaries",
        "sent_repositories",
        "star_history",
        "jobs",
        "job_events",
        "subscriptions",
    }:
        raise ValueError(f"不支持的表名：{table_name}")
    row = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
    return int(row["count"])


def _json_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(item for item in path.glob("*.json") if item.is_file())


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _read_json_list(path: Path) -> list[Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


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


def _list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _project_profile(
    *,
    full_name: str,
    description: str,
    readme_summary: str,
    language: str,
    category: str,
    selection_reasons: list[Any],
    security_flags: list[Any],
    quality_flags: list[Any],
    quality_score: int,
    quality_level: str,
    star_growth: int,
    trending_rank: int,
) -> dict[str, Any]:
    project_positioning = _first_text(
        [
            f"{full_name} 是一个 {category or '未分类'} 方向的 {language or '未知语言'} 项目。",
            description,
            readme_summary,
        ]
    )
    use_cases = _compact_list(
        [
            f"用于评估 {category} 方向的开源方案。" if category else "",
            f"适合关注 {language} 技术栈的开发者。" if language else "",
            "适合继续观察近期 GitHub Trending 热度。" if trending_rank else "",
        ]
    )
    strengths = _compact_list(
        [
            f"近期新增 Star {star_growth}。" if star_growth else "",
            f"进入 GitHub Trending 第 {trending_rank} 位。" if trending_rank else "",
            f"质量等级 {quality_level or 'unknown'}，质量分 {quality_score}。" if quality_score else "",
            *[str(item) for item in selection_reasons[:3] if item],
        ]
    )
    risks = _compact_list([str(item) for item in security_flags if item] or ["暂无明确风险提示。"])
    quality_summary = (
        f"质量分 {quality_score}，等级 {quality_level or 'unknown'}。"
        if quality_score
        else "暂无质量分，需结合 README 完整度、活跃度和风险提示继续判断。"
    )
    if quality_flags:
        quality_summary += " 质量提示：" + "；".join(str(item) for item in quality_flags[:4] if item)
    tracking_reason = _tracking_reason(star_growth=star_growth, trending_rank=trending_rank, security_flags=security_flags)
    rag_summary = (
        f"项目档案包含定位、适用场景、优势、风险、质量判断和历史入选理由，可用于 RAG 检索：{full_name}。"
    )
    agent_judgement = _agent_judgement(
        quality_score=quality_score,
        star_growth=star_growth,
        trending_rank=trending_rank,
        security_flags=security_flags,
    )
    return {
        "project_profile": True,
        "project_positioning": project_positioning,
        "use_cases": use_cases,
        "strengths": strengths,
        "risks": risks,
        "quality_summary": quality_summary,
        "tracking_reason": tracking_reason,
        "rag_summary": rag_summary,
        "agent_judgement": agent_judgement,
    }


def _project_profile_text(profile: dict[str, Any]) -> str:
    parts = [
        "项目定位：" + str(profile.get("project_positioning") or ""),
        "适用场景：" + "；".join(str(item) for item in _list_value(profile.get("use_cases")) if item),
        "优势信号：" + "；".join(str(item) for item in _list_value(profile.get("strengths")) if item),
        "风险点：" + "；".join(str(item) for item in _list_value(profile.get("risks")) if item),
        "质量判断：" + str(profile.get("quality_summary") or ""),
        "跟踪理由：" + str(profile.get("tracking_reason") or ""),
        "RAG 摘要：" + str(profile.get("rag_summary") or ""),
        "Agent 判断：" + str(profile.get("agent_judgement") or ""),
    ]
    return " ".join(part for part in parts if part.strip())


def _first_text(values: list[str]) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return "暂无项目定位，需要补充 README 摘要或项目描述。"


def _compact_list(values: list[Any]) -> list[str]:
    items = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            items.append(text)
    return items[:6]


def _tracking_reason(*, star_growth: int, trending_rank: int, security_flags: list[Any]) -> str:
    if security_flags:
        return "存在风险提示，建议谨慎跟踪并优先核查许可证、凭据和依赖安全。"
    if trending_rank and trending_rank <= 5:
        return "进入 Trending 前列，建议继续跟踪近期活跃度和社区反馈。"
    if star_growth >= 50:
        return "近期 Star 增长明显，建议继续观察增长是否可持续。"
    return "可作为普通候选项目归档，后续根据反馈和新增信号决定是否继续跟踪。"


def _agent_judgement(*, quality_score: int, star_growth: int, trending_rank: int, security_flags: list[Any]) -> str:
    if security_flags:
        return "暂不直接作为高优先级推荐，需先复核风险提示。"
    if quality_score >= 80 and (star_growth >= 20 or (trending_rank and trending_rank <= 10)):
        return "值得优先研究，可进入推荐和订阅摘要候选。"
    if quality_score >= 60:
        return "具备观察价值，建议结合 README、Issue 和 Release 活跃度继续判断。"
    return "信息不足或质量信号偏弱，建议低优先级跟踪。"


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _chunk_text(text: str, *, max_chars: int = 700, overlap: int = 120) -> list[str]:
    cleaned = _clean_text(text)
    if not cleaned:
        return []
    if len(cleaned) <= max_chars:
        return [cleaned]
    chunks = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + max_chars)
        if end < len(cleaned):
            boundary = max(cleaned.rfind("。", start, end), cleaned.rfind(".", start, end), cleaned.rfind(" ", start, end))
            if boundary > start + max_chars // 2:
                end = boundary + 1
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _token_estimate(text: str) -> int:
    return max(1, len(text) // 4)


def _json_text(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def _event_id(data: dict[str, Any]) -> str:
    text = _json_text(
        {
            "job_id": data.get("job_id") or "",
            "event_type": data.get("event_type") or "",
            "status": data.get("status") or "",
            "actor": data.get("actor") or "",
            "created_at": data.get("created_at") or "",
            "message": data.get("message") or "",
        }
    )
    return f"event:{sha1(text.encode('utf-8')).hexdigest()[:16]}"


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _float_value(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0
