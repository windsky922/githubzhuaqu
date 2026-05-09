from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query

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

    @app.get("/api/runs")
    def runs() -> dict[str, Any]:
        return repository.runs()

    @app.get("/api/profiles")
    def profiles() -> dict[str, Any]:
        return repository.profiles()

    @app.get("/api/weekly/latest")
    def latest_weekly() -> dict[str, Any]:
        return repository.latest_weekly()

    return app


app = create_app()

