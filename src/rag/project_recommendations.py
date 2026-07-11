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
        reasons = _reasons(candidate, matched, unknown)
        recommendations.append(
            {
                "full_name": candidate["full_name"],
                "rank": 0,
                "match_score": match_score,
                "matched_requirements": matched,
                "unmet_requirements": unmet,
                "reasons": reasons,
                "citation_indexes": citation_indexes,
                "evidence_chunk_ids": candidate["chunk_ids"],
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


def _reasons(candidate: dict[str, Any], matched: list[str], unknown: list[str]) -> list[str]:
    reasons = []
    if matched:
        reasons.append("满足显式筛选：" + "、".join(matched))
    reasons.append(f"本轮检索关联 {len(candidate['chunk_ids'])} 个可审计证据块。")
    source_types = [item for item in candidate["source_types"] if item]
    if source_types:
        reasons.append("证据类型：" + "、".join(source_types))
    if unknown:
        reasons.append("无法验证显式筛选：" + "、".join(unknown))
    return reasons


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
