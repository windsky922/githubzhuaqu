from __future__ import annotations

import re
from typing import Any


_CITATION_RE = re.compile(r"\[(\d+)\]")
_REPO_RE = re.compile(r"\b([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b")
_URL_RE = re.compile(r"https?://\S+")


def validate_rag_answer(
    *,
    answer: str,
    citations: list[dict[str, Any]],
    contexts: list[dict[str, Any]],
    min_chars: int = 24,
) -> dict[str, Any]:
    text = str(answer or "").strip()
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

    return {
        "passed": not issues,
        "issues": issues,
        "citation_validity": not any(
            issue == "missing_citation" or issue.startswith("invalid_citation:") for issue in issues
        ),
        "evidence_relevance": "not_evaluated",
        "claim_support": "not_evaluated",
        "data_freshness": "unknown",
        "used_citation_indexes": sorted(used_indexes),
        "valid_citation_indexes": sorted(valid_indexes),
        "mentioned_repositories": sorted(mentioned_repositories),
        "unknown_repositories": unknown_repositories,
    }


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
