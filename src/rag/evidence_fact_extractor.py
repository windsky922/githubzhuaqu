"""Closed-world extraction of evidence semantics from quoted source text."""

from __future__ import annotations

import re
from typing import Any


_PATTERNS = (
    ("network_required", False, "required", r"(?:does not|doesn't|no need to|无需|不需要|不必).{0,28}(?:network|internet|online|联网|网络)"),
    ("network_required", True, "required", r"(?:requires?|must have|needs?|需要|必须).{0,28}(?:network|internet|online|联网|网络).{0,18}(?:access|connection|连接|访问)?"),
    ("offline_capable", True, "supported", r"(?:works?|runs?|available|支持|可).{0,20}(?:offline|离线)"),
    ("offline_capable", False, "prohibited", r"(?:does not|doesn't|cannot|无法|不能|不支持).{0,20}(?:offline|离线)"),
    ("api_key_required", True, "required", r"(?:requires?|needs?|must have|需要|必须).{0,20}(?:api[ -]?key|token|密钥|令牌)"),
    ("api_key_required", False, "required", r"(?:does not|doesn't|no need to|无需|不需要).{0,20}(?:api[ -]?key|token|密钥|令牌)"),
    ("external_api_required", True, "required", r"(?:requires?|needs?|must use|需要|必须).{0,28}(?:external|cloud).{0,12}api|(?:需要|必须).{0,20}(?:外部|云).{0,12}api"),
    ("hosting_mode", "self_hosted", "supported", r"(?:self[ -]?hosted)\s+(?:mode|deployment|hosting)\s+(?:is|are)\s+(?:supported|available)|(?:自托管)\s*(?:模式|部署)?\s*(?:支持|可用)"),
    ("hosting_mode", "cloud", "required", r"(?:requires?|needs?|must use)\s+(?:cloud[ -]?hosted|cloud hosting)|(?:cloud[ -]?hosted|cloud hosting)\s+(?:is|are)\s+required|(?:需要|必须)\s*(?:云托管|云部署)"),
    ("cost", "free", "supported", r"(?:is|are)\s+(?:completely\s+)?free(?:\s+of charge)?|(?<!不)(?<!非)免费"),
    ("cost", "paid", "required", r"(?:requires?|needs?)\s+(?:a\s+)?(?:paid subscription|subscription)|(?:is|are)\s+(?:a\s+)?(?:paid plan|subscription)|(?<!不)付费"),
)


def extract_quote_semantics(quote: str) -> dict[str, Any] | None:
    """Return one unambiguous predicate/value/modality tuple, else None."""
    text = str(quote or "").strip().lower()
    if not text:
        return None
    matches = [
        {"predicate": predicate, "value": value, "modality": modality}
        for predicate, value, modality, pattern in _PATTERNS
        if re.search(pattern, text, re.IGNORECASE)
    ]
    # A negated requirement still contains words such as "require network".
    # Prefer the explicitly negated boolean reading over that positive substring.
    negative_predicates = {
        str(item["predicate"])
        for item in matches
        if item["value"] is False
    }
    matches = [
        item
        for item in matches
        if not (item["predicate"] in negative_predicates and item["value"] is True)
    ]
    unique = {(item["predicate"], repr(item["value"]), item["modality"]) for item in matches}
    if len(unique) != 1:
        return None
    return matches[0]
