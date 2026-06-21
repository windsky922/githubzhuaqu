from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from src.storage.sqlite_store import (
    connect,
    initialize,
    rebuild_project_corpus,
    upsert_project_agent_task_run,
)


EXECUTABLE_STATUSES = {"planned", "failed"}
TASK_TYPES = {"observe", "review_risk", "deep_analysis", "continue_tracking", "notify", "ignore"}


@dataclass(frozen=True)
class ProjectAgentTaskExecutionResult:
    execution_summary: str
    decision: str
    confidence: float
    evidence: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    changes: list[dict[str, Any]]
    risk_changes: list[dict[str, Any]]
    recommended_actions: list[str]
    subscription_candidate: dict[str, Any]


def project_agent_task_execution_check(
    db_path: Path,
    task_id: str,
    *,
    retry: bool = False,
) -> dict[str, Any]:
    connection = connect(db_path)
    try:
        initialize(connection)
        task = _task_by_id(connection, task_id)
        running = _running_run(connection, task_id)
        checks = [
            _check("task_exists", bool(task), "任务存在。" if task else "任务不存在。"),
            _check(
                "task_type_supported",
                bool(task and task.get("task_type") in TASK_TYPES),
                "任务类型受支持。" if task and task.get("task_type") in TASK_TYPES else "任务类型不受支持。",
            ),
            _check("no_concurrent_run", not running, "没有并发执行。" if not running else "任务已有运行中的执行记录。"),
        ]
        status = str(task.get("status") or "") if task else ""
        status_allowed = status == "failed" if retry else status == "planned"
        checks.append(
            _check(
                "status_executable",
                status_allowed,
                f"状态 {status} 可执行。" if status_allowed else f"状态 {status or 'unknown'} 不允许执行。",
            )
        )
        if retry:
            retry_allowed = status == "failed"
            checks.append(
                _check(
                    "retry_allowed",
                    retry_allowed,
                    "失败任务可以重试。" if retry_allowed else "只有失败任务可以重试。",
                )
            )
        executable = all(bool(item["passed"]) for item in checks)
        return {
            "schema_version": 1,
            "task_id": task_id,
            "retry": retry,
            "executable": executable,
            "checks": checks,
            "task": task or {},
            "running_run": running or {},
        }
    finally:
        connection.close()


