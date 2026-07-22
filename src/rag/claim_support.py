"""Deterministic structured-fact support checks for RAG answer claims.

The provider may describe a claim, but it cannot decide that the claim is true.
This module compares a claim fact with a source-bound evidence fact and verifies
that every source fact field has a concrete anchor in the quoted source text.
Unknown structure is intentionally insufficient rather than guessed.
"""

from __future__ import annotations

import re
from typing import Any

from src.rag.evidence_fact_extractor import ScopedFact, extract_quote_facts

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
    """Require one source clause that supports both fact and its scope."""
    text = _normalize_string(quote)
    if not text:
        return "empty_evidence_quote"
    candidates = [
        item for item in extract_quote_facts(quote)
        if item.predicate == fact.get("predicate")
        and item.value == fact.get("value")
        and item.modality == fact.get("modality")
    ]
    if not candidates:
        same_predicate = [item for item in extract_quote_facts(quote) if item.predicate == fact.get("predicate")]
        if same_predicate:
            if all(item.value != fact.get("value") for item in same_predicate):
                return "quote_value_mismatch"
            if all(item.modality != fact.get("modality") for item in same_predicate):
                return "quote_modality_mismatch"
        return "unextractable_predicate_value"
    compatible = [item for item in candidates if _scope_anchors_fact(item, fact)]
    if not compatible:
        for field, extracted_value in (("component", candidates[0].component), ("phase", candidates[0].phase)):
            if fact.get(field) is not None and _normalize_string(fact[field]) != _normalize_string(extracted_value):
                return f"unanchored_{field}"
        return "unanchored_scope"
    if len(compatible) != 1:
        return "ambiguous_scoped_fact"
    span = _normalize_string(compatible[0].source_span)
    for field in ("edition", "condition", "temporal", "quantity"):
        value = fact.get(field)
        if value is not None and _normalize_string(value) not in span:
            return f"unanchored_{field}"
    return ""


def _scope_anchors_fact(extracted: ScopedFact, fact: dict[str, Any]) -> bool:
    """Do not accept a scope word that occurs only in a neighbouring clause."""
    for field, extracted_value in (("component", extracted.component), ("phase", extracted.phase)):
        value = fact.get(field)
        if value is not None and _normalize_string(value) != _normalize_string(extracted_value):
            return False
    # Existing fact schema has modality but no separate necessity field.  A
    # required/optional phrase therefore must agree when it is explicit.
    if extracted.necessity and fact.get("modality") in {"required", "optional"}:
        if fact["modality"] != extracted.necessity:
            return False
    return True


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
