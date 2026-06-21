from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha1
from pathlib import Path
from typing import Any

from src.storage.sqlite_store import (
    connect,
    initialize,
    upsert_notification_candidate,
    upsert_subscription_event,
)


EVENT_TYPES = {
    "trending_entered",
    "star_growth_spike",
    "quality_changed",
    "risk_added",
    "risk_resolved",
    "release_detected",
    "agent_decision_changed",
}
SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def detect_subscription_events(
    db_path: Path,
    *,
    full_name: str = "",
    limit: int = 500,
    dry_run: bool = False,
) -> dict[str, Any]:
    connection = connect(db_path)
    try:
        initialize(connection)
        snapshots = _selection_snapshots(connection, full_name=full_name)
        corpus = _latest_corpus(connection, list(snapshots))
        events: list[dict[str, Any]] = []
        for project, project_snapshots in snapshots.items():
            events.extend(_snapshot_events(project, project_snapshots, corpus.get(project.lower())))
        events.extend(_agent_events(connection, full_name=full_name))
        events = sorted(events, key=lambda item: (item["detected_at"], item["event_id"]), reverse=True)[:max(1, min(limit, 2000))]
        existing_ids = {
            row["event_id"] for row in connection.execute("SELECT event_id FROM subscription_events").fetchall()
        }
        new_events = [event for event in events if event["event_id"] not in existing_ids]
        if not dry_run:
            for event in new_events:
                upsert_subscription_event(connection, event)
            connection.commit()
        return {
            "dry_run": dry_run,
            "matched_count": len(events),
            "detected_count": len(new_events),
            "persisted_count": 0 if dry_run else len(new_events),
            "events": new_events,
        }
    finally:
        connection.close()


def build_notification_candidates(
    db_path: Path,
    *,
    limit: int = 500,
    dry_run: bool = False,
) -> dict[str, Any]:
    connection = connect(db_path)
    try:
        initialize(connection)
        events = connection.execute(
            "SELECT * FROM subscription_events WHERE status = 'detected' ORDER BY detected_at DESC LIMIT ?",
            (max(1, min(limit, 2000)),),
        ).fetchall()
        subscriptions = connection.execute(
            "SELECT * FROM subscriptions WHERE status = 'enabled' ORDER BY updated_at DESC, subscription_id"
        ).fetchall()
        candidates: list[dict[str, Any]] = []
        for subscription_row in subscriptions:
            subscription = _subscription_rule(subscription_row)
            for event_row in events:
                event = _event_from_row(event_row)
                if not _matches(subscription, event):
                    continue
                dedupe_key = f"notification:{subscription['subscription_id']}:{event['event_id']}"
                candidate_id = "candidate:" + sha1(dedupe_key.encode("utf-8")).hexdigest()[:20]
                now = _utc_now()
                candidates.append({
                    "candidate_id": candidate_id,
                    "subscription_id": subscription["subscription_id"],
                    "event_id": event["event_id"],
                    "full_name": event["full_name"],
                    "status": "pending",
                    "channels": subscription["channels"],
                    "title": event["title"],
                    "message": _candidate_message(event),
                    "dedupe_key": dedupe_key,
                    "created_at": now,
                    "updated_at": now,
                    "payload": {
                        "frequency": subscription["frequency"],
                        "severity": event["severity"],
                        "event_type": event["event_type"],
                        "requires_confirmation": True,
                        "evidence": event["evidence"],
                        "citations": event["citations"],
                    },
                })
        existing_ids = {
            row["candidate_id"] for row in connection.execute("SELECT candidate_id FROM notification_candidates").fetchall()
        }
        new_candidates = [candidate for candidate in candidates if candidate["candidate_id"] not in existing_ids]
        if not dry_run:
            for candidate in new_candidates:
                upsert_notification_candidate(connection, candidate)
            connection.commit()
        return {
            "dry_run": dry_run,
            "matched_count": len(candidates),
            "created_count": len(new_candidates),
            "persisted_count": 0 if dry_run else len(new_candidates),
            "candidates": new_candidates,
        }
    finally:
        connection.close()


