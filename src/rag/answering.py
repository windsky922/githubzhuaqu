from __future__ import annotations

from pathlib import Path
from collections.abc import Iterator
from typing import Any

from src.llm.client import KimiChatClient, LlmClientError
from src.llm.prompts import rag_ask_messages
from src.rag.answer_quality import validate_rag_answer
from src.rag.project_recommendations import build_project_recommendations


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
    recommendations = _recommendations(retrieval, contexts, citations)

    constraint_gate = _constraint_gate_response(
        query=query,
        retrieval=retrieval,
        citations=citations,
        evidence=evidence,
        recommendations=recommendations,
        model_status=model_status,
    )
    if constraint_gate:
        return constraint_gate

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
            recommendations=recommendations,
        )

    if model_status["configured"]:
        try:
            messages = rag_ask_messages(
                root=root,
                question=query,
                prompt_context=prompt_context,
                citations=citations,
                evidence=evidence,
                recommendations=recommendations,
            )
            answer = _ensure_citation_marker(model_client.chat(messages), citations)
            answer_quality = validate_rag_answer(answer=answer, citations=citations, contexts=contexts)
            if not answer_quality["passed"]:
                raise LlmClientError("llm_quality_failed: " + "; ".join(answer_quality["issues"]))
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
                answer_quality=answer_quality,
                recommendations=recommendations,
            )
        except (LlmClientError, OSError) as error:
            fallback_reason = str(error)
    else:
        fallback_reason = "Kimi API 未配置"

    return _response(
        query=query,
        answer=_rule_answer(query=query, contexts=contexts, retrieval=retrieval, recommendations=recommendations),
        answer_model=RULE_MODEL,
        answer_mode="fallback_rule",
        fallback_reason=fallback_reason,
        confidence=_confidence(contexts),
        retrieval=retrieval,
        citations=citations,
        evidence=evidence,
        model_status={**model_status, "attempted": model_status["configured"], "used": False},
        recommendations=recommendations,
    )


