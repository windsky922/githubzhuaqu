from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def rag_ask_messages(
    *,
    root: Path,
    question: str,
    prompt_context: str,
    citations: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    recommendations: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    prompt = (root / "prompts" / "rag_ask.md").read_text(encoding="utf-8")
    payload = {
        "question": question,
        "prompt_context": prompt_context,
        "citations": citations,
        "evidence": evidence,
        "recommendations": recommendations or [],
    }
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
    ]


def follow_up_route_messages(*, root: Path, query: str, context: dict[str, Any]) -> list[dict[str, str]]:
    prompt = (root / "prompts" / "follow_up_router.md").read_text(encoding="utf-8")
    payload = {
        "query": query,
        "context": context,
    }
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
    ]
