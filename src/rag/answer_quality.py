from __future__ import annotations

import re
from typing import Any


_CITATION_RE = re.compile(r"\[(\d+)\]")
_REPO_RE = re.compile(r"\b([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b")
_URL_RE = re.compile(r"https?://\S+")
_UNSAFE_INSTRUCTION_RE = re.compile(
    r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions|system\s+(?:prompt|message)|忽略(?:之前|先前|以上)(?:的)?指令|系统(?:提示|消息)",
    re.IGNORECASE,
)
_CLAIM_LEDGER_RE = re.compile(r"\s*<claim_ledger>(.*?)</claim_ledger>\s*\Z", re.DOTALL)
_FACT_MARKER_RE = re.compile(
    r"(?:\b(?:is|supports|requires|depends|can(?:not)?|cannot|offline|best|better|rank(?:ed|ing)?|first)\b|是|支持|需要|依赖|可以|不能|无法|离线|优于|更适合|最佳|首选|第一|排名)",
    re.IGNORECASE,
)
_NEGATION_RE = re.compile(r"(?:\b(?:not|no|without|cannot)\b|不|无|未|没有|无法|不能)", re.IGNORECASE)


def validate_rag_answer(
    *,
    answer: str,
    citations: list[dict[str, Any]],
    contexts: list[dict[str, Any]],
    min_chars: int = 24,
) -> dict[str, Any]:
    text, ledger, ledger_error = _extract_claim_ledger(answer)
    issues: list[str] = []
    valid_indexes = _valid_citation_indexes(citations)
    used_indexes = _used_citation_indexes(text)
    known_repositories = _known_repositories(citations=citations, contexts=contexts)
    mentioned_repositories = _mentioned_repositories(text)
    unknown_repositories = sorted(repo for repo in mentioned_repositories if repo.lower() not in known_repositories)

    if len(text) < min_chars:
        issues.append("answer_too_short")
    if citations and not used_indexes:
        issues.append("missing_citation")
    invalid_indexes = sorted(index for index in used_indexes if index not in valid_indexes)
    if invalid_indexes:
        issues.append("invalid_citation:" + ",".join(str(index) for index in invalid_indexes))
    if unknown_repositories:
        issues.append("unknown_repository:" + ",".join(unknown_repositories[:5]))
    if len(contexts) < 1:
        issues.append("no_evidence")
    if _UNSAFE_INSTRUCTION_RE.search(text):
        issues.append("unsafe_instruction")
    claim_checks = _validate_claims(
        answer=text,
        ledger=ledger,
        ledger_error=ledger_error,
        citations=citations,
        contexts=contexts,
    )
    claim_failures = [check for check in claim_checks if check["status"] != "supported"]
    if claim_failures:
        issues.extend(f"claim_support:{check['id']}:{check['status']}" for check in claim_failures)
    applicable_claims = [check for check in claim_checks if check["status"] != "not_applicable"]
    claim_support = "supported" if applicable_claims and not claim_failures else "failed" if claim_failures else "not_applicable"
    evidence_relevance = "passed" if applicable_claims and not claim_failures else "failed" if claim_failures else "not_applicable"

    return {
        "passed": not issues,
        "issues": issues,
        "citation_validity": not any(
            issue == "missing_citation" or issue.startswith("invalid_citation:") for issue in issues
        ),
        "evidence_relevance": evidence_relevance,
        "claim_support": claim_support,
        "data_freshness": "unknown",
        "claim_checks": claim_checks,
        "validated_answer": text,
        "used_citation_indexes": sorted(used_indexes),
        "valid_citation_indexes": sorted(valid_indexes),
        "mentioned_repositories": sorted(mentioned_repositories),
        "unknown_repositories": unknown_repositories,
    }


def _extract_claim_ledger(answer: str) -> tuple[str, dict[str, Any] | None, str]:
    text = str(answer or "").strip()
    match = _CLAIM_LEDGER_RE.search(text)
    if not match:
        return text, None, ""
    visible = text[: match.start()].strip()
    try:
        import json

        ledger = json.loads(match.group(1))
    except (json.JSONDecodeError, TypeError):
        return visible, None, "invalid_ledger"
    if not isinstance(ledger, dict) or ledger.get("schema_version") != 1 or not isinstance(ledger.get("claims"), list):
        return visible, None, "invalid_ledger"
    return visible, ledger, ""


