from __future__ import annotations

from pathlib import Path
from typing import Any

from src.llm.client import KimiChatClient, LlmClientError
from src.llm.prompts import rag_ask_messages


RULE_MODEL = "rule:rag-ask-v1"


def answer_rag_question(
    *,
    root: Path,
    query: str,
    retrieval: dict[str, Any],
    client: KimiChatClient | None = None,
) -> dict[str, Any]:
    contexts = _list_of_dicts(retrieval.get("contexts"))
    citations = _list_of_dicts(retrieval.get("citations"))
    prompt_context = str(retrieval.get("prompt_context") or "")
    evidence = _evidence_from_contexts(contexts)
    model_client = client or KimiChatClient()
    model_status = model_client.status()

    if not contexts:
        return _response(
            query=query,
            answer="当前没有召回可引用的 RAG 证据，不能生成项目研究结论。请扩大关键词、放宽筛选条件，或先重建 RAG 索引。",
            answer_model=RULE_MODEL,
            answer_mode="refusal",
            fallback_reason="no_evidence",
            confidence="low",
            retrieval=retrieval,
            citations=citations,
            evidence=evidence,
            model_status={**model_status, "attempted": False, "used": False},
        )

    if model_status["configured"]:
        try:
            messages = rag_ask_messages(
                root=root,
                question=query,
                prompt_context=prompt_context,
                citations=citations,
                evidence=evidence,
            )
            answer = _ensure_citation_marker(model_client.chat(messages), citations)
            return _response(
                query=query,
                answer=answer,
                answer_model=f"kimi:{model_status['model']}",
                answer_mode="llm",
                fallback_reason="",
                confidence=_confidence(contexts),
                retrieval=retrieval,
                citations=citations,
                evidence=evidence,
                model_status={**model_status, "attempted": True, "used": True},
            )
        except (LlmClientError, OSError) as error:
            fallback_reason = str(error)
    else:
        fallback_reason = "Kimi API 未配置"

    return _response(
        query=query,
        answer=_rule_answer(query=query, contexts=contexts, retrieval=retrieval),
        answer_model=RULE_MODEL,
        answer_mode="fallback_rule",
        fallback_reason=fallback_reason,
        confidence=_confidence(contexts),
        retrieval=retrieval,
        citations=citations,
        evidence=evidence,
        model_status={**model_status, "attempted": model_status["configured"], "used": False},
    )


def _response(
    *,
    query: str,
    answer: str,
    answer_model: str,
    answer_mode: str,
    fallback_reason: str,
    confidence: str,
    retrieval: dict[str, Any],
    citations: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    model_status: dict[str, Any],
) -> dict[str, Any]:
    contexts = _list_of_dicts(retrieval.get("contexts"))
    return {
        "schema_version": 1,
        "query": retrieval.get("query") or query,
        "answer": answer,
        "answer_model": answer_model,
        "answer_mode": answer_mode,
        "fallback_reason": fallback_reason,
        "confidence": confidence,
        "count": len(contexts),
        "retrieval": retrieval.get("retrieval") or {},
        "citations": citations,
        "evidence": evidence,
        "quality": _answer_quality(contexts=contexts, citations=citations, evidence=evidence),
        "prompt_context": retrieval.get("prompt_context") or "",
        "source_explanation_id": "",
        "cached": False,
        "next_actions": _next_actions(contexts=contexts, citations=citations, answer_mode=answer_mode),
        "contexts": contexts,
        "model_status": model_status,
    }


def _rule_answer(*, query: str, contexts: list[dict[str, Any]], retrieval: dict[str, Any]) -> str:
    repositories = _unique_strings(context.get("metadata", {}).get("full_name") or "" for context in contexts)
    sources = _unique_strings(
        source
        for context in contexts
        for source in _list_strings(context.get("metadata", {}).get("sources") or [])
    )
    top = contexts[0].get("metadata", {}) if contexts else {}
    top_repo = top.get("full_name") or (repositories[0] if repositories else "")
    mode = (retrieval.get("retrieval") or {}).get("mode") or "rag"
    answer = [
        f"基于 {mode} 证据，问题“{query}”当前优先关注 {top_repo}。",
        f"证据覆盖 {len(repositories)} 个项目：{'、'.join(repositories[:5]) or '未识别项目'}。",
        f"来源包括：{'、'.join(sources[:5]) or '未标明来源'}。",
        "该回答为规则降级版，只根据已召回证据给出低到中置信结论，不补充证据外信息。",
    ]
    return "\n".join(answer)


def _evidence_from_contexts(contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence = []
    for index, context in enumerate(contexts[:8], start=1):
        metadata = context.get("metadata") or {}
        evidence.append(
            {
                "index": index,
                "full_name": metadata.get("full_name") or "",
                "run_date": metadata.get("run_date") or "",
                "chunk_id": context.get("chunk_id") or "",
                "quote": str(context.get("text") or "")[:500],
                "matched_evidence": _list_strings(context.get("evidence") or []),
            }
        )
    return evidence


def _answer_quality(
    *,
    contexts: list[dict[str, Any]],
    citations: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    score = min(100, len(contexts) * 10 + len(citations) * 8 + len(evidence) * 6)
    level = "high" if score >= 80 else "medium" if score >= 45 else "low"
    return {
        "score": score,
        "level": level,
        "metrics": {
            "context_count": len(contexts),
            "citation_count": len(citations),
            "evidence_count": len(evidence),
        },
    }


def _next_actions(*, contexts: list[dict[str, Any]], citations: list[dict[str, Any]], answer_mode: str) -> list[str]:
    if not contexts:
        return [
            "扩大关键词或取消语言/方向过滤后重试。",
            "确认 SQLite RAG 语料已构建；必要时先运行语料重建或 embedding 构建任务。",
        ]
    actions = ["回答对外使用前，保留 citations 中的项目链接和 chunk ID。"]
    if answer_mode != "llm":
        actions.insert(0, "配置 KIMI_API_KEY 和 KIMI_MODEL 后可生成真实模型回答。")
    if len(citations) < 3:
        actions.append("引用数量偏少，建议提高 limit 或使用 hybrid 模式。")
    return _unique_strings(actions)[:5]


def _ensure_citation_marker(answer: str, citations: list[dict[str, Any]]) -> str:
    if not citations or any(f"[{index}]" in answer for index in range(1, len(citations) + 1)):
        return answer
    indexes = "、".join(f"[{item.get('index') or index}]" for index, item in enumerate(citations[:3], start=1))
    return f"{answer.rstrip()}\n\n引用证据：{indexes}"


def _confidence(contexts: list[dict[str, Any]]) -> str:
    if len(contexts) >= 5:
        return "high"
    if len(contexts) >= 2:
        return "medium"
    return "low"


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _list_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _unique_strings(values: Any) -> list[str]:
    output = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            output.append(text)
    return output