def execute_project_agent_task(
    root: Path,
    db_path: Path,
    task_id: str,
    *,
    retry: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    check = project_agent_task_execution_check(db_path, task_id, retry=retry)
    if dry_run or not check["executable"]:
        return {**check, "dry_run": dry_run, "executed": False}

    connection = connect(db_path)
    run_id = f"agent-run:{uuid4().hex}"
    started_at = _utc_now()
    evidence: list[dict[str, Any]] = []
    citations: list[dict[str, Any]] = []
    input_data: dict[str, Any] = {}
    try:
        initialize(connection)
        connection.execute("BEGIN IMMEDIATE")
        task = _task_by_id(connection, task_id)
        running = _running_run(connection, task_id)
        status = str(task.get("status") or "") if task else ""
        expected_status = "failed" if retry else "planned"
        if not task or running or status != expected_status:
            connection.rollback()
            return {
                **project_agent_task_execution_check(db_path, task_id, retry=retry),
                "dry_run": False,
                "executed": False,
            }
        input_data = {
            "task_id": task_id,
            "task_type": task.get("task_type"),
            "full_name": task.get("full_name"),
            "retry": retry,
        }
        upsert_project_agent_task_run(
            connection,
            {
                "run_id": run_id,
                "task_id": task_id,
                "status": "running",
                "started_at": started_at,
                "input": input_data,
                "payload": {"executor": "project-agent-task-v1"},
            },
        )
        connection.execute(
            """
            UPDATE project_agent_tasks
            SET status = 'in_progress', started_at = ?, finished_at = '', updated_at = ?
            WHERE task_id = ?
            """,
            (started_at, started_at, task_id),
        )
        connection.commit()

        context = _load_project_context(connection, task)
        evidence = _build_evidence(context)
        citations = _build_citations(evidence)
        handler = HANDLERS[str(task["task_type"])]
        result = handler(task, context, evidence, citations)
        result_data = asdict(result)
        finished_at = _utc_now()
        upsert_project_agent_task_run(
            connection,
            {
                "run_id": run_id,
                "task_id": task_id,
                "status": "succeeded",
                "started_at": started_at,
                "finished_at": finished_at,
                "input": input_data,
                "evidence": evidence,
                "citations": citations,
                "result": result_data,
                "payload": {"executor": "project-agent-task-v1"},
            },
        )
        connection.execute(
            """
            UPDATE project_agent_tasks
            SET status = 'completed', result_summary = ?, finished_at = ?, updated_at = ?
            WHERE task_id = ?
            """,
            (result.execution_summary, finished_at, finished_at, task_id),
        )
        rebuild_project_corpus(connection)
        connection.commit()
        return {
            "schema_version": 1,
            "executed": True,
            "dry_run": False,
            "task_id": task_id,
            "run_id": run_id,
            "status": "succeeded",
            "result": result_data,
        }
    except Exception as exc:
        connection.rollback()
        finished_at = _utc_now()
        initialize(connection)
        upsert_project_agent_task_run(
            connection,
            {
                "run_id": run_id,
                "task_id": task_id,
                "status": "failed",
                "started_at": started_at,
                "finished_at": finished_at,
                "input": input_data,
                "evidence": evidence,
                "citations": citations,
                "error": str(exc),
                "payload": {"executor": "project-agent-task-v1"},
            },
        )
        connection.execute(
            """
            UPDATE project_agent_tasks
            SET status = 'failed', result_summary = ?, finished_at = ?, updated_at = ?
            WHERE task_id = ?
            """,
            (f"执行失败：{exc}", finished_at, finished_at, task_id),
        )
        rebuild_project_corpus(connection)
        connection.commit()
        return {
            "schema_version": 1,
            "executed": True,
            "dry_run": False,
            "task_id": task_id,
            "run_id": run_id,
            "status": "failed",
            "error": str(exc),
            "evidence": evidence,
        }
    finally:
        connection.close()


def project_agent_task_runs(
    db_path: Path,
    task_id: str | None = None,
    *,
    full_name: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    connection = connect(db_path)
    try:
        initialize(connection)
        parameters: list[Any] = []
        where = ""
        if task_id:
            where = "WHERE r.task_id = ?"
            parameters.append(task_id)
        elif full_name:
            where = "WHERE LOWER(t.full_name) = LOWER(?)"
            parameters.append(full_name)
        parameters.append(max(1, min(int(limit), 500)))
        rows = connection.execute(
            f"""
            SELECT r.*, t.full_name, t.task_type, t.priority
            FROM project_agent_task_runs r
            LEFT JOIN project_agent_tasks t ON t.task_id = r.task_id
            {where}
            ORDER BY r.started_at DESC, r.run_id DESC
            LIMIT ?
            """,
            parameters,
        ).fetchall()
        runs = [_run_from_row(row) for row in rows]
        counts = {"running": 0, "succeeded": 0, "failed": 0}
        for run in runs:
            status = str(run.get("status") or "")
            if status in counts:
                counts[status] += 1
        return {"schema_version": 1, "count": len(runs), "summary": counts, "runs": runs}
    finally:
        connection.close()


def batch_execute_project_agent_tasks(
    root: Path,
    db_path: Path,
    *,
    limit: int = 3,
    priority: int = 2,
    task_type: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    connection = connect(db_path)
    try:
        initialize(connection)
        clauses = ["status = 'planned'", "priority <= ?"]
        parameters: list[Any] = [max(1, min(priority, 5))]
        if task_type:
            clauses.append("task_type = ?")
            parameters.append(task_type)
        parameters.append(max(1, min(limit, 100)))
        rows = connection.execute(
            f"""
            SELECT task_id FROM project_agent_tasks
            WHERE {' AND '.join(clauses)}
            ORDER BY priority ASC, updated_at ASC, task_id ASC
            LIMIT ?
            """,
            parameters,
        ).fetchall()
        task_ids = [str(row["task_id"]) for row in rows]
    finally:
        connection.close()
    results = [
        execute_project_agent_task(root, db_path, task_id, dry_run=dry_run)
        for task_id in task_ids
    ]
    return {
        "schema_version": 1,
        "dry_run": dry_run,
        "selected_count": len(task_ids),
        "executed_count": sum(1 for item in results if item.get("executed")),
        "results": results,
    }


def _load_project_context(connection: sqlite3.Connection, task: dict[str, Any]) -> dict[str, Any]:
    rows = connection.execute(
        """
        SELECT corpus_id, run_date, full_name, html_url, title, search_text, payload_json
        FROM project_corpus
        WHERE LOWER(full_name) = LOWER(?)
        ORDER BY run_date DESC, corpus_id DESC
        LIMIT 2
        """,
        (task.get("full_name") or "",),
    ).fetchall()
    snapshots = []
    for row in rows:
        snapshots.append({
            "corpus_id": row["corpus_id"],
            "run_date": row["run_date"],
            "full_name": row["full_name"],
            "html_url": row["html_url"],
            "title": row["title"],
            "search_text": row["search_text"],
            "payload": _json_object(row["payload_json"]),
        })
    return {"task": task, "snapshots": snapshots, "latest": snapshots[0] if snapshots else {}}


def _build_evidence(context: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = []
    for index, snapshot in enumerate(context.get("snapshots") or []):
        evidence.append({
            "evidence_id": f"project-snapshot:{snapshot.get('corpus_id')}",
            "source_type": "project_corpus",
            "source_id": snapshot.get("corpus_id") or "",
            "source_path": snapshot.get("html_url") or "",
            "title": f"{snapshot.get('title') or snapshot.get('full_name')}（{snapshot.get('run_date')}）",
            "excerpt": str(snapshot.get("search_text") or "")[:600],
            "observed_at": snapshot.get("run_date") or "",
            "role": "latest" if index == 0 else "previous",
        })
    return evidence


def _build_citations(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "citation_id": f"citation:{index + 1}",
            "evidence_id": item.get("evidence_id") or "",
            "title": item.get("title") or "",
            "source_path": item.get("source_path") or "",
        }
        for index, item in enumerate(evidence)
    ]


def _common_result(
    task: dict[str, Any],
    context: dict[str, Any],
    evidence: list[dict[str, Any]],
    citations: list[dict[str, Any]],
    *,
    decision: str,
    summary: str,
    confidence: float,
    actions: list[str],
    subscription_candidate: dict[str, Any] | None = None,
) -> ProjectAgentTaskExecutionResult:
    latest = (context.get("latest") or {}).get("payload") or {}
    snapshots = context.get("snapshots") or []
    previous = snapshots[1].get("payload") if len(snapshots) > 1 else {}
    changes = _metric_changes(latest, previous or {})
    current_risks = _string_list(latest.get("security_flags")) + _string_list(latest.get("quality_flags"))
    previous_risks = _string_list((previous or {}).get("security_flags")) + _string_list((previous or {}).get("quality_flags"))
    risk_changes = [
        {"change": "added", "risk": risk} for risk in current_risks if risk not in previous_risks
    ] + [
        {"change": "resolved", "risk": risk} for risk in previous_risks if risk not in current_risks
    ]
    return ProjectAgentTaskExecutionResult(
        execution_summary=summary,
        decision=decision,
        confidence=max(0.0, min(confidence, 1.0)),
        evidence=evidence,
        citations=citations,
        changes=changes,
        risk_changes=risk_changes,
        recommended_actions=actions,
        subscription_candidate=subscription_candidate or {"eligible": False, "reason": "当前任务不产生订阅候选。"},
    )


def _observe(task: dict[str, Any], context: dict[str, Any], evidence: list[dict[str, Any]], citations: list[dict[str, Any]]) -> ProjectAgentTaskExecutionResult:
    has_history = len(context.get("snapshots") or []) > 1
    return _common_result(
        task, context, evidence, citations,
        decision="continue_tracking",
        summary="已完成项目趋势观察，并记录当前快照与历史变化。",
        confidence=0.85 if has_history else 0.65,
        actions=["下次周榜运行后复查 Star 增量与质量变化。"],
    )


def _review_risk(task: dict[str, Any], context: dict[str, Any], evidence: list[dict[str, Any]], citations: list[dict[str, Any]]) -> ProjectAgentTaskExecutionResult:
    latest = (context.get("latest") or {}).get("payload") or {}
    risks = _string_list(latest.get("security_flags")) + _string_list(latest.get("quality_flags"))
    decision = "manual_review" if risks else "continue_tracking"
    summary = f"已完成风险复核，当前识别 {len(risks)} 项风险信号。"
    actions = ["人工核验风险信号后再决定是否订阅。"] if risks else ["保持周期性观察。"]
    return _common_result(task, context, evidence, citations, decision=decision, summary=summary, confidence=0.8, actions=actions)


def _deep_analysis(task: dict[str, Any], context: dict[str, Any], evidence: list[dict[str, Any]], citations: list[dict[str, Any]]) -> ProjectAgentTaskExecutionResult:
    latest = (context.get("latest") or {}).get("payload") or {}
    score = _int_value(latest.get("quality_score"))
    decision = "recommend" if score >= 70 else "continue_tracking"
    return _common_result(
        task, context, evidence, citations,
        decision=decision,
        summary=f"已完成深度分析，当前质量分为 {score}。",
        confidence=0.75 if evidence else 0.4,
        actions=["结合项目画像与风险信号进行人工决策。"],
    )


def _continue_tracking(task: dict[str, Any], context: dict[str, Any], evidence: list[dict[str, Any]], citations: list[dict[str, Any]]) -> ProjectAgentTaskExecutionResult:
    return _common_result(
        task, context, evidence, citations,
        decision="continue_tracking",
        summary="已确认继续跟踪，当前不触发外部通知。",
        confidence=0.9,
        actions=["保留在下一轮周榜观察队列。"],
    )


def _notify(task: dict[str, Any], context: dict[str, Any], evidence: list[dict[str, Any]], citations: list[dict[str, Any]]) -> ProjectAgentTaskExecutionResult:
    return _common_result(
        task, context, evidence, citations,
        decision="subscription_candidate",
        summary="已生成订阅候选，未执行 Telegram 或其他外部推送。",
        confidence=0.8,
        actions=["由订阅模块确认渠道与频率后再发送。"],
        subscription_candidate={
            "eligible": True,
            "full_name": task.get("full_name") or "",
            "reason": task.get("reason") or "Agent 任务建议通知。",
            "requires_confirmation": True,
        },
    )


def _ignore(task: dict[str, Any], context: dict[str, Any], evidence: list[dict[str, Any]], citations: list[dict[str, Any]]) -> ProjectAgentTaskExecutionResult:
    return _common_result(
        task, context, evidence, citations,
        decision="ignore",
        summary="已记录忽略决策，不执行外部操作。",
        confidence=0.95,
        actions=[],
    )


HANDLERS: dict[str, Callable[..., ProjectAgentTaskExecutionResult]] = {
    "observe": _observe,
    "review_risk": _review_risk,
    "deep_analysis": _deep_analysis,
    "continue_tracking": _continue_tracking,
    "notify": _notify,
    "ignore": _ignore,
}


def _task_by_id(connection: sqlite3.Connection, task_id: str) -> dict[str, Any] | None:
    row = connection.execute("SELECT * FROM project_agent_tasks WHERE task_id = ?", (task_id,)).fetchone()
    if not row:
        return None
    task = dict(row)
    task["payload"] = _json_object(task.pop("payload_json", "{}"))
    return task


def _running_run(connection: sqlite3.Connection, task_id: str) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT * FROM project_agent_task_runs WHERE task_id = ? AND status = 'running' ORDER BY started_at DESC LIMIT 1",
        (task_id,),
    ).fetchone()
    return _run_from_row(row) if row else None


def _run_from_row(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    for field, default in (
        ("input_json", {}),
        ("evidence_json", []),
        ("citations_json", []),
        ("result_json", {}),
        ("payload_json", {}),
    ):
        data[field.removesuffix("_json")] = _json_value(data.pop(field, None), default)
    return data


def _metric_changes(latest: dict[str, Any], previous: dict[str, Any]) -> list[dict[str, Any]]:
    changes = []
    for field in ("quality_score", "trending_rank", "star_growth"):
        current_value = _int_value(latest.get(field))
        previous_value = _int_value(previous.get(field))
        changes.append({"field": field, "previous": previous_value, "current": current_value, "delta": current_value - previous_value})
    return changes


def _check(name: str, passed: bool, message: str) -> dict[str, Any]:
    return {"name": name, "passed": passed, "message": message}


def _json_object(value: Any) -> dict[str, Any]:
    parsed = _json_value(value, {})
    return parsed if isinstance(parsed, dict) else {}


def _json_value(value: Any, default: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value or ""))
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
