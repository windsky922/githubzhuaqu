from __future__ import annotations

import json
import os
from pathlib import Path

from .models import Repository, RunSummary
from .settings import Settings
from .storage.sqlite_store import import_json_archive
from .utils import clean_error, ensure_dir


def write_report(report: str, settings: Settings) -> Path:
    reports_dir = settings.root / "reports"
    ensure_dir(reports_dir)
    path = reports_dir / f"{settings.run_date}.md"
    path.write_text(report, encoding="utf-8")
    return path


def write_raw_repositories(repositories: list[Repository], settings: Settings) -> Path:
    raw_dir = settings.root / "data" / "raw"
    ensure_dir(raw_dir)
    path = raw_dir / f"{settings.run_date}.json"
    data = [repo.to_dict() for repo in repositories]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_selected_repositories(repositories: list[Repository], settings: Settings) -> Path:
    selected_dir = settings.root / "data" / "selected"
    ensure_dir(selected_dir)
    path = selected_dir / f"{settings.run_date}.json"
    data = [repo.to_dict() for repo in repositories]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_trend_summary(trend_summary: dict, settings: Settings) -> Path:
    trends_dir = settings.root / "data" / "trends"
    ensure_dir(trends_dir)
    path = trends_dir / f"{settings.run_date}.json"
    path.write_text(json.dumps(trend_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_run_summary(summary: RunSummary, settings: Settings) -> Path:
    runs_dir = settings.root / "data" / "runs"
    ensure_dir(runs_dir)
    path = runs_dir / f"{settings.run_date}.json"
    summary.run_summary_path = _relative(path, settings.root)
    path.write_text(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def sync_sqlite_index(settings: Settings) -> tuple[str, str]:
    if _skip_sqlite_index():
        return "", ""
    path = sqlite_index_path(settings)
    try:
        import_json_archive(settings.root, path)
    except Exception as error:
        return _relative_or_absolute(path, settings.root), clean_error(error)
    return _relative_or_absolute(path, settings.root), ""


def sqlite_index_summary_path(settings: Settings) -> str:
    return _relative_or_absolute(sqlite_index_path(settings), settings.root)


def sqlite_index_path(settings: Settings) -> Path:
    configured = os.getenv("SQLITE_INDEX_PATH", "").strip()
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else settings.root / path
    return settings.root / "data" / "github_weekly.sqlite"


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _relative_or_absolute(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _skip_sqlite_index() -> bool:
    return os.getenv("SKIP_SQLITE_INDEX", "").lower() in {"1", "true", "yes"}
