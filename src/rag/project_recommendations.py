from __future__ import annotations

from typing import Any


ELIGIBILITY_ORDER = {"eligible": 0, "unknown": 1, "rejected": 2}
CONSTRAINT_LABELS = {
    "language": "语言",
    "category": "分类",
    "source": "来源",
}


def build_project_recommendations(
    *,
    contexts: list[dict[str, Any]],
    citations: list[dict[str, Any]],
    constraints: dict[str, Any] | None = None,
    requirements: list[dict[str, Any]] | None = None,
    requirement_verification: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build an auditable, deterministic repository ranking from one retrieval result."""
    normalized_constraints = {
        key: str((constraints or {}).get(key) or "").strip()
        for key in CONSTRAINT_LABELS
        if str((constraints or {}).get(key) or "").strip()
    }
    grouped: dict[str, dict[str, Any]] = {}
    for position, context in enumerate(contexts):
        metadata = context.get("metadata") if isinstance(context.get("metadata"), dict) else {}
        full_name = str(metadata.get("full_name") or "").strip()
        if not full_name:
            continue
        candidate = grouped.setdefault(
            full_name,
            {
                "full_name": full_name,
                "first_position": position,
                "best_score": 0.0,
                "chunk_ids": [],
                "languages": [],
                "categories": [],
                "sources": [],
                "source_types": [],
            },
        )
        candidate["best_score"] = max(candidate["best_score"], _score(context.get("score")))
        _append_unique(candidate["chunk_ids"], context.get("chunk_id"))
        _append_unique(candidate["languages"], metadata.get("language"))
        _append_unique(candidate["categories"], metadata.get("category"))
        for source in _strings(metadata.get("sources")):
            _append_unique(candidate["sources"], source)
        _append_unique(candidate["source_types"], metadata.get("source_type"))

    if not grouped:
        return []

    max_score = max(candidate["best_score"] for candidate in grouped.values())
    count = len(grouped)
    zero_score_order = {
        candidate["full_name"]: index
        for index, candidate in enumerate(sorted(grouped.values(), key=lambda item: item["first_position"]))
    }
    recommendations = []
    for candidate in grouped.values():
        matched, unmet, unknown = _evaluate_constraints(candidate, normalized_constraints)
        verified = (requirement_verification or {}).get(candidate["full_name"], {})
        requirement_evaluations = [
            dict(item) for item in verified.get("requirement_evaluations", []) if isinstance(item, dict)
        ]
        for index, evaluation in enumerate(requirement_evaluations):
            source_requirement = requirements[index] if requirements and index < len(requirements) else {}
            if "hard" not in evaluation:
                evaluation["hard"] = bool(source_requirement.get("hard"))
            for key, value in _requirement_group_fields(source_requirement).items():
                evaluation.setdefault(key, value)
        if requirements and not verified:
            requirement_evaluations = [
                {
                    "field": str(requirement.get("field") or ""),
                    "operator": str(requirement.get("operator") or "eq"),
                    "value": requirement.get("value"),
                    "status": "unknown",
                    "reason": "未找到可验证该要求的可信证据。",
                    "evidence_chunk_ids": [],
                    "hard": bool(requirement.get("hard")),
                    **_requirement_group_fields(requirement),
                }
                for requirement in requirements
            ]
        hard_evaluations = [
            item for item in requirement_evaluations
            if bool(item.get("hard")) and item.get("optional") is not True
        ]
        preferences = [
            item for item in requirement_evaluations
            if not bool(item.get("hard")) and item.get("optional") is not True
        ]
        optional_requirements = [item for item in requirement_evaluations if item.get("optional") is True]
        hard_outcomes = _evaluation_outcomes(hard_evaluations)
        hard_matched = [*matched, *hard_outcomes["matched"]]
        hard_unmet = [*unmet, *hard_outcomes["unmet"]]
        hard_unknown = [*unknown, *hard_outcomes["unknown"]]
        eligibility = "rejected" if hard_unmet else "unknown" if hard_unknown else "eligible"
        if max_score > 0:
            match_score = round(candidate["best_score"] / max_score, 4)
        else:
            match_score = round((count - zero_score_order[candidate["full_name"]]) / count, 4)
        citation_indexes = []
        for citation in citations:
            if str(citation.get("full_name") or "").strip() != candidate["full_name"]:
                continue
            index = citation.get("index")
            if isinstance(index, int) and index > 0 and index not in citation_indexes:
                citation_indexes.append(index)
        evidence_chunk_ids = list(candidate["chunk_ids"])
        for chunk_id in _strings(verified.get("evidence_chunk_ids")):
            if chunk_id not in evidence_chunk_ids:
                evidence_chunk_ids.append(chunk_id)
        reasons = _reasons(candidate, hard_matched, hard_unmet, hard_unknown)
        recommendations.append(
            {
                "full_name": candidate["full_name"],
                "rank": 0,
                "match_score": match_score,
                "matched_requirements": hard_matched,
                "unmet_requirements": hard_unmet,
                "unknown_requirements": hard_unknown,
                "preferences": preferences,
                "optional_requirements": optional_requirements,
                "reasons": reasons,
                "citation_indexes": citation_indexes,
                "evidence_chunk_ids": evidence_chunk_ids,
                "requirement_evaluations": requirement_evaluations,
                "eligibility": eligibility,
            }
        )

    recommendations.sort(
        key=lambda item: (
            ELIGIBILITY_ORDER[item["eligibility"]],
            -_preference_counts(item.get("preferences", []))[0],
            _preference_counts(item.get("preferences", []))[1],
            -item["match_score"],
            grouped[item["full_name"]]["first_position"],
            item["full_name"],
        )
    )
    for rank, item in enumerate(recommendations, start=1):
        item["rank"] = rank
    return recommendations


def _evaluate_constraints(
    candidate: dict[str, Any], constraints: dict[str, str]
) -> tuple[list[str], list[str], list[str]]:
    matched: list[str] = []
    unmet: list[str] = []
    unknown: list[str] = []
    values_by_key = {
        "language": candidate["languages"],
        "category": candidate["categories"],
        "source": candidate["sources"],
    }
    for key, expected in constraints.items():
        requirement = f"{CONSTRAINT_LABELS[key]}={expected}"
        values = values_by_key[key]
        if not values:
            unknown.append(requirement)
        elif any(value.casefold() == expected.casefold() for value in values):
            matched.append(requirement)
        else:
            unmet.append(requirement)
    return matched, unmet, unknown


def _reasons(candidate: dict[str, Any], matched: list[str], unmet: list[str], unknown: list[str]) -> list[str]:
    reasons = []
    if matched:
        reasons.append("满足显式筛选：" + "、".join(matched))
    reasons.append(f"本轮检索关联 {len(candidate['chunk_ids'])} 个可审计证据块。")
    source_types = [item for item in candidate["source_types"] if item]
    if source_types:
        reasons.append("证据类型：" + "、".join(source_types))
    if unmet:
        reasons.append("违反显式约束：" + "、".join(unmet))
    if unknown:
        reasons.append("无法验证显式筛选：" + "、".join(unknown))
    return reasons


def _requirement_label(requirement: dict[str, Any]) -> str:
    labels = {
        "license": "许可证", "deployment": "部署方式", "cost": "成本", "tech_stack": "技术栈",
        "hosting_mode": "托管方式", "offline_capable": "离线能力", "network_required": "运行时联网",
        "external_api_required": "外部模型 API", "api_key_required": "API Key", "multi_agent": "多 Agent", **CONSTRAINT_LABELS,
    }
    field = str(requirement.get("field") or "")
    operator = str(requirement.get("operator") or "eq")
    raw_value = requirement.get("value")
    value = "true" if raw_value is True else "false" if raw_value is False else str(raw_value or "")
    symbol = "≠" if operator == "not_eq" else "包含" if operator == "contains" else "="
    return f"{labels.get(field, field)}{symbol}{value}"


def _evaluation_labels(evaluations: list[dict[str, Any]], status: str) -> list[str]:
    return [
        _requirement_label(item)
        for item in evaluations
        if str(item.get("status") or "") == status
    ]


def _requirement_group_fields(requirement: dict[str, Any]) -> dict[str, Any]:
    group_id = str(requirement.get("group_id") or "")
    if group_id:
        return {
            "group_id": group_id,
            "logic": "any_of" if requirement.get("logic") == "any_of" else "all_of",
            "optional": bool(requirement.get("optional", False)),
        }
    return {"optional": True} if requirement.get("optional") is True else {}


def _evaluation_outcomes(evaluations: list[dict[str, Any]]) -> dict[str, list[str]]:
    outcomes: dict[str, list[str]] = {"matched": [], "unmet": [], "unknown": []}
    grouped: dict[str, list[dict[str, Any]]] = {}
    singles: list[dict[str, Any]] = []
    for item in evaluations:
        group_id = str(item.get("group_id") or "")
        if group_id and item.get("logic") == "any_of":
            grouped.setdefault(group_id, []).append(item)
        else:
            singles.append(item)
    for item in singles:
        status = str(item.get("status") or "unknown")
        outcomes[status if status in outcomes else "unknown"].append(_requirement_label(item))
    for members in grouped.values():
        statuses = [str(item.get("status") or "unknown") for item in members]
        status = "matched" if "matched" in statuses else "unmet" if statuses and all(value == "unmet" for value in statuses) else "unknown"
        label = "任一（" + "；".join(_requirement_label(item) for item in members) + "）"
        outcomes[status].append(label)
    return outcomes


def _preference_counts(evaluations: list[dict[str, Any]]) -> tuple[int, int]:
    outcomes = _evaluation_outcomes([item for item in evaluations if isinstance(item, dict)])
    return len(outcomes["matched"]), len(outcomes["unmet"])


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _append_unique(items: list[str], value: Any) -> None:
    normalized = str(value or "").strip()
    if normalized and normalized not in items:
        items.append(normalized)


def _score(value: Any) -> float:
    try:
        return max(0.0, float(value or 0))
    except (TypeError, ValueError):
        return 0.0
