from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from src.rag.freshness import normalize_freshness


READINESS_SCHEMA_VERSION = 1
_SAFE_CODE_RE = re.compile(r"^[a-z0-9_]{1,80}$")
_CURRENT_SOURCE_KINDS = {"weekly_snapshot", "explicit_local"}


def _component(status: str, code: str, message: str, recovery: str = "") -> dict[str, Any]:
    return {
        "status": status,
        "code": code,
        "message": message,
        "recovery": recovery,
    }


def _safe_code(value: Any, fallback: str) -> str:
    candidate = str(value or "").strip().lower()
    return candidate if _SAFE_CODE_RE.fullmatch(candidate) else fallback


def _safe_label(value: Any, *, fallback: str = "", limit: int = 120) -> str:
    candidate = " ".join(str(value or "").split())[:limit]
    return candidate if all(ord(character) >= 32 for character in candidate) else fallback


def _public_source(source: Any) -> dict[str, Any]:
    value = source if isinstance(source, dict) else {}
    return {
        "kind": _safe_code(value.get("kind"), "unknown"),
        "source_id": _safe_label(value.get("source_id"), fallback="unknown"),
        "run_date": _safe_label(value.get("run_date"), limit=32),
        "available": bool(value.get("available")),
        "reason": _safe_code(value.get("reason"), "") if value.get("reason") else "",
        "attestation": normalize_freshness(value.get("attestation")),
        "history_only": bool(value.get("history_only")),
        "read_only": bool(value.get("read_only")),
    }


def _model_facts(model_client: Any) -> dict[str, Any]:
    try:
        status_method = getattr(model_client, "status", None)
        raw = status_method() if callable(status_method) else {}
    except Exception:
        raw = {}
    value = raw if isinstance(raw, dict) else {}
    configured = bool(value.get("configured"))
    return {
        "provider": _safe_code(value.get("provider"), "kimi"),
        "configured": configured,
        "model": _safe_label(value.get("model"), limit=120) if configured else "",
        "live_check": {
            "checked": False,
            "status": "not_run",
            "code": "live_check_not_run",
        },
    }


def _path(value: Any) -> Path | None:
    if isinstance(value, Path):
        return value
    if isinstance(value, str) and value:
        return Path(value)
    return None


def _sqlite_rag_available(repository: Any) -> bool:
    path = _path(getattr(repository, "db_path", None))
    if path is None or not path.is_file():
        return False
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        connection.execute("PRAGMA query_only = ON")
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(rag_chunks)").fetchall()
            if len(row) > 1
        }
        if not {"chunk_id", "full_name", "chunk_text"}.issubset(columns):
            return False
        row = connection.execute(
            """
            SELECT 1
            FROM rag_chunks
            WHERE trim(chunk_id) <> ''
              AND trim(full_name) <> ''
              AND trim(chunk_text) <> ''
            LIMIT 1
            """
        ).fetchone()
        return row is not None
    except (OSError, sqlite3.Error, ValueError):
        return False
    finally:
        if connection is not None:
            connection.close()


def _json_rag_available(repository: Any) -> bool:
    if not bool(getattr(repository, "local_json_archive", False)):
        return False
    root = _path(getattr(repository, "root", None))
    if root is None:
        return False
    selected_dir = root / "data" / "selected"
    try:
        paths = sorted(selected_dir.glob("*.json"), reverse=True)
    except OSError:
        return False
    for path in paths:
        try:
            items = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError):
            continue
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            full_name = str(item.get("full_name") or "").strip()
            if re.fullmatch(r"[^/\s]+/[^/\s]+", full_name):
                return True
    return False


