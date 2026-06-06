from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, Query
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.api.repository import ROOT, ApiRepository


def create_app(root: Path = ROOT, db_path: Path | None = None) -> FastAPI:
    repository = ApiRepository(root=root, db_path=db_path)
    app = FastAPI(title="GitHub Weekly Agent API", version="0.1.0")

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return repository.health()

    @app.get("/api/projects")
    def projects(
        language: str | None = None,
        category: str | None = None,
        profile: str | None = None,
        source: str | None = None,
        risk: str | None = Query(default=None, pattern="^(has|none)?$"),
        quality_level: str | None = Query(default=None, pattern="^(high|medium|low|unknown)?$"),
        min_quality: int | None = Query(default=None, ge=0, le=100),
        trending_top: int | None = Query(default=None, ge=1),
        query: str | None = None,
        limit: int = Query(default=20, ge=1, le=200),
        sort: str = Query(default="recent", pattern="^(recent|position|score|star-growth|trending|quality)$"),
    ) -> dict[str, Any]:
        return repository.projects(
            language=language,
            category=category,
            profile=profile,
            source=source,
            risk=risk,
            quality_level=quality_level,
            min_quality=min_quality,
            trending_top=trending_top,
            query=query,
            limit=limit,
            sort=sort,
        )

    @app.get("/api/recommendations")
    def recommendations(
        language: str | None = None,
        category: str | None = None,
        profile: str | None = None,
        query: str | None = None,
        limit: int = Query(default=20, ge=1, le=200),
        sort: str = Query(default="score", pattern="^(recent|position|score|star-growth|trending|quality)$"),
    ) -> dict[str, Any]:
        return repository.recommendations(
            language=language,
            category=category,
            profile=profile,
            query=query,
            limit=limit,
            sort=sort,
        )

    @app.get("/api/projects/compare")
    def project_compare(
        repos: str = Query(..., min_length=1),
        profile: str | None = None,
        language: str | None = None,
        category: str | None = None,
        query: str | None = None,
    ) -> dict[str, Any]:
        return repository.compare_projects(
            repos,
            profile=profile,
            language=language,
            category=category,
            query=query,
        )

    @app.get("/api/projects/{owner}/{repo}/similar")
    def project_similar(owner: str, repo: str, limit: int = Query(default=10, ge=1, le=50)) -> dict[str, Any]:
        return repository.similar_projects(f"{owner}/{repo}", limit=limit)

    @app.get("/api/projects/{owner}/{repo}")
    def project_detail(owner: str, repo: str) -> dict[str, Any]:
        return repository.project_detail(f"{owner}/{repo}")

    @app.get("/api/runs")
    def runs() -> dict[str, Any]:
        return repository.runs()

    @app.get("/api/profiles")
    def profiles() -> dict[str, Any]:
        return repository.profiles()

    @app.get("/api/weekly/latest")
    def latest_weekly() -> dict[str, Any]:
        return repository.latest_weekly()

    @app.get("/v1/health")
    def v1_health() -> dict[str, Any]:
        return repository.v1_health()

    @app.get("/v1/database/summary")
    def v1_database_summary() -> dict[str, Any]:
        return repository.database_summary()

    @app.get("/v1/database/trends")
    def v1_database_trends(limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
        return repository.database_trends(limit=limit)

    @app.get("/v1/database/facets")
    def v1_database_facets(limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
        return repository.database_facets(limit=limit)

    @app.get("/v1/projects")
    def v1_projects(
        language: str | None = None,
        category: str | None = None,
        profile: str | None = None,
        source: str | None = None,
        risk: str | None = Query(default=None, pattern="^(has|none)?$"),
        quality_level: str | None = Query(default=None, pattern="^(high|medium|low|unknown)?$"),
        min_quality: int | None = Query(default=None, ge=0, le=100),
        trending_top: int | None = Query(default=None, ge=1),
        query: str | None = None,
        limit: int = Query(default=20, ge=1, le=200),
        sort: str = Query(default="recent", pattern="^(recent|position|score|star-growth|trending|quality)$"),
    ) -> dict[str, Any]:
        return repository.projects(
            language=language,
            category=category,
            profile=profile,
            source=source,
            risk=risk,
            quality_level=quality_level,
            min_quality=min_quality,
            trending_top=trending_top,
            query=query,
            limit=limit,
            sort=sort,
        )

    @app.get("/v1/recommendations")
    def v1_recommendations(
        language: str | None = None,
        category: str | None = None,
        profile: str | None = None,
        query: str | None = None,
        limit: int = Query(default=20, ge=1, le=200),
        sort: str = Query(default="score", pattern="^(recent|position|score|star-growth|trending|quality)$"),
    ) -> dict[str, Any]:
        return repository.recommendations(
            language=language,
            category=category,
            profile=profile,
            query=query,
            limit=limit,
            sort=sort,
        )

    @app.get("/v1/projects/compare")
    def v1_project_compare(
        repos: str = Query(..., min_length=1),
        profile: str | None = None,
        language: str | None = None,
        category: str | None = None,
        query: str | None = None,
    ) -> dict[str, Any]:
        return repository.compare_projects(
            repos,
            profile=profile,
            language=language,
            category=category,
            query=query,
        )

    @app.get("/v1/projects/{owner}/{repo}/similar")
    def v1_project_similar(owner: str, repo: str, limit: int = Query(default=10, ge=1, le=50)) -> dict[str, Any]:
        return repository.similar_projects(f"{owner}/{repo}", limit=limit)

    @app.get("/v1/projects/{owner}/{repo}/rag")
    def v1_project_rag(
        owner: str,
        repo: str,
        limit: int = Query(default=8, ge=1, le=30),
        explanation_limit: int = Query(default=5, ge=1, le=50),
        mode: str = "fts5",
        model: str | None = None,
        auto_build: bool = False,
    ) -> dict[str, Any]:
        return repository.project_rag_bundle(
            f"{owner}/{repo}",
            limit=limit,
            explanation_limit=explanation_limit,
            mode=mode,
            model=model or "local-hash-v1",
            auto_build=auto_build,
        )

    @app.get("/v1/projects/{owner}/{repo}")
    def v1_project_detail(owner: str, repo: str) -> dict[str, Any]:
        return repository.project_detail(f"{owner}/{repo}")

    @app.get("/v1/search")
    def v1_search(
        q: str = Query(..., min_length=1),
        language: str | None = None,
        category: str | None = None,
        source: str | None = None,
        limit: int = Query(default=20, ge=1, le=100),
    ) -> dict[str, Any]:
        return repository.search(
            query=q,
            language=language,
            category=category,
            source=source,
            limit=limit,
        )

    @app.get("/v1/rag/corpus")
    def v1_rag_corpus(
        q: str | None = None,
        language: str | None = None,
        category: str | None = None,
        source: str | None = None,
        limit: int = Query(default=20, ge=1, le=100),
    ) -> dict[str, Any]:
        return repository.rag_corpus(
            query=q,
            language=language,
            category=category,
            source=source,
            limit=limit,
        )

    @app.get("/v1/rag/retrieve")
    def v1_rag_retrieve(
        q: str = Query(..., min_length=1),
        language: str | None = None,
        category: str | None = None,
        source: str | None = None,
        limit: int = Query(default=8, ge=1, le=30),
    ) -> dict[str, Any]:
        return repository.rag_retrieve(
            query=q,
            language=language,
            category=category,
            source=source,
            limit=limit,
        )

    @app.get("/v1/rag/vector-search")
    def v1_rag_vector_search(
        q: str = Query(..., min_length=1),
        language: str | None = None,
        category: str | None = None,
        source: str | None = None,
        limit: int = Query(default=8, ge=1, le=30),
        model: str | None = None,
        auto_build: bool = False,
    ) -> dict[str, Any]:
        return repository.rag_vector_search(
            query=q,
            language=language,
            category=category,
            source=source,
            limit=limit,
            model=model or "local-hash-v1",
            auto_build=auto_build,
        )

    @app.get("/v1/rag/hybrid-search")
    def v1_rag_hybrid_search(
        q: str = Query(..., min_length=1),
        language: str | None = None,
        category: str | None = None,
        source: str | None = None,
        limit: int = Query(default=8, ge=1, le=30),
        model: str | None = None,
        auto_build: bool = False,
    ) -> dict[str, Any]:
        return repository.rag_hybrid_search(
            query=q,
            language=language,
            category=category,
            source=source,
            limit=limit,
            model=model or "local-hash-v1",
            auto_build=auto_build,
        )

    @app.get("/v1/rag/search-compare")
    def v1_rag_search_compare(
        q: str = Query(..., min_length=1),
        language: str | None = None,
        category: str | None = None,
        source: str | None = None,
        limit: int = Query(default=8, ge=1, le=30),
        model: str | None = None,
        auto_build: bool = False,
    ) -> dict[str, Any]:
        return repository.rag_search_compare(
            query=q,
            language=language,
            category=category,
            source=source,
            limit=limit,
            model=model or "local-hash-v1",
            auto_build=auto_build,
        )

    @app.get("/v1/rag/search-evaluation")
    def v1_rag_search_evaluation(
        q: list[str] | None = Query(default=None),
        language: str | None = None,
        category: str | None = None,
        source: str | None = None,
        limit: int = Query(default=8, ge=1, le=30),
        model: str | None = None,
        auto_build: bool = False,
    ) -> dict[str, Any]:
        return repository.rag_search_evaluation(
            queries=q,
            language=language,
            category=category,
            source=source,
            limit=limit,
            model=model or "local-hash-v1",
            auto_build=auto_build,
        )

    @app.post("/v1/rag/search-evaluation", status_code=202)
    def v1_persist_rag_search_evaluation(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
        return repository.persist_rag_search_evaluation(payload)

    @app.get("/v1/rag/explain")
    def v1_rag_explain(
        q: str = Query(..., min_length=1),
        language: str | None = None,
        category: str | None = None,
        source: str | None = None,
        limit: int = Query(default=8, ge=1, le=30),
        mode: str = "fts5",
        model: str | None = None,
        auto_build: bool = False,
    ) -> dict[str, Any]:
        return repository.rag_explain(
            query=q,
            language=language,
            category=category,
            source=source,
            limit=limit,
            mode=mode,
            model=model or "local-hash-v1",
            auto_build=auto_build,
        )

    @app.get("/v1/rag/ask")
    def v1_rag_ask(
        q: str = Query(..., min_length=1),
        language: str | None = None,
        category: str | None = None,
        source: str | None = None,
        limit: int = Query(default=8, ge=1, le=30),
        mode: str = "fts5",
        model: str | None = None,
        auto_build: bool = False,
    ) -> dict[str, Any]:
        return repository.rag_ask(
            query=q,
            language=language,
            category=category,
            source=source,
            limit=limit,
            mode=mode,
            model=model or "local-hash-v1",
            auto_build=auto_build,
        )

    @app.get("/v1/rag/explanations")
    def v1_rag_explanations(
        q: str | None = None,
        repo: str | None = None,
        limit: int = Query(default=20, ge=1, le=100),
    ) -> dict[str, Any]:
        return repository.rag_explanations(query=q, repo=repo, limit=limit)

    @app.get("/v1/rag/quality-summary")
    def v1_rag_quality_summary(limit: int = Query(default=10, ge=1, le=50)) -> dict[str, Any]:
        return repository.rag_quality_summary(limit=limit)

    @app.get("/v1/rag/coverage")
    def v1_rag_coverage(limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
        return repository.rag_coverage(limit=limit)

    @app.get("/v1/rag/diagnostics")
    def v1_rag_diagnostics(limit: int = Query(default=10, ge=1, le=50)) -> dict[str, Any]:
        return repository.rag_diagnostics(limit=limit)

    @app.get("/v1/rag/maintenance-report")
    def v1_rag_maintenance_report(limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
        return repository.rag_maintenance_report(limit=limit)

    @app.post("/v1/rag/backfill-explanations", status_code=202)
    def v1_rag_backfill_explanations(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
        return repository.backfill_rag_explanations_from_payload(payload)

    @app.post("/v1/rag/backfill-plan", status_code=202)
    def v1_rag_backfill_plan(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
        return repository.plan_rag_backfill(payload)

    @app.post("/v1/rag/maintenance-plan", status_code=202)
    def v1_rag_maintenance_plan(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
        return repository.plan_rag_maintenance(payload)

    @app.get("/v1/runs")
    def v1_runs() -> dict[str, Any]:
        return repository.runs()

    @app.get("/v1/jobs")
    def v1_jobs(
        status: str | None = Query(default=None, pattern="^(planned|running|succeeded|failed)?$"),
        kind: str | None = Query(
            default=None,
            pattern="^(weekly_report|rag_backfill|rag_corpus_rebuild|rag_embedding_build|rag_search_evaluation)?$",
        ),
        profile: str | None = None,
        query: str | None = None,
        limit: int = Query(default=20, ge=1, le=200),
    ) -> dict[str, Any]:
        return repository.jobs(status=status, kind=kind, profile=profile, query=query, limit=limit)

    @app.get("/v1/subscriptions")
    def v1_subscriptions(
        status: str | None = Query(default=None, pattern="^(enabled|disabled)?$"),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, Any]:
        return repository.subscriptions(status=status, limit=limit)

    @app.get("/v1/subscriptions/{subscription_id:path}/recommendations")
    def v1_subscription_recommendations(
        subscription_id: str,
        limit: int | None = Query(default=None, ge=1, le=200),
    ) -> dict[str, Any]:
        return repository.subscription_recommendations(subscription_id, limit=limit)

    @app.post("/v1/subscriptions/{subscription_id:path}/trigger", status_code=202)
    def v1_trigger_subscription_run(
        subscription_id: str,
        payload: dict[str, Any] | None = Body(default=None),
    ) -> dict[str, Any]:
        return repository.trigger_subscription_run(subscription_id, payload)

    @app.post("/v1/subscriptions", status_code=201)
    def v1_create_subscription(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
        return repository.create_subscription(payload)

    @app.patch("/v1/subscriptions/{subscription_id:path}")
    def v1_update_subscription(
        subscription_id: str,
        payload: dict[str, Any] | None = Body(default=None),
    ) -> dict[str, Any]:
        return repository.update_subscription(subscription_id, payload)

    @app.get("/v1/job-execution-check")
    def v1_job_execution_check(job_id: str = Query(..., min_length=1)) -> dict[str, Any]:
        return repository.job_execution_check(job_id)

    @app.get("/v1/jobs/{job_id}/events")
    def v1_job_events(job_id: str, limit: int = Query(default=100, ge=1, le=500)) -> dict[str, Any]:
        return repository.job_events(job_id, limit=limit)

    @app.post("/v1/jobs/{job_id:path}/execute")
    def v1_execute_job(job_id: str, payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
        return repository.execute_job(job_id, payload)

    @app.post("/v1/jobs/{job_id:path}/retry")
    def v1_retry_job(job_id: str, payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
        return repository.retry_job(job_id, payload)

    @app.get("/v1/jobs/{job_id:path}")
    def v1_job_detail(job_id: str) -> dict[str, Any]:
        return repository.job_detail(job_id)

    @app.post("/v1/runs/trigger", status_code=202)
    def v1_trigger_run(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
        return repository.trigger_run_preview(payload)

    @app.get("/v1/reports/latest")
    def v1_latest_report() -> dict[str, Any]:
        return repository.latest_weekly()

    @app.get("/", include_in_schema=False)
    def local_admin_home() -> RedirectResponse:
        return RedirectResponse(url="/admin.html?api=1")

    docs_dir = root / "docs"
    if docs_dir.exists():
        app.mount("/", StaticFiles(directory=docs_dir, html=True), name="public_docs")

    return app


app = create_app()