def _selection_snapshots(connection: Any, *, full_name: str) -> dict[str, list[dict[str, Any]]]:
    query = "SELECT * FROM selections"
    params: tuple[Any, ...] = ()
    if full_name:
        query += " WHERE LOWER(full_name) = LOWER(?)"
        params = (full_name,)
    query += " ORDER BY full_name, run_date DESC"
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in connection.execute(query, params).fetchall():
        items = grouped.setdefault(row["full_name"], [])
        if len(items) >= 2:
            continue
        payload = _json_object(row["payload_json"])
        payload.update({
            "run_date": row["run_date"],
            "full_name": row["full_name"],
            "score": row["score"],
            "star_growth": row["star_growth"],
            "trending_rank": row["trending_rank"],
            "category": row["category"],
            "sources": _json_list(row["sources_json"]),
            "selection_reasons": _json_list(row["selection_reasons_json"]),
            "security_flags": _unique_strings(_json_list(row["security_flags_json"]) + _string_list(payload.get("security_flags"))),
        })
        items.append(payload)
    return grouped


def _latest_corpus(connection: Any, full_names: list[str]) -> dict[str, dict[str, Any]]:
    if not full_names:
        return {}
    placeholders = ",".join("?" for _ in full_names)
    rows = connection.execute(
        f"SELECT * FROM project_corpus WHERE LOWER(full_name) IN ({placeholders}) ORDER BY run_date DESC, corpus_id DESC",
        tuple(name.lower() for name in full_names),
    ).fetchall()
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        result.setdefault(row["full_name"].lower(), dict(row))
    return result


def _snapshot_events(full_name: str, snapshots: list[dict[str, Any]], corpus: dict[str, Any] | None) -> list[dict[str, Any]]:
    latest = snapshots[0]
    previous = snapshots[1] if len(snapshots) > 1 else {}
    events: list[dict[str, Any]] = []
    current_rank = _int_value(latest.get("trending_rank"))
    previous_rank = _int_value(previous.get("trending_rank"))
    if current_rank > 0 and previous_rank <= 0:
        events.append(_snapshot_event("trending_entered", full_name, latest, corpus, "进入 Trending", f"{full_name} 进入 Trending，当前排名 {current_rank}。", "high" if current_rank <= 3 else "medium", str(current_rank)))

    growth = _int_value(latest.get("star_growth"))
    previous_growth = _int_value(previous.get("star_growth"))
    if growth >= 100 and (not previous or growth >= max(100, previous_growth * 2)):
        events.append(_snapshot_event("star_growth_spike", full_name, latest, corpus, "Star 增长显著", f"{full_name} 本期 Star 增量为 {growth}，高于上一期 {previous_growth}。", "high" if growth >= 500 else "medium", str(growth)))

    quality = _number_or_none(latest.get("quality_score"))
    previous_quality = _number_or_none(previous.get("quality_score"))
    if quality is not None and previous_quality is not None and abs(quality - previous_quality) >= 10:
        direction = "上升" if quality > previous_quality else "下降"
        severity = "high" if quality < previous_quality else "medium"
        events.append(_snapshot_event("quality_changed", full_name, latest, corpus, "质量评分变化", f"{full_name} 质量分从 {previous_quality:g} {direction}到 {quality:g}。", severity, f"{previous_quality:g}:{quality:g}"))

    latest_risks = set(_risk_flags(latest))
    previous_risks = set(_risk_flags(previous))
    added = sorted(latest_risks - previous_risks)
    resolved = sorted(previous_risks - latest_risks)
    if added:
        events.append(_snapshot_event("risk_added", full_name, latest, corpus, "新增风险信号", f"{full_name} 新增风险：{'；'.join(added)}。", "high", "|".join(added), {"risks": added}))
    if resolved:
        events.append(_snapshot_event("risk_resolved", full_name, latest, corpus, "风险信号解除", f"{full_name} 已解除风险：{'；'.join(resolved)}。", "low", "|".join(resolved), {"risks": resolved}))

    release = _release_value(latest)
    previous_release = _release_value(previous)
    if release and release != previous_release:
        events.append(_snapshot_event("release_detected", full_name, latest, corpus, "发现新版本", f"{full_name} 检测到版本 {release}。", "medium", release, {"release": release, "previous_release": previous_release}))
    return events


