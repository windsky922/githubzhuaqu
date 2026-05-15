from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha1
from pathlib import Path
from typing import Any

from scripts.query_archive import query_archive
from src.job_runner import run_planned_job
from src.storage.sqlite_store import connect, import_json_archive, initialize, insert_job_event, upsert_job

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
                "runs_query": True,
                "jobs_query": True,
                "job_events": True,
                "job_execution_check": True,
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

    def trigger_run_preview(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        profile = str(payload.get("profile") or payload.get("interest_profile") or "").strip()
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

    def profiles(self) -> dict[str, Any]:
        return _read_json_object(
            self.root / "docs" / "profiles.json",
            {"schema_version": 1, "count": 0, "profiles": []},
        )

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


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _best_trending_rank(projects: list[dict[str, Any]]) -> int:
    ranks = [_int_value(project.get("trending_rank")) for project in projects]
    ranks = [rank for rank in ranks if rank > 0]
    return min(ranks) if ranks else 0


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

