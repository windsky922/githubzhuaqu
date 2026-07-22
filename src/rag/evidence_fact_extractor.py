"""Closed-world, clause-scoped extraction from quoted source text.

Evidence must not borrow a positive setup/UI/optional statement to cancel a
runtime/inference/required blocker elsewhere in the same quote.  This module
therefore keeps each deterministic fact together with the clause that states
it.  Unknown scope is intentionally not inferred from adjacent clauses.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from typing import Any


_PATTERNS = (
    ("network_required", False, "required", r"(?:does not|doesn't|no need to|无需|不需要|不必).{0,28}(?:network|internet|online|联网|网络)"),
    ("network_required", True, "required", r"(?:requires?|must have|needs?|需要|必须).{0,28}(?:network|internet|online|联网|网络).{0,18}(?:access|connection|连接|访问)?"),
    ("offline_capable", True, "supported", r"(?:works?|runs?|available|supports?|支持|可).{0,20}(?:offline|离线)"),
    ("offline_capable", False, "prohibited", r"(?:does not|doesn't|cannot|无法|不能|不支持).{0,20}(?:offline|离线)"),
    ("api_key_required", True, "required", r"(?:requires?|needs?|must have|需要|必须).{0,20}(?:api[ -]?key|token|密钥|令牌)"),
    ("api_key_required", False, "required", r"(?:does not|doesn't|no need to|无需|不需要).{0,20}(?:api[ -]?key|token|密钥|令牌)"),
    ("external_api_required", True, "required", r"(?:requires?|needs?|must use|需要|必须).{0,28}(?:external|cloud).{0,12}api|(?:需要|必须).{0,20}(?:外部|云).{0,12}api|(?:uses?|requires?)\s+hosted inference|hosted inference|托管推理|(?:calls?|connects? to|调用|连接)\s*openai"),
    ("hosting_mode", "self_hosted", "supported", r"(?:self[ -]?hosted)\s+(?:mode|deployment|hosting|ui)(?:\s+(?:is|are))?\s+(?:supported|available)|(?:自托管\s*(?:模式|部署)?\s*(?:支持|可用))"),
    ("hosting_mode", "cloud", "required", r"(?:requires?|needs?|must use)\s+(?:cloud[ -]?hosted|cloud hosting)|(?:cloud[ -]?hosted|cloud hosting)\s+(?:is|are)\s+required|(?:需要|必须)\s*(?:云托管|云部署)"),
    ("cost", "free", "supported", r"(?:is|are)\s+(?:completely\s+)?free(?:\s+of charge)?|(?<!不)(?<!非)免费"),
    ("cost", "paid", "required", r"(?:requires?|needs?)\s+(?:a\s+)?(?:paid subscription|subscription)|(?:is|are)\s+(?:a\s+)?(?:paid plan|subscription)|(?<!不)付费"),
)
_CLAUSE_RE = re.compile(r"(?<=[.!?。！？;；])\s*|\s+(?:but|however|while)\s+|(?:但|但是|而)", re.IGNORECASE)


@dataclass(frozen=True)
class ScopedFact:
    predicate: str
    value: Any
    modality: str
    component: str | None
    phase: str | None
    surface: str | None
    necessity: str | None
    source_span: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_quote_facts(quote: str) -> list[ScopedFact]:
    """Return all independently stated facts; never merge clause scopes."""
    text = str(quote or "").strip()
    if not text:
        return []
    facts: list[ScopedFact] = []
    for clause in (part.strip() for part in _CLAUSE_RE.split(text) if part.strip()):
        lowered = clause.casefold()
        matches = [
            (predicate, value, modality)
            for predicate, value, modality, pattern in _PATTERNS
            if re.search(pattern, lowered, re.IGNORECASE)
        ]
        # Negated patterns contain the same words as affirmative requirements.
        # Resolve this only inside the clause; facts in another clause survive.
        negated = {predicate for predicate, value, _ in matches if value is False}
        for predicate, value, modality in matches:
            if predicate in negated and value is True:
                continue
            facts.append(ScopedFact(
                predicate=predicate,
                value=value,
                modality=modality,
                component=_component(lowered),
                phase=_phase(lowered),
                surface=_surface(lowered),
                necessity=_necessity(lowered),
                source_span=clause,
            ))
    return facts


def extract_quote_semantics(quote: str) -> dict[str, Any] | None:
    """Compatibility view: return one fact only when the quote is unambiguous."""
    facts = extract_quote_facts(quote)
    unique = {(fact.predicate, repr(fact.value), fact.modality) for fact in facts}
    if len(facts) != 1 or len(unique) != 1:
        return None
    fact = facts[0]
    return {"predicate": fact.predicate, "value": fact.value, "modality": fact.modality}


def _phase(text: str) -> str | None:
    if re.search(r"\b(setup|install(?:ation)?|initial download)\b|安装|部署准备", text):
        return "setup"
    if re.search(r"\b(runtime|run(?:ning)?|inference)\b|运行时|推理", text):
        return "runtime"
    return None


def _surface(text: str) -> str | None:
    if re.search(r"\b(ui|web ui|frontend|control plane)\b|界面|前端|控制面", text):
        return "ui"
    if re.search(r"\b(inference|engine|model|data plane)\b|推理|引擎|数据面", text):
        return "inference"
    return None


def _component(text: str) -> str | None:
    surface = _surface(text)
    return surface


def _necessity(text: str) -> str | None:
    if re.search(r"\b(optional|may|can choose)\b|可选|非必需", text):
        return "optional"
    if re.search(r"\b(required|requires?|must|needs?)\b|必须|需要|依赖|调用|连接", text):
        return "required"
    return None
