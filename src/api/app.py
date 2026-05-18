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

    @app.get("/api/projects/{owner}/{repo}")
    def project_detail(owner: str, repo: str) -> dict[str, Any]:
        return repository.project_detail(f"{owner}/{repo}")

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

    @app.get("/v1/projects/{owner}/{repo}")
    def v1_project_detail(owner: str, repo: str) -> dict[str, Any]:
        return repository.project_detail(f"{owner}/{repo}")

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

    @app.get("/v1/runs")
    def v1_runs() -> dict[str, Any]:
        return repository.runs()

    @app.get("/v1/jobs")
    def v1_jobs(
        status: str | None = Query(default=None, pattern="^(planned|running|succeeded|failed)?$"),
        kind: str | None = Query(default=None, pattern="^(weekly_report)?$"),
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

