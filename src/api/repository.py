from __future__ import annotations

import json
import re
import sqlite3
import subprocess
from datetime import UTC, datetime
from hashlib import sha1
from pathlib import Path
from typing import Any

from scripts.query_archive import query_archive
from src.job_runner import run_planned_job
from src.rag.embeddings import (
    DEFAULT_DIMENSIONS,
    MODEL_NAME,
    build_rag_embeddings,
    cosine_similarity,
    hash_embedding,
    vector_from_json,
)
from src.rag.answering import answer_rag_question
from src.storage.sqlite_store import (
    connect,
    import_json_archive,
    initialize,
    insert_job_event,
    rebuild_project_corpus,
    table_count,
    upsert_project_agent_task,
    upsert_job,
)

ROOT = Path(__file__).resolve().parents[2]
EXECUTABLE_JOB_KINDS = {
    "weekly_report",
    "rag_backfill",
    "rag_corpus_rebuild",
    "rag_embedding_build",
    "rag_search_evaluation",
    "dev_context_index",
}
PROJECT_AGENT_TASK_TYPES = {
    "observe",
    "review_risk",
    "deep_analysis",
    "notify",
    "ignore",
    "continue_tracking",
}
PROJECT_AGENT_TASK_STATUSES = {"planned", "in_progress", "completed", "failed", "cancelled"}
PROJECT_AGENT_TASK_TRANSITIONS = {
    "planned": {"planned", "in_progress", "completed", "cancelled"},
    "in_progress": {"in_progress", "completed", "failed", "cancelled"},
    "failed": {"failed", "planned", "in_progress", "cancelled"},
    "completed": {"completed"},
    "cancelled": {"cancelled", "planned"},
}


