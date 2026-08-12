from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.llm.client import KimiChatClient, LlmClientError
from src.llm.prompts import follow_up_route_messages


ROUTER_VERSION = "follow-up-v3"
REQUIREMENT_SCHEMA_VERSION = "capability-v2"
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
GROUP_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,24}$")
ALLOWED_MODES = {"fts5", "vector", "hybrid"}
ALLOWED_ROUTES = {"new_search", "resume", "refine", "clarify"}
ALLOWED_SCOPES = {"archive", "previous_candidates", "primary_candidate", "selected_candidates", "none"}
CAPABILITY_FIELDS = {
    "hosting_mode",
    "offline_capable",
    "network_required",
    "external_api_required",
    "api_key_required",
    "multi_agent",
}
BOOLEAN_CAPABILITY_FIELDS = CAPABILITY_FIELDS - {"hosting_mode"}
ALLOWED_FIELDS = {
    "language", "category", "source", "license", "deployment", "cost", "tech_stack", *CAPABILITY_FIELDS,
}
ALLOWED_OPERATORS = {"eq", "not_eq", "contains"}
ALLOWED_LOGICS = {"all_of", "any_of"}

RESUME_WORDS = {
    "继续", "继续一下", "继续吧", "接着说", "接着来", "展开", "展开说说", "详细说说", "然后呢", "嗯", "好的",
}
PRIMARY_WORDS = {"那个呢", "那个项目呢", "这个呢", "这个项目呢", "它呢"}
RESET_MARKERS = ("重新找", "换一批", "搜索其他", "找别的", "重新搜索")
AMBIGUOUS_WORDS = {"哪个好", "还有吗", "怎么选", "可以吗", "怎么样", "还有呢"}
PREVIOUS_CANDIDATE_WORDS = {"上一个", "上一个呢", "上一个项目", "上一个项目呢", "看上一个项目", "看看上一个项目"}
NATURAL_CONTEXT_MARKERS = (
    "刚才", "之前推荐", "这些项目", "上述项目", "其中", "候选项目", "推荐的项目", "哪个项目", "哪一个项目",
)
ORDINAL_RE = re.compile(r"第\s*([一二三四五六七八九十]|\d{1,2})\s*个?")
ORDINAL_VALUES = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
ORDINAL_COMPARISON_MARKERS = ("比较", "对比", "和", "与", "跟", "、")

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
NEGATION_MARKERS = (
    "不要", "排除", "不能", "不是", "不支持", "不依赖", "无法", "禁止", "without", "does not", "doesn't", "not support", " not ", " no ",
)
CLAUSE_SPLIT_RE = re.compile(r"[，,。；;！？!?]+|但(?:是)?|不过|然而|同时|并且|而且|另外|此外|且|\bbut\b", re.IGNORECASE)
POSITIVE_BOUNDARY_RE = re.compile(r"(?<!^)(?=(?:必须|(?<!不)要求|最好|优先|需要支持|要支持|must\b|require\b|prefer\b))", re.IGNORECASE)
DISJUNCTION_RE = re.compile(r"(?:或者|或是|二选一|或|\beither\b|\bor\b)", re.IGNORECASE)
OPTIONAL_MARKERS = ("不要求", "无所谓", "随便", "可选", "不是必须", "not required", "optional")
CANCELLATION_RE = re.compile(
    r"(?:取消|移除|删除|去掉)\s*(?:之前的|此前的|原来的|原有的)?\s*([^，,。；;！？!?]{1,60}?)\s*(?:要求|条件|限制)(?=$|[，,。；;！？!?])",
    re.IGNORECASE,
)


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
            "requirements": [],
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
    requirements = _validated_requirements(value.get("requirements"))
    return {
        "previous_user_goal": goal,
        "candidate_repository_ids": repository_ids,
        "primary_repository_id": primary,
        "requirements": requirements,
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
    parsed_requirements = parse_requirements(query)
    requirements = parsed_requirements["requirements"]
    operations = parsed_requirements["requirement_operations"]
    previous_requirements = context.get("requirements") if isinstance(context.get("requirements"), list) else []
    updated_requirements = _apply_requirement_update(previous_requirements, requirements, operations)
    has_context = _has_resumable_context(context)

    if any(marker in normalized for marker in ("忽略之前", "忽略系统", "系统提示", "输出json", "绕过规则")):
        return _clarify("这句话包含无法作为项目需求处理的指令。请只描述要寻找或比较的项目。", "instruction_like_input")
    if parsed_requirements["ambiguous"]:
        return _clarify(
            "这些条件包含无法安全确定的否定范围或冲突。请把必须满足和必须排除的条件分别写清楚。",
            parsed_requirements["reason"],
            requirements,
            operations=operations,
        )
    if _requirement_conflict(updated_requirements):
        return _clarify(
            "新条件与上一轮保留条件直接冲突。请明确要保留哪一个条件。",
            "conflicting_constraint_requirements",
            updated_requirements,
            operations=operations,
        )
    if operations and not has_context:
        return _clarify(
            "当前没有可撤销的上一轮项目条件。请先给出完整项目需求。",
            "cancellation_without_context",
            [],
            operations=operations,
        )
    if any(marker in normalized for marker in RESET_MARKERS):
        resolved = _combine_query(context.get("previous_user_goal") if has_context else "", query)
        return _route("new_search", "explicit_archive_reset", resolved, "archive", requirements, operations=operations)
    ordinal_route = _ordinal_candidate_route(normalized, context, updated_requirements, has_context=has_context)
    if ordinal_route is not None:
        return ordinal_route
    if any(marker in normalized for marker in NATURAL_CONTEXT_MARKERS):
        if has_context:
            return _route(
                "refine" if requirements else "resume",
                "natural_previous_candidates_reference",
                _combine_query(context["previous_user_goal"], query),
                "previous_candidates",
                updated_requirements,
                operations=operations,
                selected_repository_ids=list(context.get("candidate_repository_ids") or []),
            )
        return _clarify("你提到了之前的项目，但当前没有可恢复的候选。请先描述要寻找的项目。", "natural_reference_without_context")
    if normalized in PRIMARY_WORDS:
        primary = str(context.get("primary_repository_id") or "")
        if has_context and primary:
            return _route(
                "resume",
                "primary_candidate_reference",
                context["previous_user_goal"],
                "primary_candidate",
                updated_requirements,
                operations=operations,
                selected_repository_ids=[primary],
            )
        return _clarify("你指的是哪个项目？请给出项目名称，或先选择一个已确认的首选项目。", "primary_candidate_missing")
    if normalized in RESUME_WORDS:
        if has_context:
            return _route(
                "resume",
                "exact_resume_command",
                context["previous_user_goal"],
                "previous_candidates",
                updated_requirements,
                operations=operations,
                selected_repository_ids=list(context.get("candidate_repository_ids") or []),
            )
        return _clarify("你想继续刚才的项目分析，还是开始一次新的项目搜索？请补充一句完整需求。", "resume_without_context")
    if (requirements or operations) and _looks_like_refinement(normalized):
        if has_context:
            return _route(
                "refine",
                "constraint_refinement",
                _combine_query(context["previous_user_goal"], query),
                "previous_candidates",
                updated_requirements,
                operations=operations,
                selected_repository_ids=list(context.get("candidate_repository_ids") or []),
            )
        if _has_search_target(normalized):
            return _route("new_search", "substantive_query_with_constraints", query.strip(), "archive", requirements, operations=operations)
        return _clarify("这些是补充条件，但当前没有可恢复的上一轮需求。请把完整项目需求一起说明。", "refinement_without_context", requirements, operations=operations)
    if normalized in AMBIGUOUS_WORDS or len(normalized) <= 3:
        return _route_with_kimi(root=root, query=query, context=context, requirements=updated_requirements, client=client)
    return _route("new_search", "substantive_query", query.strip(), "archive", requirements, operations=operations)


def _ordinal_candidate_route(
    normalized: str,
    context: dict[str, Any],
    requirements: list[dict[str, Any]],
    *,
    has_context: bool,
) -> dict[str, Any] | None:
    primary = str(context.get("primary_repository_id") or "")
    if normalized in PREVIOUS_CANDIDATE_WORDS:
        if has_context and primary:
            repository_ids = list(context.get("candidate_repository_ids") or [])
            primary_index = repository_ids.index(primary) if primary in repository_ids else -1
            return _route(
                "resume",
                "confirmed_primary_reference",
                str(context.get("previous_user_goal") or ""),
                "primary_candidate",
                requirements,
                selected_candidate_indexes=[primary_index] if primary_index >= 0 else [],
                selected_repository_ids=[primary],
            )
        return _clarify("“上一个项目”无法唯一确定。请先确认首选项目，或直接写出仓库名称。", "previous_candidate_ambiguous", requirements)

    matches = list(ORDINAL_RE.finditer(normalized))
    if not matches:
        return None
    if not has_context:
        return _clarify("当前没有可按序号选择的上一轮候选。请先搜索项目，或直接写出仓库名称。", "ordinal_without_context", requirements)
    if len(matches) > 1 and not any(marker in normalized for marker in ORDINAL_COMPARISON_MARKERS):
        return _clarify("检测到多个候选序号，但无法确定是否要比较它们。请明确写成“比较第一个和第二个”。", "ordinal_reference_ambiguous", requirements)

    indexes: list[int] = []
    for match in matches:
        token = match.group(1)
        position = ORDINAL_VALUES.get(token, int(token) if token.isdigit() else 0)
        index = position - 1
        if index not in indexes:
            indexes.append(index)
    repository_ids = list(context.get("candidate_repository_ids") or [])
    if any(index < 0 or index >= len(repository_ids) for index in indexes):
        return _clarify(
            f"上一轮只有 {len(repository_ids)} 个候选，无法选择这个序号。请使用有效序号或直接写出仓库名称。",
            "ordinal_out_of_range",
            requirements,
        )
    selected = [repository_ids[index] for index in indexes]
    reason = "ordinal_candidate_comparison" if len(selected) > 1 else "ordinal_candidate_reference"
    return _route(
        "resume",
        reason,
        str(context.get("previous_user_goal") or ""),
        "selected_candidates",
        requirements,
        selected_candidate_indexes=indexes,
        selected_repository_ids=selected,
    )


def parse_requirements(query: str) -> dict[str, Any]:
    operations = _cancellation_operations(query)
    active_query = CANCELLATION_RE.sub("", str(query or ""))
    requirements: list[dict[str, Any]] = []
    group_index = 0
    for clause in _constraint_clauses(active_query):
        clause_requirements: list[dict[str, Any]] = []
        optional = _clause_is_optional(clause)
        _extract_clause_requirements(clause, clause_requirements, optional=optional)
        if not clause_requirements:
            continue
        logic = "any_of" if DISJUNCTION_RE.search(clause) and len(clause_requirements) > 1 else "all_of"
        grouped = logic == "any_of" or optional
        group_index += 1
        group_id = f"g{group_index}" if grouped else ""
        for requirement in clause_requirements:
            _append_requirement(
                requirements,
                str(requirement.get("field") or ""),
                str(requirement.get("operator") or "eq"),
                requirement.get("value"),
                hard=bool(requirement.get("hard")),
                group_id=group_id,
                logic=logic,
                optional=optional,
            )
    ambiguity_reason = _requirement_ambiguity(query, requirements)
    return {
        "requirements": requirements,
        "requirement_operations": operations,
        "ambiguous": bool(ambiguity_reason),
        "reason": ambiguity_reason,
    }


def extract_requirements(query: str) -> list[dict[str, Any]]:
    return parse_requirements(query)["requirements"]


def _constraint_clauses(query: str) -> list[str]:
    clauses = []
    for fragment in CLAUSE_SPLIT_RE.split(str(query or "")):
        for clause in POSITIVE_BOUNDARY_RE.split(fragment):
            normalized = clause.strip()
            if normalized:
                clauses.append(normalized)
    return clauses


def _extract_clause_requirements(
    clause: str,
    requirements: list[dict[str, Any]],
    *,
    optional: bool = False,
) -> None:
    lower = f" {clause.casefold()} "
    operator = "eq" if optional else "not_eq" if any(marker in lower for marker in NEGATION_MARKERS) else "eq"
    hard = False if optional else _clause_is_hard(lower)
    language_matches: list[tuple[int, str]] = []
    for token, value in LANGUAGES.items():
        if token == "java" and "javascript" in lower:
            continue
        position = lower.find(token)
        if position >= 0:
            language_matches.append((position, value))
    for _, value in sorted(language_matches, key=lambda item: item[0]):
        _append_requirement(requirements, "language", operator, value, hard=hard)
    for token, value in LICENSES.items():
        if token in lower:
            _append_requirement(requirements, "license", operator, value, hard=hard)
    offline_negative = any(
        marker in lower
        for marker in ("不支持离线", "不能离线", "无法离线", "does not support offline", "doesn't support offline", "no offline support")
    )
    offline_positive = any(
        marker in lower
        for marker in ("完全离线", "离线运行", "离线可用", "fully offline", "offline capable", "air-gapped", "air gapped")
    )
    if offline_negative:
        _append_requirement(requirements, "offline_capable", "eq", False, hard=hard)
    elif offline_positive:
        _append_requirement(requirements, "offline_capable", "eq", True, hard=hard)
    elif "离线" in lower or "offline" in lower:
        _append_requirement(requirements, "offline_capable", "eq", operator != "not_eq", hard=hard)

    if any(marker in lower for marker in ("不能联网", "无需联网", "不需要联网", "不依赖网络", "without internet", "no internet required", "does not require internet")):
        _append_requirement(requirements, "network_required", "eq", False, hard=hard)
    elif any(marker in lower for marker in ("必须联网", "需要联网", "依赖互联网", "requires internet", "internet connection required")):
        _append_requirement(requirements, "network_required", "eq", True, hard=hard)

    external_api_negative = any(marker in lower for marker in (
        "不要云 api", "不要云api", "不需要云 api", "不需要云api", "无需云 api", "无需云api",
        "不依赖云 api", "不依赖云api", "不能依赖外部模型 api", "不依赖外部模型 api",
        "不要 cloud api", "不需要 cloud api", "无需 cloud api", "不依赖 cloud api",
        "does not require cloud api", "doesn't require cloud api", "no cloud api required",
        "works without a cloud api", "without requiring cloud api", "not dependent on cloud api",
        "without hosted inference", "不依赖托管推理",
    ))
    external_api_positive = any(marker in lower for marker in (
        "必须连接 openai", "需要连接 openai", "会调用 openai", "调用 openai", "依赖 openai",
        "依赖云 api", "依赖云api", "需要云 api", "需要云api", "依赖外部模型 api", "依赖托管推理",
        "requires cloud api", "depends on cloud api", "requires external model api", "uses hosted inference",
    ))
    if external_api_negative:
        _append_requirement(requirements, "external_api_required", "eq", False, hard=hard)
    elif external_api_positive:
        _append_requirement(requirements, "external_api_required", "eq", True, hard=hard)

    if any(marker in lower for marker in (
        "不要任何 api key", "不要 api key", "无需 api key", "不需要 api key",
        "no api key required", "without an api key", "without api key",
    )):
        _append_requirement(requirements, "api_key_required", "eq", False, hard=hard)
    elif any(marker in lower for marker in ("需要 api key", "必须 api key", "requires an api key", "api key required")):
        _append_requirement(requirements, "api_key_required", "eq", True, hard=hard)

    if any(marker in lower for marker in ("本地部署", "私有化部署", "self-hosted", "self hosted")):
        _append_requirement(requirements, "hosting_mode", "not_eq" if operator == "not_eq" else "contains", "self_hosted", hard=hard)
    cloud_hosting = any(marker in lower for marker in (
        "云端部署", "部署在云端", "运行在云端", "云端服务", "托管服务", "saas",
        "cloud deployment", "hosted in the cloud", "hosted in cloud", "cloud hosted", "managed cloud", "必须 cloud", "要求 cloud",
    )) or (any(marker in lower for marker in ("不要 cloud", "no cloud ")) and "cloud api" not in lower)
    if cloud_hosting:
        _append_requirement(requirements, "hosting_mode", "not_eq" if operator == "not_eq" else "contains", "cloud_hosted", hard=hard)
    for markers, value in (
        (("免费", " free ", "free to use", "no cost"), "free"),
        (("低成本", "low cost", "low-cost"), "low_cost"),
        (("付费", " paid ", "subscription"), "paid"),
    ):
        if any(marker in lower for marker in markers):
            _append_requirement(requirements, "cost", operator, value, hard=hard)
    for stack in TECH_STACKS:
        if stack.casefold() in lower:
            _append_requirement(requirements, "tech_stack", operator, stack, hard=hard)
    if any(marker in lower for marker in ("多 agent", "多agent", "多智能体", "multi-agent", "multi agent")):
        _append_requirement(requirements, "multi_agent", "eq", True, hard=hard)


def _requirement_ambiguity(query: str, requirements: list[dict[str, Any]]) -> str:
    if _requirement_conflict(requirements):
        return "conflicting_constraint_requirements"
    return ""


def _clause_is_optional(clause: str) -> bool:
    normalized = str(clause or "").casefold()
    return any(marker in normalized for marker in OPTIONAL_MARKERS)


def _cancellation_operations(query: str) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    for match in CANCELLATION_RE.finditer(str(query or "")):
        targets: list[dict[str, Any]] = []
        _extract_clause_requirements(match.group(1), targets)
        for target in targets:
            operation = {
                "operation": "remove",
                "field": str(target.get("field") or ""),
                "value": target.get("value"),
            }
            if operation["field"] and operation not in operations:
                operations.append(operation)
    return operations


def _requirement_conflict(requirements: list[dict[str, Any]]) -> bool:
    by_target: dict[tuple[str, str], set[str]] = {}
    for requirement in requirements:
        if requirement.get("optional") is True:
            continue
        key = (str(requirement.get("field") or ""), str(requirement.get("value") or "").casefold())
        by_target.setdefault(key, set()).add(str(requirement.get("operator") or ""))
    return any({"eq", "not_eq"}.issubset(operators) for operators in by_target.values())


def _apply_requirement_update(
    previous: list[dict[str, Any]],
    current: list[dict[str, Any]],
    operations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result = [dict(item) for item in previous if isinstance(item, dict)]
    current_items = _rebase_requirement_groups(current, result)
    for item in current_items:
        result = [
            existing
            for existing in result
            if not (
                str(existing.get("field") or "") == str(item.get("field") or "")
                and existing.get("value") == item.get("value")
            )
        ]
        result.append(dict(item))
    for operation in operations:
        if operation.get("operation") != "remove":
            continue
        field = str(operation.get("field") or "")
        expected = operation.get("value")
        result = [
            item
            for item in result
            if not (str(item.get("field") or "") == field and item.get("value") == expected)
        ]
    return _normalize_requirement_groups(result)


def _rebase_requirement_groups(
    current: list[dict[str, Any]], previous: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    used = {str(item.get("group_id") or "") for item in previous if item.get("group_id")}
    mapping: dict[str, str] = {}
    counter = 1
    result: list[dict[str, Any]] = []
    for raw in current:
        item = dict(raw)
        group_id = str(item.get("group_id") or "")
        if group_id:
            if group_id not in mapping:
                while f"g{counter}" in used:
                    counter += 1
                mapping[group_id] = f"g{counter}"
                used.add(mapping[group_id])
                counter += 1
            item["group_id"] = mapping[group_id]
        result.append(item)
    return result


def _normalize_requirement_groups(requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for item in requirements:
        group_id = str(item.get("group_id") or "")
        if group_id and item.get("logic") == "any_of":
            counts[group_id] = counts.get(group_id, 0) + 1
    result: list[dict[str, Any]] = []
    for raw in requirements:
        item = dict(raw)
        group_id = str(item.get("group_id") or "")
        if group_id and item.get("logic") == "any_of" and counts.get(group_id, 0) < 2:
            item.pop("group_id", None)
            item.pop("logic", None)
            if item.get("optional") is False:
                item.pop("optional", None)
        result.append(item)
    return result


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
    operations = _validated_requirement_operations(value.get("requirement_operations"))
    if route in {"resume", "refine"}:
        previous = context.get("requirements") if isinstance(context.get("requirements"), list) else []
        requirements = _apply_requirement_update(previous, requirements, operations)
    if route == "clarify":
        question = str(value.get("clarification_question") or "").strip()
        if not question or len(question) > 300:
            raise ValueError("invalid clarification")
        return _clarify(question, "kimi_ambiguous", requirements, parser=f"kimi:{model}", operations=operations)
    if route in {"resume", "refine"} and not _has_resumable_context(context):
        return _clarify("当前没有可恢复的上一轮需求。请写出完整项目需求。", "kimi_route_without_context", requirements, parser=f"kimi:{model}")
    resolved = str(value.get("resolved_query") or "").strip()
    if not resolved or len(resolved) > 2000:
        raise ValueError("invalid resolved query")
    scope = "archive" if route == "new_search" else "previous_candidates"
    selected_repository_ids = [] if scope == "archive" else list(context.get("candidate_repository_ids") or [])
    return _route(
        route,
        "kimi_route",
        resolved,
        scope,
        requirements,
        parser=f"kimi:{model}",
        selected_repository_ids=selected_repository_ids,
        operations=operations,
    )


def _validated_requirements(value: Any) -> list[dict[str, Any]]:
    if value in (None, []):
        return []
    if not isinstance(value, list) or len(value) > 20:
        raise ValueError("invalid requirements")
    result = []
    group_modes: dict[str, tuple[str, bool, bool]] = {}
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("invalid requirement")
        field = str(item.get("field") or "")
        operator = str(item.get("operator") or "")
        requirement_value = item.get("value")
        group_id = str(item.get("group_id") or "").strip()
        logic = str(item.get("logic") or "all_of").strip()
        optional = bool(item.get("optional", False))
        if field not in ALLOWED_FIELDS or operator not in ALLOWED_OPERATORS:
            raise ValueError("invalid requirement fields")
        if group_id and not GROUP_ID_RE.fullmatch(group_id):
            raise ValueError("invalid requirement group")
        if logic not in ALLOWED_LOGICS or (logic == "any_of" and not group_id):
            raise ValueError("invalid requirement logic")
        group_mode = (logic, bool(item.get("hard")) and not optional, optional)
        if group_id and group_id in group_modes and group_modes[group_id] != group_mode:
            raise ValueError("inconsistent requirement group mode")
        if group_id:
            group_modes[group_id] = group_mode
        if field in BOOLEAN_CAPABILITY_FIELDS:
            if not isinstance(requirement_value, bool) or operator not in {"eq", "not_eq"}:
                raise ValueError("invalid boolean requirement")
        else:
            requirement_value = str(requirement_value or "").strip()
            if not requirement_value or len(requirement_value) > 100:
                raise ValueError("invalid requirement value")
        for normalized in _canonical_requirements(field, operator, requirement_value):
            _append_requirement(
                result,
                normalized["field"],
                normalized["operator"],
                normalized["value"],
                hard=bool(item.get("hard")) and not optional,
                group_id=group_id,
                logic=logic,
                optional=optional,
            )
    return _normalize_requirement_groups(result)


def _validated_requirement_operations(value: Any) -> list[dict[str, Any]]:
    if value in (None, []):
        return []
    if not isinstance(value, list) or len(value) > 8:
        raise ValueError("invalid requirement operations")
    result: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict) or item.get("operation") != "remove":
            raise ValueError("invalid requirement operation")
        field = str(item.get("field") or "")
        target = item.get("value")
        if field not in ALLOWED_FIELDS or not isinstance(target, (str, bool)) or target == "":
            raise ValueError("invalid requirement operation target")
        operation = {"operation": "remove", "field": field, "value": target}
        if operation not in result:
            result.append(operation)
    return result


def _route(
    route: str,
    reason: str,
    resolved_query: str,
    scope: str,
    requirements: list[dict[str, Any]],
    *,
    parser: str | None = None,
    selected_candidate_indexes: list[int] | None = None,
    selected_repository_ids: list[str] | None = None,
    operations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "route": route,
        "reason": reason,
        "parser": parser or f"rule:{ROUTER_VERSION}",
        "resolved_query": resolved_query.strip(),
        "retrieval_performed": False,
        "candidate_scope": scope,
        "selected_candidate_indexes": list(selected_candidate_indexes or []),
        "selected_repository_ids": list(selected_repository_ids or []),
        "requirement_schema_version": REQUIREMENT_SCHEMA_VERSION,
        "requirements": requirements,
        "requirement_operations": list(operations or []),
        "clarification_required": False,
        "clarification_question": "",
    }


def _clarify(
    question: str,
    reason: str,
    requirements: list[dict[str, Any]] | None = None,
    *,
    parser: str | None = None,
    operations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    result = _route("clarify", reason, "", "none", requirements or [], parser=parser, operations=operations)
    result["clarification_required"] = True
    result["clarification_question"] = question
    return result


def _clause_is_hard(clause: str) -> bool:
    return any(marker in clause for marker in ("必须", "必须满足", "仅", "不得", "排除", "不能接受", "只要"))


def _append_requirement(
    items: list[dict[str, Any]],
    field: str,
    operator: str,
    value: Any,
    *,
    hard: bool = False,
    group_id: str = "",
    logic: str = "all_of",
    optional: bool = False,
) -> None:
    item = {"field": field, "operator": operator, "value": value, "hard": hard}
    if group_id:
        item.update({"group_id": group_id, "logic": logic, "optional": optional})
    elif optional:
        item["optional"] = True
    if item not in items:
        items.append(item)


def _canonical_requirements(field: str, operator: str, value: Any) -> list[dict[str, Any]]:
    if field != "deployment":
        return [{"field": field, "operator": operator, "value": value}]
    target = str(value or "").strip().casefold()
    if target == "local":
        return [{"field": "hosting_mode", "operator": "not_eq" if operator == "not_eq" else "contains", "value": "self_hosted"}]
    if target == "cloud":
        return [{"field": "hosting_mode", "operator": "not_eq" if operator == "not_eq" else "contains", "value": "cloud_hosted"}]
    if target == "offline":
        return [{"field": "offline_capable", "operator": "eq", "value": operator != "not_eq"}]
    raise ValueError("unsupported legacy deployment requirement")


def _has_resumable_context(context: dict[str, Any]) -> bool:
    return bool(context.get("resumable") and context.get("previous_user_goal") and context.get("candidate_repository_ids"))


def _looks_like_refinement(query: str) -> bool:
    return len(query) <= 80 and any(marker in query for marker in ("更", "要", "必须", "只要", "不要", "适合", "优先", "改成", "限制", "取消", "移除", "删除", "去掉"))


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