def stream_rag_answer_question(
    *,
    root: Path,
    query: str,
    retrieval: dict[str, Any],
    client: KimiChatClient | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield draft deltas, then one evidence-validated final response."""
    contexts = _list_of_dicts(retrieval.get("contexts"))
    citations = _list_of_dicts(retrieval.get("citations"))
    prompt_context = str(retrieval.get("prompt_context") or "")
    evidence = _evidence_from_contexts(contexts)
    model_client = client or KimiChatClient()
    model_status = model_client.status()
    recommendations = _recommendations(retrieval, contexts, citations)
    yield {
        "event": "meta",
        "data": {
            "query": retrieval.get("query") or query,
            "retrieval": retrieval.get("retrieval") or {},
            "citations": citations,
            "evidence": evidence,
            "model_status": model_status,
        },
    }

    constraint_gate = _constraint_gate_response(
        query=query,
        retrieval=retrieval,
        citations=citations,
        evidence=evidence,
        recommendations=recommendations,
        model_status=model_status,
    )
    if constraint_gate:
        yield {"event": "final", "data": constraint_gate}
        return


    if not contexts:
        yield {
            "event": "final",
            "data": _response(
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
                recommendations=recommendations,
            ),
        }
        return

    fallback_reason = "Kimi API 未配置"
    if model_status["configured"]:
        try:
            messages = rag_ask_messages(
                root=root,
                question=query,
                prompt_context=prompt_context,
                citations=citations,
                evidence=evidence,
                recommendations=recommendations,
            )
            chunks: list[str] = []
            for delta in model_client.stream_chat(messages):
                chunks.append(delta)
                yield {"event": "delta", "data": {"text": delta}}
            answer = _ensure_citation_marker("".join(chunks), citations)
            answer_quality = validate_rag_answer(answer=answer, citations=citations, contexts=contexts)
            if not answer_quality["passed"]:
                raise LlmClientError("llm_quality_failed: " + "; ".join(answer_quality["issues"]))
            yield {
                "event": "final",
                "data": _response(
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
                    answer_quality=answer_quality,
                    recommendations=recommendations,
                ),
            }
            return
        except (LlmClientError, OSError) as error:
            fallback_reason = str(error)

    yield {
        "event": "final",
        "data": _response(
            query=query,
            answer=_rule_answer(query=query, contexts=contexts, retrieval=retrieval, recommendations=recommendations),
            answer_model=RULE_MODEL,
            answer_mode="fallback_rule",
            fallback_reason=fallback_reason,
            confidence=_confidence(contexts),
            retrieval=retrieval,
            citations=citations,
            evidence=evidence,
            model_status={**model_status, "attempted": model_status["configured"], "used": False},
            recommendations=recommendations,
        ),
    }


def _recommendations(
    retrieval: dict[str, Any],
    contexts: list[dict[str, Any]],
    citations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return build_project_recommendations(
        contexts=contexts,
        citations=citations,
        constraints=retrieval.get("constraints") if isinstance(retrieval.get("constraints"), dict) else {},
        requirements=_list_of_dicts(retrieval.get("requirements")),
        requirement_verification=(
            retrieval.get("requirement_verification")
            if isinstance(retrieval.get("requirement_verification"), dict)
            else {}
        ),
    )


def _constraint_gate_response(
    *,
    query: str,
    retrieval: dict[str, Any],
    citations: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    model_status: dict[str, Any],
) -> dict[str, Any] | None:
    requirements = _list_of_dicts(retrieval.get("requirements"))
    if not requirements:
        return None
    if any(item.get("eligibility") == "eligible" for item in recommendations):
        return None

    has_unknown = not recommendations or any(item.get("eligibility") == "unknown" for item in recommendations)
    if has_unknown:
        question = "当前候选中存在无法核实的硬约束。请补充可验证条件，或明确允许扩大到全部归档继续搜索。"
        answer_mode = "clarification"
        fallback_reason = "hard_constraint_unknown"
    else:
        question = "当前候选全部违反了明确的硬约束。请放宽条件，或要求重新搜索全部归档。"
        answer_mode = "no_match"
        fallback_reason = "hard_constraint_no_match"

    result = _response(
        query=query,
        answer=question,
        answer_model="rule:constraint-gate-v1",
        answer_mode=answer_mode,
        fallback_reason=fallback_reason,
        confidence=_confidence(_list_of_dicts(retrieval.get("contexts"))),
        retrieval=retrieval,
        citations=citations,
        evidence=evidence,
        model_status={**model_status, "attempted": False, "used": False},
        answer_quality={
            "applicable": False,
            "passed": True,
            "issues": [],
            "citation_validity": "not_applicable",
            "evidence_relevance": "not_evaluated",
            "claim_support": "not_evaluated",
            "data_freshness": "unknown",
        },
        recommendations=recommendations,
    )
    result["clarification_required"] = has_unknown
    result["clarification_question"] = question if has_unknown else ""
    return result


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
    answer_quality: dict[str, Any] | None = None,
    recommendations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    contexts = _list_of_dicts(retrieval.get("contexts"))
    recommendations = recommendations if recommendations is not None else _recommendations(retrieval, contexts, citations)
    return {
        "schema_version": 1,
        "query": retrieval.get("query") or query,
        "answer": answer,
        "answer_model": answer_model,
        "answer_mode": answer_mode,
        "fallback_reason": fallback_reason,
        "confidence": confidence,
        "evidence_coverage": confidence,
        "match_confidence": "unknown",
        "count": len(contexts),
        "retrieval": retrieval.get("retrieval") or {},
        "citations": citations,
        "evidence": evidence,
        "recommendations": recommendations,
        "quality": _answer_quality(contexts=contexts, citations=citations, evidence=evidence),
        "prompt_context": retrieval.get("prompt_context") or "",
        "source_explanation_id": "",
        "cached": False,
        "next_actions": _next_actions(contexts=contexts, citations=citations, answer_mode=answer_mode),
        "contexts": contexts,
        "model_status": model_status,
        "answer_quality": answer_quality
        or validate_rag_answer(answer=answer, citations=citations, contexts=contexts),
    }


def _rule_answer(
    *, query: str, contexts: list[dict[str, Any]], retrieval: dict[str, Any], recommendations: list[dict[str, Any]]
) -> str:
    repositories = _unique_strings(context.get("metadata", {}).get("full_name") or "" for context in contexts)
    sources = _unique_strings(
        source
        for context in contexts
        for source in _list_strings(context.get("metadata", {}).get("sources") or [])
    )
    eligible = next((item for item in recommendations if item.get("eligibility") == "eligible"), None)
    top_repo = str((eligible or {}).get("full_name") or "")
    mode = (retrieval.get("retrieval") or {}).get("mode") or "rag"
    citation_markers = _citation_markers(contexts)
    lead = (
        f"基于 {mode} 证据，问题“{query}”当前优先关注 {top_repo}{citation_markers[:3] or ''}。"
        if top_repo
        else f"基于 {mode} 证据，问题“{query}”当前没有通过全部硬约束的首选项目。"
    )
    answer = [
        lead,
        f"证据覆盖 {len(repositories)} 个项目：{'、'.join(repositories[:5]) or '未识别项目'}{citation_markers or ''}。",
        f"来源包括：{'、'.join(sources[:5]) or '未标明来源'}{citation_markers[:3] or ''}。",
        "该回答为规则降级版，只根据已召回证据给出低到中置信结论，不补充证据外信息。",
    ]
    return "\n".join(answer)


def _citation_markers(contexts: list[dict[str, Any]]) -> str:
    if not contexts:
        return ""
    return "".join(f"[{index}]" for index in range(1, min(len(contexts), 5) + 1))


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
