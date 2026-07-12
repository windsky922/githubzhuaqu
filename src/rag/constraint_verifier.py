from __future__ import annotations

import json
import re
from typing import Any

from src.storage.sqlite_store import connect, initialize


FIELD_LABELS = {
    "language": "语言",
    "category": "分类",
    "source": "来源",
    "license": "许可证",
    "deployment": "部署方式",
    "cost": "成本",
    "tech_stack": "技术栈",
}

DEPLOYMENT_MARKERS = {
    "local": ("本地部署", "私有化部署", "本地运行", "self-hosted", "self hosted", "local deployment", "on-premise", "on premises"),
    "offline": ("完全离线", "离线运行", "离线", "无需联网", "不依赖云 api", "不依赖云api", "air-gapped", "air gapped", "fully offline", "offline", "no internet required", "without internet", "does not require cloud api"),
    "cloud": ("云端服务", "托管服务", "云 api", "云api", "cloud service", "cloud api", "hosted service", "saas"),
}
COST_MARKERS = {
    "free": ("免费使用", "完全免费", "永久免费", "免费社区版", "免费", "free to use", "completely free", "free forever", "free community edition", "no cost", "free"),
    "low_cost": ("低成本", "成本较低", "low cost"),
    "paid": ("付费版本", "付费服务", "付费订阅", "paid plan", "paid service", "subscription pricing"),
}
SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？!?；;])|[\r\n]+")
NEGATION_PATTERNS = (
    "不支持", "不能", "无法", "不可", "不提供", "不依赖", "无需", "没有", "并非", "不是", "不", "非",
    "does not support", "does not support the", "doesn't support", "not support", "cannot", "can't", "is not", "not", "no support",
)
CONDITIONAL_PATTERNS = (
    "仅当", "前提是", "取决于", "视情况", "需要额外", "需另行",
    "only if", "depends on", "subject to", "requires additional", "available when",
)
TRIAL_ONLY_PATTERNS = (
    "免费试用", "试用期", "限时免费", "free trial", "trial period", "free for 7 days", "free for 14 days", "free for 30 days",
)
EXTERNAL_DEPENDENCY_PATTERNS = (
    "依赖云 api", "依赖云api", "需要云 api", "需要云api", "依赖托管推理", "使用托管推理", "需要联网", "必须联网", "依赖互联网", "仅云端",
    "requires cloud api", "depends on cloud api", "hosted inference", "requires internet", "internet connection required", "cloud only", "only available as a cloud service",
)


