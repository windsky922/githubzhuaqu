from __future__ import annotations

import re
from typing import Any


STATE_SCHEMA_VERSION = 2
ALLOWED_MODES = {"fts5", "vector", "hybrid"}
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
KNOWLEDGE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,24}$")
GROUP_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,24}$")
CONSTRAINT_FIELDS = {
    "language", "category", "source", "license", "cost", "tech_stack", "hosting_mode",
    "offline_capable", "network_required", "external_api_required", "api_key_required", "multi_agent",
}
CONSTRAINT_OPERATORS = {"eq", "not_eq", "contains"}


def normalize_assistant_request(payload: dict[str, Any] | None) -> dict[str, Any]:
    data = payload or {}
    if not isinstance(data, dict):
        raise ValueError("请求体必须是对象")
    if "auto_build" in data:
        raise ValueError("助手接口不接受 auto_build；索引构建只能通过受控管理接口执行")
    query = str(data.get("q") or "").strip()
    if not query:
        raise ValueError("q 不能为空")
    if len(query) > 4000:
        raise ValueError("q 不能超过 4000 个字符")
    state = normalize_assistant_state(data.get("state"))
    mode = str(data.get("mode") or state.get("mode") or "hybrid").strip().lower()
    if mode not in ALLOWED_MODES:
        raise ValueError("mode 必须是 fts5、vector 或 hybrid")
    return {
        "q": query,
        "state": state,
        "language": _optional_text(data.get("language"), 100),
        "category": _optional_text(data.get("category"), 100),
        "source": _optional_text(data.get("source"), 100),
        "limit": max(1, min(_int_value(data.get("limit"), 3), 10)),
        "mode": mode,
        "model": _optional_text(data.get("model"), 100) or "local-hash-v1",
        "auto_build": False,
    }


def normalize_assistant_state(value: Any) -> dict[str, Any]:
    if value in (None, {}):
        return _empty_state()
    if not isinstance(value, dict):
        raise ValueError("state 必须是对象")
    candidates = _repository_ids(value.get("candidate_repository_ids"))
    knowledge_context = _knowledge_context(value.get("knowledge_context"))
    primary = _optional_text(value.get("primary_repository_id"), 200)
    if primary and (not REPOSITORY_RE.fullmatch(primary) or primary not in candidates):
        primary = ""
    constraints = value.get("constraints") or []
    if not isinstance(constraints, list):
        raise ValueError("state.constraints 必须是数组")
    source_identity = value.get("source_identity") or {}
    if not isinstance(source_identity, dict):
        raise ValueError("state.source_identity 必须是对象")
    mode = _optional_text(value.get("mode"), 20).lower()
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "revision": max(0, min(_int_value(value.get("revision"), 0), 1_000_000)),
        "goal": _optional_text(value.get("goal"), 2000),
        "knowledge_context": knowledge_context,
        "constraints": _constraints(constraints),
        "candidate_repository_ids": candidates,
        "primary_repository_id": primary,
        "last_intent": _optional_text(value.get("last_intent"), 50),
        "pending_question": _optional_text(value.get("pending_question"), 500),
        "source_identity": {
            "kind": _optional_text(source_identity.get("kind"), 50),
            "source_id": _optional_text(source_identity.get("source_id"), 200),
            "run_date": _optional_text(source_identity.get("run_date"), 50),
            "as_of": _optional_text(source_identity.get("as_of"), 50),
        },
        "mode": mode if mode in ALLOWED_MODES else "",
        "resumable": bool(value.get("resumable", False) and value.get("goal")),
    }


def contextual_payload(request: dict[str, Any], *, query: str | None = None) -> dict[str, Any]:
    state = request["state"]
    return {
        "q": query or request["q"],
        "context": {
            "previous_user_goal": state["goal"],
            "candidate_repository_ids": state["candidate_repository_ids"],
            "primary_repository_id": state["primary_repository_id"],
            "requirements": state["constraints"],
            "mode": state.get("mode") or request["mode"],
            "resumable": state["resumable"],
        },
        "language": request["language"],
        "category": request["category"],
        "source": request["source"],
        "limit": request["limit"],
        "mode": request["mode"],
        "model": request["model"],
        "auto_build": request["auto_build"],
    }


