from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from hashlib import sha1
from pathlib import Path
from typing import Any

from scripts.query_archive import query_archive
from src.job_runner import run_planned_job
from src.rag.embeddings import MODEL_NAME, build_rag_embeddings, cosine_similarity, hash_embedding, vector_from_json
from src.storage.sqlite_store import (
    connect,
    import_json_archive,
    initialize,
    insert_job_event,
    rebuild_project_corpus,
    table_count,
    upsert_job,
)

ROOT = Path(__file__).resolve().parents[2]


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
                "subscriptions": True,
                "subscription_recommendations": True,
                "subscription_trigger": True,
                "database_summary": True,
                "database_trends": True,
                "database_facets": True,
                "project_search": True,
                "project_similarity": True,
                "project_compare": True,
                "rag_corpus": True,
                "rag_retrieve": True,
                "rag_vector_search": True,
                "rag_explain": True,
                "rag_explanations": True,
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
        projects = self.projects(
            language=language,
            category=category,
            profile=profile,
            query=query,
            limit=limit,
            sort=sort,
        ).get("projects", [])
        projects = _dedupe_projects_by_full_name(projects)
        return {
            "schema_version": 1,
            "profile": _blank_to_none(profile) or "",
            "language": _blank_to_none(language) or "",
            "category": _blank_to_none(category) or "",
            "query": _blank_to_none(query) or "",
            "sort": sort,
            "count": len(projects),
            "selection_summary": _recommendation_summary(
                projects,
                profile=_blank_to_none(profile),
                language=_blank_to_none(language),
                category=_blank_to_none(category),
                query=_blank_to_none(query),
            ),
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
        if normalized_mode in {"vector", "embedding", "semantic"}:
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

    def rag_explanations(self, *, limit: int = 20, query: str | None = None) -> dict[str, Any]:
        self.ensure_sqlite_index()
        limit = max(1, min(int(limit or 20), 100))
        normalized_query = _blank_to_none(query)
        connection = connect(self.db_path)
        try:
            initialize(connection)
            params: list[Any] = []
            where = ""
            if normalized_query:
                where = "WHERE query LIKE ? OR answer LIKE ?"
                like = f"%{normalized_query}%"
                params.extend([like, like])
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
            "explanations": explanations,
        }

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
                "event_records": table_counts.get("job_events", 0),
                "ready_for_text_index": table_counts.get("project_corpus_fts", 0) > 0,
                "ready_for_chunk_retrieval": table_counts.get("rag_chunks_fts", 0) > 0,
                "ready_for_vector_search": table_counts.get("rag_embeddings", 0) > 0,
                "ready_for_explanation_history": table_counts.get("rag_explanations", 0) > 0,
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
        blockers = []
        warnings = []
        if job.get("kind") != "weekly_report":
            blockers.append("当前执行器只支持 weekly_report 任务。")
        if job.get("status") != "planned":
            blockers.append(f"任务状态为 {job.get('status') or 'unknown'}，只有 planned 任务可以被执行器消费。")
        if not _truthy(request.get("dry_run", True)) and not _truthy(request.get("confirm_delivery")):
            blockers.append("dry_run=false 但缺少 confirm_delivery=true，不能进入真实推送执行。")
        if not _truthy(request.get("dry_run", True)):
            warnings.append("该任务允许真实推送，执行前请确认 Telegram/飞书/微信等推送配置正确。")

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
                "dry_run": _truthy(request.get("dry_run", True)),
                "confirm_delivery": _truthy(request.get("confirm_delivery")),
                "days_back": _positive_int(request.get("days_back")),
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
        if job and job.get("kind") != "weekly_report":
            blockers.append("当前只支持 weekly_report 任务重试。")
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
        duplicate = self._find_active_duplicate_job(retry_request)
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
            "kind": "weekly_report",
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

    def create_subscription(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self.ensure_sqlite_index()
        data = _subscription_payload(payload or {})
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        data["created_at"] = now
        data["updated_at"] = now
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

    def _find_active_duplicate_job(self, request: dict[str, Any]) -> dict[str, Any]:
        self.ensure_sqlite_index()
        target_key = _job_request_key(request)
        connection = connect(self.db_path)
        try:
            rows = connection.execute(
                """
                SELECT job_id, kind, status, run_date, submitted_at, started_at, finished_at,
                       request_json, result_json, error, payload_json
                FROM jobs
                WHERE kind = 'weekly_report' AND status IN ('planned', 'running')
                ORDER BY COALESCE(NULLIF(submitted_at, ''), run_date) DESC, job_id DESC
                LIMIT 200
                """
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
            "created_at": data.get("created_at") or "",
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return "sub:" + sha1(text.encode("utf-8")).hexdigest()[:12]


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
            "query": str(request.get("query") or "").strip(),
            "sort": str(request.get("sort") or "").strip(),
            "limit": _positive_int(request.get("limit")),
            "subscription_id": str(request.get("subscription_id") or "").strip(),
            "sources": sorted(_list_strings(request.get("sources"))),
            "dry_run": _truthy(request.get("dry_run", True)),
            "confirm_delivery": _truthy(request.get("confirm_delivery")),
            "days_back": _positive_int(request.get("days_back")),
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

