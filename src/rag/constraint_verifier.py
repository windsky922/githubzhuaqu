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
    "local": ("本地部署", "私有化部署", "离线运行", "self-hosted", "self hosted", "docker compose"),
    "cloud": ("云端服务", "托管服务", "cloud service", "saas"),
}
COST_MARKERS = {
    "free": ("免费使用", "完全免费", "free to use", "no cost"),
    "low_cost": ("低成本", "low cost"),
    "paid": ("付费版本", "付费服务", "paid plan", "subscription pricing"),
}


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
    markers = DEPLOYMENT_MARKERS if field == "deployment" else COST_MARKERS
    target = _normalize_value(field, expected)
    target_hits = _chunk_hits(chunks, markers.get(target, ()))
    opposite_hits = _chunk_hits(chunks, tuple(marker for key, values in markers.items() if key != target for marker in values))
    if operator == "not_eq":
        if target_hits:
            return "unmet", target_hits
        if opposite_hits:
            return "matched", opposite_hits
        return "unknown", []
    if target_hits:
        return "matched", target_hits
    if opposite_hits:
        return "unmet", opposite_hits
    return "unknown", []


def _chunk_hits(chunks: list[Any], markers: tuple[str, ...]) -> list[str]:
    hits = []
    for row in chunks:
        text = str(row["chunk_text"] or "").casefold()
        if any(_contains_marker(text, marker.casefold()) for marker in markers):
            hits.append(str(row["chunk_id"] or ""))
    return _unique_strings(hits)


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