def build_assistant_state(
    request: dict[str, Any],
    *,
    assistant_mode: str,
    response: dict[str, Any],
) -> dict[str, Any]:
    previous = request["state"]
    route = response.get("input_route") if isinstance(response.get("input_route"), dict) else {}
    recommendations = response.get("recommendations") if isinstance(response.get("recommendations"), list) else []
    quality = response.get("answer_quality") if isinstance(response.get("answer_quality"), dict) else {}
    data_source = response.get("data_source") if isinstance(response.get("data_source"), dict) else {}
    freshness = response.get("freshness") if isinstance(response.get("freshness"), dict) else {}
    trustworthy = (
        quality.get("passed") is True
        and freshness.get("data_freshness") == "fresh"
        and bool(data_source.get("source_id"))
        and bool(data_source.get("run_date"))
    )
    candidates = [
        str(item.get("full_name") or "")
        for item in recommendations
        if trustworthy
        and isinstance(item, dict)
        and item.get("eligibility") == "eligible"
        and item.get("current_eligible") is True
        and REPOSITORY_RE.fullmatch(str(item.get("full_name") or ""))
    ][:10]
    primary = next(
        (
            str(item.get("full_name"))
            for item in recommendations
            if isinstance(item, dict)
            and item.get("eligibility") == "eligible"
            and item.get("current_eligible") is True
            and str(item.get("full_name") or "") in candidates
        ),
        "",
    )
    constraints = route.get("requirements") if isinstance(route.get("requirements"), list) else previous["constraints"]
    goal = str(response.get("resolved_query") or route.get("resolved_query") or request["q"]).strip()
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "revision": previous["revision"] + 1,
        "goal": goal[:2000],
        "knowledge_context": _knowledge_context(
            response.get("knowledge_context")
            if assistant_mode == "knowledge"
            else previous.get("knowledge_context")
        ),
        "constraints": _constraints(constraints),
        "candidate_repository_ids": candidates,
        "primary_repository_id": primary,
        "last_intent": assistant_mode,
        "pending_question": str(route.get("clarification_question") or "")[:500],
        "source_identity": {
            "kind": str(data_source.get("kind") or "")[:50],
            "source_id": str(data_source.get("source_id") or "")[:200],
            "run_date": str(data_source.get("run_date") or "")[:50],
            "as_of": str(freshness.get("as_of") or "")[:50],
        },
        "mode": request["mode"],
        "resumable": bool(goal and candidates),
    }


def _empty_state() -> dict[str, Any]:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "revision": 0,
        "goal": "",
        "knowledge_context": {"topic": "", "outline": [], "focus_id": ""},
        "constraints": [],
        "candidate_repository_ids": [],
        "primary_repository_id": "",
        "last_intent": "",
        "pending_question": "",
        "source_identity": {"kind": "", "source_id": "", "run_date": "", "as_of": ""},
        "mode": "",
        "resumable": False,
    }


def _repository_ids(value: Any) -> list[str]:
    if value in (None, []):
        return []
    if not isinstance(value, list):
        raise ValueError("state.candidate_repository_ids 必须是数组")
    result: list[str] = []
    for item in value:
        repository_id = str(item or "").strip()
        if REPOSITORY_RE.fullmatch(repository_id) and repository_id not in result:
            result.append(repository_id)
    return result[:10]


def _constraint(value: dict[str, Any]) -> dict[str, Any]:
    result = {
        "field": _optional_text(value.get("field"), 50),
        "operator": _optional_text(value.get("operator"), 20),
        "value": value.get("value") if isinstance(value.get("value"), bool) else _optional_text(value.get("value"), 200),
        "hard": bool(value.get("hard", False)),
    }
    group_id = _optional_text(value.get("group_id"), 24)
    if group_id and GROUP_ID_RE.fullmatch(group_id):
        result.update({
            "group_id": group_id,
            "logic": "any_of" if value.get("logic") == "any_of" else "all_of",
            "optional": bool(value.get("optional", False)),
        })
    elif value.get("optional") is True:
        result["optional"] = True
    if result.get("optional") is True:
        result["hard"] = False
    return result


def _constraints(value: list[Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for raw in value[:20]:
        if not isinstance(raw, dict):
            continue
        item = _constraint(raw)
        if item["field"] not in CONSTRAINT_FIELDS or item["operator"] not in CONSTRAINT_OPERATORS:
            continue
        if item["value"] in (None, ""):
            continue
        if item not in result:
            result.append(item)
    return result


def _knowledge_context(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"topic": "", "outline": [], "focus_id": ""}
    topic = _optional_text(value.get("topic"), 200)
    raw_outline = value.get("outline")
    outline: list[dict[str, str]] = []
    seen: set[str] = set()
    if isinstance(raw_outline, list):
        for raw_item in raw_outline[:12]:
            if not isinstance(raw_item, dict):
                continue
            item_id = _optional_text(raw_item.get("id"), 24)
            title = _optional_text(raw_item.get("title"), 120)
            if not KNOWLEDGE_ID_RE.fullmatch(item_id) or not title or item_id in seen:
                continue
            outline.append({"id": item_id, "title": title})
            seen.add(item_id)
    focus_id = _optional_text(value.get("focus_id"), 24)
    if focus_id not in seen:
        focus_id = ""
    if not topic or not outline:
        return {"topic": "", "outline": [], "focus_id": ""}
    return {"topic": topic, "outline": outline, "focus_id": focus_id}


def _optional_text(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _int_value(value: Any, default: int) -> int:
    if type(value) is not int:
        return default
    return value
