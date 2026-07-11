from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.llm.client import KimiChatClient, LlmClientError
from src.llm.prompts import follow_up_route_messages


ROUTER_VERSION = "follow-up-v1"
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
ALLOWED_MODES = {"fts5", "vector", "hybrid"}
ALLOWED_ROUTES = {"new_search", "resume", "refine", "clarify"}
ALLOWED_SCOPES = {"archive", "previous_candidates", "primary_candidate", "none"}
ALLOWED_FIELDS = {"language", "category", "source", "license", "deployment", "cost", "tech_stack"}
ALLOWED_OPERATORS = {"eq", "not_eq", "contains"}

RESUME_WORDS = {
    "继续", "继续一下", "继续吧", "接着说", "接着来", "展开", "展开说说", "详细说说", "然后呢", "嗯", "好的",
}
PRIMARY_WORDS = {"那个呢", "那个项目呢", "这个呢", "这个项目呢", "它呢"}
RESET_MARKERS = ("重新找", "换一批", "搜索其他", "找别的", "重新搜索")
AMBIGUOUS_WORDS = {"哪个好", "还有吗", "怎么选", "可以吗", "怎么样", "还有呢"}

LANGUAGES = {
    "python": "Python", "java": "Java", "javascript": "JavaScript", "typescript": "TypeScript",
    "golang": "Go", " go ": "Go", "rust": "Rust", "c++": "C++", "c#": "C#",
    "php": "PHP", "ruby": "Ruby", "kotlin": "Kotlin", "swift": "Swift",
}
LICENSES = {
    "mit": "MIT", "apache-2.0": "Apache-2.0", "apache 2.0": "Apache-2.0", "gpl-3.0": "GPL-3.0",
    "gplv3": "GPL-3.0", "bsd-3-clause": "BSD-3-Clause", "mpl-2.0": "MPL-2.0",
}
TECH_STACKS = ("Docker", "Kubernetes", "React", "Vue", "FastAPI", "Django", "Spring", "Node.js", "LangChain")


def normalize_contextual_request(payload: dict[str, Any] | None) -> dict[str, Any]:
    data = payload if isinstance(payload, dict) else {}
    query = str(data.get("q") or "").strip()
    if not query:
        raise ValueError("q 不能为空")
    if len(query) > 2000:
        raise ValueError("q 不能超过 2000 个字符")
    context = normalize_intent_context(data.get("context"))
    mode = str(data.get("mode") or context.get("mode") or "fts5").strip().lower()
    if mode not in ALLOWED_MODES:
        raise ValueError("mode 必须是 fts5、vector 或 hybrid")
    return {
        "q": query,
        "context": context,
        "language": _optional_text(data.get("language"), 100),
        "category": _optional_text(data.get("category"), 100),
        "source": _optional_text(data.get("source"), 100),
        "limit": max(1, min(_int_value(data.get("limit"), 8), 30)),
        "mode": mode,
        "model": _optional_text(data.get("model"), 100) or "local-hash-v1",
        "auto_build": bool(data.get("auto_build", False)),
    }


def normalize_intent_context(value: Any) -> dict[str, Any]:
    if value in (None, {}):
        return {
            "previous_user_goal": "",
            "candidate_repository_ids": [],
            "primary_repository_id": "",
            "mode": "",
            "resumable": False,
        }
    if not isinstance(value, dict):
        raise ValueError("context 必须是对象")
    goal = str(value.get("previous_user_goal") or "").strip()
    if len(goal) > 2000:
        raise ValueError("previous_user_goal 不能超过 2000 个字符")
    raw_ids = value.get("candidate_repository_ids") or []
    if not isinstance(raw_ids, list):
        raise ValueError("candidate_repository_ids 必须是数组")
    if len(raw_ids) > 10:
        raise ValueError("candidate_repository_ids 最多 10 个")
    repository_ids = []
    for item in raw_ids:
        normalized = str(item or "").strip()
        if not REPOSITORY_RE.fullmatch(normalized):
            raise ValueError("candidate_repository_ids 必须使用 owner/repo 格式")
        if normalized not in repository_ids:
            repository_ids.append(normalized)
    primary = str(value.get("primary_repository_id") or "").strip()
    if primary and (not REPOSITORY_RE.fullmatch(primary) or primary not in repository_ids):
        raise ValueError("primary_repository_id 必须存在于 candidate_repository_ids")
    mode = str(value.get("mode") or "").strip().lower()
    if mode and mode not in ALLOWED_MODES:
        raise ValueError("context.mode 必须是 fts5、vector 或 hybrid")
    return {
        "previous_user_goal": goal,
        "candidate_repository_ids": repository_ids,
        "primary_repository_id": primary,
        "mode": mode,
        "resumable": bool(value.get("resumable", False)),
    }