def build_assistant_readiness(
    repository: Any,
    model_client: Any,
    *,
    api_responded: bool = False,
) -> dict[str, Any]:
    """Build a side-effect-free, redacted Assistant dependency snapshot."""

    source = _public_source(getattr(repository, "data_source", None))
    freshness = source["attestation"]
    freshness_status = freshness["data_freshness"]
    read_only = bool(getattr(repository, "local_read_only", False) and source["read_only"])
    sqlite_available = bool(source["available"] and _sqlite_rag_available(repository))
    json_available = bool(source["available"] and _json_rag_available(repository))
    rag_mode = "sqlite" if sqlite_available else "local_archive_json" if json_available else "none"
    rag_available = rag_mode != "none"
    model_facts = _model_facts(model_client)

    components: dict[str, dict[str, Any]] = {
        "api": _component(
            "ready" if api_responded else "degraded",
            "api_process_ready" if api_responded else "api_listener_not_checked",
            "本机 API 已响应 readiness 探针。" if api_responded else "本地依赖可检查，但 CLI 不证明 API listener 已启动。",
            "" if api_responded else "启动本机 API 后读取 /v1/assistant/readiness 验证 listener。",
        ),
    }
    if model_facts["configured"]:
        components["model"] = {
            **_component(
                "ready",
                "model_configured",
                "Kimi 模型配置已就绪；普通 readiness 不执行联网验证。",
            ),
            **model_facts,
        }
    else:
        components["model"] = {
            **_component(
                "unavailable",
                "model_not_configured",
                "Kimi 模型未配置，通用教学能力不可用。",
                "配置 KIMI_API_KEY 与 KIMI_MODEL 后重新检查。",
            ),
            **model_facts,
        }

    if not source["available"]:
        snapshot_code = source["reason"] or "missing_verified_weekly_snapshot"
        components["snapshot"] = {
            **_component(
                "unavailable",
                snapshot_code,
                "当前没有可验证的 weekly snapshot。",
                "配置 GITHUB_WEEKLY_SNAPSHOT_ROOT，并生成完整 freshness attestation。",
            ),
            "data_source": source,
        }
    elif source["history_only"] or source["kind"].startswith("local_archive_"):
        components["snapshot"] = {
            **_component(
                "degraded",
                "local_history_only",
                "当前仅有显式本地历史归档，不能确认最新项目事实。",
                "切换到带完整 freshness attestation 的 weekly snapshot。",
            ),
            "data_source": source,
        }
    elif freshness_status == "fresh":
        components["snapshot"] = {
            **_component("ready", "snapshot_fresh", "已验证 snapshot 与 RAG 三层 freshness 一致且在时效窗内。"),
            "data_source": source,
        }
    elif freshness_status == "lagging":
        components["snapshot"] = {
            **_component(
                "degraded",
                "snapshot_lagging",
                "RAG 语料或 embedding 落后于源归档。",
                "重建语料与 embedding，并重新生成 freshness attestation。",
            ),
            "data_source": source,
        }
    else:
        components["snapshot"] = {
            **_component(
                "degraded",
                "snapshot_stale" if freshness_status == "stale" else "snapshot_freshness_unknown",
                "snapshot 已过期或 freshness 无法确认。",
                "刷新源归档、语料与 embedding，并重新生成 freshness attestation。",
            ),
            "data_source": source,
        }

    if rag_available:
        history = source["history_only"] or source["kind"].startswith("local_archive_")
        components["rag"] = {
            **_component(
                "degraded" if history else "ready",
                "rag_history_read_only" if history else "rag_read_only_ready",
                "只读历史 RAG 可查询。" if history else "只读 RAG 索引可查询。",
                "配置 fresh weekly snapshot 可恢复当前事实能力。" if history else "",
            ),
            "mode": rag_mode,
        }
    else:
        components["rag"] = {
            **_component(
                "unavailable",
                "rag_source_unavailable",
                "未找到可只读查询的 RAG 索引。",
                "提供含 rag_chunks 的 SQLite，或显式启用带 selected JSON 的本地历史模式。",
            ),
            "mode": "none",
        }

    components["access"] = {
        **_component(
            "ready" if read_only else "unavailable",
            "assistant_read_only" if read_only else "assistant_not_read_only",
            "Assistant 数据访问已强制只读。" if read_only else "Assistant 数据访问未证明为只读。",
            "使用 force_read_only=True 构造 Assistant repository。" if not read_only else "",
        ),
        "read_only": read_only,
        "history_only": source["history_only"],
    }

    project_available = bool(source["available"] and rag_available and read_only)
    current_project_available = bool(
        project_available
        and not source["history_only"]
        and source["kind"] in _CURRENT_SOURCE_KINDS
        and freshness_status == "fresh"
    )
    knowledge_available = bool(model_facts["configured"])
    can_chat = knowledge_available or project_available
    if knowledge_available and current_project_available and api_responded:
        overall = "ready"
        summary = "本机模型配置与当前项目证据已就绪；模型连通性未执行。"
    elif knowledge_available and current_project_available:
        overall = "degraded"
        summary = "本地依赖已就绪，但尚未证明 API listener 与模型连通性。"
    elif can_chat:
        overall = "degraded"
        summary = "至少一条安全回答链可用；请按组件恢复缺失能力。"
    else:
        overall = "unavailable"
        summary = "通用教学与项目证据链均不可用。"

    issues = [
        {
            "component": name,
            "code": component["code"],
            "message": component["message"],
            "recovery": component["recovery"],
        }
        for name, component in components.items()
        if component["status"] != "ready"
    ]
    return {
        "schema_version": READINESS_SCHEMA_VERSION,
        "status": overall,
        "summary": summary,
        "capabilities": {
            "can_chat": can_chat,
            "knowledge_available": knowledge_available,
            "project_available": project_available,
            "current_project_available": current_project_available,
        },
        "components": components,
        "issues": issues,
    }