class ApiRepository:
    """面向后端 API 的归档访问层。"""

    def __init__(self, root: Path = ROOT, db_path: Path | None = None) -> None:
        self.root = root
        self.db_path = db_path or root / "data" / "github_weekly.sqlite"

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "root": str(self.root),
            "sqlite_exists": self.db_path.exists(),
            "reports_exists": (self.root / "reports").exists(),
            "docs_exists": (self.root / "docs").exists(),
        }

    def v1_health(self) -> dict[str, Any]:
        archive_health = self.health()
        return {
            "schema_version": 1,
            "status": archive_health["status"],
            "service": "github-weekly-agent",
            "api_version": "v1",
            "capabilities": {
                "projects_query": True,
                "project_detail": True,
                "recommendations": True,
                "project_agent_tasks": True,
                "project_agent_task_execution": True,
                "subscriptions": True,
                "subscription_recommendations": True,
                "subscription_trigger": True,
                "subscription_events": True,
                "notification_candidates": True,
                "notification_delivery": True,
                "project_feedback": True,
                "feedback_memory": True,
                "database_summary": True,
                "database_trends": True,
                "database_facets": True,
                "project_search": True,
                "project_similarity": True,
                "project_compare": True,
                "rag_corpus": True,
                "rag_retrieve": True,
                "rag_vector_search": True,
                "rag_hybrid_search": True,
                "rag_search_compare": True,
                "rag_search_evaluation": True,
                "rag_search_evaluation_jobs": True,
                "rag_search_evaluation_trends": True,
                "rag_search_evaluation_plan": True,
                "rag_explain": True,
                "rag_ask": True,
                "rag_explanations": True,
                "rag_project_explanations": True,
                "rag_project_bundle": True,
                "rag_quality_summary": True,
                "rag_coverage": True,
                "rag_diagnostics": True,
                "rag_backfill_explanations": True,
                "rag_backfill_plan": True,
                "rag_maintenance_plan": True,
                "rag_maintenance_report": True,
                "rag_backfill_jobs": True,
                "dev_context_index": True,
                "dev_context_index_jobs": True,
                "dev_context_index_plan": True,
                "dev_context_search": True,
                "dev_context_ask": True,
                "dev_context_runs": True,
                "runs_query": True,
                "jobs_query": True,
                "job_events": True,
                "job_execution_check": True,
                "job_retry": True,
                "run_trigger_preview": True,
                "local_job_runner": True,
                "run_trigger_execute": True,
            },
            "archive": archive_health,
        }

    def projects(
        self,
        *,
        language: str | None = None,
        category: str | None = None,
        profile: str | None = None,
        source: str | None = None,
        risk: str | None = None,
        quality_level: str | None = None,
        min_quality: int | None = None,
        trending_top: int | None = None,
        query: str | None = None,
        limit: int = 20,
        sort: str = "recent",
    ) -> dict[str, Any]:
        self.ensure_sqlite_index()
        rows = query_archive(
            db_path=self.db_path,
            root=self.root,
            language=_blank_to_none(language),
            category=_blank_to_none(category),
            profile=_blank_to_none(profile),
            source=_blank_to_none(source),
            risk=_blank_to_none(risk),
            quality_level=_blank_to_none(quality_level),
            min_quality=min_quality,
            trending_top=trending_top,
            query=_blank_to_none(query),
            limit=limit,
            sort=sort,
        )
        return {
            "schema_version": 1,
            "count": len(rows),
            "projects": rows,
        }

    def recommendations(
        self,
        *,
        language: str | None = None,
        category: str | None = None,
        profile: str | None = None,
        query: str | None = None,
        limit: int = 20,
        sort: str = "score",
    ) -> dict[str, Any]:
        normalized_profile = _blank_to_none(profile)
        normalized_language = _blank_to_none(language)
        normalized_category = _blank_to_none(category)
        normalized_query = _blank_to_none(query)
        limit = max(1, min(_int_value(limit) or 20, 100))
        candidate_limit = min(100, max(limit, min(max(limit * 3, 50), 100)))
        projects = self.projects(
            language=normalized_language,
            category=normalized_category,
            profile=normalized_profile,
            query=normalized_query,
            limit=candidate_limit,
            sort=sort,
        ).get("projects", [])
        projects = _dedupe_projects_by_full_name(projects)
        feedback_records = self.project_feedback(profile=normalized_profile, limit=200).get("feedback", [])
        feedback_memory = _feedback_memory_by_full_name(feedback_records)
        event_records = self.subscription_events(limit=500).get("events", [])
        event_memory = _subscription_event_memory_by_full_name(event_records)
        project_profiles = self._project_profiles_by_full_name([project.get("full_name") or "" for project in projects])
        projects = [
            {
                **project,
                "project_profile": project_profiles.get(str(project.get("full_name") or "").lower())
                or _project_profile_from_project(project, feedback_memory.get(str(project.get("full_name") or "").lower())),
                "event_memory": event_memory.get(str(project.get("full_name") or "").lower(), _empty_event_memory()),
                "event_reason": _recommendation_event_reason(
                    event_memory.get(str(project.get("full_name") or "").lower(), {})
                ),
            }
            for project in projects
        ]
        projects = _apply_feedback_memory(projects, feedback_memory)[:limit]
        task_records = self.project_agent_tasks(limit=500).get("tasks", [])
        task_records = [
            task
            for task in task_records
            if not normalized_profile or not task.get("profile") or task.get("profile") == normalized_profile
        ]
        task_memory = _project_agent_tasks_by_full_name(task_records)
        projects = [
            {
                **project,
                "next_actions": _project_next_actions(
                    project,
                    task_memory.get(str(project.get("full_name") or "").lower(), []),
                ),
            }
            for project in projects
        ]
        return {
            "schema_version": 1,
            "profile": normalized_profile or "",
            "language": normalized_language or "",
            "category": normalized_category or "",
            "query": normalized_query or "",
            "sort": sort,
            "count": len(projects),
            "selection_summary": _recommendation_summary(
                projects,
                profile=normalized_profile,
                language=normalized_language,
                category=normalized_category,
                query=normalized_query,
            ),
            "feedback_memory": _feedback_memory_response(feedback_records),
            "event_memory": _event_memory_response(event_records),
            "agent_task_summary": _project_agent_task_summary(task_records),
            "recommendations": projects,
        }

    def search(
        self,
        *,
        query: str,
        language: str | None = None,
        category: str | None = None,
        source: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        self.ensure_sqlite_index()
        normalized_query = (_blank_to_none(query) or "").strip()
        terms = _search_terms(normalized_query)
        limit = max(1, min(int(limit or 20), 100))
        if not terms:
            return {
                "schema_version": 1,
                "query": normalized_query,
                "count": 0,
                "results": [],
                "summary": ["请输入搜索关键词。"],
            }

        connection = connect(self.db_path)
        search_engine = "fts5"
        try:
            initialize(connection)
            try:
                rows = _search_rows_fts(
                    connection,
                    terms=terms,
                    language=_blank_to_none(language),
                    category=_blank_to_none(category),
                    source=_blank_to_none(source),
                    limit=limit * 4,
                )
            except sqlite3.Error:
                search_engine = "like"
                rows = _search_rows_like(
                    connection,
                    terms=terms,
                    language=_blank_to_none(language),
                    category=_blank_to_none(category),
                    source=_blank_to_none(source),
                    limit=limit * 4,
                )
        finally:
            connection.close()

        ranked_results = sorted(
            [_search_result(row, terms) for row in rows],
            key=lambda item: (item["score"], item["run_date"], item["full_name"]),
            reverse=True,
        )
        results = _dedupe_search_results(ranked_results)[:limit]
        return {
            "schema_version": 1,
            "query": normalized_query,
            "language": _blank_to_none(language) or "",
            "category": _blank_to_none(category) or "",
            "source": _blank_to_none(source) or "",
            "search_engine": search_engine,
            "count": len(results),
            "results": results,
            "summary": _search_summary(results, terms),
        }

    def dev_context_index(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        self.ensure_sqlite_index()
        started_at = datetime.now(UTC).isoformat()
        run_id = str(payload.get("run_id") or "").strip()
        if not run_id:
            run_id = "dev-context:" + sha1(f"{started_at}:{self.root}".encode("utf-8")).hexdigest()[:16]
        run_checks = payload.get("run_checks", True) is not False
        replace = payload.get("replace", False) is True
        max_command_chars = _int_value(payload.get("max_command_chars")) or 120000
        max_command_chars = max(2000, min(max_command_chars, 250000))
        sources = _dev_context_sources(self.root, run_checks=run_checks, max_command_chars=max_command_chars)
        chunks: list[dict[str, Any]] = []
        embedding_count = 0

        connection = connect(self.db_path)
        try:
            initialize(connection)
            if replace:
                connection.execute("DELETE FROM dev_embeddings")
                connection.execute("DELETE FROM dev_chunks_fts")
                connection.execute("DELETE FROM dev_chunks")
                connection.execute("DELETE FROM dev_corpus")
            for source in sources:
                corpus_id = _dev_corpus_id(run_id, source)
                metadata = dict(source.get("metadata") or {})
                metadata.update({"run_id": run_id, "content_hash": source.get("content_hash") or ""})
                connection.execute(
                    """
                    INSERT INTO dev_corpus(
                      corpus_id, run_id, source_type, source_path, title,
                      content_hash, content_text, metadata_json, created_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(corpus_id) DO UPDATE SET
                      run_id = excluded.run_id,
                      source_type = excluded.source_type,
                      source_path = excluded.source_path,
                      title = excluded.title,
                      content_hash = excluded.content_hash,
                      content_text = excluded.content_text,
                      metadata_json = excluded.metadata_json,
                      created_at = excluded.created_at
                    """,
                    (
                        corpus_id,
                        run_id,
                        source.get("source_type") or "",
                        source.get("source_path") or "",
                        source.get("title") or "",
                        source.get("content_hash") or "",
                        source.get("content_text") or "",
                        json.dumps(metadata, ensure_ascii=False, sort_keys=True),
                        started_at,
                    ),
                )
                connection.execute("DELETE FROM dev_chunks_fts WHERE chunk_id IN (SELECT chunk_id FROM dev_chunks WHERE corpus_id = ?)", (corpus_id,))
                connection.execute("DELETE FROM dev_embeddings WHERE corpus_id = ?", (corpus_id,))
                connection.execute("DELETE FROM dev_chunks WHERE corpus_id = ?", (corpus_id,))
                for chunk in _dev_context_chunks(
                    corpus_id=corpus_id,
                    run_id=run_id,
                    source=source,
                    created_at=started_at,
                ):
                    chunks.append(chunk)
                    connection.execute(
                        """
                        INSERT INTO dev_chunks(
                          chunk_id, corpus_id, run_id, chunk_index, source_type,
                          source_path, title, chunk_text, token_estimate,
                          metadata_json, created_at
                        )
                        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            chunk["chunk_id"],
                            chunk["corpus_id"],
                            chunk["run_id"],
                            chunk["chunk_index"],
                            chunk["source_type"],
                            chunk["source_path"],
                            chunk["title"],
                            chunk["chunk_text"],
                            chunk["token_estimate"],
                            json.dumps(chunk["metadata"], ensure_ascii=False, sort_keys=True),
                            chunk["created_at"],
                        ),
                    )
                    connection.execute(
                        """
                        INSERT INTO dev_chunks_fts(chunk_id, source_type, source_path, title, chunk_text)
                        VALUES(?, ?, ?, ?, ?)
                        """,
                        (
                            chunk["chunk_id"],
                            chunk["source_type"],
                            chunk["source_path"],
                            chunk["title"],
                            chunk["chunk_text"],
                        ),
                    )
                    vector = hash_embedding(chunk["chunk_text"], dimensions=DEFAULT_DIMENSIONS)
                    connection.execute(
                        """
                        INSERT INTO dev_embeddings(
                          chunk_id, corpus_id, run_id, source_type, source_path,
                          embedding_model, dimensions, vector_json, metadata_json, updated_at
                        )
                        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(chunk_id, embedding_model) DO UPDATE SET
                          corpus_id = excluded.corpus_id,
                          run_id = excluded.run_id,
                          source_type = excluded.source_type,
                          source_path = excluded.source_path,
                          dimensions = excluded.dimensions,
                          vector_json = excluded.vector_json,
                          metadata_json = excluded.metadata_json,
                          updated_at = excluded.updated_at
                        """,
                        (
                            chunk["chunk_id"],
                            chunk["corpus_id"],
                            chunk["run_id"],
                            chunk["source_type"],
                            chunk["source_path"],
                            MODEL_NAME,
                            DEFAULT_DIMENSIONS,
                            json.dumps(vector, ensure_ascii=False),
                            json.dumps(chunk["metadata"], ensure_ascii=False, sort_keys=True),
                            started_at,
                        ),
                    )
                    embedding_count += 1
            finished_at = datetime.now(UTC).isoformat()
            command_count = sum(1 for source in sources if (source.get("metadata") or {}).get("kind") == "command")
            run_payload = {
                "run_checks": run_checks,
                "replace": replace,
                "sources": [
                    {
                        "source_type": source.get("source_type") or "",
                        "source_path": source.get("source_path") or "",
                        "title": source.get("title") or "",
                        "content_hash": source.get("content_hash") or "",
                    }
                    for source in sources
                ],
            }
            connection.execute(
                """
                INSERT INTO dev_runs(
                  run_id, status, started_at, finished_at, source_count,
                  chunk_count, embedding_count, command_count, error, payload_json
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                  status = excluded.status,
                  finished_at = excluded.finished_at,
                  source_count = excluded.source_count,
                  chunk_count = excluded.chunk_count,
                  embedding_count = excluded.embedding_count,
                  command_count = excluded.command_count,
                  error = excluded.error,
                  payload_json = excluded.payload_json
                """,
                (
                    run_id,
                    "succeeded",
                    started_at,
                    finished_at,
                    len(sources),
                    len(chunks),
                    embedding_count,
                    command_count,
                    "",
                    json.dumps(run_payload, ensure_ascii=False, sort_keys=True),
                ),
            )
            connection.commit()
        except Exception as exc:
            connection.rollback()
            finished_at = datetime.now(UTC).isoformat()
            connection.execute(
                """
                INSERT INTO dev_runs(
                  run_id, status, started_at, finished_at, source_count,
                  chunk_count, embedding_count, command_count, error, payload_json
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                  status = excluded.status,
                  finished_at = excluded.finished_at,
                  error = excluded.error,
                  payload_json = excluded.payload_json
                """,
                (
                    run_id,
                    "failed",
                    started_at,
                    finished_at,
                    0,
                    0,
                    0,
                    0,
                    str(exc)[:1000],
                    json.dumps({"run_checks": run_checks, "replace": replace}, ensure_ascii=False, sort_keys=True),
                ),
            )
            connection.commit()
            raise
        finally:
            connection.close()

        return {
            "schema_version": 1,
            "run_id": run_id,
            "status": "succeeded",
            "source_count": len(sources),
            "chunk_count": len(chunks),
            "embedding_count": embedding_count,
            "command_count": sum(1 for source in sources if (source.get("metadata") or {}).get("kind") == "command"),
            "started_at": started_at,
            "finished_at": finished_at,
        }

    def dev_context_search(
        self,
        *,
        query: str,
        source_type: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        self.ensure_sqlite_index()
        normalized_query = (_blank_to_none(query) or "").strip()
        terms = _search_terms(normalized_query)
        limit = max(1, min(int(limit or 20), 100))
        if not terms:
            return {
                "schema_version": 1,
                "query": normalized_query,
                "source_type": _blank_to_none(source_type) or "",
                "count": 0,
                "results": [],
                "summary": ["请输入开发上下文搜索关键词。"],
            }

        connection = connect(self.db_path)
        search_engine = "fts5"
        try:
            initialize(connection)
            try:
                rows = _dev_context_search_fts(
                    connection,
                    terms=terms,
                    source_type=_blank_to_none(source_type),
                    limit=limit * 3,
                )
                if not rows:
                    search_engine = "like"
                    rows = _dev_context_search_like(
                        connection,
                        terms=terms,
                        source_type=_blank_to_none(source_type),
                        limit=limit * 3,
                    )
            except sqlite3.Error:
                search_engine = "like"
                rows = _dev_context_search_like(
                    connection,
                    terms=terms,
                    source_type=_blank_to_none(source_type),
                    limit=limit * 3,
                )
        finally:
            connection.close()

        results = [_dev_context_result(row, terms) for row in rows][:limit]
        return {
            "schema_version": 1,
            "query": normalized_query,
            "source_type": _blank_to_none(source_type) or "",
            "search_engine": search_engine,
            "count": len(results),
            "results": results,
            "summary": _dev_context_search_summary(results, terms),
        }

    def dev_context_ask(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        question = str(payload.get("q") or payload.get("question") or payload.get("query") or "").strip()
        source_type = _blank_to_none(payload.get("source_type"))
        limit = max(1, min(_int_value(payload.get("limit")) or 8, 20))
        if not question:
            return {
                "schema_version": 1,
                "question": "",
                "answer": "请输入开发上下文问题。",
                "confidence": "low",
                "evidence": [],
                "citations": [],
                "next_actions": ["先输入一个具体问题，例如“最近测试为什么失败？”或“当前下一步该做什么？”。"],
                "retrieval": {"query": "", "count": 0, "search_engine": ""},
            }
        retrieval = self.dev_context_search(
            query=_dev_context_question_query(question),
            source_type=source_type,
            limit=limit,
        )
        evidence = [_dev_context_evidence_item(item, index) for index, item in enumerate(retrieval.get("results") or [], start=1)]
        answer_pack = _dev_context_answer(question, evidence)
        return {
            "schema_version": 1,
            "question": question,
            "answer": answer_pack["answer"],
            "confidence": answer_pack["confidence"],
            "question_type": answer_pack["question_type"],
            "evidence": evidence,
            "citations": [
                {
                    "index": item["index"],
                    "chunk_id": item["chunk_id"],
                    "source_type": item["source_type"],
                    "source_path": item["source_path"],
                    "title": item["title"],
                    "run_id": item["run_id"],
                }
                for item in evidence
            ],
            "next_actions": answer_pack["next_actions"],
            "retrieval": {
                "query": retrieval.get("query") or "",
                "source_type": retrieval.get("source_type") or "",
                "search_engine": retrieval.get("search_engine") or "",
                "count": retrieval.get("count") or 0,
            },
        }

    def plan_dev_context_index(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload if isinstance(payload, dict) else {}
        request = {
            "run_checks": _bool_value(payload.get("run_checks"), False),
            "replace": _bool_value(payload.get("replace"), False),
            "max_command_chars": max(2000, min(_int_value(payload.get("max_command_chars")) or 120000, 250000)),
            "confirm_execution": True,
            "requested_by": str(payload.get("requested_by") or "api").strip()[:120],
            "trigger_source": str(payload.get("trigger_source") or "dev_context_index_plan_api").strip()[:80],
        }
        duplicate = self._find_active_duplicate_job(request, kind="dev_context_index")
        if duplicate:
            return {
                "schema_version": 1,
                "accepted": True,
                "planned_job_created": False,
                "job_id": duplicate.get("job_id") or "",
                "status": duplicate.get("status") or "",
                "request": request,
                "duplicate_of": duplicate.get("job_id") or "",
                "job": duplicate,
            }

        submitted_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        job_id = _dev_context_index_plan_job_id(submitted_at, request)
        job = {
            "job_id": job_id,
            "kind": "dev_context_index",
            "status": "planned",
            "run_date": "",
            "submitted_at": submitted_at,
            "started_at": "",
            "finished_at": "",
            "request": request,
            "result": {},
            "error": "",
        }
        self._persist_preview_job(job)
        self._record_job_event(
            job_id,
            "job_created",
            "planned",
            str(request.get("requested_by") or "api"),
            "已创建开发上下文索引 planned 任务。",
            {"request": request},
        )
        return {
            "schema_version": 1,
            "accepted": True,
            "planned_job_created": True,
            "job_id": job_id,
            "status": "planned",
            "request": request,
            "job": job,
        }

    def dev_context_run(self, run_id: str) -> dict[str, Any]:
        self.ensure_sqlite_index()
        normalized = str(run_id or "").strip()
        connection = connect(self.db_path)
        try:
            initialize(connection)
            run = connection.execute("SELECT * FROM dev_runs WHERE run_id = ?", (normalized,)).fetchone()
            if not run:
                return {"schema_version": 1, "found": False, "run_id": normalized}
            sources = [
                _dev_context_corpus_from_row(row)
                for row in connection.execute(
                    """
                    SELECT corpus_id, run_id, source_type, source_path, title,
                           content_hash, metadata_json, created_at
                    FROM dev_corpus
                    WHERE run_id = ?
                    ORDER BY source_type ASC, source_path ASC
                    """,
                    (normalized,),
                ).fetchall()
            ]
            chunks = [
                _dev_context_result(row, [])
                for row in connection.execute(
                    """
                    SELECT *
                    FROM dev_chunks
                    WHERE run_id = ?
                    ORDER BY source_type ASC, source_path ASC, chunk_index ASC
                    LIMIT 50
                    """,
                    (normalized,),
                ).fetchall()
            ]
        finally:
            connection.close()
        return {
            "schema_version": 1,
            "found": True,
            "run": _dev_context_run_from_row(run),
            "source_count": len(sources),
            "sources": sources,
            "sample_chunks": chunks,
        }

    def rag_corpus(
        self,
        *,
        query: str | None = None,
        language: str | None = None,
        category: str | None = None,
        source: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        self.ensure_sqlite_index()
        normalized_query = (_blank_to_none(query) or "").strip()
        terms = _search_terms(normalized_query)
        limit = max(1, min(int(limit or 20), 100))
        normalized_language = _blank_to_none(language)
        normalized_category = _blank_to_none(category)
        normalized_source = _blank_to_none(source)

        connection = connect(self.db_path)
        retrieval_mode = "latest"
        try:
            initialize(connection)
            if terms:
                try:
                    rows = _search_rows_fts(
                        connection,
                        terms=terms,
                        language=normalized_language,
                        category=normalized_category,
                        source=normalized_source,
                        limit=limit,
                    )
                    retrieval_mode = "fts5"
                except sqlite3.Error:
                    rows = _search_rows_like(
                        connection,
                        terms=terms,
                        language=normalized_language,
                        category=normalized_category,
                        source=normalized_source,
                        limit=limit,
                    )
                    retrieval_mode = "like"
            else:
                rows = _corpus_rows_latest(
                    connection,
                    language=normalized_language,
                    category=normalized_category,
                    source=normalized_source,
                    limit=limit,
                )
        finally:
            connection.close()

        documents = [_rag_document(row, terms) for row in rows]
        return {
            "schema_version": 1,
            "query": normalized_query,
            "language": normalized_language or "",
            "category": normalized_category or "",
            "source": normalized_source or "",
            "count": len(documents),
            "documents": documents,
            "retrieval": {
                "mode": retrieval_mode,
                "terms": terms,
                "limit": limit,
            },
            "rag_readiness": _rag_corpus_readiness(documents),
        }

    def rag_retrieve(
        self,
        *,
        query: str,
        language: str | None = None,
        category: str | None = None,
        source: str | None = None,
        limit: int = 8,
    ) -> dict[str, Any]:
        self.ensure_sqlite_index()
        normalized_query = (_blank_to_none(query) or "").strip()
        terms = _search_terms(normalized_query)
        limit = max(1, min(int(limit or 8), 30))
        normalized_language = _blank_to_none(language)
        normalized_category = _blank_to_none(category)
        normalized_source = _blank_to_none(source)
        if not terms:
            return {
                "schema_version": 1,
                "query": normalized_query,
                "count": 0,
                "contexts": [],
                "citations": [],
                "retrieval": {"mode": "", "terms": [], "limit": limit},
                "prompt_context": "",
                "summary": ["请输入用于 RAG 检索的问题或关键词。"],
            }

        connection = connect(self.db_path)
        retrieval_mode = "fts5"
        try:
            initialize(connection)
            try:
                rows = _rag_chunk_rows_fts(
                    connection,
                    terms=terms,
                    language=normalized_language,
                    category=normalized_category,
                    source=normalized_source,
                    limit=limit * 3,
                )
            except sqlite3.Error:
                rows = _rag_chunk_rows_like(
                    connection,
                    terms=terms,
                    language=normalized_language,
                    category=normalized_category,
                    source=normalized_source,
                    limit=limit * 3,
                )
                retrieval_mode = "like"
        finally:
            connection.close()

        contexts = _dedupe_rag_contexts(
            sorted(
                [_rag_context(row, terms) for row in rows],
                key=lambda item: (item["score"], item["metadata"]["run_date"], item["metadata"]["full_name"]),
                reverse=True,
            )
        )[:limit]
        return {
            "schema_version": 1,
            "query": normalized_query,
            "language": normalized_language or "",
            "category": normalized_category or "",
            "source": normalized_source or "",
            "count": len(contexts),
            "contexts": contexts,
            "citations": _rag_citations(contexts),
            "retrieval": {"mode": retrieval_mode, "terms": terms, "limit": limit},
            "prompt_context": _rag_prompt_context(contexts),
            "summary": _rag_retrieve_summary(contexts, terms),
        }

    def rag_vector_search(
        self,
        *,
        query: str,
        language: str | None = None,
        category: str | None = None,
        source: str | None = None,
        limit: int = 8,
        model: str = MODEL_NAME,
        auto_build: bool = False,
    ) -> dict[str, Any]:
        self.ensure_sqlite_index()
        normalized_query = (_blank_to_none(query) or "").strip()
        terms = _search_terms(normalized_query)
        limit = max(1, min(int(limit or 8), 30))
        model = _blank_to_none(model) or MODEL_NAME
        if not terms:
            return {
                "schema_version": 1,
                "query": normalized_query,
                "count": 0,
                "contexts": [],
                "citations": [],
                "retrieval": {"mode": "vector", "model": model, "limit": limit, "auto_build": bool(auto_build)},
                "prompt_context": "",
                "summary": ["请输入用于向量检索的问题或关键词。"],
            }

        if auto_build and self._embedding_count(model) == 0:
            build_rag_embeddings(self.db_path, model=model)

        query_vector = hash_embedding(normalized_query)
        rows = self._embedding_rows(model)
        contexts = []
        for row in rows:
            payload = _json_object(row["payload_json"])
            if language and str(payload.get("language") or "") != language:
                continue
            if category and str(payload.get("category") or "") != category:
                continue
            sources = _list_strings(payload.get("sources") or [])
            if source and source not in sources:
                continue
            score = cosine_similarity(query_vector, vector_from_json(row["vector_json"]))
            if score <= 0:
                continue
            contexts.append(_vector_context(row, payload, score, terms))
        contexts = sorted(
            contexts,
            key=lambda item: (item["score"], item["metadata"]["run_date"], item["metadata"]["full_name"]),
            reverse=True,
        )[:limit]
        return {
            "schema_version": 1,
            "query": normalized_query,
            "language": _blank_to_none(language) or "",
            "category": _blank_to_none(category) or "",
            "source": _blank_to_none(source) or "",
            "count": len(contexts),
            "contexts": contexts,
            "citations": _rag_citations(contexts),
            "retrieval": {"mode": "vector", "model": model, "limit": limit, "auto_build": bool(auto_build)},
            "prompt_context": _rag_prompt_context(contexts),
            "summary": _rag_vector_summary(contexts, model),
        }

    def rag_hybrid_search(
        self,
        *,
        query: str,
        language: str | None = None,
        category: str | None = None,
        source: str | None = None,
        limit: int = 8,
        model: str = MODEL_NAME,
        auto_build: bool = False,
    ) -> dict[str, Any]:
        normalized_query = (_blank_to_none(query) or "").strip()
        terms = _search_terms(normalized_query)
        limit = max(1, min(int(limit or 8), 30))
        model = _blank_to_none(model) or MODEL_NAME
        if not terms:
            return {
                "schema_version": 1,
                "query": normalized_query,
                "count": 0,
                "contexts": [],
                "citations": [],
                "retrieval": {
                    "mode": "hybrid",
                    "terms": [],
                    "limit": limit,
                    "model": model,
                    "auto_build": bool(auto_build),
                    "weights": {"text": 0.55, "vector": 0.45},
                },
                "prompt_context": "",
                "summary": ["请输入用于混合 RAG 检索的问题或关键词。"],
            }

        candidate_limit = min(30, max(limit * 2, limit))
        text_result = self.rag_retrieve(
            query=normalized_query,
            language=language,
            category=category,
            source=source,
            limit=candidate_limit,
        )
        vector_result = self.rag_vector_search(
            query=normalized_query,
            language=language,
            category=category,
            source=source,
            limit=candidate_limit,
            model=model,
            auto_build=auto_build,
        )
        contexts = _merge_hybrid_contexts(
            text_result.get("contexts") if isinstance(text_result.get("contexts"), list) else [],
            vector_result.get("contexts") if isinstance(vector_result.get("contexts"), list) else [],
            limit=limit,
        )
        return {
            "schema_version": 1,
            "query": normalized_query,
            "language": _blank_to_none(language) or "",
            "category": _blank_to_none(category) or "",
            "source": _blank_to_none(source) or "",
            "count": len(contexts),
            "contexts": contexts,
            "citations": _rag_citations(contexts),
            "retrieval": {
                "mode": "hybrid",
                "terms": terms,
                "limit": limit,
                "model": model,
                "auto_build": bool(auto_build),
                "weights": {"text": 0.55, "vector": 0.45},
                "text_mode": text_result.get("retrieval", {}).get("mode") or "",
                "text_count": len(text_result.get("contexts") or []),
                "vector_count": len(vector_result.get("contexts") or []),
            },
            "prompt_context": _rag_prompt_context(contexts),
            "summary": _rag_hybrid_summary(contexts, model),
        }

    def rag_search_compare(
        self,
        *,
        query: str,
        language: str | None = None,
        category: str | None = None,
        source: str | None = None,
        limit: int = 8,
        model: str = MODEL_NAME,
        auto_build: bool = False,
    ) -> dict[str, Any]:
        normalized_query = (_blank_to_none(query) or "").strip()
        limit = max(1, min(int(limit or 8), 30))
        model = _blank_to_none(model) or MODEL_NAME
        text_result = self.rag_retrieve(
            query=normalized_query,
            language=language,
            category=category,
            source=source,
            limit=limit,
        )
        vector_result = self.rag_vector_search(
            query=normalized_query,
            language=language,
            category=category,
            source=source,
            limit=limit,
            model=model,
            auto_build=auto_build,
        )
        hybrid_result = self.rag_hybrid_search(
            query=normalized_query,
            language=language,
            category=category,
            source=source,
            limit=limit,
            model=model,
            auto_build=auto_build,
        )
        modes = {
            "fts5": _rag_compare_mode_summary(text_result),
            "vector": _rag_compare_mode_summary(vector_result),
            "hybrid": _rag_compare_mode_summary(hybrid_result),
        }
        overlap = _rag_compare_overlap(modes)
        recommendation = _rag_compare_recommendation(modes, overlap)
        return {
            "schema_version": 1,
            "query": normalized_query,
            "language": _blank_to_none(language) or "",
            "category": _blank_to_none(category) or "",
            "source": _blank_to_none(source) or "",
            "limit": limit,
            "model": model,
            "auto_build": bool(auto_build),
            "modes": modes,
            "overlap": overlap,
            "recommendation": recommendation,
            "summary": _rag_compare_summary(modes, overlap, recommendation),
        }

    def rag_search_evaluation(
        self,
        *,
        queries: list[str] | None = None,
        language: str | None = None,
        category: str | None = None,
        source: str | None = None,
        limit: int = 8,
        model: str = MODEL_NAME,
        auto_build: bool = False,
    ) -> dict[str, Any]:
        sample_queries = _normalize_rag_evaluation_queries(queries)
        limit = max(1, min(int(limit or 8), 30))
        model = _blank_to_none(model) or MODEL_NAME
        evaluations = [
            self.rag_search_compare(
                query=query,
                language=language,
                category=category,
                source=source,
                limit=limit,
                model=model,
                auto_build=auto_build,
            )
            for query in sample_queries
        ]
        aggregate = _rag_evaluation_aggregate(evaluations)
        return {
            "schema_version": 1,
            "sample_count": len(sample_queries),
            "queries": sample_queries,
            "language": _blank_to_none(language) or "",
            "category": _blank_to_none(category) or "",
            "source": _blank_to_none(source) or "",
            "limit": limit,
            "model": model,
            "auto_build": bool(auto_build),
            "aggregate": aggregate,
            "evaluations": evaluations,
            "summary": _rag_evaluation_summary(aggregate),
        }

    def persist_rag_search_evaluation(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        request = _rag_search_evaluation_request(payload)
        if not request["confirm_execution"]:
            return {
                "schema_version": 1,
                "accepted": False,
                "executed": False,
                "status": "blocked",
                "blockers": ["需要显式传入 confirm_execution=true 才会写入 SQLite jobs。"],
                "request": request,
                "preview": self.rag_search_evaluation(
                    queries=request["queries"],
                    language=request["language"] or None,
                    category=request["category"] or None,
                    source=request["source"] or None,
                    limit=request["limit"],
                    model=request["model"],
                    auto_build=request["auto_build"],
                ),
            }

        submitted_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        run_date = submitted_at[:10]
        job_id = _rag_search_evaluation_job_id(submitted_at, request)
        actor = request["requested_by"]
        running_job = {
            "job_id": job_id,
            "kind": "rag_search_evaluation",
            "status": "running",
            "run_date": run_date,
            "submitted_at": submitted_at,
            "started_at": submitted_at,
            "finished_at": "",
            "request": request,
            "result": {},
            "error": "",
        }
        self._persist_preview_job(running_job)
        self._record_job_event(
            job_id,
            "rag_search_evaluation_started",
            "running",
            actor,
            "RAG 检索评估已开始。",
            {"request": request},
        )
        try:
            result = self.rag_search_evaluation(
                queries=request["queries"],
                language=request["language"] or None,
                category=request["category"] or None,
                source=request["source"] or None,
                limit=request["limit"],
                model=request["model"],
                auto_build=request["auto_build"],
            )
        except Exception as exc:  # pragma: no cover - defensive audit path
            finished_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            failed_job = {
                **running_job,
                "status": "failed",
                "finished_at": finished_at,
                "error": str(exc),
                "result": {"error": str(exc)},
            }
            self._persist_preview_job(failed_job)
            self._record_job_event(
                job_id,
                "rag_search_evaluation_failed",
                "failed",
                actor,
                "RAG 检索评估失败。",
                {"error": str(exc)},
            )
            return {
                "schema_version": 1,
                "accepted": True,
                "executed": False,
                "status": "failed",
                "job_id": job_id,
                "error": str(exc),
                "request": request,
            }

        finished_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        result["job_id"] = job_id
        result["request"] = request
        succeeded_job = {
            **running_job,
            "status": "succeeded",
            "finished_at": finished_at,
            "result": _rag_search_evaluation_job_result(result),
            "payload": result,
        }
        self._persist_preview_job(succeeded_job)
        self._record_job_event(
            job_id,
            "rag_search_evaluation_succeeded",
            "succeeded",
            actor,
            "RAG 检索评估已完成并写入 jobs。",
            {"aggregate": result.get("aggregate") or {}, "sample_count": result.get("sample_count", 0)},
        )
        return {
            "schema_version": 1,
            "accepted": True,
            "executed": True,
            "status": "succeeded",
            "job_id": job_id,
            "request": request,
            "result": result,
        }

    def rag_search_evaluation_trends(self, *, limit: int = 20) -> dict[str, Any]:
        limit = max(1, min(_int_value(limit) or 20, 100))
        jobs = [
            job
            for job in self.jobs(kind="rag_search_evaluation", status="succeeded", limit=max(limit, 100)).get("jobs", [])
            if job.get("kind") == "rag_search_evaluation"
        ][:limit]
        trend_items = [_rag_search_evaluation_trend_item(job) for job in jobs]
        aggregate = _rag_search_evaluation_trend_aggregate(trend_items)
        return {
            "schema_version": 1,
            "count": len(trend_items),
            "jobs": trend_items,
            "aggregate": aggregate,
            "summary": _rag_search_evaluation_trend_summary(aggregate),
            "recommendations": _rag_search_evaluation_trend_recommendations(aggregate),
        }

    def rag_explain(
        self,
        *,
        query: str,
        language: str | None = None,
        category: str | None = None,
        source: str | None = None,
        limit: int = 8,
        mode: str = "fts5",
        model: str = MODEL_NAME,
        auto_build: bool = False,
    ) -> dict[str, Any]:
        normalized_mode = (_blank_to_none(mode) or "fts5").lower()
        if normalized_mode in {"hybrid", "mixed"}:
            retrieval = self.rag_hybrid_search(
                query=query,
                language=language,
                category=category,
                source=source,
                limit=limit,
                model=model,
                auto_build=auto_build,
            )
        elif normalized_mode in {"vector", "embedding", "semantic"}:
            retrieval = self.rag_vector_search(
                query=query,
                language=language,
                category=category,
                source=source,
                limit=limit,
                model=model,
                auto_build=auto_build,
            )
        else:
            retrieval = self.rag_retrieve(
                query=query,
                language=language,
                category=category,
                source=source,
                limit=limit,
            )
        contexts = retrieval.get("contexts") if isinstance(retrieval.get("contexts"), list) else []
        citations = retrieval.get("citations") if isinstance(retrieval.get("citations"), list) else []
        prompt_context = str(retrieval.get("prompt_context") or "")
        explanation = _rag_explanation(
            query=str(retrieval.get("query") or query or ""),
            contexts=contexts,
            citations=citations,
            retrieval=retrieval.get("retrieval") or {},
        )
        result = {
            "schema_version": 1,
            "query": retrieval.get("query") or (_blank_to_none(query) or ""),
            "language": retrieval.get("language") or "",
            "category": retrieval.get("category") or "",
            "source": retrieval.get("source") or "",
            "count": len(contexts),
            "contexts": contexts,
            "citations": citations,
            "retrieval": retrieval.get("retrieval") or {},
            "summary": retrieval.get("summary") or [],
            "prompt_context": prompt_context,
            "explanation": explanation,
            "quality": _rag_explanation_quality(
                contexts=contexts,
                citations=citations,
                explanation=explanation,
                prompt_context=prompt_context,
            ),
        }
        return self._persist_rag_explanation(result)

    def rag_ask(
        self,
        *,
        query: str,
        language: str | None = None,
        category: str | None = None,
        source: str | None = None,
        limit: int = 8,
        mode: str = "fts5",
        model: str = MODEL_NAME,
        auto_build: bool = False,
    ) -> dict[str, Any]:
        explained = self.rag_explain(
            query=query,
            language=language,
            category=category,
            source=source,
            limit=limit,
            mode=mode,
            model=model,
            auto_build=auto_build,
        )
        answer_result = answer_rag_question(
            root=self.root,
            query=str(explained.get("query") or query or ""),
            retrieval={
                "query": explained.get("query") or query,
                "contexts": explained.get("contexts") if isinstance(explained.get("contexts"), list) else [],
                "citations": explained.get("citations") if isinstance(explained.get("citations"), list) else [],
                "retrieval": explained.get("retrieval") or {},
                "prompt_context": explained.get("prompt_context") or "",
            },
        )
        explanation = explained.get("explanation") if isinstance(explained.get("explanation"), dict) else {}
        quality = explained.get("quality") if isinstance(explained.get("quality"), dict) else answer_result.get("quality") or {}
        answer = str(answer_result.get("answer") or explanation.get("answer") or "当前没有足够 RAG 证据形成回答。")
        evidence = answer_result.get("evidence") if isinstance(answer_result.get("evidence"), list) else []
        citations = answer_result.get("citations") if isinstance(answer_result.get("citations"), list) else []
        contexts = answer_result.get("contexts") if isinstance(answer_result.get("contexts"), list) else []
        notification_memory = _notification_rag_memory(self.db_path, query, limit=limit)
        notification_evidence = notification_memory.get("evidence") if isinstance(notification_memory.get("evidence"), list) else []
        notification_citations = notification_memory.get("citations") if isinstance(notification_memory.get("citations"), list) else []
        if notification_memory.get("event_count"):
            answer = f"{answer}\n\n通知记忆：{notification_memory.get('summary') or ''}".strip()
            evidence = [*evidence, *notification_evidence]
            citations = [*citations, *notification_citations]
        return {
            "schema_version": 1,
            "query": explained.get("query") or query,
            "answer": answer,
            "answer_model": answer_result.get("answer_model") or "rule:rag-ask-v1",
            "answer_mode": answer_result.get("answer_mode") or "fallback_rule",
            "fallback_reason": answer_result.get("fallback_reason") or "",
            "confidence": "medium" if notification_memory.get("event_count") and not contexts else answer_result.get("confidence") or explanation.get("confidence") or "low",
            "count": len(contexts) + len(notification_evidence),
            "retrieval": answer_result.get("retrieval") or explained.get("retrieval") or {},
            "citations": citations,
            "evidence": evidence,
            "quality": quality,
            "prompt_context": answer_result.get("prompt_context") or explained.get("prompt_context") or "",
            "source_explanation_id": explained.get("explanation_id") or "",
            "cached": bool(explained.get("cached")),
            "next_actions": _rag_answer_next_actions(explanation=explanation, quality=quality, citations=citations),
            "contexts": contexts,
            "notification_memory": notification_memory,
            "model_status": answer_result.get("model_status") or {},
            "answer_quality": answer_result.get("answer_quality") or {},
        }

    def rag_explanations(
        self,
        *,
        limit: int = 20,
        query: str | None = None,
        repo: str | None = None,
    ) -> dict[str, Any]:
        self.ensure_sqlite_index()
        limit = max(1, min(int(limit or 20), 100))
        normalized_query = _blank_to_none(query)
        normalized_repo = _blank_to_none(repo)
        connection = connect(self.db_path)
        try:
            initialize(connection)
            params: list[Any] = []
            filters: list[str] = []
            if normalized_query:
                filters.append("(query LIKE ? OR answer LIKE ?)")
                like = f"%{normalized_query}%"
                params.extend([like, like])
            if normalized_repo:
                filters.append("repositories_json LIKE ?")
                params.append(f"%{normalized_repo}%")
            where = f"WHERE {' AND '.join(filters)}" if filters else ""
            rows = connection.execute(
                f"""
                SELECT explanation_id, query, language, category, source, mode, model,
                       context_count, confidence, quality_score, quality_level, quality_json,
                       answer, repositories_json, citations_json,
                       explanation_json, retrieval_json, created_at
                FROM rag_explanations
                {where}
                ORDER BY created_at DESC, explanation_id DESC
                LIMIT ?
                """,
                (*params, limit),
            ).fetchall()
        finally:
            connection.close()

        explanations = [_rag_explanation_row(row) for row in rows]
        return {
            "schema_version": 1,
            "count": len(explanations),
            "query": normalized_query or "",
            "repo": normalized_repo or "",
            "explanations": explanations,
        }

    def rag_quality_summary(self, *, limit: int = 10) -> dict[str, Any]:
        self.ensure_sqlite_index()
        limit = max(1, min(int(limit or 10), 50))
        connection = connect(self.db_path)
        try:
            initialize(connection)
            summary_row = connection.execute(
                """
                SELECT COUNT(*) AS total_count,
                       AVG(quality_score) AS average_quality_score,
                       MIN(quality_score) AS min_quality_score,
                       MAX(quality_score) AS max_quality_score
                FROM rag_explanations
                """
            ).fetchone()
            quality_levels = _group_counts(connection, "rag_explanations", "quality_level")
            confidence_levels = _group_counts(connection, "rag_explanations", "confidence")
            modes = _group_counts(connection, "rag_explanations", "mode")
            recent_low_quality_rows = connection.execute(
                """
                SELECT explanation_id, query, language, category, source, mode, model,
                       context_count, confidence, quality_score, quality_level, quality_json,
                       answer, repositories_json, citations_json,
                       explanation_json, retrieval_json, created_at
                FROM rag_explanations
                WHERE quality_level = 'low' OR quality_score < 55
                ORDER BY created_at DESC, quality_score ASC, explanation_id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            latest_rows = connection.execute(
                """
                SELECT explanation_id, query, language, category, source, mode, model,
                       context_count, confidence, quality_score, quality_level, quality_json,
                       answer, repositories_json, citations_json,
                       explanation_json, retrieval_json, created_at
                FROM rag_explanations
                ORDER BY created_at DESC, explanation_id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        finally:
            connection.close()

        total_count = _int_value(summary_row["total_count"] if summary_row else 0)
        average_quality_score = round(float(summary_row["average_quality_score"] or 0), 2) if summary_row else 0
        return {
            "schema_version": 1,
            "total_count": total_count,
            "average_quality_score": average_quality_score,
            "min_quality_score": _int_value(summary_row["min_quality_score"] if summary_row else 0),
            "max_quality_score": _int_value(summary_row["max_quality_score"] if summary_row else 0),
            "quality_levels": quality_levels,
            "confidence_levels": confidence_levels,
            "modes": modes,
            "recent_low_quality": [_rag_explanation_row(row) for row in recent_low_quality_rows],
            "latest": [_rag_explanation_row(row) for row in latest_rows],
            "recommendations": _rag_quality_recommendations(total_count, average_quality_score, quality_levels),
        }

    def rag_coverage(self, *, limit: int = 20) -> dict[str, Any]:
        self.ensure_sqlite_index()
        limit = max(1, min(int(limit or 20), 100))
        connection = connect(self.db_path)
        try:
            initialize(connection)
            project_rows = connection.execute(
                """
                SELECT full_name, html_url, language, category, run_date
                FROM project_corpus
                WHERE full_name <> ''
                ORDER BY run_date DESC, full_name ASC
                """
            ).fetchall()
            chunk_counts = {
                row["full_name"]: _int_value(row["count"])
                for row in connection.execute(
                    """
                    SELECT full_name, COUNT(*) AS count
                    FROM rag_chunks
                    WHERE full_name <> ''
                    GROUP BY full_name
                    """
                ).fetchall()
            }
            embedding_counts = {
                row["full_name"]: _int_value(row["count"])
                for row in connection.execute(
                    """
                    SELECT full_name, COUNT(*) AS count
                    FROM rag_embeddings
                    WHERE full_name <> ''
                    GROUP BY full_name
                    """
                ).fetchall()
            }
            explanation_rows = connection.execute(
                """
                SELECT repositories_json, quality_score
                FROM rag_explanations
                """
            ).fetchall()
        finally:
            connection.close()

        latest_projects: dict[str, dict[str, Any]] = {}
        for row in project_rows:
            full_name = row["full_name"]
            if full_name not in latest_projects:
                latest_projects[full_name] = {
                    "full_name": full_name,
                    "html_url": row["html_url"],
                    "language": row["language"],
                    "category": row["category"],
                    "latest_run_date": row["run_date"],
                }

        explanation_counts: dict[str, int] = {}
        explanation_scores: dict[str, list[int]] = {}
        for row in explanation_rows:
            score = _int_value(row["quality_score"])
            for full_name in _list_strings(_json_list(row["repositories_json"])):
                explanation_counts[full_name] = explanation_counts.get(full_name, 0) + 1
                explanation_scores.setdefault(full_name, []).append(score)

        gaps = []
        healthy_count = 0
        for full_name, project in latest_projects.items():
            chunk_count = chunk_counts.get(full_name, 0)
            embedding_count = embedding_counts.get(full_name, 0)
            explanation_count = explanation_counts.get(full_name, 0)
            scores = explanation_scores.get(full_name, [])
            average_quality = round(sum(scores) / len(scores), 2) if scores else 0
            gap_reasons = []
            if chunk_count <= 0:
                gap_reasons.append("缺少 RAG 证据块，需要重建 project_corpus/rag_chunks。")
            if embedding_count <= 0:
                gap_reasons.append("缺少本地 embedding，向量检索无法覆盖该项目。")
            if explanation_count <= 0:
                gap_reasons.append("缺少 RAG 解释历史，项目详情页无法展示解释质量。")
            elif average_quality < 75:
                gap_reasons.append("解释平均质量分偏低，建议补充语料或扩大召回。")
            if not gap_reasons:
                healthy_count += 1
            gaps.append(
                {
                    **project,
                    "chunk_count": chunk_count,
                    "embedding_count": embedding_count,
                    "explanation_count": explanation_count,
                    "average_quality_score": average_quality,
                    "gap_reasons": gap_reasons,
                }
            )

        gaps.sort(
            key=lambda item: (
                0 if item["gap_reasons"] else 1,
                item["chunk_count"] > 0,
                item["explanation_count"] > 0,
                item["embedding_count"] > 0,
                -len(item["gap_reasons"]),
                item["full_name"],
            )
        )
        total_projects = len(latest_projects)
        coverage_rate = round(healthy_count / total_projects, 4) if total_projects else 0
        return {
            "schema_version": 1,
            "total_projects": total_projects,
            "healthy_project_count": healthy_count,
            "coverage_rate": coverage_rate,
            "gap_count": total_projects - healthy_count,
            "gaps": gaps[:limit],
            "recommendations": _rag_coverage_recommendations(total_projects, healthy_count, gaps),
        }

    def rag_diagnostics(self, *, limit: int = 10) -> dict[str, Any]:
        limit = max(1, min(int(limit or 10), 50))
        database = self.database_summary()
        quality = self.rag_quality_summary(limit=limit)
        coverage = self.rag_coverage(limit=limit)
        table_counts = database.get("table_counts") if isinstance(database.get("table_counts"), dict) else {}
        readiness = database.get("rag_readiness") if isinstance(database.get("rag_readiness"), dict) else {}
        signals = {
            "has_corpus": _int_value(table_counts.get("project_corpus")) > 0,
            "has_chunks": _int_value(table_counts.get("rag_chunks")) > 0,
            "has_embeddings": _int_value(table_counts.get("rag_embeddings")) > 0,
            "has_explanations": _int_value(table_counts.get("rag_explanations")) > 0,
            "ready_for_text_search": bool(readiness.get("ready_for_text_search")),
            "ready_for_vector_search": _int_value(table_counts.get("rag_embeddings")) > 0,
            "ready_for_answering": _int_value(table_counts.get("rag_chunks")) > 0 and _int_value(quality.get("total_count")) > 0,
        }
        health = _rag_diagnostics_health(
            signals=signals,
            coverage_rate=float(coverage.get("coverage_rate") or 0),
            average_quality_score=float(quality.get("average_quality_score") or 0),
        )
        return {
            "schema_version": 1,
            "status": health["status"],
            "level": health["level"],
            "signals": signals,
            "table_counts": {
                "project_corpus": _int_value(table_counts.get("project_corpus")),
                "rag_chunks": _int_value(table_counts.get("rag_chunks")),
                "rag_embeddings": _int_value(table_counts.get("rag_embeddings")),
                "rag_explanations": _int_value(table_counts.get("rag_explanations")),
            },
            "quality": {
                "total_count": _int_value(quality.get("total_count")),
                "average_quality_score": float(quality.get("average_quality_score") or 0),
                "quality_levels": quality.get("quality_levels") or {},
                "recommendations": quality.get("recommendations") or [],
            },
            "coverage": {
                "total_projects": _int_value(coverage.get("total_projects")),
                "healthy_project_count": _int_value(coverage.get("healthy_project_count")),
                "coverage_rate": float(coverage.get("coverage_rate") or 0),
                "gap_count": _int_value(coverage.get("gap_count")),
                "gaps": coverage.get("gaps") or [],
                "recommendations": coverage.get("recommendations") or [],
            },
            "next_actions": _rag_diagnostics_next_actions(signals=signals, quality=quality, coverage=coverage),
        }

    def rag_maintenance_report(self, *, limit: int = 20) -> dict[str, Any]:
        limit = max(1, min(_int_value(limit) or 20, 100))
        maintenance_kinds = {"rag_backfill", "rag_corpus_rebuild", "rag_embedding_build", "rag_search_evaluation"}
        jobs = [
            job
            for job in self.jobs(limit=max(limit * 4, 100)).get("jobs", [])
            if job.get("kind") in maintenance_kinds
        ][:limit]
        by_kind: dict[str, dict[str, Any]] = {
            kind: {"kind": kind, "total_count": 0, "status_counts": {}, "latest_job": {}}
            for kind in sorted(maintenance_kinds)
        }
        latest_success = {}
        latest_failed = {}
        for job in jobs:
            kind = str(job.get("kind") or "")
            status = str(job.get("status") or "")
            bucket = by_kind.setdefault(kind, {"kind": kind, "total_count": 0, "status_counts": {}, "latest_job": {}})
            bucket["total_count"] += 1
            bucket["status_counts"][status] = _int_value(bucket["status_counts"].get(status)) + 1
            if not bucket["latest_job"]:
                bucket["latest_job"] = _rag_maintenance_job_summary(job)
            if status == "succeeded" and not latest_success:
                latest_success = _rag_maintenance_job_summary(job)
            if status == "failed" and not latest_failed:
                latest_failed = _rag_maintenance_job_summary(job)
        diagnostics = self.rag_diagnostics(limit=10)
        return {
            "schema_version": 1,
            "count": len(jobs),
            "status_counts": _count_by_field(jobs, "status"),
            "kind_counts": _count_by_field(jobs, "kind"),
            "by_kind": list(by_kind.values()),
            "latest_success": latest_success,
            "latest_failed": latest_failed,
            "recent_jobs": [_rag_maintenance_job_summary(job) for job in jobs[: min(limit, 10)]],
            "diagnostics": {
                "status": diagnostics.get("status") or "",
                "level": diagnostics.get("level") or "",
                "signals": diagnostics.get("signals") or {},
                "table_counts": diagnostics.get("table_counts") or {},
                "coverage": diagnostics.get("coverage") or {},
                "next_actions": diagnostics.get("next_actions") or [],
            },
            "recommendations": _rag_maintenance_report_recommendations(jobs, diagnostics),
        }

    def backfill_rag_explanations(
        self,
        *,
        limit: int = 10,
        rag_limit: int = 8,
        mode: str = "fts5",
        model: str = "local-hash-v1",
        auto_build: bool = False,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        limit = max(1, min(_int_value(limit) or 10, 100))
        rag_limit = max(1, min(_int_value(rag_limit) or 8, 30))
        mode_value = str(mode or "fts5").lower()
        if mode_value not in {"fts5", "vector"}:
            mode_value = "fts5"
        model_value = str(model or "local-hash-v1")

        coverage = self.rag_coverage(limit=100)
        candidates = [
            item
            for item in coverage.get("gaps", [])
            if _int_value(item.get("explanation_count")) <= 0 and item.get("full_name")
        ][:limit]

        processed = []
        for item in candidates:
            full_name = str(item["full_name"])
            bundle = self.project_rag_bundle(
                full_name,
                limit=rag_limit,
                explanation_limit=1,
                mode=mode_value,
                model=model_value,
                auto_build=auto_build,
            )
            project = bundle.get("project") if isinstance(bundle.get("project"), dict) else {}
            record = {
                "full_name": full_name,
                "query": bundle.get("query") or full_name,
                "dry_run": dry_run,
                "status": "planned" if dry_run else "created",
                "previous_gap_reasons": item.get("gap_reasons") or [],
            }
            if not dry_run:
                explanation = self.rag_explain(
                    query=str(record["query"]),
                    language=str(project.get("language") or item.get("language") or "") or None,
                    category=str(project.get("category") or item.get("category") or "") or None,
                    limit=rag_limit,
                    mode=mode_value,
                    model=model_value,
                    auto_build=auto_build,
                )
                record.update(
                    {
                        "explanation_id": explanation.get("explanation_id") or "",
                        "quality_score": explanation.get("quality", {}).get("score", 0),
                        "quality_level": explanation.get("quality", {}).get("level", ""),
                        "context_count": explanation.get("count", 0),
                    }
                )
            processed.append(record)

        return {
            "schema_version": 1,
            "status": "ok",
            "dry_run": dry_run,
            "requested_limit": limit,
            "candidate_count": len(candidates),
            "processed_count": len(processed),
            "processed": processed,
            "coverage_before": {
                "total_projects": coverage.get("total_projects", 0),
                "healthy_project_count": coverage.get("healthy_project_count", 0),
                "coverage_rate": coverage.get("coverage_rate", 0),
                "gap_count": coverage.get("gap_count", 0),
            },
        }

    def plan_rag_backfill(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        request = self._rag_backfill_request_from_payload(payload, default_trigger_source="rag_backfill_plan_api")
        duplicate = self._find_active_duplicate_job(request, kind="rag_backfill")
        if duplicate:
            return {
                "schema_version": 1,
                "accepted": True,
                "planned_job_created": False,
                "job_id": duplicate.get("job_id") or "",
                "status": duplicate.get("status") or "",
                "request": request,
                "safety_warnings": request.get("safety_warnings") or [],
                "duplicate_of": duplicate.get("job_id") or "",
                "job": duplicate,
            }
        submitted_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        job_id = _rag_backfill_plan_job_id(submitted_at, request)
        job = {
            "job_id": job_id,
            "kind": "rag_backfill",
            "status": "planned",
            "run_date": "",
            "submitted_at": submitted_at,
            "started_at": "",
            "finished_at": "",
            "request": request,
            "result": {},
            "error": "",
        }
        self._persist_preview_job(job)
        self._record_job_event(
            job_id,
            "job_created",
            "planned",
            str(request.get("requested_by") or "api"),
            "已创建 RAG 回填 planned 任务。",
            {"request": request},
        )
        return {
            "schema_version": 1,
            "accepted": True,
            "planned_job_created": True,
            "job_id": job_id,
            "status": "planned",
            "request": request,
            "safety_warnings": request.get("safety_warnings") or [],
            "job": job,
        }

    def plan_rag_corpus_rebuild(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        request = self._rag_maintenance_job_request(
            payload,
            action="rebuild_corpus",
            default_trigger_source="rag_corpus_rebuild_plan_api",
        )
        return self._plan_rag_maintenance_job(
            kind="rag_corpus_rebuild",
            request=request,
            message="已创建 RAG 语料重建 planned 任务。",
        )

    def plan_rag_embedding_build(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        request = self._rag_maintenance_job_request(
            payload,
            action="build_embeddings",
            default_trigger_source="rag_embedding_build_plan_api",
        )
        return self._plan_rag_maintenance_job(
            kind="rag_embedding_build",
            request=request,
            message="已创建 RAG embedding 构建 planned 任务。",
        )

    def plan_rag_search_evaluation(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        request = _rag_search_evaluation_request(payload)
        request["confirm_execution"] = True
        request["trigger_source"] = str(request.get("trigger_source") or "rag_search_evaluation_plan_api")
        duplicate = self._find_active_duplicate_job(request, kind="rag_search_evaluation")
        if duplicate:
            return {
                "schema_version": 1,
                "accepted": True,
                "planned_job_created": False,
                "job_id": duplicate.get("job_id") or "",
                "status": duplicate.get("status") or "",
                "request": request,
                "duplicate_of": duplicate.get("job_id") or "",
                "job": duplicate,
            }

        submitted_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        job_id = _rag_search_evaluation_plan_job_id(submitted_at, request)
        job = {
            "job_id": job_id,
            "kind": "rag_search_evaluation",
            "status": "planned",
            "run_date": "",
            "submitted_at": submitted_at,
            "started_at": "",
            "finished_at": "",
            "request": request,
            "result": {},
            "error": "",
        }
        self._persist_preview_job(job)
        self._record_job_event(
            job_id,
            "job_created",
            "planned",
            str(request.get("requested_by") or "api"),
            "已创建 RAG 检索评估 planned 任务。",
            {"request": request},
        )
        return {
            "schema_version": 1,
            "accepted": True,
            "planned_job_created": True,
            "job_id": job_id,
            "status": "planned",
            "request": request,
            "job": job,
        }

    def plan_rag_maintenance(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        payload = payload if isinstance(payload, dict) else {}
        coverage_limit = max(1, min(_int_value(payload.get("coverage_limit")) or 100, 500))
        diagnostics = self.rag_diagnostics(limit=coverage_limit)
        signals = diagnostics.get("signals") if isinstance(diagnostics.get("signals"), dict) else {}
        coverage = diagnostics.get("coverage") if isinstance(diagnostics.get("coverage"), dict) else {}
        gap_count = _int_value(coverage.get("gap_count"))
        min_gap_count = max(1, _int_value(payload.get("min_gap_count")) or 1)
        if (
            diagnostics.get("status") == "needs_corpus"
            or not signals.get("has_corpus")
            or not signals.get("has_chunks")
        ):
            plan = self.plan_rag_corpus_rebuild(payload)
            return {
                **plan,
                "reason": "rag_diagnostics_needs_corpus",
                "gap_count": gap_count,
                "min_gap_count": min_gap_count,
                "coverage": coverage,
                "diagnostics": diagnostics,
            }
        if not signals.get("has_embeddings"):
            plan = self.plan_rag_embedding_build(payload)
            return {
                **plan,
                "reason": "rag_diagnostics_needs_embeddings",
                "gap_count": gap_count,
                "min_gap_count": min_gap_count,
                "coverage": coverage,
                "diagnostics": diagnostics,
            }
        if gap_count < min_gap_count:
            evaluation_payload = {
                **payload,
                "limit": max(1, min(_int_value(payload.get("evaluation_limit")) or _int_value(payload.get("limit")) or 8, 30)),
                "auto_build": _bool_value(payload.get("auto_build"), True),
                "trigger_source": str(payload.get("trigger_source") or "rag_maintenance_api"),
                "requested_by": str(payload.get("requested_by") or "api"),
            }
            plan = self.plan_rag_search_evaluation(evaluation_payload)
            return {
                **plan,
                "reason": "rag_coverage_healthy_search_evaluation",
                "gap_count": gap_count,
                "min_gap_count": min_gap_count,
                "coverage": coverage,
                "diagnostics": diagnostics,
            }

        plan_payload = {
            **payload,
            "limit": max(1, min(_int_value(payload.get("limit")) or min(gap_count, 10), gap_count, 100)),
            "dry_run": _bool_value(payload.get("dry_run"), True),
            "trigger_source": str(payload.get("trigger_source") or "rag_maintenance_api"),
            "requested_by": str(payload.get("requested_by") or "api"),
        }
        plan = self.plan_rag_backfill(plan_payload)
        return {
            **plan,
            "reason": "rag_coverage_gap_detected",
            "gap_count": gap_count,
            "min_gap_count": min_gap_count,
            "coverage": coverage,
            "diagnostics": diagnostics,
        }

    def _rag_maintenance_job_request(
        self,
        payload: dict[str, Any] | None,
        *,
        action: str,
        default_trigger_source: str,
    ) -> dict[str, Any]:
        payload = payload if isinstance(payload, dict) else {}
        dry_run = _bool_value(payload.get("dry_run"), True)
        requested_dry_run = dry_run
        confirm_execution = _bool_value(payload.get("confirm_execution"), False)
        safety_warnings = []
        if not requested_dry_run and not confirm_execution:
            dry_run = True
            safety_warnings.append("未显式确认真实写库，已自动改为 dry_run=true。")
        return {
            "maintenance_action": action,
            "limit": max(1, min(_int_value(payload.get("limit")) or 10, 100)),
            "coverage_limit": max(1, min(_int_value(payload.get("coverage_limit")) or 100, 500)),
            "min_gap_count": max(1, _int_value(payload.get("min_gap_count")) or 1),
            "dry_run": dry_run,
            "requested_dry_run": requested_dry_run,
            "confirm_execution": confirm_execution,
            "requested_by": str(payload.get("requested_by") or "api").strip()[:120],
            "trigger_source": str(payload.get("trigger_source") or default_trigger_source).strip()[:80],
            "model": str(payload.get("model") or MODEL_NAME).strip(),
            "dimensions": max(8, min(_int_value(payload.get("dimensions")) or DEFAULT_DIMENSIONS, 512)),
            "safety_warnings": safety_warnings,
        }

    def _plan_rag_maintenance_job(self, *, kind: str, request: dict[str, Any], message: str) -> dict[str, Any]:
        duplicate = self._find_active_duplicate_job(request, kind=kind)
        if duplicate:
            return {
                "schema_version": 1,
                "accepted": True,
                "planned_job_created": False,
                "job_id": duplicate.get("job_id") or "",
                "status": duplicate.get("status") or "",
                "request": request,
                "safety_warnings": request.get("safety_warnings") or [],
                "duplicate_of": duplicate.get("job_id") or "",
                "job": duplicate,
            }

        submitted_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        job_id = _rag_maintenance_plan_job_id(kind, submitted_at, request)
        job = {
            "job_id": job_id,
            "kind": kind,
            "status": "planned",
            "run_date": "",
            "submitted_at": submitted_at,
            "started_at": "",
            "finished_at": "",
            "request": request,
            "result": {},
            "error": "",
        }
        self._persist_preview_job(job)
        self._record_job_event(
            job_id,
            "job_created",
            "planned",
            str(request.get("requested_by") or "api"),
            message,
            {"request": request},
        )
        return {
            "schema_version": 1,
            "accepted": True,
            "planned_job_created": True,
            "job_id": job_id,
            "status": "planned",
            "request": request,
            "safety_warnings": request.get("safety_warnings") or [],
            "job": job,
        }

    def _rag_backfill_request_from_payload(
        self,
        payload: dict[str, Any] | None,
        *,
        default_trigger_source: str,
    ) -> dict[str, Any]:
        payload = payload if isinstance(payload, dict) else {}
        dry_run = _bool_value(payload.get("dry_run"), True)
        confirm_execution = _bool_value(payload.get("confirm_execution"), False)
        safety_warnings = []
        if not dry_run and not confirm_execution:
            dry_run = True
            safety_warnings.append("未传入 confirm_execution=true，API 已自动改为 dry_run=true。")

        request = {
            "limit": _int_value(payload.get("limit")) or 10,
            "rag_limit": _int_value(payload.get("rag_limit")) or 8,
            "mode": str(payload.get("mode") or "fts5"),
            "model": str(payload.get("model") or "local-hash-v1"),
            "auto_build": _bool_value(payload.get("auto_build"), False),
            "dry_run": dry_run,
            "confirm_execution": confirm_execution,
            "trigger_source": str(payload.get("trigger_source") or default_trigger_source),
            "requested_by": str(payload.get("requested_by") or "api"),
            "safety_warnings": safety_warnings,
        }
        return request

    def backfill_rag_explanations_from_payload(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        request = self._rag_backfill_request_from_payload(payload, default_trigger_source="rag_backfill_api")
        dry_run = _truthy(request.get("dry_run", True))
        safety_warnings = list(request.get("safety_warnings") or [])
        submitted_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        run_date = submitted_at[:10]
        job_id = _rag_backfill_job_id(submitted_at, request)
        actor = request["requested_by"]

        running_job = {
            "job_id": job_id,
            "kind": "rag_backfill",
            "status": "running",
            "run_date": run_date,
            "submitted_at": submitted_at,
            "started_at": submitted_at,
            "finished_at": "",
            "request": request,
            "result": {},
            "error": "",
        }
        self._persist_preview_job(running_job)
        self._record_job_event(
            job_id,
            "rag_backfill_started",
            "running",
            actor,
            "RAG 解释回填已开始。",
            {"request": request},
        )

        try:
            result = self.backfill_rag_explanations(
                limit=request["limit"],
                rag_limit=request["rag_limit"],
                mode=request["mode"],
                model=request["model"],
                auto_build=request["auto_build"],
                dry_run=dry_run,
            )
        except Exception as exc:  # pragma: no cover - defensive audit path
            finished_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            failed_job = {
                **running_job,
                "status": "failed",
                "finished_at": finished_at,
                "error": str(exc),
                "result": {"dry_run": dry_run, "safety_warnings": safety_warnings},
            }
            self._persist_preview_job(failed_job)
            self._record_job_event(
                job_id,
                "rag_backfill_failed",
                "failed",
                actor,
                "RAG 解释回填失败。",
                {"error": str(exc)},
            )
            return {
                "schema_version": 1,
                "accepted": False,
                "status": "failed",
                "job_id": job_id,
                "dry_run": dry_run,
                "error": str(exc),
                "request": request,
                "safety_warnings": safety_warnings,
            }

        result["accepted"] = True
        result["safety_warnings"] = safety_warnings
        result["request"] = {**request, "limit": result["requested_limit"]}
        result["job_id"] = job_id

        finished_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        job_result = _rag_backfill_job_result(result)
        succeeded_job = {
            **running_job,
            "status": "succeeded",
            "finished_at": finished_at,
            "result": job_result,
        }
        self._persist_preview_job(succeeded_job)
        self._record_job_event(
            job_id,
            "rag_backfill_completed",
            "succeeded",
            actor,
            "RAG 解释回填已完成。",
            {"result": job_result},
        )
        result["job"] = succeeded_job
        return result

    def project_rag_bundle(
        self,
        full_name: str,
        *,
        limit: int = 8,
        explanation_limit: int = 5,
        mode: str = "fts5",
        model: str = "local-hash-v1",
        auto_build: bool = False,
    ) -> dict[str, Any]:
        detail = self.project_detail(full_name)
        normalized = _normalize_full_name(full_name)
        if not detail.get("found"):
            return {
                "schema_version": 1,
                "found": False,
                "full_name": normalized,
                "query": "",
                "project_profile": {},
                "agent_tasks": {"count": 0, "tasks": [], "summary": _project_agent_task_summary([])},
                "agent_task_runs": {"count": 0, "runs": [], "summary": {"running": 0, "succeeded": 0, "failed": 0}},
                "notification_memory": {"event_count": 0, "candidate_count": 0, "delivery_count": 0, "events": [], "candidates": [], "deliveries": []},
                "next_actions": [],
                "retrieval": {},
                "contexts": [],
                "citations": [],
                "prompt_context": "",
                "explanations": [],
                "explanation_summary": {
                    "count": 0,
                    "average_quality_score": 0,
                    "quality_levels": {},
                    "recommendations": ["未找到该项目的历史入选记录，暂不能构建项目级 RAG 包。"],
                },
            }

        limit = max(1, min(int(limit or 8), 30))
        explanation_limit = max(1, min(int(explanation_limit or 5), 50))
        query = _project_rag_query(detail)
        if str(mode or "").lower() == "vector":
            retrieval = self.rag_vector_search(
                query=query,
                language=detail.get("language") or None,
                category=detail.get("category") or None,
                limit=limit,
                model=model,
                auto_build=auto_build,
            )
        else:
            retrieval = self.rag_retrieve(
                query=query,
                language=detail.get("language") or None,
                category=detail.get("category") or None,
                limit=limit,
            )
        explanations = self.rag_explanations(repo=detail.get("full_name") or normalized, limit=explanation_limit)
        explanation_items = explanations.get("explanations") if isinstance(explanations.get("explanations"), list) else []
        feedback = self.project_feedback(full_name=detail.get("full_name") or normalized, limit=20)
        feedback_summary = feedback.get("summary") if isinstance(feedback.get("summary"), dict) else {}
        agent_tasks = self.project_agent_tasks(full_name=detail.get("full_name") or normalized, limit=50)
        agent_task_runs = self.project_agent_task_runs(full_name=detail.get("full_name") or normalized, limit=50)
        project_events = self.subscription_events(full_name=detail.get("full_name") or normalized, limit=50)
        project_candidates = self.notification_candidates(full_name=detail.get("full_name") or normalized, limit=50)
        candidate_ids = {item.get("candidate_id") for item in project_candidates.get("candidates", [])}
        project_deliveries = [
            item for item in self.notification_deliveries(limit=200).get("deliveries", [])
            if item.get("candidate_id") in candidate_ids
        ]
        project_profile = self._project_profile_for_full_name(detail.get("full_name") or normalized) or _project_profile_from_detail(detail)
        project_profile = _merge_project_profile_runtime_signals(project_profile, feedback_summary, explanation_items)
        next_actions = _project_next_actions(
            {
                **detail,
                "project_profile": project_profile,
                "quality_score": detail.get("latest_quality_score") or detail.get("quality_score") or 0,
            },
            agent_tasks.get("tasks") if isinstance(agent_tasks.get("tasks"), list) else [],
        )
        return {
            "schema_version": 1,
            "found": True,
            "full_name": detail.get("full_name") or normalized,
            "query": query,
            "project": {
                "full_name": detail.get("full_name") or normalized,
                "html_url": detail.get("html_url") or "",
                "description": detail.get("description") or "",
                "language": detail.get("language") or "",
                "category": detail.get("category") or "",
                "history_count": _int_value(detail.get("history_count")),
                "total_star_growth": _int_value(detail.get("total_star_growth")),
                "best_trending_rank": _int_value(detail.get("best_trending_rank")),
            },
            "project_profile": project_profile,
            "agent_tasks": agent_tasks,
            "agent_task_runs": agent_task_runs,
            "notification_memory": {
                "event_count": project_events.get("count", 0),
                "candidate_count": project_candidates.get("count", 0),
                "delivery_count": len(project_deliveries),
                "events": project_events.get("events", []),
                "candidates": project_candidates.get("candidates", []),
                "deliveries": project_deliveries,
                "summary": _project_notification_summary(
                    project_events.get("events", []), project_candidates.get("candidates", []), project_deliveries
                ),
            },
            "next_actions": next_actions,
            "retrieval": retrieval.get("retrieval") if isinstance(retrieval.get("retrieval"), dict) else {},
            "contexts": retrieval.get("contexts") if isinstance(retrieval.get("contexts"), list) else [],
            "citations": retrieval.get("citations") if isinstance(retrieval.get("citations"), list) else [],
            "prompt_context": retrieval.get("prompt_context") or "",
            "summary": retrieval.get("summary") if isinstance(retrieval.get("summary"), list) else [],
            "explanations": explanation_items,
            "explanation_summary": _project_rag_explanation_summary(explanation_items),
            "feedback_memory": {
                "count": feedback.get("count", 0),
                "summary": feedback.get("summary") if isinstance(feedback.get("summary"), dict) else {},
                "feedback": feedback.get("feedback") if isinstance(feedback.get("feedback"), list) else [],
            },
        }

    def _project_profile_for_full_name(self, full_name: str) -> dict[str, Any]:
        profiles = self._project_profiles_by_full_name([full_name])
        return profiles.get(_normalize_full_name(full_name).lower(), {})

    def _project_profiles_by_full_name(self, full_names: list[str]) -> dict[str, dict[str, Any]]:
        normalized = [_normalize_full_name(name) for name in full_names if _normalize_full_name(name)]
        if not normalized:
            return {}
        self.ensure_sqlite_index()
        placeholders = ",".join("?" for _ in normalized)
        connection = connect(self.db_path)
        try:
            initialize(connection)
            rows = connection.execute(
                f"""
                SELECT full_name, payload_json
                FROM project_corpus
                WHERE lower(full_name) IN ({placeholders})
                ORDER BY run_date DESC
                """,
                [name.lower() for name in normalized],
            ).fetchall()
        finally:
            connection.close()
        profiles: dict[str, dict[str, Any]] = {}
        for row in rows:
            key = str(row["full_name"] or "").lower()
            if key in profiles:
                continue
            payload = _json_object(row["payload_json"])
            profile = payload.get("project_profile") if isinstance(payload.get("project_profile"), dict) else {}
            if profile:
                profiles[key] = profile
        return profiles

    def _persist_rag_explanation(self, result: dict[str, Any]) -> dict[str, Any]:
        explanation = result.get("explanation") if isinstance(result.get("explanation"), dict) else {}
        quality = result.get("quality") if isinstance(result.get("quality"), dict) else {}
        retrieval = result.get("retrieval") if isinstance(result.get("retrieval"), dict) else {}
        citations = result.get("citations") if isinstance(result.get("citations"), list) else []
        contexts = result.get("contexts") if isinstance(result.get("contexts"), list) else []
        coverage = explanation.get("coverage") if isinstance(explanation.get("coverage"), dict) else {}
        repositories = _list_strings(coverage.get("repositories") or [])
        created_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        explanation_id = _rag_explanation_id(result)
        enriched = {
            **result,
            "explanation_id": explanation_id,
            "created_at": created_at,
            "cached": True,
        }
        connection = connect(self.db_path)
        try:
            initialize(connection)
            connection.execute(
                """
                INSERT INTO rag_explanations(
                  explanation_id, query, language, category, source, mode, model,
                  context_count, confidence, quality_score, quality_level, quality_json,
                  answer, repositories_json, citations_json,
                  explanation_json, retrieval_json, prompt_context, payload_json, created_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(explanation_id) DO UPDATE SET
                  query = excluded.query,
                  language = excluded.language,
                  category = excluded.category,
                  source = excluded.source,
                  mode = excluded.mode,
                  model = excluded.model,
                  context_count = excluded.context_count,
                  confidence = excluded.confidence,
                  quality_score = excluded.quality_score,
                  quality_level = excluded.quality_level,
                  quality_json = excluded.quality_json,
                  answer = excluded.answer,
                  repositories_json = excluded.repositories_json,
                  citations_json = excluded.citations_json,
                  explanation_json = excluded.explanation_json,
                  retrieval_json = excluded.retrieval_json,
                  prompt_context = excluded.prompt_context,
                  payload_json = excluded.payload_json,
                  created_at = excluded.created_at
                """,
                (
                    explanation_id,
                    str(result.get("query") or ""),
                    str(result.get("language") or ""),
                    str(result.get("category") or ""),
                    str(result.get("source") or ""),
                    str(retrieval.get("mode") or ""),
                    str(retrieval.get("model") or ""),
                    len(contexts),
                    str(explanation.get("confidence") or ""),
                    _int_value(quality.get("score")),
                    str(quality.get("level") or ""),
                    json.dumps(quality, ensure_ascii=False, sort_keys=True),
                    str(explanation.get("answer") or ""),
                    json.dumps(repositories, ensure_ascii=False, sort_keys=True),
                    json.dumps(citations, ensure_ascii=False, sort_keys=True),
                    json.dumps(explanation, ensure_ascii=False, sort_keys=True),
                    json.dumps(retrieval, ensure_ascii=False, sort_keys=True),
                    str(result.get("prompt_context") or ""),
                    json.dumps(enriched, ensure_ascii=False, sort_keys=True),
                    created_at,
                ),
            )
            connection.commit()
        finally:
            connection.close()
        return enriched

    def similar_projects(self, full_name: str, *, limit: int = 10) -> dict[str, Any]:
        detail = self.project_detail(full_name)
        normalized = _normalize_full_name(full_name)
        limit = max(1, min(int(limit or 10), 50))
        if not detail.get("found"):
            return {
                "schema_version": 1,
                "found": False,
                "full_name": normalized,
                "query": "",
                "search_engine": "",
                "count": 0,
                "source_project": {},
                "similar_projects": [],
                "selection_summary": ["项目不存在，无法生成相似项目候选。"],
            }

        latest = detail["history"][0] if detail.get("history") else detail
        query = _similarity_query(latest)
        candidate_results = []
        search_engines = []
        for attempt in _similarity_search_attempts(latest):
            search = self.search(
                query=attempt["query"],
                language=attempt["language"],
                category=attempt["category"],
                limit=max(limit * 5, 30),
            )
            candidate_results.extend(search.get("results") or [])
            if search.get("search_engine"):
                search_engines.append(str(search.get("search_engine")))
            candidates = _rank_similar_search_results(
                latest,
                candidate_results,
                exclude_full_name=normalized,
            )
            if len(_dedupe_search_results(candidates)) >= limit:
                break

        candidates = _rank_similar_search_results(latest, candidate_results, exclude_full_name=normalized)
        similar = _dedupe_search_results(candidates)[:limit]
        return {
            "schema_version": 1,
            "found": True,
            "full_name": detail.get("full_name") or normalized,
            "query": query,
            "search_engine": "+".join(_unique_strings(search_engines)),
            "count": len(similar),
            "source_project": {
                "full_name": detail.get("full_name") or normalized,
                "html_url": detail.get("html_url") or "",
                "description": detail.get("description") or "",
                "language": detail.get("language") or "",
                "category": detail.get("category") or "",
                "sources": detail.get("sources") or [],
            },
            "similar_projects": similar,
            "selection_summary": _similarity_summary(detail, similar),
        }

    def compare_projects(
        self,
        full_names: list[str] | str,
        *,
        profile: str | None = None,
        language: str | None = None,
        category: str | None = None,
        query: str | None = None,
    ) -> dict[str, Any]:
        requested = _normalize_project_list(full_names)
        details = [self.project_detail(name) for name in requested]
        found = [detail for detail in details if detail.get("found")]
        missing = [detail.get("full_name") or name for detail, name in zip(details, requested) if not detail.get("found")]
        projects = [_comparison_project(detail) for detail in found]
        preference = _comparison_preference(
            self.profiles(),
            profile=profile,
            language=language,
            category=category,
            query=query,
        )
        return {
            "schema_version": 1,
            "requested": requested,
            "count": len(projects),
            "missing": missing,
            "preference": preference,
            "projects": projects,
            "matrix": _comparison_matrix(projects),
            "best_by": _comparison_best_by(projects),
            "recommendation": _comparison_recommendation(projects, missing, preference),
            "selection_summary": _comparison_summary(projects, missing),
        }

    def subscription_recommendations(self, subscription_id: str, *, limit: int | None = None) -> dict[str, Any]:
        self.ensure_sqlite_index()
        normalized = _blank_to_none(subscription_id) or ""
        subscription = self._subscription_by_id(normalized)
        if not subscription:
            return {
                "schema_version": 1,
                "found": False,
                "subscription_id": normalized,
                "subscription": {},
                "count": 0,
                "selection_summary": ["订阅不存在，无法生成推荐预览。"],
                "recommendations": [],
            }

        target_limit = limit or _int_value(subscription.get("limit")) or 20
        target_limit = max(1, min(target_limit, 200))
        recommendations = self.recommendations(
            profile=_blank_to_none(subscription.get("profile")),
            language=_blank_to_none(subscription.get("language")),
            category=_blank_to_none(subscription.get("category")),
            query=_blank_to_none(subscription.get("query")),
            limit=target_limit,
            sort=subscription.get("sort") or "score",
        )
        summary = list(recommendations.get("selection_summary") or [])
        status = subscription.get("status") or "unknown"
        summary.insert(0, f"订阅 {subscription.get('name') or normalized} 当前状态为 {status}。")
        return {
            "schema_version": 1,
            "found": True,
            "subscription_id": normalized,
            "subscription": subscription,
            "profile": recommendations.get("profile") or "",
            "language": recommendations.get("language") or "",
            "category": recommendations.get("category") or "",
            "query": recommendations.get("query") or "",
            "sort": recommendations.get("sort") or "",
            "count": recommendations.get("count") or 0,
            "selection_summary": summary,
            "recommendations": recommendations.get("recommendations") or [],
        }

    def project_detail(self, full_name: str) -> dict[str, Any]:
        self.ensure_sqlite_index()
        normalized = _normalize_full_name(full_name)
        history = [
            project
            for project in query_archive(
                db_path=self.db_path,
                root=self.root,
                query=normalized,
                limit=200,
                sort="recent",
            )
            if str(project.get("full_name") or "").lower() == normalized.lower()
        ]
        if not history:
            return {
                "schema_version": 1,
                "found": False,
                "full_name": normalized,
                "history_count": 0,
                "history": [],
                "selection_reasons": [],
                "trend_summary": [],
                "similar_projects": [],
            }

        history = sorted(history, key=lambda project: str(project.get("run_date") or ""), reverse=True)
        latest = history[0]
        return {
            "schema_version": 1,
            "found": True,
            "full_name": latest.get("full_name") or normalized,
            "html_url": latest.get("html_url") or "",
            "description": latest.get("description") or "",
            "language": latest.get("language") or "",
            "category": latest.get("category") or "",
            "latest_run_date": latest.get("run_date") or "",
            "first_run_date": history[-1].get("run_date") or "",
            "history_count": len(history),
            "total_star_growth": sum(_int_value(project.get("star_growth")) for project in history),
            "best_trending_rank": _best_trending_rank(history),
            "sources": _unique_strings(source for project in history for source in project.get("sources") or []),
            "selection_reasons": _project_selection_reasons(history),
            "trend_summary": _project_trend_summary(history),
            "security_flags": _unique_strings(flag for project in history for flag in project.get("security_flags") or []),
            "quality_flags": _unique_strings(flag for project in history for flag in project.get("quality_flags") or []),
            "best_quality_score": max((_int_value(project.get("quality_score")) for project in history), default=0),
            "latest_quality_score": _int_value(latest.get("quality_score")),
            "latest_quality_level": latest.get("quality_level") or "unknown",
            "history": history,
            "similar_projects": self._similar_projects(latest, normalized),
        }

    def runs(self) -> dict[str, Any]:
        return _read_json_object(self.root / "docs" / "runs.json", {"schema_version": 1, "count": 0, "runs": []})

    def database_summary(self) -> dict[str, Any]:
        self.ensure_sqlite_index()
        connection = connect(self.db_path)
        try:
            initialize(connection)
            tables = [
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
                "dev_corpus",
                "dev_chunks",
                "dev_chunks_fts",
                "dev_embeddings",
                "dev_runs",
                "trend_summaries",
                "jobs",
                "job_events",
                "subscriptions",
            ]
            table_counts = {name: table_count(connection, name) for name in tables}
            latest_run = _optional_row(
                connection.execute(
                    """
                    SELECT run_date, status, collected_count, selected_count, kimi_used,
                           fallback_used, telegram_sent, telegram_report_url
                    FROM runs
                    ORDER BY run_date DESC
                    LIMIT 1
                    """
                ).fetchone()
            )
            latest_job = _optional_row(
                connection.execute(
                    """
                    SELECT job_id, kind, status, run_date, submitted_at, started_at, finished_at, error
                    FROM jobs
                    ORDER BY COALESCE(NULLIF(finished_at, ''), NULLIF(submitted_at, ''), run_date) DESC, job_id DESC
                    LIMIT 1
                    """
                ).fetchone()
            )
            job_status_counts = _group_counts(connection, "jobs", "status")
            subscription_status_counts = _group_counts(connection, "subscriptions", "status")
            top_languages = _top_counts(connection, "repositories", "language")
            top_categories = _top_counts(connection, "selections", "category")
            recent_events = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT job_id, event_type, status, actor, created_at, message
                    FROM job_events
                    ORDER BY created_at DESC, event_id DESC
                    LIMIT 10
                    """
                ).fetchall()
            ]
        finally:
            connection.close()

        return {
            "schema_version": 1,
            "sqlite_path": str(self.db_path),
            "sqlite_exists": self.db_path.exists(),
            "table_counts": table_counts,
            "latest_run": latest_run,
            "latest_job": latest_job,
            "job_status_counts": job_status_counts,
            "subscription_status_counts": subscription_status_counts,
            "top_languages": top_languages,
            "top_categories": top_categories,
            "recent_events": recent_events,
            "rag_readiness": {
                "project_records": table_counts.get("repositories", 0),
                "selection_records": table_counts.get("selections", 0),
                "corpus_records": table_counts.get("project_corpus", 0),
                "fts_records": table_counts.get("project_corpus_fts", 0),
                "chunk_records": table_counts.get("rag_chunks", 0),
                "chunk_fts_records": table_counts.get("rag_chunks_fts", 0),
                "embedding_records": table_counts.get("rag_embeddings", 0),
                "explanation_records": table_counts.get("rag_explanations", 0),
                "feedback_records": table_counts.get("project_feedback", 0),
                "dev_corpus_records": table_counts.get("dev_corpus", 0),
                "dev_chunk_records": table_counts.get("dev_chunks", 0),
                "dev_embedding_records": table_counts.get("dev_embeddings", 0),
                "dev_run_records": table_counts.get("dev_runs", 0),
                "event_records": table_counts.get("job_events", 0),
                "ready_for_text_index": table_counts.get("project_corpus_fts", 0) > 0,
                "ready_for_chunk_retrieval": table_counts.get("rag_chunks_fts", 0) > 0,
                "ready_for_vector_search": table_counts.get("rag_embeddings", 0) > 0,
                "ready_for_explanation_history": table_counts.get("rag_explanations", 0) > 0,
                "ready_for_feedback_memory": table_counts.get("project_feedback", 0) > 0,
                "ready_for_dev_context_search": table_counts.get("dev_chunks_fts", 0) > 0,
            },
        }

    def database_trends(self, *, limit: int = 20) -> dict[str, Any]:
        self.ensure_sqlite_index()
        limit = max(1, min(int(limit or 20), 100))
        connection = connect(self.db_path)
        try:
            initialize(connection)
            rows = connection.execute(
                """
                SELECT
                  r.run_date,
                  r.status,
                  r.collected_count,
                  r.selected_count,
                  r.kimi_used,
                  r.fallback_used,
                  r.telegram_sent,
                  COALESCE(t.total_projects, 0) AS total_projects,
                  COALESCE(t.trending_project_count, 0) AS trending_project_count,
                  COALESCE(t.total_star_growth, selection_stats.total_star_growth, 0) AS total_star_growth,
                  COALESCE(selection_stats.trending_top10_count, 0) AS trending_top10_count,
                  COALESCE(selection_stats.avg_score, 0) AS avg_score
                FROM runs r
                LEFT JOIN trend_summaries t ON t.run_date = r.run_date
                LEFT JOIN (
                  SELECT
                    run_date,
                    SUM(star_growth) AS total_star_growth,
                    SUM(CASE WHEN trending_rank BETWEEN 1 AND 10 THEN 1 ELSE 0 END) AS trending_top10_count,
                    AVG(score) AS avg_score
                  FROM selections
                  GROUP BY run_date
                ) AS selection_stats ON selection_stats.run_date = r.run_date
                ORDER BY r.run_date DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            points = [dict(row) for row in rows]
        finally:
            connection.close()

        points = list(reversed(points))
        return {
            "schema_version": 1,
            "count": len(points),
            "limit": limit,
            "points": [_trend_point(point) for point in points],
            "summary": _database_trend_summary(points),
        }

    def database_facets(self, *, limit: int = 20) -> dict[str, Any]:
        self.ensure_sqlite_index()
        limit = max(1, min(int(limit or 20), 100))
        connection = connect(self.db_path)
        try:
            initialize(connection)
            language_rows = connection.execute(
                """
                SELECT
                  COALESCE(NULLIF(language, ''), 'unknown') AS name,
                  COUNT(*) AS project_count,
                  SUM(stargazers_count) AS total_stars,
                  SUM(forks_count) AS total_forks,
                  MAX(pushed_at) AS latest_pushed_at
                FROM repositories
                GROUP BY COALESCE(NULLIF(language, ''), 'unknown')
                ORDER BY project_count DESC, total_stars DESC, name ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            category_rows = connection.execute(
                """
                SELECT
                  COALESCE(NULLIF(category, ''), 'Other') AS name,
                  COUNT(*) AS selection_count,
                  COUNT(DISTINCT full_name) AS project_count,
                  SUM(star_growth) AS total_star_growth,
                  AVG(score) AS avg_score,
                  SUM(CASE WHEN trending_rank BETWEEN 1 AND 10 THEN 1 ELSE 0 END) AS trending_top10_count
                FROM selections
                GROUP BY COALESCE(NULLIF(category, ''), 'Other')
                ORDER BY selection_count DESC, total_star_growth DESC, name ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            selection_rows = connection.execute(
                "SELECT full_name, sources_json, payload_json FROM selections"
            ).fetchall()
            subscription_rows = connection.execute(
                "SELECT status, profile, language, category FROM subscriptions"
            ).fetchall()
            corpus_count = table_count(connection, "project_corpus")
        finally:
            connection.close()

        sources = _source_facets(selection_rows, limit)
        quality_levels, risk_levels = _quality_facets(selection_rows, limit)
        subscription_facets = _subscription_facets(subscription_rows, limit)
        return {
            "schema_version": 1,
            "limit": limit,
            "languages": [_language_facet(row) for row in language_rows],
            "categories": [_category_facet(row) for row in category_rows],
            "sources": sources,
            "quality_levels": quality_levels,
            "risk_levels": risk_levels,
            "subscriptions": subscription_facets,
            "rag_readiness": {
                "has_language_facets": bool(language_rows),
                "has_category_facets": bool(category_rows),
                "has_source_facets": bool(sources),
                "ready_for_personalized_filters": bool(language_rows or category_rows or subscription_facets["profiles"]),
                "ready_for_text_search": corpus_count > 0,
            },
        }

    def jobs(
        self,
        *,
        status: str | None = None,
        kind: str | None = None,
        profile: str | None = None,
        query: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        self.ensure_sqlite_index()
        jobs = self._jobs_from_sqlite(max(limit, 500))
        if not jobs:
            runs = self.runs().get("runs") or []
            jobs = [_job_from_run(run) for run in runs[: max(limit, 500)]]
        jobs = [
            job
            for job in jobs
            if _job_matches(
                job,
                status=_blank_to_none(status),
                kind=_blank_to_none(kind),
                profile=_blank_to_none(profile),
                query=_blank_to_none(query),
            )
        ][:limit]
        return {
            "schema_version": 1,
            "count": len(jobs),
            "jobs": jobs,
        }

    def job_detail(self, job_id: str) -> dict[str, Any]:
        normalized = _blank_to_none(job_id) or ""
        for job in self.jobs(limit=500).get("jobs", []):
            if job.get("job_id") == normalized:
                return {
                    "schema_version": 1,
                    "found": True,
                    "job": job,
                    "run_summary": _read_json_object(self.root / "data" / "runs" / f"{job.get('run_date')}.json", {}),
                }
        return {
            "schema_version": 1,
            "found": False,
            "job_id": normalized,
            "job": {},
        }

    def job_events(self, job_id: str, limit: int = 100) -> dict[str, Any]:
        self.ensure_sqlite_index()
        normalized = _blank_to_none(job_id) or ""
        connection = connect(self.db_path)
        try:
            initialize(connection)
            rows = connection.execute(
                """
                SELECT event_id, job_id, event_type, status, actor, created_at, message, payload_json
                FROM job_events
                WHERE job_id = ?
                ORDER BY created_at ASC, event_id ASC
                LIMIT ?
                """,
                (normalized, limit),
            ).fetchall()
        finally:
            connection.close()
        events = [_job_event_from_row(row) for row in rows]
        return {
            "schema_version": 1,
            "job_id": normalized,
            "count": len(events),
            "events": events,
        }

    def job_execution_check(self, job_id: str) -> dict[str, Any]:
        detail = self.job_detail(job_id)
        normalized = _blank_to_none(job_id) or ""
        if not detail.get("found"):
            return {
                "schema_version": 1,
                "found": False,
                "job_id": normalized,
                "executable": False,
                "execution_path": "scripts/run_planned_job.py",
                "blockers": ["任务不存在。"],
                "warnings": [],
                "next_command": "",
            }

        job = detail.get("job") if isinstance(detail.get("job"), dict) else {}
        request = job.get("request") if isinstance(job.get("request"), dict) else {}
        kind = str(job.get("kind") or "")
        blockers = []
        warnings = []
        if kind not in EXECUTABLE_JOB_KINDS:
            blockers.append(
                "当前执行器只支持 weekly_report、rag_backfill、rag_corpus_rebuild、rag_embedding_build 和 rag_search_evaluation 任务。"
            )
        if job.get("status") != "planned":
            blockers.append(f"任务状态为 {job.get('status') or 'unknown'}，只有 planned 任务可以被执行器消费。")
        if kind == "weekly_report":
            if not _truthy(request.get("dry_run", True)) and not _truthy(request.get("confirm_delivery")):
                blockers.append("dry_run=false 但缺少 confirm_delivery=true，不能进入真实推送执行。")
            if not _truthy(request.get("dry_run", True)):
                warnings.append("该任务允许真实推送，执行前请确认 Telegram/飞书/微信等推送配置正确。")
        if kind == "rag_backfill":
            if not _truthy(request.get("dry_run", True)) and not _truthy(request.get("confirm_execution")):
                blockers.append("dry_run=false 但缺少 confirm_execution=true，不能进入真实补库执行。")
            if not _truthy(request.get("dry_run", True)):
                warnings.append("该任务允许写入 RAG 解释历史，执行前请确认 SQLite 数据库状态正确。")
        if kind in {"rag_corpus_rebuild", "rag_embedding_build"}:
            if not _truthy(request.get("dry_run", True)) and not _truthy(request.get("confirm_execution")):
                blockers.append("dry_run=false 但缺少 confirm_execution=true，不能进入真实 RAG 维护执行。")
            if not _truthy(request.get("dry_run", True)):
                warnings.append("该任务允许写入 SQLite 派生表，执行前请确认本地归档数据完整。")
        if kind == "rag_search_evaluation":
            warnings.append("该任务会写入 RAG 检索评估结果，用于后续质量趋势分析。")

        if kind == "dev_context_index":
            if _truthy(request.get("run_checks")):
                warnings.append("该任务会运行单元测试和安全检查，执行时间可能较长。")
            else:
                warnings.append("该任务会轻量刷新开发上下文索引，不重复运行完整测试。")

        executable = not blockers
        return {
            "schema_version": 1,
            "found": True,
            "job_id": job.get("job_id") or normalized,
            "status": job.get("status") or "",
            "kind": job.get("kind") or "",
            "executable": executable,
            "execution_path": "scripts/run_planned_job.py",
            "request": {
                "profile": request.get("profile") or "",
                "sources": _list_strings(request.get("sources")),
                "queries": _list_strings(request.get("queries")),
                "dry_run": _truthy(request.get("dry_run", True)),
                "confirm_delivery": _truthy(request.get("confirm_delivery")),
                "days_back": _positive_int(request.get("days_back")),
                "limit": _positive_int(request.get("limit")),
                "rag_limit": _positive_int(request.get("rag_limit")),
                "mode": request.get("mode") or "",
                "model": request.get("model") or "",
                "source": request.get("source") or "",
                "auto_build": _truthy(request.get("auto_build")),
                "confirm_execution": _truthy(request.get("confirm_execution")),
                "maintenance_action": request.get("maintenance_action") or "",
                "dimensions": _positive_int(request.get("dimensions")),
                "run_checks": _truthy(request.get("run_checks")),
                "replace": _truthy(request.get("replace")),
                "max_command_chars": _positive_int(request.get("max_command_chars")),
                "trigger_source": request.get("trigger_source") or "",
                "requested_by": request.get("requested_by") or "",
            },
            "blockers": blockers,
            "warnings": warnings,
            "next_command": f"python scripts/run_planned_job.py --job-id {job.get('job_id') or normalized}" if executable else "",
        }

    def execute_job(self, job_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        check = self.job_execution_check(job_id)
        normalized_job_id = str(check.get("job_id") or (_blank_to_none(job_id) or ""))
        actor = str(payload.get("requested_by") or (check.get("request") or {}).get("requested_by") or "api").strip()[:120]
        self._record_job_event(
            normalized_job_id,
            "execution_requested",
            str(check.get("status") or ""),
            actor,
            "收到任务执行请求。",
            {"confirm_execution": _truthy(payload.get("confirm_execution")), "precheck": check},
        )
        blockers = list(check.get("blockers") or [])
        if not _truthy(payload.get("confirm_execution")):
            blockers.append("缺少 confirm_execution=true，未执行任务。")

        if blockers:
            self._record_job_event(
                normalized_job_id,
                "execution_blocked",
                str(check.get("status") or "blocked"),
                actor,
                "任务执行被阻止。",
                {"blockers": blockers, "precheck": check},
            )
            return {
                "schema_version": 1,
                "accepted": False,
                "executed": False,
                "job_id": normalized_job_id,
                "status": check.get("status") or "blocked",
                "blockers": blockers,
                "warnings": check.get("warnings") or [],
                "precheck": check,
                "runner_result": {},
            }

        self._record_job_event(
            normalized_job_id,
            "execution_started",
            "running",
            actor,
            "任务已交给本地 job runner。",
            {"precheck": check},
        )
        runner_result = run_planned_job(root=self.root, db_path=self.db_path, job_id=normalized_job_id)
        self._record_job_event(
            normalized_job_id,
            "execution_finished",
            str(runner_result.get("status") or ""),
            actor,
            "任务执行结束。",
            {"runner_result": runner_result},
        )
        return {
            "schema_version": 1,
            "accepted": True,
            "executed": bool(runner_result.get("executed")),
            "job_id": runner_result.get("job_id") or normalized_job_id,
            "status": runner_result.get("status") or "",
            "blockers": [],
            "warnings": check.get("warnings") or [],
            "precheck": check,
            "runner_result": runner_result,
        }

    def retry_job(self, job_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        detail = self.job_detail(job_id)
        normalized = _blank_to_none(job_id) or ""
        job = detail.get("job") if isinstance(detail.get("job"), dict) else {}
        actor = str(payload.get("requested_by") or (job.get("request") or {}).get("requested_by") or "api").strip()[:120]
        blockers = []
        if not detail.get("found"):
            blockers.append("任务不存在，不能重试。")
        if job and job.get("kind") not in EXECUTABLE_JOB_KINDS:
            blockers.append(
                "当前只支持 weekly_report、rag_backfill、rag_corpus_rebuild、rag_embedding_build 和 rag_search_evaluation 任务重试。"
            )
        if job and job.get("status") != "failed":
            blockers.append(f"任务状态为 {job.get('status') or 'unknown'}，只有 failed 任务可以重试。")

        self._record_job_event(
            normalized,
            "retry_requested",
            str(job.get("status") or ""),
            actor,
            "收到任务重试请求。",
            {"requested_by": actor},
        )
        if blockers:
            self._record_job_event(
                normalized,
                "retry_blocked",
                str(job.get("status") or "blocked"),
                actor,
                "任务重试被阻止。",
                {"blockers": blockers},
            )
            return {
                "schema_version": 1,
                "accepted": False,
                "retry_created": False,
                "original_job_id": normalized,
                "job_id": "",
                "status": "blocked",
                "blockers": blockers,
                "retry_job": {},
            }

        request = job.get("request") if isinstance(job.get("request"), dict) else {}
        retry_request = {
            **request,
            "trigger_source": "retry",
            "requested_by": actor,
            "retry_of": normalized,
        }
        duplicate = self._find_active_duplicate_job(retry_request, kind=str(job.get("kind") or "weekly_report"))
        if duplicate:
            self._record_job_event(
                normalized,
                "retry_duplicate_ignored",
                duplicate.get("status") or "",
                actor,
                "已存在相同 active 任务，未创建重试任务。",
                {"duplicate_of": duplicate.get("job_id") or "", "request": retry_request},
            )
            return {
                "schema_version": 1,
                "accepted": True,
                "retry_created": False,
                "original_job_id": normalized,
                "job_id": duplicate.get("job_id") or "",
                "status": duplicate.get("status") or "",
                "blockers": [],
                "duplicate_of": duplicate.get("job_id") or "",
                "retry_job": duplicate,
            }

        submitted_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        fingerprint = sha1(
            json.dumps(
                {"original_job_id": normalized, "submitted_at": submitted_at, "request": retry_request},
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()[:12]
        retry_job = {
            "job_id": f"retry:{fingerprint}",
            "kind": job.get("kind") or "weekly_report",
            "status": "planned",
            "run_date": "",
            "submitted_at": submitted_at,
            "started_at": "",
            "finished_at": "",
            "request": retry_request,
            "result": {},
            "error": "",
        }
        self._persist_preview_job(retry_job)
        self._record_job_event(
            normalized,
            "retry_created",
            "planned",
            actor,
            "已创建重试 planned 任务。",
            {"retry_job_id": retry_job["job_id"], "request": retry_request},
        )
        self._record_job_event(
            retry_job["job_id"],
            "job_created",
            "planned",
            actor,
            "已创建 failed 任务的重试任务。",
            {"retry_of": normalized, "request": retry_request},
        )
        return {
            "schema_version": 1,
            "accepted": True,
            "retry_created": True,
            "original_job_id": normalized,
            "job_id": retry_job["job_id"],
            "status": retry_job["status"],
            "blockers": [],
            "retry_job": retry_job,
        }

    def trigger_run_preview(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        profile = str(payload.get("profile") or payload.get("interest_profile") or "").strip()
        language = str(payload.get("language") or "").strip()[:80]
        category = str(payload.get("category") or "").strip()[:120]
        query = str(payload.get("query") or payload.get("q") or "").strip()[:160]
        sort = str(payload.get("sort") or "").strip()
        if sort and sort not in {"recent", "position", "score", "star-growth", "trending", "quality"}:
            sort = "score"
        limit = _positive_int(payload.get("limit") or payload.get("limit_count"))
        if limit is not None:
            limit = max(1, min(limit, 50))
        subscription_id = str(payload.get("subscription_id") or "").strip()[:120]
        subscription_name = str(payload.get("subscription_name") or "").strip()[:120]
        sources = _list_strings(payload.get("sources"))
        requested_dry_run = _truthy(payload.get("dry_run", True))
        confirm_delivery = _truthy(payload.get("confirm_delivery"))
        dry_run = requested_dry_run
        safety_warnings = []
        if not requested_dry_run and not confirm_delivery:
            dry_run = True
            safety_warnings.append("未显式确认真实推送，已自动改为 dry_run=true。")
        days_back = _positive_int(payload.get("days_back"))
        trigger_source = str(payload.get("trigger_source") or "api").strip()[:80]
        requested_by = str(payload.get("requested_by") or "").strip()[:120]
        submitted_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        fingerprint = sha1(
            json.dumps(
                {
                    "profile": profile,
                    "language": language,
                    "category": category,
                    "query": query,
                    "sort": sort,
                    "limit": limit,
                    "subscription_id": subscription_id,
                    "sources": sources,
                    "dry_run": dry_run,
                    "confirm_delivery": confirm_delivery,
                    "days_back": days_back,
                    "trigger_source": trigger_source,
                    "requested_by": requested_by,
                    "submitted_at": submitted_at,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()[:12]
        request = {
            "profile": profile,
            "language": language,
            "category": category,
            "query": query,
            "sort": sort,
            "limit": limit,
            "subscription_id": subscription_id,
            "subscription_name": subscription_name,
            "sources": sources,
            "dry_run": dry_run,
            "requested_dry_run": requested_dry_run,
            "confirm_delivery": confirm_delivery,
            "delivery_allowed": not dry_run,
            "days_back": days_back,
            "trigger_source": trigger_source,
            "requested_by": requested_by,
            "safety_warnings": safety_warnings,
        }
        duplicate = self._find_active_duplicate_job(request)
        if duplicate:
            duplicate_warnings = [*safety_warnings, "已存在相同 planned/running 任务，未重复创建。"]
            self._record_job_event(
                duplicate.get("job_id") or "",
                "duplicate_trigger_ignored",
                duplicate.get("status") or "",
                requested_by or trigger_source or "api",
                "命中已有 active 任务，未重复创建。",
                {"request": request, "duplicate_of": duplicate.get("job_id") or ""},
            )
            return {
                "schema_version": 1,
                "job_id": duplicate.get("job_id") or "",
                "status": duplicate.get("status") or "",
                "submitted_at": duplicate.get("submitted_at") or "",
                "execution_supported": False,
                "http_execution_supported": False,
                "planned_job_created": False,
                "duplicate_of": duplicate.get("job_id") or "",
                "execution_path": "scripts/run_planned_job.py",
                "message": "已存在相同 planned/running 任务，本次请求未重复创建。",
                "request": request,
                "safety_warnings": duplicate_warnings,
                "next_steps": [
                    "查看已有任务状态，等待 job runner 或 GitHub Actions 消费。",
                    "如需重新创建，请先让已有任务完成，或调整 profile、来源、回看天数、dry_run 参数。",
                ],
            }
        job = {
            "job_id": f"preview:{fingerprint}",
            "kind": "weekly_report",
            "status": "planned",
            "run_date": "",
            "submitted_at": submitted_at,
            "started_at": "",
            "finished_at": "",
            "request": request,
            "result": {},
            "error": "",
        }
        self._persist_preview_job(job)
        self._record_job_event(
            job["job_id"],
            "job_created",
            job["status"],
            requested_by or trigger_source or "api",
            "已创建 planned 周报任务。",
            {"request": request},
        )
        return {
            "schema_version": 1,
            "job_id": job["job_id"],
            "status": job["status"],
            "submitted_at": submitted_at,
            "execution_supported": False,
            "http_execution_supported": False,
            "planned_job_created": True,
            "execution_path": "scripts/run_planned_job.py",
            "message": "当前接口只创建 planned 任务，不在 HTTP 请求中直接执行采集、生成或推送。",
            "request": request,
            "safety_warnings": safety_warnings,
            "next_steps": [
                "由 job runner 消费 planned 任务并推进为 running/succeeded/failed。",
                "dry_run=true 时跳过主流程内置推送，适合验证采集和生成。",
                "dry_run=false 必须同时提供 confirm_delivery=true，避免误触发真实推送。",
            ],
        }

    def trigger_subscription_run(self, subscription_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self.ensure_sqlite_index()
        payload = payload or {}
        subscription = self._subscription_by_id(subscription_id)
        actor = str(payload.get("requested_by") or "subscription").strip()[:120]
        normalized_id = str(subscription_id or "").strip()
        if not subscription:
            return {
                "schema_version": 1,
                "found": False,
                "accepted": False,
                "planned_job_created": False,
                "subscription_id": normalized_id,
                "subscription": {},
                "job_id": "",
                "status": "",
                "blockers": ["订阅不存在，无法生成计划任务。"],
                "next_steps": ["先在订阅配置页保存订阅，再生成计划任务。"],
            }
        if subscription.get("status") != "enabled":
            self._record_job_event(
                f"subscription:{normalized_id}",
                "subscription_trigger_blocked",
                str(subscription.get("status") or "disabled"),
                actor or "subscription",
                "订阅未启用，未创建 planned 周报任务。",
                {"subscription_id": normalized_id, "subscription": subscription},
            )
            return {
                "schema_version": 1,
                "found": True,
                "accepted": False,
                "planned_job_created": False,
                "subscription_id": normalized_id,
                "subscription": subscription,
                "job_id": "",
                "status": "",
                "blockers": ["订阅当前不是 enabled 状态，不能生成计划任务。"],
                "next_steps": ["先启用订阅，再生成计划任务。"],
            }

        request_payload = {
            "profile": subscription.get("profile") or "",
            "language": subscription.get("language") or "",
            "category": subscription.get("category") or "",
            "query": subscription.get("query") or "",
            "sort": subscription.get("sort") or "",
            "limit": subscription.get("limit") or "",
            "subscription_id": normalized_id,
            "subscription_name": subscription.get("name") or "",
            "sources": _list_strings(payload.get("sources")) or ["github_trending"],
            "days_back": _positive_int(payload.get("days_back")) or 7,
            "dry_run": payload.get("dry_run", True),
            "confirm_delivery": payload.get("confirm_delivery", False),
            "trigger_source": "subscription",
            "requested_by": actor,
        }
        result = self.trigger_run_preview(request_payload)
        result.update(
            {
                "found": True,
                "accepted": bool(result.get("planned_job_created") or result.get("duplicate_of")),
                "subscription_id": normalized_id,
                "subscription": subscription,
            }
        )
        return result

    def profiles(self) -> dict[str, Any]:
        return _read_json_object(
            self.root / "docs" / "profiles.json",
            {"schema_version": 1, "count": 0, "profiles": []},
        )

    def subscriptions(self, *, status: str | None = None, limit: int = 50) -> dict[str, Any]:
        self.ensure_sqlite_index()
        status = _blank_to_none(status)
        limit = max(1, min(int(limit or 50), 200))
        conditions = []
        parameters: list[Any] = []
        if status:
            conditions.append("status = ?")
            parameters.append(status)
        sql = """
            SELECT subscription_id, name, status, profile, language, category, query,
                   sort, limit_count, channels_json, created_at, updated_at, payload_json
            FROM subscriptions
        """
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY updated_at DESC, created_at DESC, subscription_id DESC LIMIT ?"
        parameters.append(limit)
        connection = connect(self.db_path)
        try:
            initialize(connection)
            rows = connection.execute(sql, parameters).fetchall()
        finally:
            connection.close()
        subscriptions = [_subscription_from_row(row) for row in rows]
        return {
            "schema_version": 1,
            "count": len(subscriptions),
            "subscriptions": subscriptions,
        }

    def subscription_events(
        self,
        *,
        full_name: str | None = None,
        event_type: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        self.ensure_sqlite_index()
        from src.notifications.service import subscription_events

        return subscription_events(
            self.db_path,
            full_name=str(full_name or "").strip(),
            event_type=str(event_type or "").strip(),
            severity=str(severity or "").strip(),
            status=str(status or "").strip(),
            limit=limit,
        )

    def detect_subscription_events(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self.ensure_sqlite_index()
        from src.notifications.service import detect_subscription_events

        data = payload or {}
        return detect_subscription_events(
            self.db_path,
            full_name=str(data.get("full_name") or data.get("repo") or "").strip(),
            limit=max(1, min(_int_value(data.get("limit")) or 500, 2000)),
            dry_run=data.get("dry_run") is True,
        )

    def notification_candidates(
        self,
        *,
        status: str | None = None,
        subscription_id: str | None = None,
        full_name: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        self.ensure_sqlite_index()
        from src.notifications.service import notification_candidates

        return notification_candidates(
            self.db_path,
            status=str(status or "").strip(),
            subscription_id=str(subscription_id or "").strip(),
            full_name=str(full_name or "").strip(),
            limit=limit,
        )

    def build_notification_candidates(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self.ensure_sqlite_index()
        from src.notifications.service import build_notification_candidates

        data = payload or {}
        return build_notification_candidates(
            self.db_path,
            limit=max(1, min(_int_value(data.get("limit")) or 500, 2000)),
            dry_run=data.get("dry_run") is True,
        )

    def notification_deliveries(
        self,
        *,
        candidate_id: str | None = None,
        status: str | None = None,
        channel: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        self.ensure_sqlite_index()
        from src.notifications.service import notification_deliveries

        return notification_deliveries(
            self.db_path,
            candidate_id=str(candidate_id or "").strip(),
            status=str(status or "").strip(),
            channel=str(channel or "").strip(),
            limit=limit,
        )

    def deliver_notification_candidate(
        self,
        candidate_id: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.ensure_sqlite_index()
        from src.notifications.service import deliver_notification_candidate
        from src.settings import load_settings

        data = payload or {}
        today = datetime.now(UTC).date().isoformat()
        settings = load_settings(today, today, root=self.root)
        raw_channels = data.get("channels")
        channels = raw_channels if isinstance(raw_channels, list) else None
        return deliver_notification_candidate(
            self.db_path,
            settings,
            candidate_id,
            dry_run=data.get("dry_run", True) is not False,
            confirm_delivery=data.get("confirm_delivery") is True,
            channels=channels,
            retry_failed=data.get("retry_failed") is True,
            requested_by=str(data.get("requested_by") or "api").strip(),
        )

    def create_subscription(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self.ensure_sqlite_index()
        data = _subscription_payload(payload or {})
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        data["created_at"] = now
        data["updated_at"] = now
        if data["status"] == "in_progress":
            data["started_at"] = now
        if data["status"] in {"completed", "failed", "cancelled"}:
            data["finished_at"] = now
        data["subscription_id"] = _subscription_id(data)
        self._upsert_subscription(data)
        return {
            "schema_version": 1,
            "created": True,
            "subscription": data,
        }

    def update_subscription(self, subscription_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self.ensure_sqlite_index()
        current = self._subscription_by_id(subscription_id)
        if not current:
            return {
                "schema_version": 1,
                "found": False,
                "updated": False,
                "subscription_id": subscription_id,
                "subscription": {},
            }
        updates = _subscription_payload({**current, **(payload or {})})
        updates["subscription_id"] = current["subscription_id"]
        updates["created_at"] = current.get("created_at") or ""
        updates["updated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        self._upsert_subscription(updates)
        return {
            "schema_version": 1,
            "found": True,
            "updated": True,
            "subscription_id": updates["subscription_id"],
            "subscription": updates,
        }

    def create_project_agent_task(
        self,
        full_name: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.ensure_sqlite_index()
        data = _project_agent_task_payload(payload or {}, full_name=full_name)
        error = _project_agent_task_validation_error(data)
        if error:
            return {"schema_version": 1, "accepted": False, "created": False, "error": error, "task": {}}
        now = _utc_now()
        data["created_at"] = now
        data["updated_at"] = now
        data["dedupe_key"] = data["dedupe_key"] or _project_agent_task_dedupe_key(data)
        existing = self._project_agent_task_by_dedupe_key(data["dedupe_key"])
        if existing:
            return {
                "schema_version": 1,
                "accepted": True,
                "created": False,
                "deduplicated": True,
                "task": existing,
            }
        data["task_id"] = data["task_id"] or _project_agent_task_id(data)
        self._upsert_project_agent_task(data)
        return {
            "schema_version": 1,
            "accepted": True,
            "created": True,
            "deduplicated": False,
            "task": data,
        }

    def project_agent_tasks(
        self,
        *,
        full_name: str | None = None,
        profile: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        self.ensure_sqlite_index()
        limit = max(1, min(_int_value(limit) or 50, 500))
        conditions = []
        parameters: list[Any] = []
        if _blank_to_none(full_name):
            conditions.append("LOWER(full_name) = LOWER(?)")
            parameters.append(_normalize_full_name(str(full_name)))
        if _blank_to_none(profile):
            conditions.append("profile = ?")
            parameters.append(str(profile).strip())
        if _blank_to_none(status):
            conditions.append("status = ?")
            parameters.append(str(status).strip())
        sql = """
            SELECT task_id, full_name, profile, task_type, priority, status, reason,
                   result_summary, source, dedupe_key, created_at, updated_at,
                   started_at, finished_at, payload_json,
                   (SELECT result_json FROM project_agent_task_runs r
                    WHERE r.task_id = project_agent_tasks.task_id AND r.status = 'succeeded'
                    ORDER BY r.started_at DESC, r.run_id DESC LIMIT 1) AS latest_result_json
            FROM project_agent_tasks
        """
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY CASE status WHEN 'in_progress' THEN 0 WHEN 'planned' THEN 1 ELSE 2 END, priority ASC, updated_at DESC LIMIT ?"
        parameters.append(limit)
        connection = connect(self.db_path)
        try:
            initialize(connection)
            rows = connection.execute(sql, parameters).fetchall()
        finally:
            connection.close()
        tasks = [_project_agent_task_from_row(row) for row in rows]
        return {
            "schema_version": 1,
            "count": len(tasks),
            "tasks": tasks,
            "summary": _project_agent_task_summary(tasks),
        }

    def update_project_agent_task(
        self,
        task_id: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.ensure_sqlite_index()
        current = self._project_agent_task_by_id(task_id)
        if not current:
            return {"schema_version": 1, "found": False, "updated": False, "error": "任务不存在。", "task": {}}
        incoming = payload or {}
        next_status = str(incoming.get("status") or current["status"]).strip()
        if next_status not in PROJECT_AGENT_TASK_STATUSES:
            return {"schema_version": 1, "found": True, "updated": False, "error": "不支持的任务状态。", "task": current}
        if next_status not in PROJECT_AGENT_TASK_TRANSITIONS.get(current["status"], {current["status"]}):
            return {
                "schema_version": 1,
                "found": True,
                "updated": False,
                "error": f"任务状态不能从 {current['status']} 变更为 {next_status}。",
                "task": current,
            }
        updated = {
            **current,
            "status": next_status,
            "priority": max(1, min(_int_value(incoming.get("priority")) or current["priority"], 5)),
            "reason": str(incoming.get("reason") if "reason" in incoming else current["reason"]).strip()[:1000],
            "result_summary": str(
                incoming.get("result_summary") if "result_summary" in incoming else current["result_summary"]
            ).strip()[:2000],
            "updated_at": _utc_now(),
        }
        if next_status == "in_progress" and not updated.get("started_at"):
            updated["started_at"] = updated["updated_at"]
        if next_status in {"completed", "failed", "cancelled"}:
            updated["finished_at"] = updated["updated_at"]
        elif next_status == "planned":
            updated["started_at"] = ""
            updated["finished_at"] = ""
        current_payload = current.get("payload") if isinstance(current.get("payload"), dict) else {}
        incoming_payload = incoming.get("payload") if isinstance(incoming.get("payload"), dict) else {}
        updated["payload"] = {**current_payload, **incoming_payload}
        self._upsert_project_agent_task(updated)
        return {"schema_version": 1, "found": True, "updated": True, "task": updated}

    def project_agent_task_execution_check(self, task_id: str, *, retry: bool = False) -> dict[str, Any]:
        self.ensure_sqlite_index()
        from src.agent.task_executor import project_agent_task_execution_check

        return project_agent_task_execution_check(self.db_path, task_id, retry=retry)

    def execute_project_agent_task(
        self,
        task_id: str,
        *,
        retry: bool = False,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        self.ensure_sqlite_index()
        from src.agent.task_executor import execute_project_agent_task

        return execute_project_agent_task(self.root, self.db_path, task_id, retry=retry, dry_run=dry_run)

    def project_agent_task_runs(
        self,
        task_id: str | None = None,
        *,
        full_name: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        self.ensure_sqlite_index()
        from src.agent.task_executor import project_agent_task_runs

        normalized = _normalize_full_name(str(full_name)) if _blank_to_none(full_name) else None
        return project_agent_task_runs(
            self.db_path,
            task_id=task_id,
            full_name=normalized,
            limit=limit,
        )

    def create_project_feedback(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self.ensure_sqlite_index()
        data = _project_feedback_payload(payload or {})
        if not data["full_name"]:
            return {
                "schema_version": 1,
                "accepted": False,
                "created": False,
                "error": "full_name 不能为空。",
                "feedback": {},
            }
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        data["created_at"] = now
        data["updated_at"] = now
        data["feedback_id"] = _project_feedback_id(data)
        self._upsert_project_feedback(data)
        return {
            "schema_version": 1,
            "accepted": True,
            "created": True,
            "feedback": data,
        }

    def project_feedback(
        self,
        *,
        full_name: str | None = None,
        profile: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        self.ensure_sqlite_index()
        limit = max(1, min(_int_value(limit) or 50, 200))
        conditions = []
        parameters: list[Any] = []
        normalized_full_name = _blank_to_none(full_name)
        normalized_profile = _blank_to_none(profile)
        if normalized_full_name:
            conditions.append("LOWER(full_name) = LOWER(?)")
            parameters.append(normalized_full_name)
        if normalized_profile:
            conditions.append("profile = ?")
            parameters.append(normalized_profile)
        sql = """
            SELECT feedback_id, full_name, profile, rating, labels_json, note,
                   source, created_at, updated_at, payload_json
            FROM project_feedback
        """
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY updated_at DESC, feedback_id DESC LIMIT ?"
        parameters.append(limit)
        connection = connect(self.db_path)
        try:
            initialize(connection)
            rows = connection.execute(sql, parameters).fetchall()
        finally:
            connection.close()
        feedback = [_project_feedback_from_row(row) for row in rows]
        return {
            "schema_version": 1,
            "count": len(feedback),
            "feedback": feedback,
            "summary": _project_feedback_summary(feedback),
        }

    def latest_weekly(self) -> dict[str, Any]:
        reports = sorted((self.root / "reports").glob("*.md"), key=lambda path: path.stem, reverse=True)
        reports = [path for path in reports if path.name != ".gitkeep"]
        if not reports:
            return {
                "schema_version": 1,
                "run_date": "",
                "report_url": "",
                "markdown": "",
                "run_summary": {},
            }
        latest = reports[0]
        return {
            "schema_version": 1,
            "run_date": latest.stem,
            "report_url": f"weekly/{latest.stem}.html",
            "markdown": latest.read_text(encoding="utf-8"),
            "run_summary": _read_json_object(self.root / "data" / "runs" / f"{latest.stem}.json", {}),
        }

    def ensure_sqlite_index(self) -> None:
        if not self.db_path.exists() or not self._sqlite_table_exists("jobs"):
            import_json_archive(self.root, self.db_path)
        if (
            not self._sqlite_table_exists("subscriptions")
            or not self._sqlite_table_exists("project_corpus")
            or not self._sqlite_table_exists("project_corpus_fts")
            or not self._sqlite_table_exists("rag_chunks")
            or not self._sqlite_table_exists("rag_chunks_fts")
            or not self._sqlite_table_exists("rag_embeddings")
            or not self._sqlite_table_exists("dev_corpus")
            or not self._sqlite_table_exists("dev_chunks")
            or not self._sqlite_table_exists("dev_chunks_fts")
            or not self._sqlite_table_exists("dev_embeddings")
            or not self._sqlite_table_exists("dev_runs")
            or not self._sqlite_table_exists("project_agent_task_runs")
        ):
            connection = connect(self.db_path)
            try:
                initialize(connection)
            finally:
                connection.close()
        if (
            self._sqlite_table_exists("selections")
            and self._sqlite_table_exists("project_corpus")
            and self._sqlite_table_exists("project_corpus_fts")
            and self._sqlite_table_exists("rag_chunks")
            and self._sqlite_table_exists("rag_chunks_fts")
            and self._sqlite_table_exists("rag_embeddings")
        ):
            connection = connect(self.db_path)
            try:
                initialize(connection)
                if (
                    table_count(connection, "project_corpus") == 0
                    or table_count(connection, "project_corpus_fts") == 0
                    or table_count(connection, "rag_chunks") == 0
                    or table_count(connection, "rag_chunks_fts") == 0
                ) and table_count(connection, "selections") > 0:
                    rebuild_project_corpus(connection)
                    connection.commit()
            finally:
                connection.close()

    def _embedding_count(self, model: str) -> int:
        connection = connect(self.db_path)
        try:
            initialize(connection)
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM rag_embeddings WHERE embedding_model = ?",
                (model,),
            ).fetchone()
            return _int_value(row["count"] if row else 0)
        finally:
            connection.close()

    def _embedding_rows(self, model: str) -> list[Any]:
        connection = connect(self.db_path)
        try:
            initialize(connection)
            return connection.execute(
                """
                SELECT e.chunk_id, e.corpus_id, e.run_date, e.full_name, e.html_url,
                       e.embedding_model, e.dimensions, e.vector_json, e.payload_json,
                       c.chunk_index, c.chunk_text, c.language, c.category, c.sources_json
                FROM rag_embeddings e
                LEFT JOIN rag_chunks c ON c.chunk_id = e.chunk_id
                WHERE e.embedding_model = ?
                ORDER BY e.run_date DESC, e.full_name ASC
                """,
                (model,),
            ).fetchall()
        finally:
            connection.close()

    def _jobs_from_sqlite(self, limit: int) -> list[dict[str, Any]]:
        connection = connect(self.db_path)
        try:
            rows = connection.execute(
                """
                SELECT job_id, kind, status, run_date, submitted_at, started_at, finished_at,
                       request_json, result_json, error, payload_json
                FROM jobs
                ORDER BY COALESCE(NULLIF(submitted_at, ''), run_date) DESC, job_id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        finally:
            connection.close()
        return [_job_from_row(row) for row in rows]

    def _find_active_duplicate_job(self, request: dict[str, Any], *, kind: str = "weekly_report") -> dict[str, Any]:
        self.ensure_sqlite_index()
        target_key = _job_request_key(request)
        normalized_kind = kind if kind in EXECUTABLE_JOB_KINDS else "weekly_report"
        connection = connect(self.db_path)
        try:
            rows = connection.execute(
                """
                SELECT job_id, kind, status, run_date, submitted_at, started_at, finished_at,
                       request_json, result_json, error, payload_json
                FROM jobs
                WHERE kind = ? AND status IN ('planned', 'running')
                ORDER BY COALESCE(NULLIF(submitted_at, ''), run_date) DESC, job_id DESC
                LIMIT 200
                """,
                (normalized_kind,),
            ).fetchall()
        finally:
            connection.close()
        for row in rows:
            job = _job_from_row(row)
            if _job_request_key(job.get("request") or {}) == target_key:
                return job
        return {}

    def _persist_preview_job(self, job: dict[str, Any]) -> None:
        self.ensure_sqlite_index()
        connection = connect(self.db_path)
        try:
            initialize(connection)
            upsert_job(connection, job)
            connection.commit()
        finally:
            connection.close()

    def _record_job_event(
        self,
        job_id: str,
        event_type: str,
        status: str,
        actor: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if not job_id:
            return
        self.ensure_sqlite_index()
        connection = connect(self.db_path)
        try:
            initialize(connection)
            insert_job_event(
                connection,
                {
                    "job_id": job_id,
                    "event_type": event_type,
                    "status": status,
                    "actor": actor,
                    "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                    "message": message,
                    "payload": payload or {},
                },
            )
            connection.commit()
        finally:
            connection.close()

    def _subscription_by_id(self, subscription_id: str) -> dict[str, Any]:
        connection = connect(self.db_path)
        try:
            initialize(connection)
            row = connection.execute(
                """
                SELECT subscription_id, name, status, profile, language, category, query,
                       sort, limit_count, channels_json, created_at, updated_at, payload_json
                FROM subscriptions
                WHERE subscription_id = ?
                """,
                (subscription_id,),
            ).fetchone()
        finally:
            connection.close()
        return _subscription_from_row(row) if row else {}

    def _upsert_subscription(self, data: dict[str, Any]) -> None:
        connection = connect(self.db_path)
        try:
            initialize(connection)
            connection.execute(
                """
                INSERT INTO subscriptions(
                  subscription_id, name, status, profile, language, category, query,
                  sort, limit_count, channels_json, created_at, updated_at, payload_json
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(subscription_id) DO UPDATE SET
                  name = excluded.name,
                  status = excluded.status,
                  profile = excluded.profile,
                  language = excluded.language,
                  category = excluded.category,
                  query = excluded.query,
                  sort = excluded.sort,
                  limit_count = excluded.limit_count,
                  channels_json = excluded.channels_json,
                  updated_at = excluded.updated_at,
                  payload_json = excluded.payload_json
                """,
                (
                    data["subscription_id"],
                    data["name"],
                    data["status"],
                    data["profile"],
                    data["language"],
                    data["category"],
                    data["query"],
                    data["sort"],
                    data["limit"],
                    json.dumps(data["channels"], ensure_ascii=False, sort_keys=True),
                    data["created_at"],
                    data["updated_at"],
                    json.dumps(data, ensure_ascii=False, sort_keys=True),
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def _project_agent_task_by_id(self, task_id: str) -> dict[str, Any]:
        normalized = str(task_id or "").strip()
        if not normalized:
            return {}
        connection = connect(self.db_path)
        try:
            initialize(connection)
            row = connection.execute(
                """
                SELECT task_id, full_name, profile, task_type, priority, status, reason,
                       result_summary, source, dedupe_key, created_at, updated_at,
                       started_at, finished_at, payload_json
                FROM project_agent_tasks WHERE task_id = ?
                """,
                (normalized,),
            ).fetchone()
        finally:
            connection.close()
        return _project_agent_task_from_row(row) if row else {}

    def _project_agent_task_by_dedupe_key(self, dedupe_key: str) -> dict[str, Any]:
        if not dedupe_key:
            return {}
        connection = connect(self.db_path)
        try:
            initialize(connection)
            row = connection.execute(
                """
                SELECT task_id, full_name, profile, task_type, priority, status, reason,
                       result_summary, source, dedupe_key, created_at, updated_at,
                       started_at, finished_at, payload_json
                FROM project_agent_tasks WHERE dedupe_key = ?
                """,
                (dedupe_key,),
            ).fetchone()
        finally:
            connection.close()
        return _project_agent_task_from_row(row) if row else {}

    def _upsert_project_agent_task(self, data: dict[str, Any]) -> None:
        connection = connect(self.db_path)
        try:
            initialize(connection)
            upsert_project_agent_task(connection, data)
            rebuild_project_corpus(connection)
            connection.commit()
        finally:
            connection.close()

    def _upsert_project_feedback(self, data: dict[str, Any]) -> None:
        connection = connect(self.db_path)
        try:
            initialize(connection)
            connection.execute(
                """
                INSERT INTO project_feedback(
                  feedback_id, full_name, profile, rating, labels_json, note,
                  source, created_at, updated_at, payload_json
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(feedback_id) DO UPDATE SET
                  full_name = excluded.full_name,
                  profile = excluded.profile,
                  rating = excluded.rating,
                  labels_json = excluded.labels_json,
                  note = excluded.note,
                  source = excluded.source,
                  updated_at = excluded.updated_at,
                  payload_json = excluded.payload_json
                """,
                (
                    data["feedback_id"],
                    data["full_name"],
                    data["profile"],
                    data["rating"],
                    json.dumps(data["labels"], ensure_ascii=False, sort_keys=True),
                    data["note"],
                    data["source"],
                    data["created_at"],
                    data["updated_at"],
                    json.dumps(data, ensure_ascii=False, sort_keys=True),
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def _sqlite_table_exists(self, table_name: str) -> bool:
        if not self.db_path.exists():
            return False
        connection = connect(self.db_path)
        try:
            row = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table_name,),
            ).fetchone()
            return bool(row)
        finally:
            connection.close()

    def _similar_projects(self, base: dict[str, Any], full_name: str) -> list[dict[str, Any]]:
        candidates = query_archive(db_path=self.db_path, root=self.root, limit=200, sort="recent")
        scored = []
        seen = set()
        for candidate in candidates:
            candidate_name = str(candidate.get("full_name") or "")
            if not candidate_name or candidate_name.lower() == full_name.lower() or candidate_name in seen:
                continue
            seen.add(candidate_name)
            score = _similarity_score(base, candidate)
            if score <= 0:
                continue
            scored.append((score, candidate))
        scored.sort(
            key=lambda item: (
                item[0],
                _int_value(item[1].get("star_growth")),
                -_rank_value(item[1].get("trending_rank")),
                str(item[1].get("run_date") or ""),
            ),
            reverse=True,
        )
        return [
            {
                "full_name": project.get("full_name") or "",
                "html_url": project.get("html_url") or "",
                "description": project.get("description") or "",
                "language": project.get("language") or "",
                "category": project.get("category") or "",
                "run_date": project.get("run_date") or "",
                "star_growth": _int_value(project.get("star_growth")),
                "trending_rank": _int_value(project.get("trending_rank")),
                "similarity_score": score,
            }
            for score, project in scored[:5]
        ]


def _read_json_object(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default
    return data if isinstance(data, dict) else default


def _job_from_run(run: dict[str, Any]) -> dict[str, Any]:
    run_date = str(run.get("run_date") or "")
    status = str(run.get("status") or "")
    failed = bool(run.get("report_error") or run.get("telegram_error") or run.get("sqlite_error"))
    job_status = "failed" if status == "failed" or failed else "succeeded"
    return {
        "job_id": f"run:{run_date}",
        "run_date": run_date,
        "kind": "weekly_report",
        "status": job_status,
        "selected_count": _int_value(run.get("selected_count")),
        "collected_count": _int_value(run.get("collected_count")),
        "kimi_used": bool(run.get("kimi_used")),
        "telegram_sent": bool(run.get("telegram_sent")),
        "report_url": run.get("report_url") or run.get("telegram_report_url") or "",
    }


def _job_from_row(row: Any) -> dict[str, Any]:
    payload = _json_object(row["payload_json"])
    result = _json_object(row["result_json"])
    request = _json_object(row["request_json"])
    return {
        "job_id": row["job_id"],
        "run_date": row["run_date"],
        "kind": row["kind"],
        "status": row["status"],
        "submitted_at": row["submitted_at"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "request": request,
        "result": result,
        "error": row["error"],
        "selected_count": _int_value(result.get("selected_count")),
        "collected_count": _int_value(result.get("collected_count")),
        "kimi_used": bool(result.get("kimi_used")),
        "telegram_sent": bool(result.get("telegram_sent")),
        "report_url": result.get("report_url") or result.get("telegram_report_url") or payload.get("report_url") or "",
    }


def _count_by_field(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = str(item.get(field) or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _rag_maintenance_job_summary(job: dict[str, Any]) -> dict[str, Any]:
    result = job.get("result") if isinstance(job.get("result"), dict) else {}
    before_counts = result.get("before_counts") if isinstance(result.get("before_counts"), dict) else {}
    after_counts = result.get("after_counts") if isinstance(result.get("after_counts"), dict) else {}
    summary = {
        "job_id": job.get("job_id") or "",
        "kind": job.get("kind") or "",
        "status": job.get("status") or "",
        "run_date": job.get("run_date") or "",
        "submitted_at": job.get("submitted_at") or "",
        "finished_at": job.get("finished_at") or "",
        "dry_run": bool(result.get("dry_run")),
        "error": job.get("error") or "",
        "before_counts": before_counts,
        "after_counts": after_counts,
        "count_delta": {
            key: _int_value(after_counts.get(key)) - _int_value(before_counts.get(key))
            for key in sorted(set(before_counts) | set(after_counts))
        },
    }
    kind = str(job.get("kind") or "")
    if kind == "rag_backfill":
        summary.update(
            {
                "candidate_count": _int_value(result.get("candidate_count")),
                "processed_count": _int_value(result.get("processed_count")),
                "coverage_before": result.get("coverage_before")
                if isinstance(result.get("coverage_before"), dict)
                else {},
                "processed_repositories": result.get("processed_repositories")
                if isinstance(result.get("processed_repositories"), list)
                else [],
            }
        )
    elif kind == "rag_corpus_rebuild":
        summary.update(
            {
                "selected_archive_count": _int_value(result.get("selected_archive_count")),
                "import_counts": result.get("import_counts") if isinstance(result.get("import_counts"), dict) else {},
            }
        )
    elif kind == "rag_embedding_build":
        summary.update(
            {
                "model": result.get("model") or "",
                "dimensions": _int_value(result.get("dimensions")),
                "chunk_count": _int_value(result.get("chunk_count")),
                "embedding_count": _int_value(result.get("embedding_count")),
            }
        )
    elif kind == "rag_search_evaluation":
        aggregate = result.get("aggregate") if isinstance(result.get("aggregate"), dict) else {}
        summary.update(
            {
                "sample_count": _int_value(result.get("sample_count")),
                "queries": result.get("queries") if isinstance(result.get("queries"), list) else [],
                "language": result.get("language") or "",
                "category": result.get("category") or "",
                "source": result.get("source") or "",
                "limit": _int_value(result.get("limit")),
                "model": result.get("model") or "",
                "auto_build": bool(result.get("auto_build")),
                "preferred_mode_counts": aggregate.get("preferred_mode_counts")
                if isinstance(aggregate.get("preferred_mode_counts"), dict)
                else {},
                "zero_hit_queries": aggregate.get("zero_hit_queries")
                if isinstance(aggregate.get("zero_hit_queries"), list)
                else [],
                "repository_count": _int_value(aggregate.get("repository_count")),
            }
        )
    return summary


def _rag_maintenance_report_recommendations(jobs: list[dict[str, Any]], diagnostics: dict[str, Any]) -> list[str]:
    recommendations = []
    signals = diagnostics.get("signals") if isinstance(diagnostics.get("signals"), dict) else {}
    coverage = diagnostics.get("coverage") if isinstance(diagnostics.get("coverage"), dict) else {}
    if not jobs:
        recommendations.append("还没有 RAG 维护任务记录，建议先在管理页生成维护计划。")
    if not signals.get("has_corpus"):
        recommendations.append("语料表为空，优先执行 rag_corpus_rebuild。")
    elif not signals.get("has_embeddings"):
        recommendations.append("向量索引为空，优先执行 rag_embedding_build。")
    elif _int_value(coverage.get("gap_count")) > 0:
        recommendations.append("仍存在解释覆盖缺口，继续执行 rag_backfill。")
    failed_count = sum(1 for job in jobs if job.get("status") == "failed")
    if failed_count:
        recommendations.append(f"最近维护任务中有 {failed_count} 个失败任务，需要查看任务详情和事件日志。")
    if not recommendations:
        recommendations.append("RAG 维护链路已有可用记录，下一步可以观察覆盖率和解释质量变化。")
    return recommendations


def _rag_backfill_job_id(submitted_at: str, request: dict[str, Any]) -> str:
    compact_time = submitted_at.replace("-", "").replace(":", "").replace(".", "").replace("Z", "")
    fingerprint = json.dumps(request, ensure_ascii=False, sort_keys=True)
    digest = sha1(fingerprint.encode("utf-8")).hexdigest()[:10]
    return f"rag-backfill:{compact_time}:{digest}"


def _rag_backfill_plan_job_id(submitted_at: str, request: dict[str, Any]) -> str:
    compact_time = submitted_at.replace("-", "").replace(":", "").replace(".", "").replace("Z", "")
    fingerprint = json.dumps(request, ensure_ascii=False, sort_keys=True)
    digest = sha1(fingerprint.encode("utf-8")).hexdigest()[:10]
    return f"rag-backfill-plan:{compact_time}:{digest}"


def _rag_maintenance_plan_job_id(kind: str, submitted_at: str, request: dict[str, Any]) -> str:
    compact_time = submitted_at.replace("-", "").replace(":", "").replace(".", "").replace("Z", "")
    fingerprint = json.dumps({"kind": kind, "request": request}, ensure_ascii=False, sort_keys=True)
    digest = sha1(fingerprint.encode("utf-8")).hexdigest()[:10]
    prefix = "rag-corpus-plan" if kind == "rag_corpus_rebuild" else "rag-embedding-plan"
    return f"{prefix}:{compact_time}:{digest}"


def _dev_context_index_plan_job_id(submitted_at: str, request: dict[str, Any]) -> str:
    compact_time = submitted_at.replace("-", "").replace(":", "").replace(".", "").replace("Z", "")
    fingerprint = json.dumps(request, ensure_ascii=False, sort_keys=True)
    digest = sha1(fingerprint.encode("utf-8")).hexdigest()[:10]
    return f"dev-context-index-plan:{compact_time}:{digest}"


def _rag_backfill_job_result(result: dict[str, Any]) -> dict[str, Any]:
    processed = result.get("processed") if isinstance(result.get("processed"), list) else []
    processed_repositories = [
        {
            "full_name": item.get("full_name") or "",
            "status": item.get("status") or "",
            "dry_run": bool(item.get("dry_run")),
            "quality_score": _int_value(item.get("quality_score")),
            "quality_level": item.get("quality_level") or "",
            "explanation_id": item.get("explanation_id") or "",
        }
        for item in processed
        if isinstance(item, dict)
    ]
    return {
        "dry_run": bool(result.get("dry_run")),
        "requested_limit": _int_value(result.get("requested_limit")),
        "candidate_count": _int_value(result.get("candidate_count")),
        "processed_count": _int_value(result.get("processed_count")),
        "coverage_before": result.get("coverage_before") if isinstance(result.get("coverage_before"), dict) else {},
        "processed_repositories": processed_repositories,
        "safety_warnings": result.get("safety_warnings") if isinstance(result.get("safety_warnings"), list) else [],
    }


def _job_event_from_row(row: Any) -> dict[str, Any]:
    return {
        "event_id": row["event_id"],
        "job_id": row["job_id"],
        "event_type": row["event_type"],
        "status": row["status"],
        "actor": row["actor"],
        "created_at": row["created_at"],
        "message": row["message"],
        "payload": _json_object(row["payload_json"]),
    }


def _optional_row(row: Any) -> dict[str, Any]:
    return dict(row) if row else {}


def _group_counts(connection: Any, table_name: str, column_name: str) -> dict[str, int]:
    rows = connection.execute(
        f"""
        SELECT COALESCE(NULLIF({column_name}, ''), 'unknown') AS name, COUNT(*) AS count
        FROM {table_name}
        GROUP BY COALESCE(NULLIF({column_name}, ''), 'unknown')
        ORDER BY count DESC, name ASC
        """
    ).fetchall()
    return {str(row["name"]): _int_value(row["count"]) for row in rows}


def _top_counts(connection: Any, table_name: str, column_name: str, limit: int = 8) -> list[dict[str, Any]]:
    rows = connection.execute(
        f"""
        SELECT COALESCE(NULLIF({column_name}, ''), 'unknown') AS name, COUNT(*) AS count
        FROM {table_name}
        GROUP BY COALESCE(NULLIF({column_name}, ''), 'unknown')
        ORDER BY count DESC, name ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [{"name": str(row["name"]), "count": _int_value(row["count"])} for row in rows]


def _trend_point(point: dict[str, Any]) -> dict[str, Any]:
    selected_count = _int_value(point.get("selected_count"))
    collected_count = _int_value(point.get("collected_count"))
    trending_project_count = _int_value(point.get("trending_project_count"))
    return {
        "run_date": point.get("run_date") or "",
        "status": point.get("status") or "",
        "collected_count": collected_count,
        "selected_count": selected_count,
        "kimi_used": bool(point.get("kimi_used")),
        "fallback_used": bool(point.get("fallback_used")),
        "telegram_sent": bool(point.get("telegram_sent")),
        "total_projects": _int_value(point.get("total_projects")),
        "trending_project_count": trending_project_count,
        "trending_selected_rate": _rate(trending_project_count, selected_count),
        "trending_top10_count": _int_value(point.get("trending_top10_count")),
        "total_star_growth": _int_value(point.get("total_star_growth")),
        "avg_score": round(float(point.get("avg_score") or 0), 4),
        "collection_to_selection_rate": _rate(selected_count, collected_count),
    }


def _database_trend_summary(points: list[dict[str, Any]]) -> dict[str, Any]:
    trend_points = [_trend_point(point) for point in points]
    if not trend_points:
        return {
            "run_count": 0,
            "latest_run_date": "",
            "latest_status": "",
            "total_selected_count": 0,
            "total_star_growth": 0,
            "average_trending_selected_rate": 0,
            "failed_run_count": 0,
            "fallback_run_count": 0,
            "telegram_sent_count": 0,
        }
    return {
        "run_count": len(trend_points),
        "latest_run_date": trend_points[-1]["run_date"],
        "latest_status": trend_points[-1]["status"],
        "total_selected_count": sum(point["selected_count"] for point in trend_points),
        "total_star_growth": sum(point["total_star_growth"] for point in trend_points),
        "average_trending_selected_rate": round(
            sum(point["trending_selected_rate"] for point in trend_points) / len(trend_points),
            4,
        ),
        "failed_run_count": sum(1 for point in trend_points if point["status"] == "failed"),
        "fallback_run_count": sum(1 for point in trend_points if point["fallback_used"]),
        "telegram_sent_count": sum(1 for point in trend_points if point["telegram_sent"]),
    }


def _language_facet(row: Any) -> dict[str, Any]:
    return {
        "name": str(row["name"] or "unknown"),
        "project_count": _int_value(row["project_count"]),
        "total_stars": _int_value(row["total_stars"]),
        "total_forks": _int_value(row["total_forks"]),
        "latest_pushed_at": row["latest_pushed_at"] or "",
    }


def _category_facet(row: Any) -> dict[str, Any]:
    selection_count = _int_value(row["selection_count"])
    return {
        "name": str(row["name"] or "Other"),
        "selection_count": selection_count,
        "project_count": _int_value(row["project_count"]),
        "total_star_growth": _int_value(row["total_star_growth"]),
        "avg_score": round(float(row["avg_score"] or 0), 4),
        "trending_top10_count": _int_value(row["trending_top10_count"]),
        "trending_top10_rate": _rate(_int_value(row["trending_top10_count"]), selection_count),
    }


def _source_facets(rows: list[Any], limit: int) -> list[dict[str, Any]]:
    counts: dict[str, dict[str, Any]] = {}
    for row in rows:
        full_name = str(row["full_name"] or "")
        sources = _list_strings(_json_list(row["sources_json"]))
        if not sources:
            sources = ["unknown"]
        for source in sources:
            item = counts.setdefault(source, {"name": source, "selection_count": 0, "projects": set()})
            item["selection_count"] += 1
            if full_name:
                item["projects"].add(full_name)
    return [
        {
            "name": str(item["name"]),
            "selection_count": _int_value(item["selection_count"]),
            "project_count": len(item["projects"]),
        }
        for item in sorted(counts.values(), key=lambda value: (-value["selection_count"], value["name"]))[:limit]
    ]


def _quality_facets(rows: list[Any], limit: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    quality_counts: dict[str, dict[str, Any]] = {}
    risk_counts: dict[str, dict[str, Any]] = {}
    for row in rows:
        full_name = str(row["full_name"] or "")
        payload = _json_object(row["payload_json"])
        quality_level = str(payload.get("quality_level") or "unknown").strip() or "unknown"
        security_flags = _list_strings(payload.get("security_flags"))
        risk_level = "has" if security_flags else "none"
        _increment_facet(quality_counts, quality_level, full_name)
        _increment_facet(risk_counts, risk_level, full_name)
    return _facet_counts(quality_counts, limit), _facet_counts(risk_counts, limit)


def _subscription_facets(rows: list[Any], limit: int) -> dict[str, Any]:
    status_counts: dict[str, dict[str, Any]] = {}
    profile_counts: dict[str, dict[str, Any]] = {}
    language_counts: dict[str, dict[str, Any]] = {}
    category_counts: dict[str, dict[str, Any]] = {}
    for row in rows:
        _increment_facet(status_counts, str(row["status"] or "unknown"), "")
        _increment_facet(profile_counts, str(row["profile"] or "unknown"), "")
        _increment_facet(language_counts, str(row["language"] or "unknown"), "")
        _increment_facet(category_counts, str(row["category"] or "unknown"), "")
    return {
        "statuses": _facet_counts(status_counts, limit),
        "profiles": _facet_counts(profile_counts, limit),
        "languages": _facet_counts(language_counts, limit),
        "categories": _facet_counts(category_counts, limit),
    }


def _increment_facet(counts: dict[str, dict[str, Any]], name: str, full_name: str) -> None:
    key = name.strip() or "unknown"
    item = counts.setdefault(key, {"name": key, "count": 0, "projects": set()})
    item["count"] += 1
    if full_name:
        item["projects"].add(full_name)


def _facet_counts(counts: dict[str, dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    values = sorted(counts.values(), key=lambda value: (-value["count"], value["name"]))[:limit]
    return [
        {
            "name": str(item["name"]),
            "count": _int_value(item["count"]),
            "project_count": len(item["projects"]),
        }
        for item in values
    ]


def _search_terms(query: str) -> list[str]:
    return [part.strip() for part in query.replace(",", " ").split() if part.strip()][:8]


def _search_rows_fts(
    connection: Any,
    *,
    terms: list[str],
    language: str | None,
    category: str | None,
    source: str | None,
    limit: int,
) -> list[Any]:
    conditions = ["project_corpus_fts MATCH ?"]
    parameters: list[Any] = [_fts_query(terms)]
    if language:
        conditions.append("c.language = ?")
        parameters.append(language)
    if category:
        conditions.append("c.category = ?")
        parameters.append(category)
    if source:
        conditions.append("c.sources_json LIKE ?")
        parameters.append(f"%{source}%")
    parameters.append(limit)
    return connection.execute(
        f"""
        SELECT c.corpus_id, c.run_date, c.full_name, c.html_url, c.title, c.language, c.category,
               c.sources_json, c.search_text, c.payload_json
        FROM project_corpus c
        JOIN project_corpus_fts f ON f.corpus_id = c.corpus_id
        WHERE {" AND ".join(conditions)}
        ORDER BY bm25(project_corpus_fts), c.run_date DESC, c.full_name ASC
        LIMIT ?
        """,
        parameters,
    ).fetchall()


def _search_rows_like(
    connection: Any,
    *,
    terms: list[str],
    language: str | None,
    category: str | None,
    source: str | None,
    limit: int,
) -> list[Any]:
    conditions = []
    parameters: list[Any] = []
    if language:
        conditions.append("language = ?")
        parameters.append(language)
    if category:
        conditions.append("category = ?")
        parameters.append(category)
    if source:
        conditions.append("sources_json LIKE ?")
        parameters.append(f"%{source}%")
    for term in terms:
        conditions.append("LOWER(search_text) LIKE ?")
        parameters.append(f"%{term.lower()}%")
    sql = """
        SELECT corpus_id, run_date, full_name, html_url, title, language, category,
               sources_json, search_text, payload_json
        FROM project_corpus
    """
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY run_date DESC, full_name ASC LIMIT ?"
    parameters.append(limit)
    return connection.execute(sql, parameters).fetchall()


def _corpus_rows_latest(
    connection: Any,
    *,
    language: str | None,
    category: str | None,
    source: str | None,
    limit: int,
) -> list[Any]:
    conditions = []
    parameters: list[Any] = []
    if language:
        conditions.append("language = ?")
        parameters.append(language)
    if category:
        conditions.append("category = ?")
        parameters.append(category)
    if source:
        conditions.append("sources_json LIKE ?")
        parameters.append(f"%{source}%")
    sql = """
        SELECT corpus_id, run_date, full_name, html_url, title, language, category,
               sources_json, search_text, payload_json
        FROM project_corpus
    """
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY run_date DESC, full_name ASC LIMIT ?"
    parameters.append(limit)
    return connection.execute(sql, parameters).fetchall()


def _rag_chunk_rows_fts(
    connection: Any,
    *,
    terms: list[str],
    language: str | None,
    category: str | None,
    source: str | None,
    limit: int,
) -> list[Any]:
    conditions = ["rag_chunks_fts MATCH ?"]
    parameters: list[Any] = [_fts_query(terms)]
    if language:
        conditions.append("c.language = ?")
        parameters.append(language)
    if category:
        conditions.append("c.category = ?")
        parameters.append(category)
    if source:
        conditions.append("c.sources_json LIKE ?")
        parameters.append(f"%{source}%")
    parameters.append(limit)
    return connection.execute(
        f"""
        SELECT c.chunk_id, c.corpus_id, c.chunk_index, c.run_date, c.full_name, c.html_url,
               c.language, c.category, c.sources_json, c.chunk_text, c.token_estimate, c.payload_json
        FROM rag_chunks c
        JOIN rag_chunks_fts f ON f.chunk_id = c.chunk_id
        WHERE {" AND ".join(conditions)}
        ORDER BY bm25(rag_chunks_fts), c.run_date DESC, c.full_name ASC, c.chunk_index ASC
        LIMIT ?
        """,
        parameters,
    ).fetchall()


def _rag_chunk_rows_like(
    connection: Any,
    *,
    terms: list[str],
    language: str | None,
    category: str | None,
    source: str | None,
    limit: int,
) -> list[Any]:
    conditions = []
    parameters: list[Any] = []
    if language:
        conditions.append("language = ?")
        parameters.append(language)
    if category:
        conditions.append("category = ?")
        parameters.append(category)
    if source:
        conditions.append("sources_json LIKE ?")
        parameters.append(f"%{source}%")
    for term in terms:
        conditions.append("LOWER(chunk_text) LIKE ?")
        parameters.append(f"%{term.lower()}%")
    sql = """
        SELECT chunk_id, corpus_id, chunk_index, run_date, full_name, html_url,
               language, category, sources_json, chunk_text, token_estimate, payload_json
        FROM rag_chunks
    """
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY run_date DESC, full_name ASC, chunk_index ASC LIMIT ?"
    parameters.append(limit)
    return connection.execute(sql, parameters).fetchall()


def _fts_query(terms: list[str]) -> str:
    quoted_terms = []
    for term in terms:
        cleaned = term.replace('"', " ").strip()
        if cleaned:
            quoted_terms.append(f'"{cleaned}"')
    return " ".join(quoted_terms) or '""'


def _search_result(row: Any, terms: list[str]) -> dict[str, Any]:
    text = str(row["search_text"] or "")
    lower_text = text.lower()
    score = 0
    for term in terms:
        term_lower = term.lower()
        score += lower_text.count(term_lower) * 10
        if str(row["full_name"] or "").lower().find(term_lower) >= 0:
            score += 20
        if str(row["category"] or "").lower().find(term_lower) >= 0:
            score += 8
        if str(row["language"] or "").lower().find(term_lower) >= 0:
            score += 6
    payload = _json_object(row["payload_json"])
    return {
        "corpus_id": row["corpus_id"],
        "run_date": row["run_date"],
        "full_name": row["full_name"],
        "html_url": row["html_url"],
        "title": row["title"],
        "language": row["language"],
        "category": row["category"],
        "sources": _list_strings(_json_list(row["sources_json"])),
        "score": score,
        "snippet": _snippet(text, terms),
        "quality_level": payload.get("quality_level") or "",
        "trending_rank": _int_value(payload.get("trending_rank")),
        "star_growth": _int_value(payload.get("star_growth")),
    }


def _rag_document(row: Any, terms: list[str]) -> dict[str, Any]:
    text = str(row["search_text"] or "").strip()
    payload = _json_object(row["payload_json"])
    return {
        "id": row["corpus_id"],
        "text": text,
        "metadata": {
            "run_date": row["run_date"],
            "full_name": row["full_name"],
            "html_url": row["html_url"],
            "title": row["title"],
            "language": row["language"],
            "category": row["category"],
            "sources": _list_strings(_json_list(row["sources_json"])),
            "quality_level": payload.get("quality_level") or "",
            "trending_rank": _int_value(payload.get("trending_rank")),
            "star_growth": _int_value(payload.get("star_growth")),
            "project_profile": payload.get("project_profile") if isinstance(payload.get("project_profile"), dict) else {},
        },
        "evidence": _rag_evidence(text, terms),
    }


def _rag_evidence(text: str, terms: list[str]) -> list[str]:
    snippet = _snippet(text, terms, size=260) if terms else _snippet(text, [], size=260)
    return [snippet] if snippet else []


def _rag_corpus_readiness(documents: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "ready_for_embedding": bool(documents),
        "has_metadata": all(bool(document.get("metadata", {}).get("full_name")) for document in documents),
        "has_evidence": any(bool(document.get("evidence")) for document in documents),
        "next_steps": (
            ["接入 embedding 生成向量索引。", "把 documents 写入 LangChain retriever 或其他 RAG 检索器。"]
            if documents
            else ["先运行周报生成并同步 SQLite 语料。"]
        ),
    }


def _rag_context(row: Any, terms: list[str]) -> dict[str, Any]:
    text = str(row["chunk_text"] or "").strip()
    lower_text = text.lower()
    score = 0
    for term in terms:
        term_lower = term.lower()
        score += lower_text.count(term_lower) * 10
        if str(row["full_name"] or "").lower().find(term_lower) >= 0:
            score += 15
        if str(row["category"] or "").lower().find(term_lower) >= 0:
            score += 8
        if str(row["language"] or "").lower().find(term_lower) >= 0:
            score += 5
    payload = _json_object(row["payload_json"])
    return {
        "chunk_id": row["chunk_id"],
        "corpus_id": row["corpus_id"],
        "text": text,
        "score": score,
        "evidence": _rag_evidence(text, terms),
        "metadata": {
            "chunk_index": _int_value(row["chunk_index"]),
            "run_date": row["run_date"],
            "full_name": row["full_name"],
            "html_url": row["html_url"],
            "language": row["language"],
            "category": row["category"],
            "sources": _list_strings(_json_list(row["sources_json"])),
            "token_estimate": _int_value(row["token_estimate"]),
            "quality_level": payload.get("quality_level") or "",
            "trending_rank": _int_value(payload.get("trending_rank")),
            "star_growth": _int_value(payload.get("star_growth")),
            "project_profile": payload.get("project_profile") if isinstance(payload.get("project_profile"), dict) else {},
        },
    }


def _dedupe_rag_contexts(contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    deduped = []
    for context in contexts:
        key = (
            str(context.get("metadata", {}).get("full_name") or "").lower(),
            _int_value(context.get("metadata", {}).get("chunk_index")),
        )
        if not key[0] or key in seen:
            continue
        seen.add(key)
        deduped.append(context)
    return deduped


def _rag_citations(contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    citations = []
    for index, context in enumerate(contexts, start=1):
        metadata = context.get("metadata", {})
        citations.append(
            {
                "index": index,
                "full_name": metadata.get("full_name") or "",
                "html_url": metadata.get("html_url") or "",
                "run_date": metadata.get("run_date") or "",
                "chunk_id": context.get("chunk_id") or "",
            }
        )
    return citations


def _rag_prompt_context(contexts: list[dict[str, Any]]) -> str:
    parts = []
    for index, context in enumerate(contexts, start=1):
        metadata = context.get("metadata", {})
        parts.append(
            "\n".join(
                [
                    f"[{index}] {metadata.get('full_name') or ''} ({metadata.get('run_date') or ''})",
                    str(context.get("text") or ""),
                ]
            )
        )
    return "\n\n".join(parts)


def _rag_retrieve_summary(contexts: list[dict[str, Any]], terms: list[str]) -> list[str]:
    if not contexts:
        return [f"没有找到匹配 {'、'.join(terms)} 的 RAG 语料块。"]
    repositories = _unique_strings(context.get("metadata", {}).get("full_name") or "" for context in contexts)
    return [
        f"召回 {len(contexts)} 个 RAG 语料块，关键词：{'、'.join(terms)}。",
        f"覆盖 {len(repositories)} 个项目：{'、'.join(repositories[:5])}。",
    ]


def _vector_context(row: Any, payload: dict[str, Any], score: float, terms: list[str]) -> dict[str, Any]:
    text = str(row["chunk_text"] or "")
    sources = _list_strings(payload.get("sources") or _json_list(row["sources_json"]))
    return {
        "chunk_id": row["chunk_id"],
        "corpus_id": row["corpus_id"],
        "text": text,
        "score": round(float(score), 6),
        "evidence": _rag_evidence(text, terms),
        "metadata": {
            "chunk_index": _int_value(row["chunk_index"]),
            "run_date": row["run_date"],
            "full_name": row["full_name"],
            "html_url": row["html_url"],
            "language": payload.get("language") or row["language"] or "",
            "category": payload.get("category") or row["category"] or "",
            "sources": sources,
            "token_estimate": _int_value(payload.get("token_estimate")),
            "quality_level": payload.get("quality_level") or "",
            "trending_rank": _int_value(payload.get("trending_rank")),
            "star_growth": _int_value(payload.get("star_growth")),
            "embedding_model": row["embedding_model"],
            "dimensions": _int_value(row["dimensions"]),
        },
    }


def _rag_vector_summary(contexts: list[dict[str, Any]], model: str) -> list[str]:
    if not contexts:
        return [f"本地向量索引未命中；请确认已运行 build_rag_embeddings.py，当前模型：{model}。"]
    repositories = _unique_strings(context.get("metadata", {}).get("full_name") or "" for context in contexts)
    return [
        f"本地向量索引召回 {len(contexts)} 个证据块，模型：{model}。",
        f"覆盖 {len(repositories)} 个项目：{'、'.join(repositories[:5])}。",
    ]


def _merge_hybrid_contexts(
    text_contexts: list[dict[str, Any]],
    vector_contexts: list[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    merged: dict[tuple[str, int], dict[str, Any]] = {}
    _add_hybrid_contexts(merged, text_contexts, source="text", weight=0.55)
    _add_hybrid_contexts(merged, vector_contexts, source="vector", weight=0.45)
    contexts = list(merged.values())
    for context in contexts:
        context["retrieval_sources"] = sorted(set(_list_strings(context.get("retrieval_sources") or [])))
        context["score"] = round(float(context.get("hybrid_score") or 0), 6)
    contexts.sort(
        key=lambda item: (
            float(item.get("score") or 0),
            len(item.get("retrieval_sources") or []),
            item.get("metadata", {}).get("run_date") or "",
            item.get("metadata", {}).get("full_name") or "",
        ),
        reverse=True,
    )
    return contexts[:limit]


def _add_hybrid_contexts(
    merged: dict[tuple[str, int], dict[str, Any]],
    contexts: list[dict[str, Any]],
    *,
    source: str,
    weight: float,
) -> None:
    total = max(len(contexts), 1)
    for index, context in enumerate(contexts, start=1):
        metadata = context.get("metadata") if isinstance(context.get("metadata"), dict) else {}
        key = (
            str(metadata.get("full_name") or "").lower(),
            _int_value(metadata.get("chunk_index")),
        )
        if not key[0]:
            continue
        rank_score = (total - index + 1) / total
        item = merged.get(key)
        if not item:
            item = json.loads(json.dumps(context, ensure_ascii=False))
            item["hybrid_score"] = 0.0
            item["retrieval_sources"] = []
            item["retrieval_scores"] = {}
            merged[key] = item
        item["hybrid_score"] = round(float(item.get("hybrid_score") or 0) + rank_score * weight, 6)
        item["retrieval_sources"].append(source)
        item["retrieval_scores"][source] = context.get("score", 0)


def _rag_hybrid_summary(contexts: list[dict[str, Any]], model: str) -> list[str]:
    if not contexts:
        return [f"混合检索没有命中证据块；请放宽过滤条件，或先构建 {model} 向量索引。"]
    repositories = _unique_strings(context.get("metadata", {}).get("full_name") or "" for context in contexts)
    source_counts = {
        "text": sum(1 for context in contexts if "text" in _list_strings(context.get("retrieval_sources") or [])),
        "vector": sum(1 for context in contexts if "vector" in _list_strings(context.get("retrieval_sources") or [])),
    }
    return [
        f"混合检索召回 {len(contexts)} 个证据块，覆盖 {len(repositories)} 个项目。",
        f"文本命中 {source_counts['text']} 个，向量命中 {source_counts['vector']} 个，向量模型：{model}。",
        f"优先项目：{'、'.join(repositories[:5])}。",
    ]


def _rag_compare_mode_summary(result: dict[str, Any]) -> dict[str, Any]:
    contexts = result.get("contexts") if isinstance(result.get("contexts"), list) else []
    repositories = _unique_strings(
        context.get("metadata", {}).get("full_name") or "" for context in contexts if isinstance(context, dict)
    )
    return {
        "mode": result.get("retrieval", {}).get("mode") or "",
        "count": len(contexts),
        "citation_count": len(result.get("citations") or []),
        "repositories": repositories,
        "top_repositories": repositories[:5],
        "top_contexts": _rag_compare_top_contexts(contexts),
        "retrieval": result.get("retrieval") or {},
    }


def _rag_compare_top_contexts(contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for context in contexts[:5]:
        metadata = context.get("metadata") if isinstance(context.get("metadata"), dict) else {}
        output.append(
            {
                "full_name": metadata.get("full_name") or "",
                "html_url": metadata.get("html_url") or "",
                "run_date": metadata.get("run_date") or "",
                "chunk_id": context.get("chunk_id") or "",
                "score": context.get("score", 0),
                "retrieval_sources": _list_strings(context.get("retrieval_sources") or []),
                "text_preview": str(context.get("text") or "")[:220],
            }
        )
    return output


def _rag_compare_overlap(modes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sets = {name: set(_list_strings(data.get("repositories") or [])) for name, data in modes.items()}
    all_repositories = set().union(*sets.values()) if sets else set()
    common_repositories = set.intersection(*sets.values()) if sets and all(sets.values()) else set()
    pairwise = {}
    pairs = [("fts5", "vector"), ("fts5", "hybrid"), ("vector", "hybrid")]
    for left, right in pairs:
        left_set = sets.get(left, set())
        right_set = sets.get(right, set())
        union = left_set | right_set
        intersection = left_set & right_set
        pairwise[f"{left}_vs_{right}"] = {
            "intersection_count": len(intersection),
            "union_count": len(union),
            "overlap_rate": round(len(intersection) / len(union), 4) if union else 0,
            "repositories": sorted(intersection),
        }
    return {
        "repository_count": len(all_repositories),
        "common_count": len(common_repositories),
        "common_repositories": sorted(common_repositories),
        "pairwise": pairwise,
    }


def _rag_compare_recommendation(modes: dict[str, dict[str, Any]], overlap: dict[str, Any]) -> dict[str, Any]:
    hybrid = modes.get("hybrid", {})
    text = modes.get("fts5", {})
    vector = modes.get("vector", {})
    if hybrid.get("count", 0) > 0:
        mode = "hybrid"
        reason = "混合检索已有命中，能同时吸收关键词精确匹配和向量相似召回。"
    elif text.get("count", 0) >= vector.get("count", 0) and text.get("count", 0) > 0:
        mode = "fts5"
        reason = "文本检索命中更多，适合作为当前查询的主要证据来源。"
    elif vector.get("count", 0) > 0:
        mode = "vector"
        reason = "向量检索有命中，适合查询词和项目描述不完全一致的场景。"
    else:
        mode = "none"
        reason = "三种模式都没有命中，需要放宽筛选条件或补充 RAG 语料。"
    return {
        "preferred_mode": mode,
        "reason": reason,
        "common_repository_count": overlap.get("common_count", 0),
    }


def _rag_compare_summary(
    modes: dict[str, dict[str, Any]],
    overlap: dict[str, Any],
    recommendation: dict[str, Any],
) -> list[str]:
    return [
        (
            "FTS5 命中 {fts5} 个证据块，向量命中 {vector} 个证据块，混合命中 {hybrid} 个证据块。"
        ).format(
            fts5=modes.get("fts5", {}).get("count", 0),
            vector=modes.get("vector", {}).get("count", 0),
            hybrid=modes.get("hybrid", {}).get("count", 0),
        ),
        f"三种模式共同覆盖 {overlap.get('common_count', 0)} 个项目，总覆盖 {overlap.get('repository_count', 0)} 个项目。",
        f"建议优先使用 {recommendation.get('preferred_mode')}：{recommendation.get('reason')}",
    ]


def _normalize_rag_evaluation_queries(queries: list[str] | None) -> list[str]:
    defaults = [
        "agent workflow",
        "python automation",
        "developer tools",
        "rag search",
        "java backend",
    ]
    candidates = queries if queries else defaults
    output = []
    seen = set()
    for query in candidates:
        normalized = str(query or "").strip()
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        output.append(normalized)
        if len(output) >= 10:
            break
    return output or defaults[:1]


def _rag_evaluation_aggregate(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    mode_names = ["fts5", "vector", "hybrid"]
    preferred_mode_counts: dict[str, int] = {}
    mode_totals = {name: {"count": 0, "citation_count": 0, "hit_queries": 0} for name in mode_names}
    all_repositories: set[str] = set()
    zero_hit_queries = []
    pairwise_overlap_totals: dict[str, float] = {}
    for evaluation in evaluations:
        recommendation = evaluation.get("recommendation") if isinstance(evaluation.get("recommendation"), dict) else {}
        preferred = str(recommendation.get("preferred_mode") or "none")
        preferred_mode_counts[preferred] = preferred_mode_counts.get(preferred, 0) + 1
        modes = evaluation.get("modes") if isinstance(evaluation.get("modes"), dict) else {}
        query_has_hit = False
        for name in mode_names:
            mode = modes.get(name) if isinstance(modes.get(name), dict) else {}
            count = _int_value(mode.get("count"))
            citation_count = _int_value(mode.get("citation_count"))
            mode_totals[name]["count"] += count
            mode_totals[name]["citation_count"] += citation_count
            if count > 0:
                mode_totals[name]["hit_queries"] += 1
                query_has_hit = True
            all_repositories.update(_list_strings(mode.get("repositories") or []))
        if not query_has_hit:
            zero_hit_queries.append(evaluation.get("query") or "")
        pairwise = evaluation.get("overlap", {}).get("pairwise", {})
        if isinstance(pairwise, dict):
            for name, data in pairwise.items():
                if isinstance(data, dict):
                    pairwise_overlap_totals[name] = pairwise_overlap_totals.get(name, 0.0) + float(
                        data.get("overlap_rate") or 0
                    )
    sample_count = max(len(evaluations), 1)
    modes = {
        name: {
            "total_count": values["count"],
            "average_count": round(values["count"] / sample_count, 4),
            "total_citation_count": values["citation_count"],
            "hit_queries": values["hit_queries"],
            "hit_rate": round(values["hit_queries"] / sample_count, 4),
        }
        for name, values in mode_totals.items()
    }
    return {
        "preferred_mode_counts": preferred_mode_counts,
        "modes": modes,
        "repository_count": len(all_repositories),
        "repositories": sorted(all_repositories)[:30],
        "zero_hit_queries": [query for query in zero_hit_queries if query],
        "pairwise_average_overlap": {
            name: round(total / sample_count, 4) for name, total in sorted(pairwise_overlap_totals.items())
        },
        "recommendations": _rag_evaluation_recommendations(preferred_mode_counts, modes, zero_hit_queries),
    }


def _rag_evaluation_recommendations(
    preferred_mode_counts: dict[str, int],
    modes: dict[str, dict[str, Any]],
    zero_hit_queries: list[str],
) -> list[str]:
    recommendations = []
    if preferred_mode_counts.get("hybrid", 0) >= max(preferred_mode_counts.get("fts5", 0), preferred_mode_counts.get("vector", 0)):
        recommendations.append("当前样本中混合检索最稳定，后续解释和问答可以优先使用 hybrid。")
    if modes.get("vector", {}).get("hit_rate", 0) == 0:
        recommendations.append("向量检索没有命中样本，请先检查 embedding 索引是否已构建。")
    if zero_hit_queries:
        recommendations.append("存在未命中的查询样本，建议补充项目语料或放宽语言/方向过滤。")
    return recommendations or ["当前样本召回正常，可以继续扩大评估样本集。"]


def _rag_evaluation_summary(aggregate: dict[str, Any]) -> list[str]:
    modes = aggregate.get("modes") if isinstance(aggregate.get("modes"), dict) else {}
    preferred = aggregate.get("preferred_mode_counts") if isinstance(aggregate.get("preferred_mode_counts"), dict) else {}
    return [
        (
            "样本评估完成：FTS5 平均命中 {fts5}，向量平均命中 {vector}，混合平均命中 {hybrid}。"
        ).format(
            fts5=modes.get("fts5", {}).get("average_count", 0),
            vector=modes.get("vector", {}).get("average_count", 0),
            hybrid=modes.get("hybrid", {}).get("average_count", 0),
        ),
        f"推荐模式分布：{preferred}。",
        f"覆盖项目数：{aggregate.get('repository_count', 0)}；零命中样本数：{len(aggregate.get('zero_hit_queries') or [])}。",
    ]


def _rag_search_evaluation_request(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    raw_queries = payload.get("queries", payload.get("q"))
    if isinstance(raw_queries, str):
        queries = [raw_queries]
    elif isinstance(raw_queries, list):
        queries = [str(item) for item in raw_queries]
    else:
        queries = []
    return {
        "queries": _normalize_rag_evaluation_queries(queries),
        "language": _blank_to_none(str(payload.get("language") or "")) or "",
        "category": _blank_to_none(str(payload.get("category") or "")) or "",
        "source": _blank_to_none(str(payload.get("source") or "")) or "",
        "limit": max(1, min(_int_value(payload.get("limit")) or 8, 30)),
        "model": _blank_to_none(str(payload.get("model") or "")) or MODEL_NAME,
        "auto_build": _bool_value(payload.get("auto_build"), False),
        "confirm_execution": _truthy(payload.get("confirm_execution", False)),
        "trigger_source": str(payload.get("trigger_source") or "rag_search_evaluation_api"),
        "requested_by": str(payload.get("requested_by") or "api").strip()[:120],
    }


def _rag_search_evaluation_job_id(submitted_at: str, request: dict[str, Any]) -> str:
    text = json.dumps(
        {
            "submitted_at": submitted_at,
            "queries": request.get("queries") or [],
            "language": request.get("language") or "",
            "category": request.get("category") or "",
            "source": request.get("source") or "",
            "limit": request.get("limit") or 0,
            "model": request.get("model") or "",
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    digest = sha1(text.encode("utf-8")).hexdigest()[:12]
    return f"rag-search-eval:{submitted_at[:10]}:{digest}"


def _rag_search_evaluation_plan_job_id(submitted_at: str, request: dict[str, Any]) -> str:
    text = json.dumps(
        {
            "submitted_at": submitted_at,
            "queries": request.get("queries") or [],
            "language": request.get("language") or "",
            "category": request.get("category") or "",
            "source": request.get("source") or "",
            "limit": request.get("limit") or 0,
            "model": request.get("model") or "",
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    digest = sha1(text.encode("utf-8")).hexdigest()[:12]
    return f"rag-search-eval-plan:{submitted_at[:10]}:{digest}"


def _rag_search_evaluation_job_result(result: dict[str, Any]) -> dict[str, Any]:
    aggregate = result.get("aggregate") if isinstance(result.get("aggregate"), dict) else {}
    return {
        "schema_version": result.get("schema_version", 1),
        "sample_count": result.get("sample_count", 0),
        "queries": result.get("queries") or [],
        "language": result.get("language") or "",
        "category": result.get("category") or "",
        "source": result.get("source") or "",
        "limit": _int_value(result.get("limit")),
        "model": result.get("model") or "",
        "auto_build": bool(result.get("auto_build")),
        "aggregate": aggregate,
        "summary": result.get("summary") or [],
    }


def _rag_search_evaluation_trend_item(job: dict[str, Any]) -> dict[str, Any]:
    result = job.get("result") if isinstance(job.get("result"), dict) else {}
    aggregate = result.get("aggregate") if isinstance(result.get("aggregate"), dict) else {}
    modes = aggregate.get("modes") if isinstance(aggregate.get("modes"), dict) else {}
    return {
        "job_id": job.get("job_id") or "",
        "status": job.get("status") or "",
        "run_date": job.get("run_date") or "",
        "submitted_at": job.get("submitted_at") or "",
        "finished_at": job.get("finished_at") or "",
        "sample_count": _int_value(result.get("sample_count")),
        "queries": result.get("queries") if isinstance(result.get("queries"), list) else [],
        "preferred_mode_counts": aggregate.get("preferred_mode_counts") or {},
        "repository_count": _int_value(aggregate.get("repository_count")),
        "zero_hit_count": len(aggregate.get("zero_hit_queries") or []),
        "mode_average_counts": {
            name: float(data.get("average_count") or 0) if isinstance(data, dict) else 0
            for name, data in modes.items()
        },
        "mode_hit_rates": {
            name: float(data.get("hit_rate") or 0) if isinstance(data, dict) else 0 for name, data in modes.items()
        },
        "pairwise_average_overlap": aggregate.get("pairwise_average_overlap") or {},
        "recommendations": aggregate.get("recommendations") or [],
    }


def _rag_search_evaluation_trend_aggregate(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        return {
            "job_count": 0,
            "average_sample_count": 0,
            "average_zero_hit_count": 0,
            "preferred_mode_counts": {},
            "latest_preferred_mode": "",
            "mode_average_counts": {},
            "mode_hit_rates": {},
            "repository_count_max": 0,
        }
    preferred_counts: dict[str, int] = {}
    mode_count_totals: dict[str, float] = {}
    mode_hit_rate_totals: dict[str, float] = {}
    for item in items:
        for mode, count in (item.get("preferred_mode_counts") or {}).items():
            preferred_counts[str(mode)] = preferred_counts.get(str(mode), 0) + _int_value(count)
        for mode, value in (item.get("mode_average_counts") or {}).items():
            mode_count_totals[str(mode)] = mode_count_totals.get(str(mode), 0.0) + float(value or 0)
        for mode, value in (item.get("mode_hit_rates") or {}).items():
            mode_hit_rate_totals[str(mode)] = mode_hit_rate_totals.get(str(mode), 0.0) + float(value or 0)
    count = len(items)
    latest_preferred = ""
    if items:
        latest_counts = items[0].get("preferred_mode_counts") or {}
        if latest_counts:
            latest_preferred = max(latest_counts.items(), key=lambda item: _int_value(item[1]))[0]
    return {
        "job_count": count,
        "average_sample_count": round(sum(_int_value(item.get("sample_count")) for item in items) / count, 4),
        "average_zero_hit_count": round(sum(_int_value(item.get("zero_hit_count")) for item in items) / count, 4),
        "preferred_mode_counts": preferred_counts,
        "latest_preferred_mode": latest_preferred,
        "mode_average_counts": {mode: round(total / count, 4) for mode, total in sorted(mode_count_totals.items())},
        "mode_hit_rates": {mode: round(total / count, 4) for mode, total in sorted(mode_hit_rate_totals.items())},
        "repository_count_max": max(_int_value(item.get("repository_count")) for item in items),
    }


def _rag_search_evaluation_trend_summary(aggregate: dict[str, Any]) -> list[str]:
    if _int_value(aggregate.get("job_count")) == 0:
        return ["暂无 RAG 检索评估历史；可先调用 POST /v1/rag/search-evaluation 写入一次评估。"]
    return [
        f"已汇总 {aggregate.get('job_count', 0)} 次 RAG 检索评估。",
        f"平均零命中样本数：{aggregate.get('average_zero_hit_count', 0)}；最大覆盖项目数：{aggregate.get('repository_count_max', 0)}。",
        f"最新推荐模式：{aggregate.get('latest_preferred_mode') or 'unknown'}。",
    ]


def _rag_search_evaluation_trend_recommendations(aggregate: dict[str, Any]) -> list[str]:
    if _int_value(aggregate.get("job_count")) == 0:
        return ["先执行一次确认式 RAG 检索评估，建立趋势基线。"]
    recommendations = []
    if float(aggregate.get("average_zero_hit_count") or 0) > 0:
        recommendations.append("存在零命中样本，建议补充语料或扩展查询同义词。")
    latest = str(aggregate.get("latest_preferred_mode") or "")
    if latest == "hybrid":
        recommendations.append("最新评估倾向 hybrid，可继续把 hybrid 作为解释和问答默认候选。")
    elif latest:
        recommendations.append(f"最新评估倾向 {latest}，建议检查 hybrid 未成为首选的原因。")
    return recommendations or ["检索趋势稳定，可继续扩大样本集。"]


def _rag_explanation(
    *,
    query: str,
    contexts: list[dict[str, Any]],
    citations: list[dict[str, Any]],
    retrieval: dict[str, Any],
) -> dict[str, Any]:
    if not contexts:
        return {
            "scoring_model": "rule:rag-explain-v1",
            "confidence": "low",
            "answer": "当前没有足够 RAG 证据支撑推荐解释。",
            "why_recommended": [],
            "evidence": [],
            "risks": ["证据块为空，需要扩大关键词、放宽语言/方向过滤，或先构建 RAG 索引。"],
            "next_steps": [
                "检查 /v1/rag/retrieve 是否能召回语料。",
                "如使用向量模式，先运行 scripts/build_rag_embeddings.py 或设置 auto_build=true。",
            ],
        }

    repositories = _unique_strings(context.get("metadata", {}).get("full_name") or "" for context in contexts)
    languages = _unique_strings(context.get("metadata", {}).get("language") or "" for context in contexts)
    categories = _unique_strings(context.get("metadata", {}).get("category") or "" for context in contexts)
    sources = _unique_strings(
        source
        for context in contexts
        for source in _list_strings(context.get("metadata", {}).get("sources") or [])
    )
    top_context = contexts[0]
    top_metadata = top_context.get("metadata", {})
    top_repo = str(top_metadata.get("full_name") or (repositories[0] if repositories else ""))
    top_rank = _int_value(top_metadata.get("trending_rank"))
    top_growth = _int_value(top_metadata.get("star_growth"))
    quality_level = str(top_metadata.get("quality_level") or "")

    why = [
        f"当前问题“{query}”召回了 {len(contexts)} 个证据块，覆盖 {len(repositories)} 个历史热点项目。",
        f"优先关注 {top_repo}，它在当前证据中排序最高。",
    ]
    if languages:
        why.append(f"主要语言覆盖：{'、'.join(languages[:5])}。")
    if categories:
        why.append(f"主要方向覆盖：{'、'.join(categories[:5])}。")
    if top_rank:
        why.append(f"{top_repo} 曾进入 GitHub Trending 第 {top_rank} 位。")
    if top_growth:
        why.append(f"{top_repo} 对应记录的新增 Star 为 {top_growth}。")
    if quality_level:
        why.append(f"{top_repo} 的质量等级为 {quality_level}。")

    evidence = []
    for index, context in enumerate(contexts[:5], start=1):
        metadata = context.get("metadata", {})
        text = str(context.get("text") or "").strip()
        evidence.append(
            {
                "index": index,
                "full_name": metadata.get("full_name") or "",
                "run_date": metadata.get("run_date") or "",
                "chunk_id": context.get("chunk_id") or "",
                "quote": text[:260],
                "matched_evidence": _list_strings(context.get("evidence") or []),
            }
        )

    risks = []
    if len(contexts) < 3:
        risks.append("证据块数量偏少，解释置信度有限。")
    if not any(_int_value(context.get("metadata", {}).get("trending_rank")) for context in contexts):
        risks.append("召回证据缺少 Trending 排名字段，需要结合项目详情页继续判断热度。")
    if not sources:
        risks.append("召回证据缺少来源字段，需要检查语料入库质量。")
    if not risks:
        risks.append("当前未发现明显证据缺口，但仍需人工打开项目 README 和许可证确认。")

    confidence = "high" if len(contexts) >= 5 else "medium" if len(contexts) >= 2 else "low"
    answer = (
        f"基于 {retrieval.get('mode') or 'rag'} 检索，{top_repo} 是当前最值得优先查看的项目；"
        f"证据覆盖 {len(repositories)} 个项目，来源包括 {('、'.join(sources[:5]) if sources else '未标明来源')}。"
    )
    return {
        "scoring_model": "rule:rag-explain-v1",
        "confidence": confidence,
        "answer": answer,
        "why_recommended": why,
        "evidence": evidence,
        "risks": risks,
        "next_steps": [
            "先打开 citations 中排名靠前的项目链接，核对 README、许可证和维护状态。",
            "把 prompt_context 交给后续模型总结时，要求模型必须引用 citation index。",
            "如果解释不够准确，优先补充 README 摘要和真实 embedding，而不是先改前端样式。",
        ],
        "coverage": {
            "repositories": repositories,
            "languages": languages,
            "categories": categories,
            "sources": sources,
            "citation_count": len(citations),
        },
    }


def _rag_explanation_quality(
    *,
    contexts: list[dict[str, Any]],
    citations: list[dict[str, Any]],
    explanation: dict[str, Any],
    prompt_context: str,
) -> dict[str, Any]:
    coverage = explanation.get("coverage") if isinstance(explanation.get("coverage"), dict) else {}
    repositories = _list_strings(coverage.get("repositories") or [])
    evidence = explanation.get("evidence") if isinstance(explanation.get("evidence"), list) else []
    risks = explanation.get("risks") if isinstance(explanation.get("risks"), list) else []
    why = explanation.get("why_recommended") if isinstance(explanation.get("why_recommended"), list) else []
    context_score = min(30, len(contexts) * 6)
    citation_score = min(20, len(citations) * 4)
    repository_score = min(15, len(repositories) * 5)
    evidence_score = min(15, len(evidence) * 3)
    explanation_score = min(10, len(why) * 2)
    prompt_score = 10 if prompt_context.strip() else 0
    risk_penalty = min(20, len(risks) * 5)
    score = max(0, min(100, context_score + citation_score + repository_score + evidence_score + explanation_score + prompt_score - risk_penalty))
    level = "high" if score >= 80 else "medium" if score >= 55 else "low"
    return {
        "score": score,
        "level": level,
        "metrics": {
            "context_count": len(contexts),
            "citation_count": len(citations),
            "repository_count": len(repositories),
            "evidence_count": len(evidence),
            "why_count": len(why),
            "risk_count": len(risks),
            "has_prompt_context": bool(prompt_context.strip()),
        },
        "penalties": {
            "risk_penalty": risk_penalty,
        },
    }


def _rag_answer_next_actions(
    *,
    explanation: dict[str, Any],
    quality: dict[str, Any],
    citations: list[dict[str, Any]],
) -> list[str]:
    actions = _list_strings(explanation.get("next_steps") or [])[:3]
    quality_level = str(quality.get("level") or "").lower()
    if quality_level in {"low", "medium"}:
        actions.insert(0, "先补充 README 摘要、Trending 排名或新增 Star 证据，再让模型生成最终结论。")
    if citations:
        actions.append("回答对外展示前，应保留 citations 中的项目链接和 chunk ID。")
    else:
        actions.append("当前没有可引用项目，建议扩大关键词或取消语言/方向过滤。")
    return _unique_strings(actions)[:5]


def _rag_quality_recommendations(total_count: int, average_quality_score: float, quality_levels: dict[str, int]) -> list[str]:
    if total_count <= 0:
        return ["暂无 RAG 解释历史；先调用 /v1/rag/explain 生成可评估样本。"]
    recommendations = []
    low_count = _int_value(quality_levels.get("low"))
    if low_count:
        recommendations.append(f"存在 {low_count} 条低质量解释，优先检查关键词、语料覆盖和引用完整度。")
    if average_quality_score < 55:
        recommendations.append("平均质量分偏低，建议补充 README 摘要并扩大 RAG 证据召回。")
    elif average_quality_score < 80:
        recommendations.append("平均质量分中等，适合继续对比 FTS 与向量检索效果。")
    else:
        recommendations.append("平均质量分较高，可以开始评估接入模型总结或 LangChain 编排。")
    if not quality_levels.get("high"):
        recommendations.append("暂未形成高质量解释样本，后续应增加更多引用和更完整 prompt_context。")
    return recommendations


def _rag_coverage_recommendations(total_projects: int, healthy_count: int, gaps: list[dict[str, Any]]) -> list[str]:
    if total_projects <= 0:
        return ["暂无项目语料，建议先运行主流程或导入历史归档以生成 SQLite 索引。"]
    missing_chunks = sum(1 for item in gaps if item["chunk_count"] <= 0)
    missing_embeddings = sum(1 for item in gaps if item["embedding_count"] <= 0)
    missing_explanations = sum(1 for item in gaps if item["explanation_count"] <= 0)
    recommendations = []
    if missing_chunks:
        recommendations.append(f"有 {missing_chunks} 个项目缺少 RAG 证据块，优先重建语料索引。")
    if missing_embeddings:
        recommendations.append(f"有 {missing_embeddings} 个项目缺少本地 embedding，向量检索覆盖不足。")
    if missing_explanations:
        recommendations.append(f"有 {missing_explanations} 个项目缺少解释历史，可批量调用项目 RAG 聚合后生成解释样本。")
    if healthy_count == total_projects:
        recommendations.append("所有项目已具备基础 RAG 覆盖，可以继续做模型总结或自动重排。")
    if not recommendations:
        recommendations.append("当前项目已具备部分 RAG 覆盖，建议继续补齐低质量解释和向量索引。")
    return recommendations


def _rag_diagnostics_health(
    *,
    signals: dict[str, bool],
    coverage_rate: float,
    average_quality_score: float,
) -> dict[str, str]:
    if not signals.get("has_corpus") or not signals.get("has_chunks"):
        return {"status": "needs_corpus", "level": "low"}
    if not signals.get("has_explanations"):
        return {"status": "needs_explanations", "level": "medium"}
    if coverage_rate < 0.6 or average_quality_score < 55:
        return {"status": "needs_maintenance", "level": "medium"}
    if not signals.get("has_embeddings"):
        return {"status": "ready_for_text_rag", "level": "medium"}
    return {"status": "ready", "level": "high"}


def _rag_diagnostics_next_actions(
    *,
    signals: dict[str, bool],
    quality: dict[str, Any],
    coverage: dict[str, Any],
) -> list[str]:
    actions: list[str] = []
    if not signals.get("has_corpus") or not signals.get("has_chunks"):
        actions.append("先运行 python scripts\\migrate_json_to_sqlite.py，重建 project_corpus 和 rag_chunks。")
    if not signals.get("has_embeddings"):
        actions.append("运行 python scripts\\build_rag_embeddings.py，补齐本地向量检索索引。")
    if not signals.get("has_explanations") or _int_value(coverage.get("gap_count")) > 0:
        actions.append("运行 RAG 回填预览，确认后执行解释回填，减少 coverage gaps。")
    if float(quality.get("average_quality_score") or 0) < 55:
        actions.append("优先检查低质量解释样本，补充 README 摘要、Trending 排名和新增 Star 证据。")
    if not actions:
        actions.append("当前 RAG 语料、解释和向量索引可用，下一步可以接入真实 embedding 或 LangChain 编排。")
    return _unique_strings(actions)[:5]


def _project_rag_query(detail: dict[str, Any]) -> str:
    repo_name = str(detail.get("full_name") or "").split("/")[-1]
    values = _unique_strings(
        value
        for value in [
            repo_name,
            detail.get("category") or "",
            detail.get("language") or "",
            detail.get("description") or "",
        ]
        if value
    )
    return " ".join(values) or str(detail.get("full_name") or "")


def _project_rag_explanation_summary(explanations: list[dict[str, Any]]) -> dict[str, Any]:
    levels: dict[str, int] = {}
    scores = []
    for item in explanations:
        level = str(item.get("quality_level") or "unknown")
        levels[level] = levels.get(level, 0) + 1
        scores.append(_int_value(item.get("quality_score")))
    average = round(sum(scores) / len(scores), 2) if scores else 0
    recommendations = []
    if not explanations:
        recommendations.append("暂无该项目的 RAG 解释历史，可先调用 /v1/rag/explain 生成解释样本。")
    elif levels.get("low", 0):
        recommendations.append("存在低质量解释，建议补充项目语料或对比 FTS 与向量检索结果。")
    elif average < 75:
        recommendations.append("项目解释质量中等，建议增加引用覆盖并检查 prompt_context。")
    else:
        recommendations.append("项目解释质量较稳定，可以作为后续模型总结或项目对比的输入。")
    return {
        "count": len(explanations),
        "average_quality_score": average,
        "quality_levels": levels,
        "recommendations": recommendations,
    }


def _rag_explanation_id(result: dict[str, Any]) -> str:
    retrieval = result.get("retrieval") if isinstance(result.get("retrieval"), dict) else {}
    contexts = result.get("contexts") if isinstance(result.get("contexts"), list) else []
    text = json.dumps(
        {
            "query": result.get("query") or "",
            "language": result.get("language") or "",
            "category": result.get("category") or "",
            "source": result.get("source") or "",
            "mode": retrieval.get("mode") or "",
            "model": retrieval.get("model") or "",
            "chunks": [context.get("chunk_id") or "" for context in contexts],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return "ragx:" + sha1(text.encode("utf-8")).hexdigest()[:16]


def _rag_explanation_row(row: Any) -> dict[str, Any]:
    explanation = _json_object(row["explanation_json"])
    retrieval = _json_object(row["retrieval_json"])
    quality = _json_object(row["quality_json"])
    return {
        "explanation_id": row["explanation_id"],
        "query": row["query"],
        "language": row["language"],
        "category": row["category"],
        "source": row["source"],
        "mode": row["mode"],
        "model": row["model"],
        "context_count": _int_value(row["context_count"]),
        "confidence": row["confidence"],
        "quality_score": _int_value(row["quality_score"]),
        "quality_level": row["quality_level"],
        "quality": quality,
        "answer": row["answer"],
        "repositories": _list_strings(_json_list(row["repositories_json"])),
        "citations": _json_list(row["citations_json"]),
        "explanation": explanation,
        "retrieval": retrieval,
        "created_at": row["created_at"],
    }


def _dedupe_search_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    deduped = []
    for result in results:
        full_name = str(result.get("full_name") or "").lower()
        if not full_name or full_name in seen:
            continue
        seen.add(full_name)
        deduped.append(result)
    return deduped


def _similarity_query(project: dict[str, Any]) -> str:
    keywords = sorted(_project_keywords(project))
    priority = []
    for value in [
        str(project.get("full_name") or "").split("/")[-1],
        str(project.get("category") or ""),
        str(project.get("description") or ""),
    ]:
        priority.extend(_search_terms(value.replace("-", " ").replace("_", " ")))
    ordered = []
    seen = set()
    for term in [*priority, *keywords]:
        cleaned = term.strip()
        key = cleaned.lower()
        if len(cleaned) < 3 or key in seen:
            continue
        seen.add(key)
        ordered.append(cleaned)
    return " ".join(ordered[:2]) or str(project.get("full_name") or "")


def _similarity_search_attempts(project: dict[str, Any]) -> list[dict[str, str | None]]:
    language = _blank_to_none(str(project.get("language") or ""))
    category = _blank_to_none(str(project.get("category") or ""))
    primary = _similarity_query(project)
    first_keyword = _search_terms(primary)[0] if _search_terms(primary) else ""
    attempts = [
        {"query": primary, "language": language, "category": category},
        {"query": category or primary, "language": None, "category": category},
        {"query": language or primary, "language": language, "category": None},
        {"query": first_keyword or category or language or primary, "language": None, "category": None},
    ]
    unique_attempts = []
    seen = set()
    for attempt in attempts:
        query = str(attempt.get("query") or "").strip()
        if not query:
            continue
        key = (query.lower(), attempt.get("language") or "", attempt.get("category") or "")
        if key in seen:
            continue
        seen.add(key)
        unique_attempts.append(attempt)
    return unique_attempts


def _rank_similar_search_results(
    base: dict[str, Any],
    results: list[dict[str, Any]],
    *,
    exclude_full_name: str,
) -> list[dict[str, Any]]:
    ranked = []
    for result in results:
        full_name = str(result.get("full_name") or "")
        if not full_name or full_name.lower() == exclude_full_name.lower():
            continue
        item = dict(result)
        score, reasons = _similar_search_score(base, item)
        item["similarity_score"] = score
        item["similarity_reasons"] = reasons
        ranked.append(item)
    return sorted(
        ranked,
        key=lambda item: (
            _int_value(item.get("similarity_score")),
            _int_value(item.get("star_growth")),
            -_rank_value(item.get("trending_rank")),
            str(item.get("run_date") or ""),
            str(item.get("full_name") or ""),
        ),
        reverse=True,
    )


def _similar_search_score(base: dict[str, Any], candidate: dict[str, Any]) -> tuple[int, list[str]]:
    score = _int_value(candidate.get("score"))
    reasons = []
    if base.get("language") and base.get("language") == candidate.get("language"):
        score += 20
        reasons.append(f"同为 {base.get('language')} 项目")
    if base.get("category") and base.get("category") == candidate.get("category"):
        score += 24
        reasons.append(f"同属 {base.get('category')} 方向")
    source_overlap = set(base.get("sources") or []) & set(candidate.get("sources") or [])
    if source_overlap:
        score += 8 * len(source_overlap)
        reasons.append(f"来源重合：{'、'.join(sorted(source_overlap))}")
    shared_keywords = sorted((_project_keywords(base) & _project_keywords(candidate)))[:4]
    if shared_keywords:
        score += 6 * len(shared_keywords)
        reasons.append(f"关键词重合：{'、'.join(shared_keywords)}")
    if _int_value(candidate.get("trending_rank")):
        score += max(1, 12 - min(_int_value(candidate.get("trending_rank")), 10))
        reasons.append(f"进入 Trending 第 {_int_value(candidate.get('trending_rank'))} 位")
    if _int_value(candidate.get("star_growth")):
        score += min(12, _int_value(candidate.get("star_growth")) // 10)
        reasons.append(f"新增 Star {_int_value(candidate.get('star_growth'))}")
    return score, reasons[:5]


def _similarity_summary(detail: dict[str, Any], similar: list[dict[str, Any]]) -> list[str]:
    if not similar:
        return ["暂未找到足够相似的历史项目候选。"]
    language = detail.get("language") or "unknown"
    category = detail.get("category") or "Other"
    top = similar[0]
    return [
        f"基于项目名称、简介、方向、语言、来源和历史热度召回 {len(similar)} 个相似候选。",
        f"优先匹配同语言 {language}、同方向 {category} 的历史入选项目。",
        f"当前最相似候选为 {top.get('full_name') or ''}，相似度分 {top.get('similarity_score') or 0}。",
    ]


def _normalize_project_list(value: list[str] | str) -> list[str]:
    raw_items = value if isinstance(value, list) else [value]
    normalized = []
    seen = set()
    for item in raw_items:
        for part in str(item or "").replace("\n", ",").split(","):
            name = _normalize_full_name(part)
            key = name.lower()
            if name and "/" in name and key not in seen:
                seen.add(key)
                normalized.append(name)
    return normalized[:8]


def _comparison_project(detail: dict[str, Any]) -> dict[str, Any]:
    history = detail.get("history") if isinstance(detail.get("history"), list) else []
    latest = history[0] if history else detail
    return {
        "full_name": detail.get("full_name") or "",
        "html_url": detail.get("html_url") or "",
        "description": detail.get("description") or "",
        "language": detail.get("language") or "",
        "category": detail.get("category") or "",
        "sources": detail.get("sources") or [],
        "latest_run_date": detail.get("latest_run_date") or "",
        "first_run_date": detail.get("first_run_date") or "",
        "history_count": _int_value(detail.get("history_count")),
        "total_star_growth": _int_value(detail.get("total_star_growth")),
        "best_trending_rank": _int_value(detail.get("best_trending_rank")),
        "latest_quality_score": _int_value(detail.get("latest_quality_score")),
        "latest_quality_level": detail.get("latest_quality_level") or "unknown",
        "security_flag_count": len(detail.get("security_flags") or []),
        "quality_flag_count": len(detail.get("quality_flags") or []),
        "latest_star_growth": _int_value(latest.get("star_growth")),
        "latest_trending_rank": _int_value(latest.get("trending_rank")),
        "selection_reasons": (detail.get("selection_reasons") or [])[:5],
        "trend_summary": (detail.get("trend_summary") or [])[:5],
    }


def _comparison_matrix(projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    metrics = [
        ("language", "主要语言"),
        ("category", "项目方向"),
        ("latest_run_date", "最近入选"),
        ("history_count", "历史入选次数"),
        ("total_star_growth", "累计新增 Star"),
        ("latest_star_growth", "最近新增 Star"),
        ("best_trending_rank", "最好 Trending 排名"),
        ("latest_quality_score", "最新质量分"),
        ("security_flag_count", "风险提示数量"),
        ("quality_flag_count", "质量提示数量"),
    ]
    return [
        {
            "metric": key,
            "label": label,
            "values": {project.get("full_name") or "": project.get(key) for project in projects},
        }
        for key, label in metrics
    ]


def _comparison_best_by(projects: list[dict[str, Any]]) -> dict[str, str]:
    if not projects:
        return {}
    return {
        "most_history_count": _best_project(projects, "history_count"),
        "highest_total_star_growth": _best_project(projects, "total_star_growth"),
        "highest_latest_star_growth": _best_project(projects, "latest_star_growth"),
        "highest_quality_score": _best_project(projects, "latest_quality_score"),
        "best_trending_rank": _best_project(projects, "best_trending_rank", lower_positive=True),
        "lowest_risk_flags": _best_project(projects, "security_flag_count", lower=True),
    }


def _best_project(
    projects: list[dict[str, Any]],
    key: str,
    *,
    lower: bool = False,
    lower_positive: bool = False,
) -> str:
    candidates = [project for project in projects if project.get("full_name")]
    if lower_positive:
        positives = [project for project in candidates if _int_value(project.get(key)) > 0]
        candidates = positives or candidates
    if not candidates:
        return ""
    if lower or lower_positive:
        return str(min(candidates, key=lambda project: _int_value(project.get(key))).get("full_name") or "")
    return str(max(candidates, key=lambda project: _int_value(project.get(key))).get("full_name") or "")


def _comparison_preference(
    profiles_data: dict[str, Any],
    *,
    profile: str | None,
    language: str | None,
    category: str | None,
    query: str | None,
) -> dict[str, Any]:
    profile_name = _blank_to_none(profile) or ""
    selected = _find_profile(profiles_data, profile_name)
    preferred_languages = _unique_strings(
        [
            *(_as_list(selected.get("preferred_languages")) if selected else []),
            *(_as_list(selected.get("search_languages")) if selected else []),
            *([language] if _blank_to_none(language) else []),
        ]
    )
    preferred_topics = _unique_strings(
        [
            *(_as_list(selected.get("preferred_topics")) if selected else []),
            *(_as_list(selected.get("search_topics")) if selected else []),
            *([category] if _blank_to_none(category) else []),
            *(_query_terms(query)),
        ]
    )
    return {
        "profile": profile_name,
        "profile_label": (selected.get("label") or selected.get("profile_label") or "") if selected else "",
        "language": _blank_to_none(language) or "",
        "category": _blank_to_none(category) or "",
        "query": _blank_to_none(query) or "",
        "preferred_languages": preferred_languages,
        "preferred_topics": preferred_topics,
        "active": bool(profile_name or preferred_languages or preferred_topics),
    }


def _find_profile(profiles_data: dict[str, Any], name: str) -> dict[str, Any]:
    if not name:
        return {}
    key = name.lower()
    for profile in profiles_data.get("profiles") or []:
        names = [
            profile.get("name"),
            profile.get("profile"),
            profile.get("id"),
            profile.get("label"),
            profile.get("profile_label"),
        ]
        if any(str(value or "").lower() == key for value in names):
            return profile
    return {}


def _query_terms(value: str | None) -> list[str]:
    text = _blank_to_none(value)
    if not text:
        return []
    return [part.strip() for part in text.replace(",", " ").replace("，", " ").split() if part.strip()]


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _comparison_recommendation(
    projects: list[dict[str, Any]],
    missing: list[str],
    preference: dict[str, Any] | None = None,
) -> dict[str, Any]:
    preference = preference or {}
    if not projects:
        return {
            "primary_project": "",
            "reasons": ["没有找到可对比项目，无法给出优先推荐。"],
            "cautions": [f"未找到项目：{', '.join(missing)}。"] if missing else [],
            "next_actions": ["请从项目筛选页或项目详情页选择已归档项目进入对比。"],
            "scoring_model": _comparison_model_name(preference),
        }

    ranked = sorted(projects, key=lambda project: _comparison_score(project, preference), reverse=True)
    primary = ranked[0]
    reasons = _comparison_project_reasons(primary, preference)
    cautions = _comparison_project_cautions(primary, missing)
    next_actions = [
        f"优先打开 {primary.get('full_name') or ''} 的详情页，确认 README 摘要、风险提示和历史趋势。",
        "如需进一步细分，请调整 profile、language、category 或 query 后重新对比。",
    ]
    return {
        "primary_project": primary.get("full_name") or "",
        "score": round(_comparison_score(primary, preference), 2),
        "reasons": reasons,
        "cautions": cautions,
        "next_actions": next_actions,
        "scoring_model": _comparison_model_name(preference),
    }


def _comparison_model_name(preference: dict[str, Any]) -> str:
    return "rule:v2-preference" if preference.get("active") else "rule:v1"


def _comparison_score(project: dict[str, Any], preference: dict[str, Any] | None = None) -> float:
    preference = preference or {}
    trending_rank = _int_value(project.get("best_trending_rank"))
    trending_bonus = max(0, 60 - trending_rank) if trending_rank else 0
    return (
        _int_value(project.get("total_star_growth")) * 2.0
        + _int_value(project.get("latest_star_growth")) * 2.0
        + _int_value(project.get("latest_quality_score")) * 1.5
        + _int_value(project.get("history_count")) * 5.0
        + trending_bonus
        - _int_value(project.get("security_flag_count")) * 8.0
        + _comparison_preference_bonus(project, preference)
    )


def _comparison_preference_bonus(project: dict[str, Any], preference: dict[str, Any]) -> float:
    if not preference.get("active"):
        return 0
    bonus = 0.0
    languages = {value.lower() for value in preference.get("preferred_languages") or []}
    topics = {value.lower() for value in preference.get("preferred_topics") or []}
    if (project.get("language") or "").lower() in languages:
        bonus += 80
    text = _comparison_project_text(project)
    matches = [topic for topic in topics if topic and topic in text]
    bonus += min(len(matches), 5) * 20
    return bonus


def _comparison_project_text(project: dict[str, Any]) -> str:
    values = [
        project.get("full_name"),
        project.get("description"),
        project.get("language"),
        project.get("category"),
        *(project.get("sources") or []),
        *(project.get("selection_reasons") or []),
        *(project.get("trend_summary") or []),
    ]
    return " ".join(str(value or "") for value in values).lower()


def _comparison_project_reasons(project: dict[str, Any], preference: dict[str, Any] | None = None) -> list[str]:
    preference = preference or {}
    reasons = [
        f"综合规则评分最高：{round(_comparison_score(project, preference), 2)}。",
        f"累计新增 Star {_int_value(project.get('total_star_growth'))}，最近一次新增 Star {_int_value(project.get('latest_star_growth'))}。",
        f"历史入选 {_int_value(project.get('history_count'))} 次，最新质量分 {_int_value(project.get('latest_quality_score'))}。",
    ]
    if _int_value(project.get("best_trending_rank")):
        reasons.append(f"最好 GitHub Trending 排名第 {_int_value(project.get('best_trending_rank'))} 位。")
    preference_reasons = _comparison_preference_reasons(project, preference)
    reasons.extend(preference_reasons)
    return reasons


def _comparison_preference_reasons(project: dict[str, Any], preference: dict[str, Any]) -> list[str]:
    if not preference.get("active"):
        return []
    reasons = []
    languages = {value.lower() for value in preference.get("preferred_languages") or []}
    if (project.get("language") or "").lower() in languages:
        reasons.append(f"语言匹配当前偏好：{project.get('language') or ''}。")
    text = _comparison_project_text(project)
    matched_topics = [topic for topic in preference.get("preferred_topics") or [] if topic and topic.lower() in text]
    if matched_topics:
        reasons.append(f"关键词匹配当前偏好：{', '.join(matched_topics[:5])}。")
    return reasons


def _comparison_project_cautions(project: dict[str, Any], missing: list[str]) -> list[str]:
    cautions = []
    if _int_value(project.get("security_flag_count")):
        cautions.append(f"该项目仍有 {_int_value(project.get('security_flag_count'))} 条风险提示，需要人工复核。")
    if project.get("latest_quality_level") and project.get("latest_quality_level") != "good":
        cautions.append(f"最新质量等级为 {project.get('latest_quality_level')}，建议查看质量提示。")
    if missing:
        cautions.append(f"未找到项目：{', '.join(missing)}。")
    return cautions or ["暂未发现额外注意事项。"]


def _comparison_summary(projects: list[dict[str, Any]], missing: list[str]) -> list[str]:
    if not projects:
        return ["没有找到可对比的项目。"]
    summary = [f"已找到 {len(projects)} 个可对比项目。"]
    languages = _summary_text(_summary_counts(project.get("language") or "unknown" for project in projects))
    categories = _summary_text(_summary_counts(project.get("category") or "Other" for project in projects))
    summary.append(f"语言分布：{languages}。")
    summary.append(f"方向分布：{categories}。")
    best = _comparison_best_by(projects)
    if best.get("highest_total_star_growth"):
        summary.append(f"累计新增 Star 最高：{best['highest_total_star_growth']}。")
    if best.get("best_trending_rank"):
        summary.append(f"最好 Trending 排名：{best['best_trending_rank']}。")
    if missing:
        summary.append(f"未找到 {len(missing)} 个项目：{'、'.join(missing)}。")
    return summary


def _snippet(text: str, terms: list[str], size: int = 180) -> str:
    if not text:
        return ""
    lower_text = text.lower()
    positions = [lower_text.find(term.lower()) for term in terms if term and lower_text.find(term.lower()) >= 0]
    start = max(0, min(positions) - 40) if positions else 0
    snippet = text[start : start + size].strip()
    if start > 0:
        snippet = "..." + snippet
    if start + size < len(text):
        snippet += "..."
    return snippet


def _search_summary(results: list[dict[str, Any]], terms: list[str]) -> list[str]:
    if not results:
        return [f"没有找到同时匹配 {'、'.join(terms)} 的项目语料。"]
    top_languages = _summary_counts(result.get("language") or "unknown" for result in results)
    top_categories = _summary_counts(result.get("category") or "Other" for result in results)
    return [
        f"命中 {len(results)} 条项目语料，关键词：{'、'.join(terms)}。",
        f"主要语言：{_summary_text(top_languages)}。",
        f"主要方向：{_summary_text(top_categories)}。",
    ]


def _summary_counts(values: Any) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for value in values:
        name = str(value or "unknown")
        counts[name] = counts.get(name, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:3]


def _summary_text(items: list[tuple[str, int]]) -> str:
    return "、".join(f"{name}({count})" for name, count in items) if items else "无"


def _subscription_from_row(row: Any) -> dict[str, Any]:
    payload = _json_object(row["payload_json"])
    return {
        "subscription_id": row["subscription_id"],
        "name": row["name"],
        "status": row["status"],
        "profile": row["profile"],
        "language": row["language"],
        "category": row["category"],
        "query": row["query"],
        "sort": row["sort"],
        "limit": _int_value(row["limit_count"]),
        "channels": _list_strings(_json_list(row["channels_json"])),
        "full_names": _list_strings(payload.get("full_names")),
        "event_types": _list_strings(payload.get("event_types")),
        "min_severity": str(payload.get("min_severity") or "info"),
        "frequency": str(payload.get("frequency") or "immediate"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "payload": payload,
    }


def _subscription_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sort = str(payload.get("sort") or "score").strip()
    if sort not in {"recent", "position", "score", "star-growth", "trending", "quality"}:
        sort = "score"
    status = str(payload.get("status") or "enabled").strip().lower()
    if status not in {"enabled", "disabled"}:
        status = "enabled"
    channels = [
        channel
        for channel in _list_strings(payload.get("channels"))
        if channel.lower() in {"telegram", "feishu", "wechat", "wecom"}
    ]
    limit = _positive_int(payload.get("limit") or payload.get("limit_count")) or 20
    limit = max(1, min(limit, 50))
    profile = str(payload.get("profile") or "").strip()[:80]
    language = str(payload.get("language") or "").strip()[:80]
    category = str(payload.get("category") or "").strip()[:120]
    query = str(payload.get("query") or "").strip()[:160]
    name = str(payload.get("name") or "").strip()[:120]
    full_names = _normalize_project_list(payload.get("full_names") or payload.get("projects") or [])[:50]
    event_types = [
        item for item in _list_strings(payload.get("event_types"))
        if item in {
            "trending_entered", "star_growth_spike", "quality_changed", "risk_added",
            "risk_resolved", "release_detected", "agent_decision_changed",
        }
    ]
    min_severity = str(payload.get("min_severity") or "info").strip().lower()
    if min_severity not in {"info", "low", "medium", "high", "critical"}:
        min_severity = "info"
    frequency = str(payload.get("frequency") or "immediate").strip().lower()
    if frequency not in {"immediate", "daily", "weekly"}:
        frequency = "immediate"
    if not name:
        name = profile or language or category or query or "默认订阅"
    return {
        "subscription_id": str(payload.get("subscription_id") or "").strip(),
        "name": name,
        "status": status,
        "profile": profile,
        "language": language,
        "category": category,
        "query": query,
        "sort": sort,
        "limit": limit,
        "channels": channels or ["telegram"],
        "full_names": full_names,
        "event_types": event_types,
        "min_severity": min_severity,
        "frequency": frequency,
        "created_at": str(payload.get("created_at") or ""),
        "updated_at": str(payload.get("updated_at") or ""),
    }


def _subscription_id(data: dict[str, Any]) -> str:
    if data.get("subscription_id"):
        return str(data["subscription_id"])
    text = json.dumps(
        {
            "name": data.get("name") or "",
            "profile": data.get("profile") or "",
            "language": data.get("language") or "",
            "category": data.get("category") or "",
            "query": data.get("query") or "",
            "channels": data.get("channels") or [],
            "full_names": data.get("full_names") or [],
            "event_types": data.get("event_types") or [],
            "min_severity": data.get("min_severity") or "info",
            "frequency": data.get("frequency") or "immediate",
            "created_at": data.get("created_at") or "",
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return "sub:" + sha1(text.encode("utf-8")).hexdigest()[:12]


def _project_feedback_payload(payload: dict[str, Any]) -> dict[str, Any]:
    rating = _int_value(payload.get("rating"))
    rating = max(-2, min(rating, 2))
    labels = _list_strings(payload.get("labels"))
    return {
        "feedback_id": str(payload.get("feedback_id") or "").strip(),
        "full_name": _normalize_full_name(str(payload.get("full_name") or payload.get("repo") or ""))[:180],
        "profile": str(payload.get("profile") or "").strip()[:80],
        "rating": rating,
        "labels": labels[:12],
        "note": str(payload.get("note") or "").strip()[:500],
        "source": str(payload.get("source") or "api").strip()[:80],
        "created_at": str(payload.get("created_at") or ""),
        "updated_at": str(payload.get("updated_at") or ""),
    }


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _project_agent_task_payload(payload: dict[str, Any], *, full_name: str = "") -> dict[str, Any]:
    task_type = str(payload.get("task_type") or "observe").strip()
    status = str(payload.get("status") or "planned").strip()
    return {
        "task_id": str(payload.get("task_id") or "").strip()[:120],
        "full_name": _normalize_full_name(full_name or str(payload.get("full_name") or payload.get("repo") or ""))[:180],
        "profile": str(payload.get("profile") or "").strip()[:80],
        "task_type": task_type,
        "priority": max(1, min(_int_value(payload.get("priority")) or 3, 5)),
        "status": status,
        "reason": str(payload.get("reason") or "").strip()[:1000],
        "result_summary": str(payload.get("result_summary") or "").strip()[:2000],
        "source": str(payload.get("source") or "api").strip()[:80],
        "dedupe_key": str(payload.get("dedupe_key") or "").strip()[:300],
        "created_at": str(payload.get("created_at") or ""),
        "updated_at": str(payload.get("updated_at") or ""),
        "started_at": str(payload.get("started_at") or ""),
        "finished_at": str(payload.get("finished_at") or ""),
        "payload": payload.get("payload") if isinstance(payload.get("payload"), dict) else {},
    }


def _project_agent_task_validation_error(data: dict[str, Any]) -> str:
    if not data.get("full_name"):
        return "full_name 不能为空。"
    if data.get("task_type") not in PROJECT_AGENT_TASK_TYPES:
        return "不支持的任务类型。"
    if data.get("status") not in PROJECT_AGENT_TASK_STATUSES:
        return "不支持的任务状态。"
    if not data.get("reason"):
        return "reason 不能为空。"
    return ""


def _project_agent_task_dedupe_key(data: dict[str, Any]) -> str:
    stable = json.dumps(
        {
            "full_name": str(data.get("full_name") or "").lower(),
            "profile": data.get("profile") or "",
            "task_type": data.get("task_type") or "observe",
            "reason": data.get("reason") or "",
            "source": data.get("source") or "api",
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return "agent-task-dedupe:" + sha1(stable.encode("utf-8")).hexdigest()[:20]


def _project_agent_task_id(data: dict[str, Any]) -> str:
    stable = f"{data.get('dedupe_key') or _project_agent_task_dedupe_key(data)}:{data.get('created_at') or ''}"
    return "agent-task:" + sha1(stable.encode("utf-8")).hexdigest()[:16]


def _project_agent_task_from_row(row: Any) -> dict[str, Any]:
    task = {
        "task_id": row["task_id"],
        "full_name": row["full_name"],
        "profile": row["profile"],
        "task_type": row["task_type"],
        "priority": _int_value(row["priority"]),
        "status": row["status"],
        "reason": row["reason"],
        "result_summary": row["result_summary"],
        "source": row["source"],
        "dedupe_key": row["dedupe_key"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "payload": _json_object(row["payload_json"]),
    }
    if "latest_result_json" in row.keys():
        task["latest_execution"] = _json_object(row["latest_result_json"])
    return task


def _project_agent_task_summary(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    repositories: set[str] = set()
    for task in tasks:
        status = str(task.get("status") or "planned")
        task_type = str(task.get("task_type") or "observe")
        status_counts[status] = status_counts.get(status, 0) + 1
        type_counts[task_type] = type_counts.get(task_type, 0) + 1
        if task.get("full_name"):
            repositories.add(str(task["full_name"]))
    return {
        "total_count": len(tasks),
        "active_count": sum(status_counts.get(status, 0) for status in ("planned", "in_progress")),
        "repository_count": len(repositories),
        "status_counts": status_counts,
        "type_counts": type_counts,
    }


def _project_agent_tasks_by_full_name(tasks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for task in tasks:
        key = str(task.get("full_name") or "").lower()
        if key:
            grouped.setdefault(key, []).append(task)
    return grouped


def _project_next_actions(project: dict[str, Any], tasks: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    active = [task for task in tasks or [] if task.get("status") in {"planned", "in_progress"}]
    if active:
        return [
            {
                "task_id": task.get("task_id") or "",
                "task_type": task.get("task_type") or "observe",
                "priority": _int_value(task.get("priority")) or 3,
                "status": task.get("status") or "planned",
                "reason": task.get("reason") or "",
                "source": task.get("source") or "task_memory",
                "subscription_action": _json_object_value(task.get("payload"), "subscription_action"),
            }
            for task in active[:3]
        ]
    profile = project.get("project_profile") if isinstance(project.get("project_profile"), dict) else {}
    risks = _list_strings(profile.get("risks")) or _list_strings(project.get("security_flags"))
    quality_score = _int_value(project.get("quality_score"))
    if risks:
        action = {
            "task_id": "",
            "task_type": "review_risk",
            "priority": 1,
            "status": "suggested",
            "reason": f"复查项目档案中的 {len(risks)} 个风险点，并记录风险变化。",
            "source": "recommendation_agent",
            "subscription_action": "watch",
        }
    elif quality_score >= 80:
        action = {
            "task_id": "",
            "task_type": "deep_analysis",
            "priority": 2,
            "status": "suggested",
            "reason": "质量信号较强，建议验证核心能力、维护活跃度和真实落地场景。",
            "source": "recommendation_agent",
            "subscription_action": "notify",
        }
    else:
        action = {
            "task_id": "",
            "task_type": "continue_tracking",
            "priority": 3,
            "status": "suggested",
            "reason": str(profile.get("tracking_reason") or "持续观察 Star 增量、版本发布和风险变化。"),
            "source": "recommendation_agent",
            "subscription_action": "watch",
        }
    completed_types = {
        str(task.get("task_type") or "")
        for task in tasks or []
        if task.get("status") == "completed"
        and isinstance(task.get("latest_execution"), dict)
        and task["latest_execution"].get("decision")
    }
    completed_decisions = {
        str(task["latest_execution"].get("decision") or "")
        for task in tasks or []
        if task.get("status") == "completed" and isinstance(task.get("latest_execution"), dict)
    }
    if "ignore" in completed_decisions:
        return []
    actions = [] if action["task_type"] in completed_types else [action]
    if _int_value(project.get("recommendation_score")) >= 70 and action["task_type"] != "review_risk":
        notify_completed = "notify" in completed_types or "subscription_candidate" in completed_decisions
        if not notify_completed:
            actions.append(
            {
                "task_id": "",
                "task_type": "notify",
                "priority": 2,
                "status": "suggested",
                "reason": "推荐分较高，可进入订阅推送候选队列。",
                "source": "recommendation_agent",
                "subscription_action": "notify",
            }
            )
    return actions


def _json_object_value(value: Any, key: str) -> Any:
    return value.get(key) if isinstance(value, dict) else ""


def _project_feedback_id(data: dict[str, Any]) -> str:
    if data.get("feedback_id"):
        return str(data["feedback_id"])
    text = json.dumps(
        {
            "full_name": data.get("full_name") or "",
            "profile": data.get("profile") or "",
            "rating": data.get("rating") or 0,
            "labels": data.get("labels") or [],
            "note": data.get("note") or "",
            "source": data.get("source") or "",
            "created_at": data.get("created_at") or "",
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return "feedback:" + sha1(text.encode("utf-8")).hexdigest()[:16]


def _project_feedback_from_row(row: Any) -> dict[str, Any]:
    payload = _json_object(row["payload_json"])
    return {
        "feedback_id": row["feedback_id"],
        "full_name": row["full_name"],
        "profile": row["profile"],
        "rating": _int_value(row["rating"]),
        "labels": _list_strings(_json_list(row["labels_json"])),
        "note": row["note"],
        "source": row["source"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "payload": payload,
    }


def _project_feedback_summary(feedback: list[dict[str, Any]]) -> dict[str, Any]:
    rating_counts: dict[str, int] = {}
    profile_counts: dict[str, int] = {}
    label_counts: dict[str, int] = {}
    repository_counts: dict[str, int] = {}
    total_rating = 0
    for item in feedback:
        rating = _int_value(item.get("rating"))
        total_rating += rating
        rating_counts[str(rating)] = rating_counts.get(str(rating), 0) + 1
        profile = str(item.get("profile") or "default")
        profile_counts[profile] = profile_counts.get(profile, 0) + 1
        full_name = str(item.get("full_name") or "")
        if full_name:
            repository_counts[full_name] = repository_counts.get(full_name, 0) + 1
        for label in _list_strings(item.get("labels")):
            label_counts[label] = label_counts.get(label, 0) + 1
    count = len(feedback)
    return {
        "total_count": count,
        "average_rating": round(total_rating / count, 2) if count else 0,
        "rating_counts": rating_counts,
        "profile_counts": profile_counts,
        "label_counts": label_counts,
        "repository_counts": repository_counts,
        "ready_for_preference_memory": count > 0,
    }


def _feedback_memory_by_full_name(feedback: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for item in feedback:
        full_name = _normalize_full_name(str(item.get("full_name") or ""))
        if not full_name:
            continue
        entry = grouped.setdefault(
            full_name.lower(),
            {
                "full_name": full_name,
                "count": 0,
                "rating_total": 0,
                "latest_rating": 0,
                "labels": [],
                "latest_note": "",
                "latest_updated_at": "",
            },
        )
        rating = _int_value(item.get("rating"))
        entry["count"] += 1
        entry["rating_total"] += rating
        updated_at = str(item.get("updated_at") or item.get("created_at") or "")
        if updated_at >= str(entry.get("latest_updated_at") or ""):
            entry["latest_updated_at"] = updated_at
            entry["latest_rating"] = rating
            entry["latest_note"] = str(item.get("note") or "")
        labels = _list_strings(item.get("labels"))
        entry["labels"] = _unique_strings([*entry.get("labels", []), *labels])[:12]
    for entry in grouped.values():
        count = _int_value(entry.get("count"))
        entry["average_rating"] = round(_int_value(entry.get("rating_total")) / count, 2) if count else 0
        entry["preference_adjustment"] = _feedback_preference_adjustment(entry)
        entry.pop("rating_total", None)
    return grouped


def _feedback_preference_adjustment(memory: dict[str, Any]) -> int:
    average_rating = float(memory.get("average_rating") or 0)
    latest_rating = _int_value(memory.get("latest_rating"))
    count = _int_value(memory.get("count"))
    base = int(round((average_rating * 12) + (latest_rating * 4)))
    confidence = min(count, 5)
    return max(-40, min(40, base + confidence))


def _apply_feedback_memory(
    projects: list[dict[str, Any]],
    feedback_memory: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    enriched = []
    for project in projects:
        full_name = _normalize_full_name(str(project.get("full_name") or ""))
        memory = feedback_memory.get(full_name.lower()) if full_name else None
        item = dict(project)
        adjustment = _int_value(memory.get("preference_adjustment")) if memory else 0
        ranking_factors = _recommendation_ranking_factors(item, memory)
        recommendation_score = sum(ranking_factors.values())
        item["ranking_factors"] = ranking_factors
        item["recommendation_score"] = recommendation_score
        item["preference_score"] = ranking_factors["preference_score"]
        item["feedback_reason"] = _feedback_recommendation_reason(memory)
        item["rag_reason"] = _rag_recommendation_reason(item)
        item["recommendation_reason"] = _recommendation_reason(item, ranking_factors)
        if memory:
            item["feedback_memory"] = {
                "count": _int_value(memory.get("count")),
                "average_rating": memory.get("average_rating") or 0,
                "latest_rating": _int_value(memory.get("latest_rating")),
                "labels": _list_strings(memory.get("labels")),
                "latest_note": str(memory.get("latest_note") or ""),
                "preference_adjustment": adjustment,
            }
        enriched.append(item)
    return sorted(
        enriched,
        key=lambda project: (
            _int_value(project.get("recommendation_score")),
            _int_value(project.get("preference_score")),
            _int_value(project.get("score")),
            _int_value(project.get("star_growth")),
            -(_int_value(project.get("trending_rank")) or 9999),
        ),
        reverse=True,
    )


def _recommendation_ranking_factors(project: dict[str, Any], memory: dict[str, Any] | None) -> dict[str, int]:
    base_score = min(40, max(0, _int_value(project.get("score"))))
    quality_score = min(25, max(0, _int_value(project.get("quality_score")) // 4))
    star_growth = _int_value(project.get("star_growth"))
    trending_rank = _int_value(project.get("trending_rank"))
    trend_score = min(25, max(0, star_growth // 10))
    if trending_rank:
        trend_score += max(0, 16 - min(trending_rank, 15))
    rag_relevance_score = _recommendation_rag_score(project)
    preference_score = _int_value(memory.get("preference_adjustment")) if memory else 0
    tracking_score = _recommendation_tracking_score(memory)
    risk_penalty = -min(30, len(_list_strings(project.get("security_flags"))) * 8)
    return {
        "base_score": base_score,
        "quality_score": quality_score,
        "trend_score": trend_score,
        "rag_relevance_score": rag_relevance_score,
        "preference_score": preference_score,
        "tracking_score": tracking_score,
        "risk_penalty": risk_penalty,
    }


def _recommendation_rag_score(project: dict[str, Any]) -> int:
    profile = project.get("project_profile") if isinstance(project.get("project_profile"), dict) else {}
    if profile:
        score = 10
        for key in ["project_positioning", "quality_summary", "tracking_reason", "agent_judgement"]:
            if str(profile.get(key) or "").strip():
                score += 3
        for key in ["use_cases", "strengths", "risks"]:
            score += min(3, len(_list_strings(profile.get(key))))
        return min(24, score)
    reasons = " ".join(_list_strings(project.get("selection_reasons"))).lower()
    description = str(project.get("description") or "").lower()
    category = str(project.get("category") or "").lower()
    text = " ".join([str(project.get("full_name") or "").lower(), description, category, reasons])
    score = 8 if text else 0
    for term in ["rag", "agent", "llm", "workflow", "tool", "retrieval", "embedding"]:
        if term in text:
            score += 3
    if _list_strings(project.get("selection_reasons")):
        score += 4
    return min(24, score)


def _recommendation_tracking_score(memory: dict[str, Any] | None) -> int:
    if not memory:
        return 0
    labels = {label.lower() for label in _list_strings(memory.get("labels"))}
    latest_rating = _int_value(memory.get("latest_rating"))
    if "watch" in labels or "tracking" in labels or "continue_tracking" in labels:
        return 12
    if latest_rating > 0 and ("useful" in labels or "agent" in labels):
        return 6
    return 0


def _feedback_recommendation_reason(memory: dict[str, Any] | None) -> str:
    if not memory:
        return "暂无该项目的反馈记忆，当前排序主要依据热度、质量、RAG 相关性和风险信号。"
    adjustment = _int_value(memory.get("preference_adjustment"))
    labels = "、".join(_list_strings(memory.get("labels"))[:4])
    latest_rating = _int_value(memory.get("latest_rating"))
    if adjustment > 0:
        return f"历史反馈偏正向，最近评分 {latest_rating}，因此推荐排序被提升。" + (f" 标签：{labels}。" if labels else "")
    if adjustment < 0:
        return f"历史反馈偏负向，最近评分 {latest_rating}，因此推荐排序被降低。" + (f" 标签：{labels}。" if labels else "")
    return "已有反馈记录，但整体偏好影响接近中性。"


def _rag_recommendation_reason(project: dict[str, Any]) -> str:
    profile = project.get("project_profile") if isinstance(project.get("project_profile"), dict) else {}
    if profile:
        judgement = str(profile.get("agent_judgement") or "").strip()
        tracking = str(profile.get("tracking_reason") or "").strip()
        positioning = str(profile.get("project_positioning") or "").strip()
        parts = _unique_strings([positioning, judgement, tracking])
        return "项目 RAG 档案显示：" + " ".join(parts[:3])
    score = _recommendation_rag_score(project)
    category = str(project.get("category") or "未分类")
    if score >= 18:
        return f"项目描述、方向或入选理由与 {category} 主题高度相关，可进入项目 RAG 档案继续检索解释。"
    if score >= 10:
        return f"项目已有摘要和入选理由可用于 RAG 召回，当前与 {category} 方向存在中等相关性。"
    return "当前 RAG 相关信号较弱，后续需要更多 README、历史解释或用户反馈补充判断。"


def _recommendation_reason(project: dict[str, Any], factors: dict[str, int]) -> str:
    reasons = []
    if _int_value(project.get("quality_score")):
        reasons.append(f"质量分 {_int_value(project.get('quality_score'))}")
    if _int_value(project.get("star_growth")):
        reasons.append(f"新增 Star {_int_value(project.get('star_growth'))}")
    if _int_value(project.get("trending_rank")):
        reasons.append(f"Trending 第 {_int_value(project.get('trending_rank'))} 位")
    if factors.get("preference_score", 0) > 0:
        reasons.append("用户反馈提升")
    elif factors.get("preference_score", 0) < 0:
        reasons.append("用户反馈降低")
    if factors.get("risk_penalty", 0) < 0:
        reasons.append("存在风险扣分")
    return "；".join(reasons) + "。" if reasons else "基于综合热度、质量信号和历史入选记录推荐。"


def _project_profile_from_project(project: dict[str, Any], memory: dict[str, Any] | None = None) -> dict[str, Any]:
    security_flags = _list_strings(project.get("security_flags"))
    quality_flags = _list_strings(project.get("quality_flags"))
    selection_reasons = _list_strings(project.get("selection_reasons"))
    quality_score = _int_value(project.get("quality_score"))
    star_growth = _int_value(project.get("star_growth"))
    trending_rank = _int_value(project.get("trending_rank"))
    full_name = str(project.get("full_name") or "")
    category = str(project.get("category") or "未分类")
    language = str(project.get("language") or "未知语言")
    positioning = str(project.get("description") or "").strip() or f"{full_name} 是一个 {category} 方向的 {language} 项目。"
    use_cases = _unique_strings(
        [
            f"用于评估 {category} 方向的开源方案。" if category else "",
            f"适合关注 {language} 技术栈的开发者。" if language else "",
            "适合继续观察近期 GitHub Trending 热度。" if trending_rank else "",
        ]
    )
    strengths = _unique_strings(
        [
            f"近期新增 Star {star_growth}。" if star_growth else "",
            f"进入 GitHub Trending 第 {trending_rank} 位。" if trending_rank else "",
            f"质量分 {quality_score}。" if quality_score else "",
            *selection_reasons[:3],
        ]
    )
    risks = security_flags or ["暂无明确风险提示。"]
    quality_summary = (
        f"质量分 {quality_score}，等级 {project.get('quality_level') or 'unknown'}。"
        if quality_score
        else "暂无质量分，需继续结合 README、Issue 和 Release 活跃度判断。"
    )
    if quality_flags:
        quality_summary += " 质量提示：" + "；".join(quality_flags[:4])
    tracking_reason = _profile_tracking_reason(
        star_growth=star_growth,
        trending_rank=trending_rank,
        security_flags=security_flags,
        memory=memory,
    )
    return {
        "project_profile": True,
        "project_positioning": positioning,
        "use_cases": use_cases[:6],
        "strengths": strengths[:6],
        "risks": risks[:6],
        "quality_summary": quality_summary,
        "tracking_reason": tracking_reason,
        "rag_summary": f"项目档案覆盖定位、适用场景、优势、风险、质量和历史入选理由，可用于 RAG 检索：{full_name}。",
        "agent_judgement": _profile_agent_judgement(
            quality_score=quality_score,
            star_growth=star_growth,
            trending_rank=trending_rank,
            security_flags=security_flags,
            memory=memory,
        ),
    }


def _project_profile_from_detail(detail: dict[str, Any]) -> dict[str, Any]:
    latest = {}
    history = detail.get("history") if isinstance(detail.get("history"), list) else []
    if history:
        latest = history[0] if isinstance(history[0], dict) else {}
    project = {
        "full_name": detail.get("full_name") or "",
        "description": detail.get("description") or "",
        "language": detail.get("language") or "",
        "category": detail.get("category") or "",
        "star_growth": detail.get("total_star_growth") or latest.get("star_growth") or 0,
        "trending_rank": detail.get("best_trending_rank") or latest.get("trending_rank") or 0,
        "quality_score": detail.get("latest_quality_score") or latest.get("quality_score") or 0,
        "quality_level": detail.get("latest_quality_level") or latest.get("quality_level") or "unknown",
        "selection_reasons": detail.get("selection_reasons") or [],
        "security_flags": detail.get("security_flags") or [],
        "quality_flags": detail.get("quality_flags") or [],
    }
    return _project_profile_from_project(project)


def _merge_project_profile_runtime_signals(
    profile: dict[str, Any],
    feedback_summary: dict[str, Any],
    explanations: list[dict[str, Any]],
) -> dict[str, Any]:
    item = dict(profile)
    average_rating = feedback_summary.get("average_rating")
    if average_rating:
        item["tracking_reason"] = str(item.get("tracking_reason") or "") + f" 用户反馈均分 {average_rating}。"
    if explanations:
        item["rag_summary"] = str(item.get("rag_summary") or "") + f" 已有 {len(explanations)} 条 RAG 解释历史可复用。"
    return item


def _profile_tracking_reason(
    *,
    star_growth: int,
    trending_rank: int,
    security_flags: list[str],
    memory: dict[str, Any] | None,
) -> str:
    labels = {label.lower() for label in _list_strings(memory.get("labels"))} if memory else set()
    if "watch" in labels or "tracking" in labels or "continue_tracking" in labels:
        return "用户已标记继续跟踪，推荐保留在观察池。"
    if security_flags:
        return "存在风险提示，建议谨慎跟踪并先复核许可证、凭据和依赖安全。"
    if trending_rank and trending_rank <= 5:
        return "进入 Trending 前列，建议继续跟踪近期活跃度和社区反馈。"
    if star_growth >= 50:
        return "近期 Star 增长明显，建议继续观察增长是否可持续。"
    return "可作为普通候选项目归档，后续根据反馈和新增信号决定是否继续跟踪。"


def _profile_agent_judgement(
    *,
    quality_score: int,
    star_growth: int,
    trending_rank: int,
    security_flags: list[str],
    memory: dict[str, Any] | None,
) -> str:
    latest_rating = _int_value(memory.get("latest_rating")) if memory else 0
    if latest_rating < 0:
        return "用户反馈偏负向，暂不作为高优先级推荐。"
    if security_flags:
        return "暂不直接作为高优先级推荐，需先复核风险提示。"
    if latest_rating > 0:
        return "用户反馈偏正向，值得继续跟踪并进入订阅摘要候选。"
    if quality_score >= 80 and (star_growth >= 20 or (trending_rank and trending_rank <= 10)):
        return "值得优先研究，可进入推荐和订阅摘要候选。"
    if quality_score >= 60:
        return "具备观察价值，建议结合 README、Issue 和 Release 活跃度继续判断。"
    return "信息不足或质量信号偏弱，建议低优先级跟踪。"


def _feedback_memory_response(feedback: list[dict[str, Any]]) -> dict[str, Any]:
    summary = _project_feedback_summary(feedback)
    return {
        "record_count": summary.get("total_count", 0),
        "average_rating": summary.get("average_rating", 0),
        "label_counts": summary.get("label_counts", {}),
        "repository_counts": summary.get("repository_counts", {}),
        "ready_for_preference_memory": summary.get("ready_for_preference_memory", False),
    }


def _empty_event_memory() -> dict[str, Any]:
    return {"count": 0, "event_types": [], "severity_counts": {}, "latest_event": {}, "latest_detected_at": ""}


def _subscription_event_memory_by_full_name(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for event in events:
        full_name = str(event.get("full_name") or "").lower()
        if not full_name:
            continue
        memory = grouped.setdefault(full_name, _empty_event_memory())
        memory["count"] = _int_value(memory.get("count")) + 1
        event_type = str(event.get("event_type") or "")
        if event_type and event_type not in memory["event_types"]:
            memory["event_types"].append(event_type)
        severity = str(event.get("severity") or "info")
        memory["severity_counts"][severity] = _int_value(memory["severity_counts"].get(severity)) + 1
        detected_at = str(event.get("detected_at") or "")
        if detected_at >= str(memory.get("latest_detected_at") or ""):
            memory["latest_detected_at"] = detected_at
            memory["latest_event"] = {
                "event_id": event.get("event_id") or "", "event_type": event_type,
                "severity": severity, "title": event.get("title") or "",
                "summary": event.get("summary") or "", "detected_at": detected_at,
            }
    return grouped


def _event_memory_response(events: list[dict[str, Any]]) -> dict[str, Any]:
    grouped = _subscription_event_memory_by_full_name(events)
    return {"event_count": len(events), "project_count": len(grouped), "projects": grouped}


def _recommendation_event_reason(memory: dict[str, Any]) -> str:
    if not memory or not _int_value(memory.get("count")):
        return "暂无项目变化事件记忆。"
    latest = memory.get("latest_event") if isinstance(memory.get("latest_event"), dict) else {}
    return (
        f"最近事件：{latest.get('title') or latest.get('event_type') or '项目变化'}"
        f"（{latest.get('severity') or 'info'}），累计 {_int_value(memory.get('count'))} 条变化记录。"
    )


def _project_notification_summary(
    events: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    deliveries: list[dict[str, Any]],
) -> list[str]:
    summaries = [f"检测到 {len(events)} 条项目事件，生成 {len(candidates)} 条推送候选，记录 {len(deliveries)} 次逐渠道投递。"]
    if events:
        latest = events[0]
        summaries.append(f"最近事件：{latest.get('title') or latest.get('event_type')}；{latest.get('summary') or ''}")
    if deliveries:
        succeeded = sum(1 for item in deliveries if item.get("status") == "succeeded")
        failed = sum(1 for item in deliveries if item.get("status") in {"failed", "skipped"})
        summaries.append(f"渠道成功 {succeeded} 次，失败或跳过 {failed} 次。")
    return summaries


def _notification_rag_memory(db_path: Path, query: str, *, limit: int) -> dict[str, Any]:
    lower_query = str(query or "").lower()
    relevant_terms = ("通知", "推送", "订阅", "触发", "notification", "delivery", "subscribe")
    empty = {
        "event_count": 0, "candidate_count": 0, "delivery_count": 0,
        "summary": "", "events": [], "deliveries": [], "evidence": [], "citations": [],
    }
    if not any(term in lower_query for term in relevant_terms):
        return empty
    connection = connect(db_path)
    try:
        initialize(connection)
        rows = connection.execute(
            "SELECT * FROM subscription_events ORDER BY detected_at DESC, event_id DESC LIMIT ?",
            (max(1, min(limit * 5, 100)),),
        ).fetchall()
        all_events = [_subscription_event_row_for_memory(row) for row in rows]
        named = [event for event in all_events if str(event.get("full_name") or "").lower() in lower_query]
        events = (named or all_events)[:max(1, min(limit, 20))]
        event_ids = [event["event_id"] for event in events]
        candidates: list[dict[str, Any]] = []
        deliveries: list[dict[str, Any]] = []
        if event_ids:
            placeholders = ",".join("?" for _ in event_ids)
            candidates = [dict(row) for row in connection.execute(
                f"SELECT candidate_id, subscription_id, event_id, status FROM notification_candidates WHERE event_id IN ({placeholders})",
                event_ids,
            ).fetchall()]
            candidate_ids = [item["candidate_id"] for item in candidates]
            if candidate_ids:
                candidate_placeholders = ",".join("?" for _ in candidate_ids)
                deliveries = [dict(row) for row in connection.execute(
                    f"SELECT delivery_id, candidate_id, subscription_id, event_id, channel, status, attempt_count, finished_at, error FROM notification_deliveries WHERE candidate_id IN ({candidate_placeholders}) ORDER BY finished_at DESC",
                    candidate_ids,
                ).fetchall()]
    finally:
        connection.close()
    evidence = [{
        "evidence_id": f"notification-event:{event['event_id']}", "source_type": "subscription_event",
        "source_id": event["event_id"], "full_name": event["full_name"], "title": event["title"],
        "excerpt": event["summary"], "observed_at": event["detected_at"],
    } for event in events]
    citations = [{
        "citation_id": f"notification-citation:{index}", "evidence_id": item["evidence_id"],
        "title": item["title"], "source_type": item["source_type"], "source_id": item["source_id"],
    } for index, item in enumerate(evidence, start=1)]
    return {
        "event_count": len(events), "candidate_count": len(candidates), "delivery_count": len(deliveries),
        "summary": " ".join(_project_notification_summary(events, candidates, deliveries)),
        "events": events, "deliveries": deliveries, "evidence": evidence, "citations": citations,
    }


def _subscription_event_row_for_memory(row: Any) -> dict[str, Any]:
    return {
        "event_id": row["event_id"], "event_type": row["event_type"], "full_name": row["full_name"],
        "severity": row["severity"], "status": row["status"], "title": row["title"],
        "summary": row["summary"], "detected_at": row["detected_at"],
    }


def _job_matches(
    job: dict[str, Any],
    *,
    status: str | None = None,
    kind: str | None = None,
    profile: str | None = None,
    query: str | None = None,
) -> bool:
    if status and str(job.get("status") or "") != status:
        return False
    if kind and str(job.get("kind") or "") != kind:
        return False

    request = job.get("request") if isinstance(job.get("request"), dict) else {}
    result = job.get("result") if isinstance(job.get("result"), dict) else {}
    if profile and str(request.get("profile") or "").lower() != profile.lower():
        return False
    if query and query.lower() not in _job_search_text(job, request, result):
        return False
    return True


def _job_search_text(job: dict[str, Any], request: dict[str, Any], result: dict[str, Any]) -> str:
    values = [
        job.get("job_id"),
        job.get("run_date"),
        job.get("kind"),
        job.get("status"),
        job.get("error"),
        job.get("report_url"),
        request.get("profile"),
        request.get("language"),
        request.get("category"),
        request.get("query"),
        request.get("sort"),
        request.get("limit"),
        request.get("subscription_id"),
        request.get("subscription_name"),
        result.get("report_url"),
        result.get("telegram_report_url"),
        request.get("trigger_source"),
        request.get("requested_by"),
        request.get("maintenance_action"),
    ]
    values.extend(request.get("sources") or [])
    values.extend(request.get("safety_warnings") or [])
    return " ".join(str(value or "") for value in values).lower()


def _job_request_key(request: dict[str, Any]) -> str:
    return json.dumps(
        {
            "profile": str(request.get("profile") or "").strip(),
            "language": str(request.get("language") or "").strip(),
            "category": str(request.get("category") or "").strip(),
            "source": str(request.get("source") or "").strip(),
            "queries": _list_strings(request.get("queries")),
            "query": str(request.get("query") or "").strip(),
            "sort": str(request.get("sort") or "").strip(),
            "limit": _positive_int(request.get("limit")),
            "subscription_id": str(request.get("subscription_id") or "").strip(),
            "sources": sorted(_list_strings(request.get("sources"))),
            "dry_run": _truthy(request.get("dry_run", True)),
            "confirm_delivery": _truthy(request.get("confirm_delivery")),
            "confirm_execution": _truthy(request.get("confirm_execution")),
            "days_back": _positive_int(request.get("days_back")),
            "rag_limit": _positive_int(request.get("rag_limit")),
            "mode": str(request.get("mode") or "").strip(),
            "model": str(request.get("model") or "").strip(),
            "auto_build": _truthy(request.get("auto_build")),
            "maintenance_action": str(request.get("maintenance_action") or "").strip(),
            "dimensions": _positive_int(request.get("dimensions")),
        },
        ensure_ascii=False,
        sort_keys=True,
    )


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


def _list_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, list):
        return [str(part).strip() for part in value if str(part).strip()]
    return []


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _normalize_full_name(value: str) -> str:
    return value.strip().strip("/")


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _bool_value(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _positive_int(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _recommendation_summary(
    projects: list[dict[str, Any]],
    *,
    profile: str | None,
    language: str | None,
    category: str | None,
    query: str | None,
) -> list[str]:
    filters = []
    if profile:
        filters.append(f"profile={profile}")
    if language:
        filters.append(f"language={language}")
    if category:
        filters.append(f"category={category}")
    if query:
        filters.append(f"query={query}")

    summary = [
        "当前筛选：" + ("、".join(filters) if filters else "全部项目"),
        f"返回 {len(projects)} 个候选项目，排序优先考虑综合分、Trending 和新增 Star。",
    ]
    trending_count = sum(1 for project in projects if _int_value(project.get("trending_rank")) > 0)
    if trending_count:
        summary.append(f"其中 {trending_count} 个项目进入过 GitHub Trending。")
    if projects:
        top = projects[0]
        name = str(top.get("full_name") or "")
        growth = _int_value(top.get("star_growth"))
        reasons = _unique_strings(top.get("selection_reasons") or [])
        reason_text = reasons[0] if reasons else "综合热度最高"
        summary.append(f"当前首选项目是 {name}，新增 Star {growth}，原因：{reason_text}")
    return summary


def _dedupe_projects_by_full_name(projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped = []
    seen = set()
    for project in projects:
        full_name = str(project.get("full_name") or "").lower()
        if not full_name or full_name in seen:
            continue
        seen.add(full_name)
        deduped.append(project)
    return deduped


def _best_trending_rank(projects: list[dict[str, Any]]) -> int:
    ranks = [_int_value(project.get("trending_rank")) for project in projects]
    ranks = [rank for rank in ranks if rank > 0]
    return min(ranks) if ranks else 0


def _project_selection_reasons(history: list[dict[str, Any]]) -> list[str]:
    return _unique_strings(reason for project in history for reason in project.get("selection_reasons") or [])


def _project_trend_summary(history: list[dict[str, Any]]) -> list[str]:
    if not history:
        return []
    ordered = sorted(history, key=lambda project: str(project.get("run_date") or ""))
    total_growth = sum(_int_value(project.get("star_growth")) for project in ordered)
    best_rank = _best_trending_rank(ordered)
    latest = ordered[-1]
    summary = [
        f"历史入选 {len(ordered)} 次，累计新增 Star {total_growth}。",
        f"最近一次入选日期为 {latest.get('run_date') or 'unknown'}。",
    ]
    if best_rank:
        summary.append(f"最好 GitHub Trending 排名为第 {best_rank} 位。")
    if len(ordered) >= 2:
        latest_growth = _int_value(ordered[-1].get("star_growth"))
        previous_growth = _int_value(ordered[-2].get("star_growth"))
        if latest_growth > previous_growth:
            summary.append("最近一次新增 Star 高于上次入选，热度仍在上升。")
        elif latest_growth < previous_growth:
            summary.append("最近一次新增 Star 低于上次入选，热度可能回落。")
        else:
            summary.append("最近两次新增 Star 持平，热度相对稳定。")
    return summary


def _unique_strings(values: Any) -> list[str]:
    output = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            output.append(text)
    return output


def _similarity_score(base: dict[str, Any], candidate: dict[str, Any]) -> int:
    score = 0
    if base.get("language") and base.get("language") == candidate.get("language"):
        score += 4
    if base.get("category") and base.get("category") == candidate.get("category"):
        score += 5
    score += len(set(base.get("sources") or []) & set(candidate.get("sources") or []))
    score += min(4, len(_project_keywords(base) & _project_keywords(candidate)))
    return score


def _project_keywords(project: dict[str, Any]) -> set[str]:
    text = " ".join(
        [
            str(project.get("full_name") or ""),
            str(project.get("description") or ""),
            str(project.get("category") or ""),
            " ".join(str(reason) for reason in project.get("selection_reasons") or []),
        ]
    ).lower()
    return {part for part in text.replace("/", " ").replace("-", " ").replace("_", " ").split() if len(part) >= 3}


def _rank_value(value: Any) -> int:
    rank = _int_value(value)
    return rank if rank > 0 else 9999


def _dev_context_sources(root: Path, *, run_checks: bool, max_command_chars: int) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for relative, title in [
        ("README.md", "README"),
        ("docs/api.md", "API 文档"),
        ("docs/data-contracts.md", "数据契约"),
        ("docs/operation-log.md", "操作日志"),
    ]:
        path = root / relative
        if not path.exists() or not path.is_file():
            continue
        content = _redact_sensitive_text(path.read_text(encoding="utf-8", errors="replace"))
        sources.append(
            _dev_context_source(
                source_type="document",
                source_path=relative,
                title=title,
                content_text=content,
                metadata={"kind": "file", "relative_path": relative, "bytes": len(content.encode("utf-8"))},
            )
        )

    command_specs: list[tuple[str, str, list[str], str]] = [
        ("git_diff", "git diff --stat", ["git", "diff", "--stat"], "Git diff 摘要"),
        ("git_diff", "git diff", ["git", "diff", "--", "README.md", "docs", "src", "scripts", "tests"], "Git diff 详情"),
    ]
    if run_checks:
        command_specs.extend(
            [
                ("test_output", "python -m unittest discover -q", ["python", "-m", "unittest", "discover", "-q"], "单元测试输出"),
                ("security_check", "python scripts/security_check.py", ["python", "scripts/security_check.py"], "安全检查输出"),
            ]
        )
    for source_type, command_text, args, title in command_specs:
        command_result = _run_dev_context_command(root, args, max_chars=max_command_chars)
        sources.append(
            _dev_context_source(
                source_type=source_type,
                source_path=f"command:{command_text}",
                title=title,
                content_text=command_result["content"],
                metadata={
                    "kind": "command",
                    "command": command_text,
                    "exit_code": command_result["exit_code"],
                    "timed_out": command_result["timed_out"],
                },
            )
        )
    return sources


def _dev_context_source(
    *,
    source_type: str,
    source_path: str,
    title: str,
    content_text: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    content = _redact_sensitive_text(content_text or "")
    content_hash = sha1(content.encode("utf-8")).hexdigest()
    return {
        "source_type": source_type,
        "source_path": source_path,
        "title": title,
        "content_hash": content_hash,
        "content_text": content,
        "metadata": metadata,
    }


def _run_dev_context_command(root: Path, args: list[str], *, max_chars: int) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            args,
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
            check=False,
        )
        output = "\n".join(
            [
                f"$ {' '.join(args)}",
                f"exit_code={completed.returncode}",
                completed.stdout or "",
                completed.stderr or "",
            ]
        ).strip()
        return {
            "exit_code": completed.returncode,
            "timed_out": False,
            "content": _redact_sensitive_text(output[:max_chars]),
        }
    except subprocess.TimeoutExpired as exc:
        output = "\n".join(
            [
                f"$ {' '.join(args)}",
                "timed_out=true",
                str(exc.stdout or ""),
                str(exc.stderr or ""),
            ]
        ).strip()
        return {"exit_code": -1, "timed_out": True, "content": _redact_sensitive_text(output[:max_chars])}
    except OSError as exc:
        return {
            "exit_code": -1,
            "timed_out": False,
            "content": _redact_sensitive_text(f"$ {' '.join(args)}\ncommand_error={exc}"),
        }


def _redact_sensitive_text(text: str) -> str:
    value = text or ""
    patterns = [
        r"(?i)(api[_-]?key|token|secret|webhook|chat[_-]?id)(\s*[:=]\s*)([^\s,;]+)",
        r"(?i)(authorization\s*:\s*bearer\s+)([^\s,;]+)",
    ]
    for pattern in patterns:
        value = re.sub(pattern, lambda match: "".join(match.groups()[:-1]) + "[REDACTED]", value)
    return value


def _dev_corpus_id(run_id: str, source: dict[str, Any]) -> str:
    text = json.dumps(
        {
            "run_id": run_id,
            "source_path": source.get("source_path") or "",
            "content_hash": source.get("content_hash") or "",
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return "dev-corpus:" + sha1(text.encode("utf-8")).hexdigest()[:16]


def _dev_context_chunks(
    *,
    corpus_id: str,
    run_id: str,
    source: dict[str, Any],
    created_at: str,
) -> list[dict[str, Any]]:
    content = str(source.get("content_text") or "").strip() or "(empty)"
    raw_chunks = _split_dev_context_text(content)
    chunks = []
    for index, chunk_text in enumerate(raw_chunks):
        chunk_id = "dev-chunk:" + sha1(f"{corpus_id}:{index}:{chunk_text[:120]}".encode("utf-8")).hexdigest()[:18]
        metadata = dict(source.get("metadata") or {})
        metadata.update({"content_hash": source.get("content_hash") or ""})
        chunks.append(
            {
                "chunk_id": chunk_id,
                "corpus_id": corpus_id,
                "run_id": run_id,
                "chunk_index": index,
                "source_type": source.get("source_type") or "",
                "source_path": source.get("source_path") or "",
                "title": source.get("title") or "",
                "chunk_text": chunk_text,
                "token_estimate": max(1, len(chunk_text) // 4),
                "metadata": metadata,
                "created_at": created_at,
            }
        )
    return chunks


def _split_dev_context_text(text: str, *, max_chars: int = 1800) -> list[str]:
    lines = (text or "").splitlines()
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for line in lines:
        line_size = len(line) + 1
        if current and current_size + line_size > max_chars:
            chunks.append("\n".join(current).strip())
            current = []
            current_size = 0
        current.append(line)
        current_size += line_size
    if current:
        chunks.append("\n".join(current).strip())
    return [chunk for chunk in chunks if chunk] or [text[:max_chars]]


def _dev_context_search_fts(
    connection: sqlite3.Connection,
    *,
    terms: list[str],
    source_type: str | None,
    limit: int,
) -> list[Any]:
    return connection.execute(
        """
        SELECT c.*, bm25(dev_chunks_fts) AS fts_rank
        FROM dev_chunks_fts
        JOIN dev_chunks c ON c.chunk_id = dev_chunks_fts.chunk_id
        WHERE dev_chunks_fts MATCH ?
          AND (? = '' OR c.source_type = ?)
        ORDER BY fts_rank ASC, c.created_at DESC
        LIMIT ?
        """,
        (_dev_context_match_query(terms), source_type or "", source_type or "", limit),
    ).fetchall()


def _dev_context_search_like(
    connection: sqlite3.Connection,
    *,
    terms: list[str],
    source_type: str | None,
    limit: int,
) -> list[Any]:
    where = []
    params: list[Any] = []
    for term in terms:
        where.append("LOWER(c.chunk_text || ' ' || c.title || ' ' || c.source_path) LIKE ?")
        params.append(f"%{term.lower()}%")
    if source_type:
        where.append("c.source_type = ?")
        params.append(source_type)
    params.append(limit)
    return connection.execute(
        f"""
        SELECT c.*
        FROM dev_chunks c
        WHERE {' AND '.join(where)}
        ORDER BY c.created_at DESC, c.source_type ASC
        LIMIT ?
        """,
        params,
    ).fetchall()


def _dev_context_match_query(terms: list[str]) -> str:
    return _fts_query(terms)


def _dev_context_result(row: Any, terms: list[str]) -> dict[str, Any]:
    keys = set(row.keys()) if hasattr(row, "keys") else set()
    chunk_text = str(row["chunk_text"] or "")
    return {
        "chunk_id": row["chunk_id"],
        "corpus_id": row["corpus_id"],
        "run_id": row["run_id"],
        "chunk_index": _int_value(row["chunk_index"]),
        "source_type": row["source_type"],
        "source_path": row["source_path"],
        "title": row["title"],
        "snippet": _snippet(chunk_text, terms, size=260) if terms else chunk_text[:260],
        "chunk_text": chunk_text,
        "token_estimate": _int_value(row["token_estimate"]),
        "metadata": _json_object(row["metadata_json"]),
        "created_at": row["created_at"],
        "rank": float(row["fts_rank"]) if "fts_rank" in keys else 0.0,
    }


def _dev_context_corpus_from_row(row: Any) -> dict[str, Any]:
    return {
        "corpus_id": row["corpus_id"],
        "run_id": row["run_id"],
        "source_type": row["source_type"],
        "source_path": row["source_path"],
        "title": row["title"],
        "content_hash": row["content_hash"],
        "metadata": _json_object(row["metadata_json"]),
        "created_at": row["created_at"],
    }


def _dev_context_run_from_row(row: Any) -> dict[str, Any]:
    return {
        "run_id": row["run_id"],
        "status": row["status"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "source_count": _int_value(row["source_count"]),
        "chunk_count": _int_value(row["chunk_count"]),
        "embedding_count": _int_value(row["embedding_count"]),
        "command_count": _int_value(row["command_count"]),
        "error": row["error"],
        "payload": _json_object(row["payload_json"]),
    }


def _dev_context_search_summary(results: list[dict[str, Any]], terms: list[str]) -> list[str]:
    if not results:
        return [f"没有找到匹配 {'、'.join(terms)} 的开发上下文片段。"]
    source_counts = _summary_counts(result.get("source_type") or "unknown" for result in results)
    return [
        f"命中 {len(results)} 条开发上下文片段，关键词：{'、'.join(terms)}。",
        f"主要来源：{_summary_text(source_counts)}。",
    ]


def _dev_context_question_query(question: str) -> str:
    text = question.strip()
    question_type = _dev_context_question_type(text)
    if question_type == "test_diagnosis":
        lower = text.lower()
        for term in ("测试", "失败", "报错", "test", "failed", "error"):
            if term in text or term in lower:
                return term
    query_by_type = {
        "recent_changes": "diff",
        "api_contract": "API",
        "next_step": "下一步",
        "risk_review": "安全",
    }
    return query_by_type.get(question_type, text)


def _dev_context_question_type(question: str) -> str:
    lower = question.lower()
    if any(word in question for word in ["测试", "失败", "报错"]) or any(word in lower for word in ["test", "failed", "error"]):
        return "test_diagnosis"
    if any(word in question for word in ["最近改", "改了什么", "变更"]) or "diff" in lower:
        return "recent_changes"
    if any(word in question for word in ["API", "接口", "数据契约", "契约"]) or any(
        word in lower for word in ["api", "contract", "schema"]
    ):
        return "api_contract"
    if any(word in question for word in ["下一步", "后续", "做什么", "方向"]):
        return "next_step"
    if any(word in question for word in ["安全", "风险", "架构"]) or any(
        word in lower for word in ["security", "risk", "architecture"]
    ):
        return "risk_review"
    return "general"


def _dev_context_evidence_item(item: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "index": index,
        "chunk_id": item.get("chunk_id") or "",
        "run_id": item.get("run_id") or "",
        "source_type": item.get("source_type") or "",
        "source_path": item.get("source_path") or "",
        "title": item.get("title") or "",
        "snippet": item.get("snippet") or "",
    }


def _dev_context_answer(question: str, evidence: list[dict[str, Any]]) -> dict[str, Any]:
    question_type = _dev_context_question_type(question)
    confidence = "high" if len(evidence) >= 3 else "medium" if evidence else "low"
    if not evidence:
        return {
            "question_type": question_type,
            "confidence": "low",
            "answer": "当前没有召回开发上下文证据。请先在管理页执行开发上下文索引，或换一个更具体的问题。",
            "next_actions": [
                "执行 POST /v1/dev-context/index 或在管理页点击“索引开发上下文”。",
                "重新提问时加入关键词，例如测试、API、数据契约、RAG 维护或反馈入口。",
            ],
        }
    handlers = {
        "test_diagnosis": _dev_context_test_answer,
        "recent_changes": _dev_context_changes_answer,
        "api_contract": _dev_context_api_contract_answer,
        "next_step": _dev_context_next_step_answer,
        "risk_review": _dev_context_risk_answer,
    }
    handler = handlers.get(question_type, _dev_context_general_answer)
    answer, next_actions = handler(question, evidence)
    return {
        "question_type": question_type,
        "confidence": confidence,
        "answer": answer,
        "next_actions": next_actions,
    }


def _dev_context_test_answer(question: str, evidence: list[dict[str, Any]]) -> tuple[str, list[str]]:
    test_items = [item for item in evidence if item["source_type"] in {"test_output", "security_check"}]
    target = test_items or evidence[:3]
    status_hint = "；".join(_compact_evidence(item) for item in target[:3])
    return (
        f"根据开发上下文，测试/检查问题优先看 {len(test_items)} 条测试或安全检查证据。关键线索：{status_hint}",
        [
            "先查看 test_output 和 security_check 来源的证据片段。",
            "若输出显示 OK 或安全检查通过，则当前问题更可能是历史问题或文档中的风险提示。",
            "若输出包含 failed/error，先定位对应测试名，再修复最小失败点。",
        ],
    )


def _dev_context_changes_answer(question: str, evidence: list[dict[str, Any]]) -> tuple[str, list[str]]:
    diff_items = [item for item in evidence if item["source_type"] == "git_diff"]
    target = diff_items or evidence[:3]
    return (
        f"最近变更主要来自 {len(diff_items)} 条 Git diff 证据。关键片段：{'; '.join(_compact_evidence(item) for item in target[:3])}",
        [
            "优先审查 Git diff 中的 API、schema、测试和页面生成器改动。",
            "变更稳定后运行单元测试、安全检查和 git diff --check。",
        ],
    )


def _dev_context_api_contract_answer(question: str, evidence: list[dict[str, Any]]) -> tuple[str, list[str]]:
    contract_items = [
        item
        for item in evidence
        if "api" in item["source_path"].lower() or "data-contracts" in item["source_path"].lower() or "schema" in item["snippet"].lower()
    ]
    target = contract_items or evidence[:3]
    return (
        f"API/数据契约相关证据有 {len(contract_items)} 条。当前应检查路由、SQLite 表字段、数据契约和测试是否同步。关键片段：{'; '.join(_compact_evidence(item) for item in target[:3])}",
        [
            "新增或修改 API 时同步 docs/api.md。",
            "新增 SQLite 表或字段时同步 schema.sql、sqlite_store.py、docs/data-contracts.md 和 tests/test_data_contracts.py。",
            "管理页调用新接口后同步 tests/test_build_pages.py。",
        ],
    )


def _dev_context_next_step_answer(question: str, evidence: list[dict[str, Any]]) -> tuple[str, list[str]]:
    return (
        f"下一步应从召回证据中优先处理仍未闭环的开发项。当前证据显示：{'; '.join(_compact_evidence(item) for item in evidence[:3])}",
        [
            "先确认当前目标的 API、页面、测试和文档是否都已同步。",
            "再选择一个闭环小目标推进，避免提前做复杂 UI 或外部服务。",
            "完成后执行单元测试、安全检查、diff 检查、提交并推送。",
        ],
    )


def _dev_context_risk_answer(question: str, evidence: list[dict[str, Any]]) -> tuple[str, list[str]]:
    return (
        f"安全或架构风险需要重点看密钥、写接口鉴权、外部命令和过早复杂化。当前证据：{'; '.join(_compact_evidence(item) for item in evidence[:3])}",
        [
            "确认所有写接口仍使用管理口令边界。",
            "确认索引材料写入前脱敏，且外部命令有超时。",
            "不要引入外部向量库、多用户权限或复杂聊天 UI，除非后续目标明确要求。",
        ],
    )


def _dev_context_general_answer(question: str, evidence: list[dict[str, Any]]) -> tuple[str, list[str]]:
    return (
        f"已基于开发上下文召回 {len(evidence)} 条证据。结论需要人工复核，主要线索：{'; '.join(_compact_evidence(item) for item in evidence[:3])}",
        [
            "先查看 citations 中的来源文件或命令输出。",
            "如果证据不准，换用更具体关键词重新提问。",
        ],
    )


def _compact_evidence(item: dict[str, Any]) -> str:
    snippet = str(item.get("snippet") or "").replace("\n", " ").strip()
    if len(snippet) > 120:
        snippet = snippet[:117] + "..."
    return f"[{item.get('index')}] {item.get('source_type')}/{item.get('title')}: {snippet}"