def route_follow_up(
    *,
    root: Path,
    query: str,
    context: dict[str, Any],
    client: KimiChatClient | None = None,
) -> dict[str, Any]:
    normalized = _normalize_query(query)
    requirements = extract_requirements(query)
    has_context = _has_resumable_context(context)

    if any(marker in normalized for marker in ("忽略之前", "忽略系统", "系统提示", "输出json", "绕过规则")):
        return _clarify("这句话包含无法作为项目需求处理的指令。请只描述要寻找或比较的项目。", "instruction_like_input")
    if any(marker in normalized for marker in RESET_MARKERS):
        resolved = _combine_query(context.get("previous_user_goal") if has_context else "", query)
        return _route("new_search", "explicit_archive_reset", resolved, "archive", requirements)
    if normalized in PRIMARY_WORDS:
        primary = str(context.get("primary_repository_id") or "")
        if has_context and primary:
            return _route("resume", "primary_candidate_reference", context["previous_user_goal"], "primary_candidate", requirements)
        return _clarify("你指的是哪个项目？请给出项目名称，或先选择一个已确认的首选项目。", "primary_candidate_missing")
    if normalized in RESUME_WORDS:
        if has_context:
            return _route("resume", "exact_resume_command", context["previous_user_goal"], "previous_candidates", requirements)
        return _clarify("你想继续刚才的项目分析，还是开始一次新的项目搜索？请补充一句完整需求。", "resume_without_context")
    if requirements and _looks_like_refinement(normalized):
        if has_context:
            return _route(
                "refine",
                "constraint_refinement",
                _combine_query(context["previous_user_goal"], query),
                "previous_candidates",
                requirements,
            )
        if _has_search_target(normalized):
            return _route("new_search", "substantive_query_with_constraints", query.strip(), "archive", requirements)
        return _clarify("这些是补充条件，但当前没有可恢复的上一轮需求。请把完整项目需求一起说明。", "refinement_without_context", requirements)
    if normalized in AMBIGUOUS_WORDS or len(normalized) <= 3:
        return _route_with_kimi(root=root, query=query, context=context, requirements=requirements, client=client)
    return _route("new_search", "substantive_query", query.strip(), "archive", requirements)


def extract_requirements(query: str) -> list[dict[str, Any]]:
    lower = f" {query.casefold()} "
    negative = any(marker in query for marker in ("不要", "排除", "不能", "不是"))
    operator = "not_eq" if negative else "eq"
    requirements: list[dict[str, Any]] = []
    for token, value in sorted(LANGUAGES.items(), key=lambda item: len(item[0]), reverse=True):
        if token == "java" and "javascript" in lower:
            continue
        if token in lower:
            _append_requirement(requirements, "language", operator, value)
    for token, value in LICENSES.items():
        if token in lower:
            _append_requirement(requirements, "license", operator, value)
    deployment_values = []
    if any(marker in lower for marker in ("本地部署", "私有化", "离线", "self-hosted", "self hosted")):
        deployment_values.append("local")
    if any(marker in lower for marker in ("云端", "saas", "cloud")):
        deployment_values.append("cloud")
    for value in deployment_values:
        _append_requirement(requirements, "deployment", operator, value)
    for marker, value in (("免费", "free"), ("低成本", "low_cost"), ("付费", "paid")):
        if marker in lower:
            _append_requirement(requirements, "cost", operator, value)
    for stack in TECH_STACKS:
        if stack.casefold() in lower:
            _append_requirement(requirements, "tech_stack", operator, stack)
    return requirements


