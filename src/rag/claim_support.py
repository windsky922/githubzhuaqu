"""Deterministic structured-fact support checks for RAG answer claims.

The provider may describe a claim, but it cannot decide that the claim is true.
This module compares a claim fact with a source-bound evidence fact and verifies
that every source fact field has a concrete anchor in the quoted source text.
Unknown structure is intentionally insufficient rather than guessed.
"""

from __future__ import annotations

import re
from typing import Any


FACT_FIELDS = (
    "subject",
    "component",
    "phase",
    "predicate",
    "value",
    "modality",
    "edition",
    "condition",
    "temporal",
    "quantity",
)
_REQUIRED = ("subject", "component", "phase", "predicate", "value", "modality", "edition")
_PREDICATE_ANCHORS = {
    "network_required": ("network", "internet", "online", "联网", "网络"),
    "offline_capable": ("offline", "离线"),
    "api_key_required": ("api key", "apikey", "token", "密钥", "令牌"),
    "external_api_required": ("external api", "cloud api", "外部 api", "云 api"),
    "hosting_mode": ("self-hosted", "self hosted", "cloud", "部署", "托管"),
    "cost": ("free", "paid", "price", "免费", "付费", "价格"),
}
_MODALITY_ANCHORS = {
    "required": ("require", "must", "mandatory", "需要", "必须"),
    "optional": ("optional", "may", "可选", "可以"),
    "supported": ("support", "available", "支持", "可用"),
    "prohibited": ("not allowed", "forbidden", "禁止", "不允许"),
}
_NEGATION_RE = re.compile(r"(?:\b(?:not|no|without|cannot|never)\b|不|无|未|没有|无法|不能)", re.IGNORECASE)


def normalize_fact(value: Any) -> tuple[dict[str, Any] | None, str]:
    """Return a closed-world fact; missing or unknown fields are insufficient."""
    if not isinstance(value, dict):
        return None, "missing_structured_fact"
    fact: dict[str, Any] = {}
    for field in FACT_FIELDS:
        item = value.get(field)
        if field in _REQUIRED:
            if field == "value":
                if item is None or isinstance(item, (dict, list)):
                    return None, f"missing_fact_{field}"
                fact[field] = item
                continue
            normalized = _normalize_string(item)
            if not normalized:
                return None, f"missing_fact_{field}"
            fact[field] = normalized
            continue
        if item is None or item == "":
            fact[field] = None
        elif isinstance(item, (str, int, float, bool)):
            fact[field] = _normalize_string(item) if isinstance(item, str) else item
        else:
            return None, f"invalid_fact_{field}"
    return fact, ""


def compare_facts(*, claim: dict[str, Any], evidence: dict[str, Any], quote: str) -> dict[str, str]:
    """Compare structured facts and anchor evidence fields in its source quote."""
    claim_fact, claim_error = normalize_fact(claim)
    evidence_fact, evidence_error = normalize_fact(evidence)
    result = {
        "polarity_status": "insufficient",
        "scope_status": "insufficient",
        "semantic_support_status": "insufficient",
        "reason": claim_error or evidence_error or "",
    }
    if claim_fact is None or evidence_fact is None:
        return result
    anchor_error = evidence_fact_anchor_error(evidence_fact, quote)
    if anchor_error:
        result["reason"] = anchor_error
        return result

    if _polarity(claim_fact) != _polarity(evidence_fact):
        result["polarity_status"] = "contradicted"
        result["reason"] = "polarity_mismatch"
        return result
    result["polarity_status"] = "matched"

    scope_fields = ("subject", "component", "phase", "edition", "condition", "temporal")
    scope_mismatch = _first_mismatch(claim_fact, evidence_fact, scope_fields)
    if scope_mismatch:
        result["scope_status"] = "mismatched"
        result["reason"] = f"{scope_mismatch}_mismatch"
        return result
    result["scope_status"] = "matched"

    semantic_fields = ("predicate", "value", "modality", "quantity")
    semantic_mismatch = _first_mismatch(claim_fact, evidence_fact, semantic_fields)
    if semantic_mismatch:
        result["semantic_support_status"] = "mismatched"
        result["reason"] = f"{semantic_mismatch}_mismatch"
        return result
    result["semantic_support_status"] = "supported"
    result["reason"] = ""
    return result


def evidence_fact_anchor_error(fact: dict[str, Any], quote: str) -> str:
    """Require source wording for every non-repository evidence fact field."""
    text = _normalize_string(quote)
    if not text:
        return "empty_evidence_quote"
    for field in ("component", "phase", "edition", "condition", "temporal", "quantity"):
        value = fact.get(field)
        if value is not None and _normalize_string(value) not in text:
            return f"unanchored_{field}"
    predicate = str(fact["predicate"])
    anchors = _PREDICATE_ANCHORS.get(predicate, (predicate,))
    if not any(_normalize_string(anchor) in text for anchor in anchors):
        return "unanchored_predicate"
    modality = str(fact["modality"])
    modality_anchors = _MODALITY_ANCHORS.get(modality, (modality,))
    if not any(_normalize_string(anchor) in text for anchor in modality_anchors):
        return "unanchored_modality"
    expected_negative = _polarity(fact) == "negative"
    if bool(_NEGATION_RE.search(text)) != expected_negative:
        return "unanchored_value"
    return ""


def _polarity(fact: dict[str, Any]) -> str:
    value = fact.get("value")
    if isinstance(value, bool):
        return "positive" if value else "negative"
    return "negative" if isinstance(value, str) and value.startswith("not ") else "positive"


def _first_mismatch(claim: dict[str, Any], evidence: dict[str, Any], fields: tuple[str, ...]) -> str:
    for field in fields:
        if claim.get(field) != evidence.get(field):
            return field
    return ""


def _normalize_string(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())