def _snapshot_event(
    event_type: str,
    full_name: str,
    latest: dict[str, Any],
    corpus: dict[str, Any] | None,
    title: str,
    summary: str,
    severity: str,
    signal: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run_date = str(latest.get("run_date") or "")
    evidence = [{
        "evidence_id": f"selection:{full_name}:{run_date}",
        "source_type": "selection",
        "source_id": f"{run_date}:{full_name}",
        "source_path": str(latest.get("html_url") or ""),
        "title": f"{full_name} 周榜快照（{run_date}）",
        "excerpt": summary,
        "observed_at": run_date,
    }]
    if corpus:
        evidence.append({
            "evidence_id": f"project-corpus:{corpus.get('corpus_id')}",
            "source_type": "project_corpus",
            "source_id": corpus.get("corpus_id") or "",
            "source_path": corpus.get("html_url") or "",
            "title": corpus.get("title") or full_name,
            "excerpt": str(corpus.get("search_text") or "")[:600],
            "observed_at": corpus.get("run_date") or run_date,
        })
    payload = {
        "language": str(latest.get("language") or (corpus or {}).get("language") or ""),
        "category": str(latest.get("category") or (corpus or {}).get("category") or ""),
        "profile": str(latest.get("profile") or latest.get("project_profile") or ""),
        "search_text": str((corpus or {}).get("search_text") or ""),
        "signal": signal,
    }
    payload.update(extra or {})
    return _event(event_type, full_name, run_date, severity, title, summary, evidence, _citations(evidence), signal, payload)


def _agent_events(connection: Any, *, full_name: str) -> list[dict[str, Any]]:
    query = """
        SELECT r.*, t.full_name, t.profile, t.task_type, t.reason
        FROM project_agent_task_runs r
        JOIN project_agent_tasks t ON t.task_id = r.task_id
        WHERE r.status = 'succeeded'
    """
    params: tuple[Any, ...] = ()
    if full_name:
        query += " AND LOWER(t.full_name) = LOWER(?)"
        params = (full_name,)
    query += " ORDER BY t.full_name, r.started_at"
    previous_decisions: dict[str, str] = {}
    events: list[dict[str, Any]] = []
    for row in connection.execute(query, params).fetchall():
        result = _json_object(row["result_json"])
        decision = str(result.get("decision") or "")
        previous = previous_decisions.get(row["full_name"].lower(), "")
        candidate = result.get("subscription_candidate") if isinstance(result.get("subscription_candidate"), dict) else {}
        eligible = bool(candidate.get("eligible"))
        if decision and ((previous and decision != previous) or eligible):
            evidence = result.get("evidence") if isinstance(result.get("evidence"), list) else _json_list(row["evidence_json"])
            citations = result.get("citations") if isinstance(result.get("citations"), list) else _json_list(row["citations_json"])
            if not evidence:
                evidence = [{
                    "evidence_id": f"agent-run:{row['run_id']}", "source_type": "project_agent_task_run",
                    "source_id": row["run_id"], "source_path": "", "title": f"Agent 运行 {row['run_id']}",
                    "excerpt": str(result.get("execution_summary") or row["reason"] or "")[:600], "observed_at": row["finished_at"] or row["started_at"],
                }]
            if not citations:
                citations = _citations(evidence)
            reason = str(candidate.get("reason") or result.get("execution_summary") or "Agent 决策发生变化。")
            title = "Agent 生成订阅候选" if eligible else "Agent 决策变化"
            summary = f"{row['full_name']}：{reason}"
            events.append(_event(
                "agent_decision_changed", row["full_name"], row["run_id"], "high" if eligible else "medium",
                title, summary, evidence, citations, f"{previous}:{decision}:{eligible}",
                {"profile": row["profile"], "task_type": row["task_type"], "previous_decision": previous,
                 "decision": decision, "subscription_candidate": candidate},
                detected_at=row["finished_at"] or row["started_at"],
            ))
        if decision:
            previous_decisions[row["full_name"].lower()] = decision
    return events


def _event(
    event_type: str,
    full_name: str,
    source_run_id: str,
    severity: str,
    title: str,
    summary: str,
    evidence: list[dict[str, Any]],
    citations: list[dict[str, Any]],
    signal: str,
    payload: dict[str, Any],
    *,
    detected_at: str = "",
) -> dict[str, Any]:
    dedupe_key = f"event:{event_type}:{full_name.lower()}:{source_run_id}:{signal}"
    event_id = "event:" + sha1(dedupe_key.encode("utf-8")).hexdigest()[:20]
    now = _utc_now()
    return {
        "event_id": event_id, "event_type": event_type, "full_name": full_name,
        "source_run_id": source_run_id, "severity": severity, "status": "detected",
        "title": title, "summary": summary, "evidence": evidence, "citations": citations,
        "dedupe_key": dedupe_key, "detected_at": detected_at or source_run_id or now,
        "updated_at": now, "payload": payload,
    }


def _subscription_rule(row: Any) -> dict[str, Any]:
    payload = _json_object(row["payload_json"])
    event_types = [item for item in _string_list(payload.get("event_types")) if item in EVENT_TYPES]
    projects = _string_list(payload.get("full_names") or payload.get("projects") or payload.get("repositories"))
    channels = [item.lower() for item in _json_list(row["channels_json"]) if str(item).lower() in {"telegram", "feishu", "wechat", "wecom"}]
    severity = str(payload.get("min_severity") or "info").lower()
    frequency = str(payload.get("frequency") or "immediate").lower()
    return {
        "subscription_id": row["subscription_id"], "profile": row["profile"], "language": row["language"],
        "category": row["category"], "query": row["query"], "full_names": projects,
        "event_types": event_types, "min_severity": severity if severity in SEVERITY_ORDER else "info",
        "channels": channels or ["telegram"], "frequency": frequency if frequency in {"immediate", "daily", "weekly"} else "immediate",
    }


def _matches(subscription: dict[str, Any], event: dict[str, Any]) -> bool:
    payload = event["payload"]
    if subscription["full_names"] and event["full_name"].lower() not in {item.lower() for item in subscription["full_names"]}:
        return False
    if subscription["event_types"] and event["event_type"] not in subscription["event_types"]:
        return False
    if SEVERITY_ORDER.get(event["severity"], 0) < SEVERITY_ORDER[subscription["min_severity"]]:
        return False
    for key in ("profile", "language", "category"):
        expected = str(subscription.get(key) or "").strip().lower()
        if expected and expected != str(payload.get(key) or "").strip().lower():
            return False
    query = str(subscription.get("query") or "").strip().lower()
    haystack = " ".join((event["full_name"], event["title"], event["summary"], str(payload.get("search_text") or ""))).lower()
    return not query or query in haystack


def _event_from_row(row: Any) -> dict[str, Any]:
    return {
        "event_id": row["event_id"], "event_type": row["event_type"], "full_name": row["full_name"],
        "severity": row["severity"], "title": row["title"], "summary": row["summary"],
        "evidence": _json_list(row["evidence_json"]), "citations": _json_list(row["citations_json"]),
        "payload": _json_object(row["payload_json"]),
    }


def _candidate_message(event: dict[str, Any]) -> str:
    source_paths = [str(item.get("source_path") or "") for item in event["citations"] if isinstance(item, dict) and item.get("source_path")]
    suffix = f"\n证据：{source_paths[0]}" if source_paths else ""
    return f"[{event['severity'].upper()}] {event['title']}\n{event['summary']}{suffix}"


def _risk_flags(payload: dict[str, Any]) -> list[str]:
    return _unique_strings(_string_list(payload.get("security_flags")) + _string_list(payload.get("quality_flags")))


def _release_value(payload: dict[str, Any]) -> str:
    for key in ("latest_release", "release_tag", "tag_name", "version", "release_name"):
        value = payload.get(key)
        if isinstance(value, dict):
            value = value.get("tag_name") or value.get("name") or value.get("version")
        if value:
            return str(value).strip()[:160]
    return ""


def _citations(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "citation_id": f"citation:{index + 1}", "evidence_id": item.get("evidence_id") or "",
        "title": item.get("title") or "", "source_path": item.get("source_path") or "",
    } for index, item in enumerate(evidence)]


def _json_object(value: Any) -> dict[str, Any]:
    parsed = _json_value(value, {})
    return parsed if isinstance(parsed, dict) else {}


def _json_list(value: Any) -> list[Any]:
    parsed = _json_value(value, [])
    return parsed if isinstance(parsed, list) else []


def _json_value(value: Any, default: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return default


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [value]
    return [str(item).strip() for item in (value or []) if str(item).strip()]


def _unique_strings(values: list[Any]) -> list[str]:
    return list(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))


def _int_value(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _number_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