def verify_project_requirements(
    db_path: Any,
    full_names: list[str],
    requirements: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    names = _unique_strings(full_names)
    if not names or not requirements:
        return {}
    connection = connect(db_path)
    try:
        initialize(connection)
        return {
            full_name: _verify_one(connection, full_name, requirements)
            for full_name in names
        }
    finally:
        connection.close()


def requirement_label(requirement: dict[str, Any]) -> str:
    field = str(requirement.get("field") or "")
    operator = str(requirement.get("operator") or "eq")
    value = str(requirement.get("value") or "")
    symbol = "≠" if operator == "not_eq" else "包含" if operator == "contains" else "="
    return f"{FIELD_LABELS.get(field, field)}{symbol}{value}"


def _verify_one(connection: Any, full_name: str, requirements: list[dict[str, Any]]) -> dict[str, Any]:
    repository = connection.execute(
        "SELECT language, license_name, payload_json FROM repositories WHERE full_name=?",
        (full_name,),
    ).fetchone()
    corpus = connection.execute(
        "SELECT language, category, sources_json, payload_json FROM project_corpus WHERE full_name=? ORDER BY run_date DESC LIMIT 1",
        (full_name,),
    ).fetchone()
    chunks = connection.execute(
        "SELECT chunk_id, chunk_text, source_type FROM rag_chunks WHERE full_name=? AND source_type!='model_enrichment' ORDER BY run_date DESC, chunk_index ASC",
        (full_name,),
    ).fetchall()
    repository_payload = _json_object(repository["payload_json"] if repository else "{}")
    corpus_payload = _json_object(corpus["payload_json"] if corpus else "{}")
    topics = _unique_strings([
        *_list_strings(repository_payload.get("topics")),
        *_list_strings(corpus_payload.get("topics")),
        *_list_strings((corpus_payload.get("project_profile") or {}).get("topics") if isinstance(corpus_payload.get("project_profile"), dict) else []),
    ])
    metadata = {
        "language": _unique_strings([repository["language"] if repository else "", corpus["language"] if corpus else ""]),
        "category": _unique_strings([corpus["category"] if corpus else ""]),
        "source": _list_strings(json.loads(corpus["sources_json"] or "[]")) if corpus else [],
        "license": _unique_strings([repository["license_name"] if repository else ""]),
        "tech_stack": _unique_strings([repository["language"] if repository else "", *topics]),
    }
    matched: list[str] = []
    unmet: list[str] = []
    unknown: list[str] = []
    evidence_chunk_ids: list[str] = []
    for requirement in requirements:
        label = requirement_label(requirement)
        field = str(requirement.get("field") or "")
        operator = str(requirement.get("operator") or "eq")
        expected = str(requirement.get("value") or "")
        if field in {"deployment", "cost"}:
            status, evidence = _verify_text_requirement(field, operator, expected, chunks)
        else:
            status, evidence = _verify_metadata_requirement(field, operator, expected, metadata.get(field, []))
        if status == "matched":
            matched.append(label)
        elif status == "unmet":
            unmet.append(label)
        else:
            unknown.append(label)
        for chunk_id in evidence:
            if chunk_id not in evidence_chunk_ids:
                evidence_chunk_ids.append(chunk_id)
    return {
        "matched_requirements": matched,
        "unmet_requirements": unmet,
        "unknown_requirements": unknown,
        "evidence_chunk_ids": evidence_chunk_ids,
    }


def _verify_metadata_requirement(field: str, operator: str, expected: str, values: list[str]) -> tuple[str, list[str]]:
    normalized_values = {_normalize_value(field, value) for value in values if value}
    if not normalized_values:
        return "unknown", []
    target = _normalize_value(field, expected)
    matched = (
        any(target in value for value in normalized_values)
        if operator == "contains"
        else target in normalized_values
    )
    if operator == "not_eq":
        return ("unmet" if matched else "matched"), []
    return ("matched" if matched else "unmet"), []


def _verify_text_requirement(field: str, operator: str, expected: str, chunks: list[Any]) -> tuple[str, list[str]]:
    target = _normalize_value(field, expected)
    states: dict[str, list[str]] = {
        "supports": [],
        "contradicts": [],
        "conditional": [],
        "trial_only": [],
        "external_dependency": [],
    }
    for row in chunks:
        chunk_id = str(row["chunk_id"] or "")
        for sentence in _sentences(str(row["chunk_text"] or "")):
            state = classify_text_evidence(field, target, sentence)
            if state != "unknown" and chunk_id not in states[state]:
                states[state].append(chunk_id)
    supports = states["supports"]
    blockers = _unique_strings([
        *states["contradicts"],
        *states["trial_only"],
        *states["external_dependency"],
    ])
    conditional = states["conditional"]
    if operator == "not_eq":
        if supports:
            return "unmet", _unique_strings([*supports, *blockers])
        if blockers:
            return "matched", blockers
        if conditional:
            return "unknown", conditional
        return "unknown", []
    if blockers:
        return "unmet", _unique_strings([*blockers, *supports])
    if supports:
        return "matched", supports
    if conditional:
        return "unknown", conditional
    return "unknown", []


def classify_text_evidence(field: str, expected: str, sentence: str) -> str:
    """Classify one deterministic sentence without using model-enriched evidence."""
    text = " ".join(str(sentence or "").casefold().split())
    target = _normalize_value(field, expected)
    markers = DEPLOYMENT_MARKERS if field == "deployment" else COST_MARKERS
    target_markers = markers.get(target, ())
    target_present = any(_contains_marker(text, marker.casefold()) for marker in target_markers)

    if field == "cost" and target == "free" and any(marker in text for marker in TRIAL_ONLY_PATTERNS):
        return "trial_only"
    if field == "deployment" and target in {"local", "offline"} and _has_external_dependency(text):
        return "external_dependency"
    if target_present and _target_is_negated(text, target_markers):
        return "contradicts"
    if target_present and any(marker in text for marker in CONDITIONAL_PATTERNS):
        return "conditional"
    if target_present:
        return "supports"

    if field == "deployment":
        if target == "offline" and _has_markers(text, DEPLOYMENT_MARKERS["cloud"]):
            return "external_dependency"
        if target == "cloud" and _has_markers(text, DEPLOYMENT_MARKERS["offline"]):
            return "contradicts"
    if field == "cost":
        if target == "free" and _has_markers(text, COST_MARKERS["paid"]):
            return "contradicts"
        if target == "paid" and _has_markers(text, COST_MARKERS["free"]):
            return "contradicts"
    return "unknown"


def evidence_state_status(state: str, operator: str = "eq") -> str:
    """Map one evidence state to the existing matched/unmet/unknown contract."""
    if operator == "not_eq":
        if state == "supports":
            return "unmet"
        if state in {"contradicts", "trial_only", "external_dependency"}:
            return "matched"
        return "unknown"
    if state == "supports":
        return "matched"
    if state in {"contradicts", "trial_only", "external_dependency"}:
        return "unmet"
    return "unknown"


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE_SPLIT_RE.split(text) if part.strip()]


def _has_markers(text: str, markers: tuple[str, ...]) -> bool:
    return any(_contains_marker(text, marker.casefold()) for marker in markers)


def _target_is_negated(text: str, markers: tuple[str, ...]) -> bool:
    for marker in markers:
        position = text.find(marker.casefold())
        if position < 0:
            continue
        prefix = text[max(0, position - 28):position].rstrip(" ：:-")
        if any(prefix.endswith(negation) for negation in NEGATION_PATTERNS):
            return True
    return False


def _has_external_dependency(text: str) -> bool:
    for marker in EXTERNAL_DEPENDENCY_PATTERNS:
        position = text.find(marker)
        if position < 0:
            continue
        prefix = text[max(0, position - 12):position]
        if not any(negation in prefix for negation in ("不", "无", "not ", "does not ", "doesn't ")):
            return True
    return False


def _contains_marker(text: str, marker: str) -> bool:
    if marker.isascii() and marker.replace(" ", "").replace("-", "").isalnum():
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(marker)}(?![a-z0-9])", text))
    return marker in text


def _normalize_value(field: str, value: Any) -> str:
    text = str(value or "").strip().casefold()
    if field == "license":
        text = text.removesuffix(" license").replace("apache 2.0", "apache-2.0")
    return text


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(str(value or "{}"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _list_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _unique_strings(values: list[Any]) -> list[str]:
    result = []
    for value in values:
        normalized = str(value or "").strip()
        if normalized and normalized not in result:
            result.append(normalized)
    return result
