from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from src.models import RunSummary
from src.storage.sqlite_store import connect, initialize, upsert_job
from src.weekly_run import run_weekly_report

ROOT = Path(__file__).resolve().parents[1]


def run_planned_job(root: Path = ROOT, db_path: Path | None = None, job_id: str | None = None) -> dict[str, Any]:
    database = db_path or root / "data" / "github_weekly.sqlite"
    job = _load_planned_job(database, job_id)
    if not job:
        return {
            "executed": False,
            "job_id": job_id or "",
            "status": "not_found",
            "message": "没有找到可执行的 planned 任务。",
        }

    started_at = _now()
    _save_job(database, {**job, "status": "running", "started_at": started_at, "error": ""})

    try:
        request = job.get("request") or {}
        summary = _execute_weekly_report(request)
        finished_at = _now()
        result = _summary_result(summary)
        status = "failed" if summary.status == "failed" or summary.error else "succeeded"
        _save_job(
            database,
            {
                **job,
                "status": status,
                "run_date": summary.run_date,
                "started_at": started_at,
                "finished_at": finished_at,
                "result": result,
                "error": summary.error,
                "payload": {"request": request, "result": result},
            },
        )
        return {"executed": True, "job_id": job["job_id"], "status": status, "result": result}
    except Exception as error:
        finished_at = _now()
        message = str(error)
        _save_job(
            database,
            {
                **job,
                "status": "failed",
                "started_at": started_at,
                "finished_at": finished_at,
                "error": message,
                "payload": {"request": job.get("request") or {}, "error": message},
            },
        )
        return {"executed": True, "job_id": job["job_id"], "status": "failed", "error": message}


def _execute_weekly_report(request: dict[str, Any]) -> RunSummary:
    dry_run = bool(request.get("dry_run", True))
    days_back = _positive_int(request.get("days_back"))
    profile = str(request.get("profile") or "").strip()
    with _temporary_env({"INTEREST_PROFILE": profile} if profile else {}):
        return run_weekly_report(days_back=days_back, skip_telegram_send=True if dry_run else None)


def _load_planned_job(db_path: Path, job_id: str | None) -> dict[str, Any]:
    connection = connect(db_path)
    try:
        initialize(connection)
        if job_id:
            row = connection.execute(
                """
                SELECT job_id, kind, status, run_date, submitted_at, started_at, finished_at,
                       request_json, result_json, error, payload_json
                FROM jobs
                WHERE job_id = ? AND status = 'planned'
                """,
                (job_id,),
            ).fetchone()
        else:
            row = connection.execute(
                """
                SELECT job_id, kind, status, run_date, submitted_at, started_at, finished_at,
                       request_json, result_json, error, payload_json
                FROM jobs
                WHERE status = 'planned'
                ORDER BY submitted_at ASC, job_id ASC
                LIMIT 1
                """,
            ).fetchone()
    finally:
        connection.close()
    return _job_from_row(row) if row else {}


def _save_job(db_path: Path, job: dict[str, Any]) -> None:
    connection = connect(db_path)
    try:
        initialize(connection)
        upsert_job(connection, job)
        connection.commit()
    finally:
        connection.close()


def _job_from_row(row: Any) -> dict[str, Any]:
    return {
        "job_id": row["job_id"],
        "kind": row["kind"],
        "status": row["status"],
        "run_date": row["run_date"],
        "submitted_at": row["submitted_at"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "request": _json_object(row["request_json"]),
        "result": _json_object(row["result_json"]),
        "error": row["error"],
        "payload": _json_object(row["payload_json"]),
    }


def _summary_result(summary: RunSummary) -> dict[str, Any]:
    return {
        "run_date": summary.run_date,
        "status": summary.status,
        "selected_count": summary.selected_count,
        "collected_count": summary.collected_count,
        "kimi_used": summary.kimi_used,
        "fallback_used": summary.fallback_used,
        "telegram_sent": summary.telegram_sent,
        "telegram_error": summary.telegram_error,
        "report_path": summary.report_path,
        "report_url": summary.telegram_report_url,
        "sqlite_index_path": summary.sqlite_index_path,
        "sqlite_error": summary.sqlite_error,
        "error": summary.error,
    }


def _json_object(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _positive_int(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


@contextmanager
def _temporary_env(values: dict[str, str]) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in values}
    try:
        for key, value in values.items():
            os.environ[key] = value
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
