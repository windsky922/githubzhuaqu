from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from src.models import RunSummary
from src.rag.embeddings import DEFAULT_DIMENSIONS, MODEL_NAME, build_rag_embeddings
from src.storage.sqlite_store import connect, import_json_archive, initialize, insert_job_event, table_count, upsert_job
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
    _record_job_event(
        database,
        job["job_id"],
        "runner_started",
        "running",
        "本地任务执行器已开始执行 planned 任务。",
        {"request": job.get("request") or {}, "started_at": started_at},
    )

    try:
        request = job.get("request") or {}
        kind = str(job.get("kind") or "weekly_report")
        finished_at = _now()
        result = _execute_job_by_kind(root=root, db_path=database, kind=kind, request=request)
        status = "failed" if result.get("status") == "failed" or result.get("error") else "succeeded"
        _save_job(
            database,
            {
                **job,
                "status": status,
                "run_date": str(result.get("run_date") or job.get("run_date") or ""),
                "started_at": started_at,
                "finished_at": finished_at,
                "result": result,
                "error": str(result.get("error") or ""),
                "payload": {"request": request, "result": result},
            },
        )
        _record_job_event(
            database,
            job["job_id"],
            "runner_finished",
            status,
            "本地任务执行器已完成任务。",
            {"result": result, "finished_at": finished_at},
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
        _record_job_event(
            database,
            job["job_id"],
            "runner_failed",
            "failed",
            "本地任务执行器执行失败。",
            {"error": message, "finished_at": finished_at},
        )
        return {"executed": True, "job_id": job["job_id"], "status": "failed", "error": message}


def _execute_job_by_kind(root: Path, db_path: Path, kind: str, request: dict[str, Any]) -> dict[str, Any]:
    if kind == "weekly_report":
        summary = _execute_weekly_report(request)
        result = _summary_result(summary)
        result["request_context"] = _request_context(request)
        return result
    if kind == "rag_backfill":
        return _execute_rag_backfill(root=root, db_path=db_path, request=request)
    if kind == "rag_corpus_rebuild":
        return _execute_rag_corpus_rebuild(root=root, db_path=db_path, request=request)
    if kind == "rag_corpus_enrichment":
        return _execute_rag_corpus_enrichment(root=root, db_path=db_path, request=request)
    if kind == "rag_embedding_build":
        return _execute_rag_embedding_build(db_path=db_path, request=request)
    if kind == "rag_search_evaluation":
        return _execute_rag_search_evaluation(root=root, db_path=db_path, request=request)
    if kind == "dev_context_index":
        return _execute_dev_context_index(root=root, db_path=db_path, request=request)
    raise ValueError(f"不支持的任务类型：{kind}")


def _execute_weekly_report(request: dict[str, Any]) -> RunSummary:
    dry_run = bool(request.get("dry_run", True))
    days_back = _positive_int(request.get("days_back"))
    profile = str(request.get("profile") or "").strip()
    limit = _positive_int(request.get("limit"))
    env = _request_env(request, profile, limit)
    with _temporary_env(env):
        return run_weekly_report(days_back=days_back, skip_telegram_send=True if dry_run else None)


def _execute_rag_backfill(root: Path, db_path: Path, request: dict[str, Any]) -> dict[str, Any]:
    from src.api.repository import ApiRepository

    repository = ApiRepository(root=root, db_path=db_path)
    result = repository.backfill_rag_explanations(
        limit=_positive_int(request.get("limit")) or 10,
        rag_limit=_positive_int(request.get("rag_limit")) or 8,
        mode=str(request.get("mode") or "fts5"),
        model=str(request.get("model") or "local-hash-v1"),
        auto_build=_bool_value(request.get("auto_build"), False),
        dry_run=_bool_value(request.get("dry_run", True), True),
    )
    processed = result.get("processed") if isinstance(result.get("processed"), list) else []
    return {
        "run_date": _now()[:10],
        "status": result.get("status") or "ok",
        "dry_run": bool(result.get("dry_run")),
        "requested_limit": result.get("requested_limit") or 0,
        "candidate_count": result.get("candidate_count") or 0,
        "processed_count": result.get("processed_count") or 0,
        "coverage_before": result.get("coverage_before") if isinstance(result.get("coverage_before"), dict) else {},
        "processed_repositories": [
            {
                "full_name": item.get("full_name") or "",
                "status": item.get("status") or "",
                "dry_run": bool(item.get("dry_run")),
                "quality_score": item.get("quality_score") or 0,
                "quality_level": item.get("quality_level") or "",
                "explanation_id": item.get("explanation_id") or "",
            }
            for item in processed
            if isinstance(item, dict)
        ],
        "request_context": _request_context(request),
    }


def _execute_rag_corpus_rebuild(root: Path, db_path: Path, request: dict[str, Any]) -> dict[str, Any]:
    dry_run = _bool_value(request.get("dry_run"), True)
    before_counts = _rag_table_counts(db_path)
    selected_count = _selected_archive_count(root)
    if dry_run:
        return {
            "run_date": _now()[:10],
            "status": "ok",
            "dry_run": True,
            "selected_archive_count": selected_count,
            "before_counts": before_counts,
            "after_counts": before_counts,
            "message": "dry_run=true，仅预览 RAG 语料重建任务，未写入 SQLite。",
            "request_context": _request_context(request),
        }

    counts = import_json_archive(root, db_path)
    after_counts = _rag_table_counts(db_path)
    return {
        "run_date": _now()[:10],
        "status": "ok",
        "dry_run": False,
        "selected_archive_count": selected_count,
        "import_counts": counts,
        "before_counts": before_counts,
        "after_counts": after_counts,
        "invalidated_embedding_count": before_counts.get("rag_embeddings", 0),
        "embedding_rebuild_required": after_counts.get("rag_chunks", 0) > 0 and after_counts.get("rag_embeddings", 0) == 0,
        "request_context": _request_context(request),
    }


def _execute_rag_corpus_enrichment(root: Path, db_path: Path, request: dict[str, Any]) -> dict[str, Any]:
    from src.rag.corpus_enrichment import enrich_rag_corpus

    dry_run = _bool_value(request.get("dry_run"), True)
    if dry_run:
        return {
            "run_date": _now()[:10], "status": "ok", "dry_run": True,
            "limit": _positive_int(request.get("limit")) or 10,
            "message": "dry_run=true，仅预览 Kimi 语料增强任务，未调用模型或写入 SQLite。",
            "request_context": _request_context(request),
        }
    result = enrich_rag_corpus(
        db_path=db_path, root=root, limit=_positive_int(request.get("limit")) or 10,
        replace=_bool_value(request.get("replace"), False),
    )
    return {"run_date": _now()[:10], "status": "ok", "dry_run": False, **result, "request_context": _request_context(request)}


def _execute_rag_embedding_build(db_path: Path, request: dict[str, Any]) -> dict[str, Any]:
    dry_run = _bool_value(request.get("dry_run"), True)
    model = str(request.get("model") or MODEL_NAME)
    dimensions = max(8, min(_positive_int(request.get("dimensions")) or DEFAULT_DIMENSIONS, 512))
    before_counts = _rag_table_counts(db_path)
    if dry_run:
        return {
            "run_date": _now()[:10],
            "status": "ok",
            "dry_run": True,
            "model": model,
            "dimensions": dimensions,
            "chunk_count": before_counts.get("rag_chunks", 0),
            "embedding_count": before_counts.get("rag_embeddings", 0),
            "before_counts": before_counts,
            "after_counts": before_counts,
            "message": "dry_run=true，仅预览 RAG embedding 构建任务，未写入 SQLite。",
            "request_context": _request_context(request),
        }

    result = build_rag_embeddings(db_path, model=model, dimensions=dimensions)
    return {
        "run_date": _now()[:10],
        "status": "ok",
        "dry_run": False,
        **result,
        "before_counts": before_counts,
        "after_counts": _rag_table_counts(db_path),
        "request_context": _request_context(request),
    }


def _execute_rag_search_evaluation(root: Path, db_path: Path, request: dict[str, Any]) -> dict[str, Any]:
    from src.api.repository import ApiRepository

    repository = ApiRepository(root=root, db_path=db_path)
    queries = request.get("queries") if isinstance(request.get("queries"), list) else []
    result = repository.rag_search_evaluation(
        queries=[str(item) for item in queries],
        language=str(request.get("language") or "") or None,
        category=str(request.get("category") or "") or None,
        source=str(request.get("source") or "") or None,
        limit=_positive_int(request.get("limit")) or 8,
        model=str(request.get("model") or MODEL_NAME),
        auto_build=_bool_value(request.get("auto_build"), True),
    )
    return {
        "run_date": _now()[:10],
        "status": "ok",
        "schema_version": result.get("schema_version", 1),
        "sample_count": result.get("sample_count", 0),
        "queries": result.get("queries") or [],
        "language": result.get("language") or "",
        "category": result.get("category") or "",
        "source": result.get("source") or "",
        "limit": result.get("limit") or 0,
        "model": result.get("model") or "",
        "auto_build": bool(result.get("auto_build")),
        "aggregate": result.get("aggregate") if isinstance(result.get("aggregate"), dict) else {},
        "summary": result.get("summary") if isinstance(result.get("summary"), list) else [],
        "request_context": _request_context(request),
    }


def _execute_dev_context_index(root: Path, db_path: Path, request: dict[str, Any]) -> dict[str, Any]:
    from src.api.repository import ApiRepository

    repository = ApiRepository(root=root, db_path=db_path)
    result = repository.dev_context_index(
        {
            "run_checks": _bool_value(request.get("run_checks"), False),
            "replace": _bool_value(request.get("replace"), False),
            "max_command_chars": _positive_int(request.get("max_command_chars")) or 120000,
            "requested_by": request.get("requested_by") or "job_runner",
            "trigger_source": request.get("trigger_source") or "dev_context_index_job",
        }
    )
    return {
        "run_date": _now()[:10],
        "status": result.get("status") or "ok",
        "run_id": result.get("run_id") or "",
        "source_count": result.get("source_count") or 0,
        "chunk_count": result.get("chunk_count") or 0,
        "embedding_count": result.get("embedding_count") or 0,
        "command_count": result.get("command_count") or 0,
        "started_at": result.get("started_at") or "",
        "finished_at": result.get("finished_at") or "",
        "run_checks": _bool_value(request.get("run_checks"), False),
        "replace": _bool_value(request.get("replace"), False),
        "request_context": _request_context(request),
    }


def _request_env(request: dict[str, Any], profile: str, limit: int | None) -> dict[str, str]:
    env = {}
    if profile:
        env["INTEREST_PROFILE"] = profile
    for key, env_name in (
        ("language", "INTEREST_LANGUAGE"),
        ("category", "INTEREST_CATEGORY"),
        ("query", "INTEREST_QUERY"),
    ):
        value = str(request.get(key) or "").strip()
        if value:
            env[env_name] = value
    if limit:
        env["MAX_PROJECTS"] = str(limit)
    return env


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


def _record_job_event(
    db_path: Path,
    job_id: str,
    event_type: str,
    status: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> None:
    connection = connect(db_path)
    try:
        initialize(connection)
        insert_job_event(
            connection,
            {
                "job_id": job_id,
                "event_type": event_type,
                "status": status,
                "actor": "job_runner",
                "created_at": _now(),
                "message": message,
                "payload": payload or {},
            },
        )
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


def _request_context(request: dict[str, Any]) -> dict[str, Any]:
    return {
        key: request.get(key)
        for key in (
            "profile",
            "language",
            "category",
            "query",
            "queries",
            "source",
            "sort",
            "limit",
            "subscription_id",
            "subscription_name",
            "days_back",
            "dry_run",
            "rag_limit",
            "mode",
            "model",
            "auto_build",
            "confirm_execution",
            "maintenance_action",
            "coverage_limit",
            "min_gap_count",
            "dimensions",
            "run_checks",
            "replace",
            "max_command_chars",
        )
        if request.get(key) not in (None, "", [])
    }


def _rag_table_counts(db_path: Path) -> dict[str, int]:
    connection = connect(db_path)
    try:
        initialize(connection)
        return {
            name: table_count(connection, name)
            for name in ("project_corpus", "rag_chunks", "rag_embeddings", "rag_explanations")
        }
    finally:
        connection.close()


def _selected_archive_count(root: Path) -> int:
    count = 0
    for path in sorted((root / "data" / "selected").glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        if isinstance(data, list):
            count += len(data)
    return count


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