def _route_with_kimi(
    *, root: Path, query: str, context: dict[str, Any], requirements: list[dict[str, Any]], client: KimiChatClient | None
) -> dict[str, Any]:
    model_client = client or KimiChatClient()
    status = model_client.status()
    if not status.get("configured"):
        return _clarify("这个输入太短或含义不明确。请说明要继续哪个分析，或写出新的完整项目需求。", "router_model_unavailable", requirements)
    try:
        raw = model_client.chat(follow_up_route_messages(root=root, query=query, context=context))
        parsed = json.loads(raw)
        return _validated_model_route(parsed, query=query, context=context, model=str(status.get("model") or ""))
    except (LlmClientError, OSError, ValueError, json.JSONDecodeError):
        return _clarify("我无法可靠判断这句话是追问还是新搜索。请补充上一轮目标或写出完整项目需求。", "router_model_failed", requirements)


def _validated_model_route(value: Any, *, query: str, context: dict[str, Any], model: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("router output must be object")
    route = str(value.get("route") or "")
    if route not in ALLOWED_ROUTES:
        raise ValueError("invalid route")
    requirements = _validated_requirements(value.get("requirements"))
    if route == "clarify":
        question = str(value.get("clarification_question") or "").strip()
        if not question or len(question) > 300:
            raise ValueError("invalid clarification")
        return _clarify(question, "kimi_ambiguous", requirements, parser=f"kimi:{model}")
    if route in {"resume", "refine"} and not _has_resumable_context(context):
        return _clarify("当前没有可恢复的上一轮需求。请写出完整项目需求。", "kimi_route_without_context", requirements, parser=f"kimi:{model}")
    resolved = str(value.get("resolved_query") or "").strip()
    if not resolved or len(resolved) > 2000:
        raise ValueError("invalid resolved query")
    scope = "archive" if route == "new_search" else "previous_candidates"
    return _route(route, "kimi_route", resolved, scope, requirements, parser=f"kimi:{model}")


def _validated_requirements(value: Any) -> list[dict[str, Any]]:
    if value in (None, []):
        return []
    if not isinstance(value, list) or len(value) > 8:
        raise ValueError("invalid requirements")
    result = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("invalid requirement")
        field = str(item.get("field") or "")
        operator = str(item.get("operator") or "")
        requirement_value = str(item.get("value") or "").strip()
        if field not in ALLOWED_FIELDS or operator not in ALLOWED_OPERATORS or not requirement_value or len(requirement_value) > 100:
            raise ValueError("invalid requirement fields")
        _append_requirement(result, field, operator, requirement_value)
    return result


def _route(route: str, reason: str, resolved_query: str, scope: str, requirements: list[dict[str, Any]], *, parser: str | None = None) -> dict[str, Any]:
    return {
        "route": route,
        "reason": reason,
        "parser": parser or f"rule:{ROUTER_VERSION}",
        "resolved_query": resolved_query.strip(),
        "retrieval_performed": False,
        "candidate_scope": scope,
        "requirements": requirements,
        "clarification_required": False,
        "clarification_question": "",
    }


def _clarify(question: str, reason: str, requirements: list[dict[str, Any]] | None = None, *, parser: str | None = None) -> dict[str, Any]:
    result = _route("clarify", reason, "", "none", requirements or [], parser=parser)
    result["clarification_required"] = True
    result["clarification_question"] = question
    return result


def _append_requirement(items: list[dict[str, Any]], field: str, operator: str, value: str) -> None:
    item = {"field": field, "operator": operator, "value": value, "hard": True}
    if item not in items:
        items.append(item)


def _has_resumable_context(context: dict[str, Any]) -> bool:
    return bool(context.get("resumable") and context.get("previous_user_goal") and context.get("candidate_repository_ids"))


def _looks_like_refinement(query: str) -> bool:
    return len(query) <= 80 and any(marker in query for marker in ("更", "要", "必须", "只要", "不要", "适合", "优先", "改成", "限制"))


def _has_search_target(query: str) -> bool:
    return any(marker in query for marker in ("项目", "框架", "平台", "工具", "组件库", "系统", "服务", "仓库"))


def _combine_query(previous: Any, current: Any) -> str:
    previous_text = str(previous or "").strip()
    current_text = str(current or "").strip()
    return f"{previous_text}；补充要求：{current_text}" if previous_text else current_text


def _normalize_query(value: Any) -> str:
    return re.sub(r"[\s，。！？!?；;]+", "", str(value or "").strip().casefold())


def _optional_text(value: Any, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) > limit:
        raise ValueError(f"字段不能超过 {limit} 个字符")
    return text


def _int_value(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