def _validate_claims(
    *,
    answer: str,
    ledger: dict[str, Any] | None,
    ledger_error: str,
    citations: list[dict[str, Any]],
    contexts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if ledger_error:
        return [{"id": "ledger", "kind": "ledger", "status": "insufficient", "reason": ledger_error, "evidence_refs": []}]
    requires_ledger = bool(_mentioned_repositories(answer) and _FACT_MARKER_RE.search(answer))
    if ledger is None:
        return ([{"id": "ledger", "kind": "ledger", "status": "insufficient", "reason": "missing_ledger", "evidence_refs": []}] if requires_ledger else [])
    claims = ledger["claims"]
    if not claims:
        return ([{"id": "ledger", "kind": "ledger", "status": "insufficient", "reason": "missing_claim", "evidence_refs": []}] if requires_ledger else [])
    citation_map = {_int_value(item.get("index")) or index: item for index, item in enumerate(citations, start=1)}
    context_map = {str(item.get("chunk_id") or ""): item for item in contexts}
    checks: list[dict[str, Any]] = []
    for fallback_id, claim in enumerate(claims, start=1):
        checks.append(_validate_claim(claim, fallback_id, answer, citation_map, context_map))
    return checks


def _validate_claim(
    claim: Any,
    fallback_id: int,
    answer: str,
    citation_map: dict[int, dict[str, Any]],
    context_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if not isinstance(claim, dict):
        return {"id": str(fallback_id), "kind": "unknown", "status": "insufficient", "reason": "invalid_claim", "evidence_refs": []}
    claim_id = str(claim.get("id") or fallback_id)
    kind = str(claim.get("kind") or "")
    text = str(claim.get("text") or "").strip()
    subjects = [str(item).strip().lower() for item in claim.get("subjects", []) if str(item).strip()]
    indexes = {_int_value(item) for item in claim.get("citation_indexes", []) if _int_value(item) > 0}
    refs = claim.get("evidence_refs") if isinstance(claim.get("evidence_refs"), list) else []
    result = {"id": claim_id, "kind": kind or "unknown", "status": "insufficient", "reason": "", "evidence_refs": refs}
    if kind not in {"project_fact", "comparison", "ranking"} or not text or not subjects or not indexes or not refs:
        result["reason"] = "invalid_claim"
        return result
    if text not in answer or not _claim_has_citations(answer, text, indexes):
        result["reason"] = "unbound_answer_claim"
        return result
    if kind == "project_fact" and len(subjects) != 1:
        result["reason"] = "project_fact_subject_count"
        return result
    if kind in {"comparison", "ranking"} and len(set(subjects)) < 2:
        result["reason"] = "comparison_without_subjects"
        return result
    covered: set[str] = set()
    contradiction = False
    for ref in refs:
        if not isinstance(ref, dict):
            result["reason"] = "invalid_evidence_ref"
            return result
        index = _int_value(ref.get("citation_index"))
        repository = str(ref.get("repository") or "").strip().lower()
        chunk_id = str(ref.get("chunk_id") or "")
        quote = str(ref.get("quote") or "").strip()
        citation = citation_map.get(index)
        context = context_map.get(chunk_id)
        metadata = context.get("metadata") if isinstance(context, dict) and isinstance(context.get("metadata"), dict) else {}
        source_repo = str(metadata.get("full_name") or "").strip().lower()
        source_text = str(context.get("text") or "") if isinstance(context, dict) else ""
        if index not in indexes or not citation or str(citation.get("full_name") or "").strip().lower() != repository or str(citation.get("chunk_id") or "") != chunk_id:
            result["reason"] = "citation_repository_chunk_mismatch"
            return result
        if source_repo != repository or len(quote) < 12 or _normalize(quote) not in _normalize(source_text):
            result["reason"] = "irrelevant_evidence"
            return result
        if kind == "project_fact" and repository != subjects[0]:
            result["reason"] = "cross_project_evidence"
            return result
        covered.add(repository)
        contradiction = contradiction or (_has_negation(text) != _has_negation(quote))
    if kind in {"comparison", "ranking"} and not set(subjects).issubset(covered):
        result["reason"] = "comparison_without_basis"
        return result
    if contradiction:
        result["status"] = "contradicted"
        result["reason"] = "polarity_conflicts_with_evidence"
        return result
    result["status"] = "supported"
    result["reason"] = ""
    return result


def _claim_has_citations(answer: str, text: str, indexes: set[int]) -> bool:
    position = answer.find(text)
    if position < 0:
        return False
    nearby = answer[position + len(text) : position + len(text) + 48]
    return indexes.issubset(_used_citation_indexes(nearby))


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()


def _has_negation(value: str) -> bool:
    return bool(_NEGATION_RE.search(value))


def _valid_citation_indexes(citations: list[dict[str, Any]]) -> set[int]:
    indexes = set()
    for fallback_index, citation in enumerate(citations, start=1):
        index = _int_value(citation.get("index")) or fallback_index
        if index > 0:
            indexes.add(index)
    return indexes


def _used_citation_indexes(answer: str) -> set[int]:
    indexes = set()
    for match in _CITATION_RE.finditer(answer):
        index = _int_value(match.group(1))
        if index > 0:
            indexes.add(index)
    return indexes


def _known_repositories(*, citations: list[dict[str, Any]], contexts: list[dict[str, Any]]) -> set[str]:
    repositories = set()
    for citation in citations:
        name = str(citation.get("full_name") or "").strip().lower()
        if name:
            repositories.add(name)
    for context in contexts:
        metadata = context.get("metadata") if isinstance(context.get("metadata"), dict) else {}
        name = str(metadata.get("full_name") or "").strip().lower()
        if name:
            repositories.add(name)
    return repositories


def _mentioned_repositories(answer: str) -> set[str]:
    without_urls = _URL_RE.sub("", answer)
    return {match.group(1).strip() for match in _REPO_RE.finditer(without_urls)}


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
