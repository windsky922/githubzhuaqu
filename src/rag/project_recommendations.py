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
        matched.extend(item for item in _strings(verified.get("matched_requirements")) if item not in matched)
        unmet.extend(item for item in _strings(verified.get("unmet_requirements")) if item not in unmet)
        unknown.extend(item for item in _strings(verified.get("unknown_requirements")) if item not in unknown)
        if requirements and not verified:
            unknown.extend(
                item for item in (_requirement_label(requirement) for requirement in requirements)
                if item not in unknown
            )
            requirement_evaluations = [
                {
                    "field": str(requirement.get("field") or ""),
                    "operator": str(requirement.get("operator") or "eq"),
                    "value": requirement.get("value"),
                    "status": "unknown",
                    "reason": "未找到可验证该要求的可信证据。",
                    "evidence_chunk_ids": [],
                }
                for requirement in requirements
            ]
        eligibility = "rejected" if unmet else "unknown" if unknown else "eligible"
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
        reasons = _reasons(candidate, matched, unmet, unknown)
        recommendations.append(
            {
                "full_name": candidate["full_name"],
                "rank": 0,
                "match_score": match_score,
                "matched_requirements": matched,
                "unmet_requirements": unmet,
                "unknown_requirements": unknown,
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
        "external_api_required": "外部模型 API", "api_key_required": "API Key", **CONSTRAINT_LABELS,
    }
    field = str(requirement.get("field") or "")
    operator = str(requirement.get("operator") or "eq")
    raw_value = requirement.get("value")
    value = "true" if raw_value is True else "false" if raw_value is False else str(raw_value or "")
    symbol = "≠" if operator == "not_eq" else "包含" if operator == "contains" else "="
    return f"{labels.get(field, field)}{symbol}{value}"


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
