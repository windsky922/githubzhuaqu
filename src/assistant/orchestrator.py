from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterator

from src.llm.client import KimiChatClient, LlmClientError
from src.llm.prompts import assistant_knowledge_messages, assistant_route_messages

from .state import build_assistant_state, contextual_payload, normalize_assistant_request


ASSISTANT_MODES = {"knowledge", "project_search", "project_follow_up", "project_compare", "help", "clarify"}
RESET_MARKERS = ("重新搜索", "重新找", "换一批", "不限刚才", "搜索其他", "找别的")
CONTEXT_MARKERS = ("刚才", "之前推荐", "这些项目", "上述项目", "其中", "候选项目", "推荐的项目", "哪个项目")
KNOWLEDGE_MARKERS = ("学习", "知识", "概念", "原理", "路线", "教程", "怎么入门", "如何入门", "开发方向", "实践方法")
PROJECT_MARKERS = ("项目", "仓库", "github", "推荐", "比较", "对比", "适合", "选择")
COMPARE_MARKERS = ("比较", "对比", "区别", "差异", "哪个好", "更适合")
HELP_MARKERS = ("你能做什么", "怎么使用", "帮助", "功能介绍")
GREETING_RE = re.compile(r"^(你好|您好|hi|hello|嗨)[！!。.]?$", re.IGNORECASE)
REPOSITORY_REFERENCE_RE = re.compile(r"\b[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\b")


class AssistantOrchestrator:
    def __init__(
        self,
        repository: Any,
        *,
        prompt_root: Path,
        model_client: KimiChatClient | None = None,
        router_client: KimiChatClient | None = None,
    ) -> None:
        self.repository = repository
        self.prompt_root = prompt_root
        self.model_client = model_client or KimiChatClient()
        self.router_client = router_client or self.model_client

    def normalize_request(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        request = normalize_assistant_request(payload)
        current_source = getattr(self.repository, "data_source", None)
        previous_source = request["state"].get("source_identity") or {}
        has_client_context = bool(
            request["state"].get("resumable") or request["state"].get("candidate_repository_ids")
        )
        if has_client_context and not _source_matches(previous_source, current_source):
            request["state"] = {
                **request["state"],
                "candidate_repository_ids": [],
                "primary_repository_id": "",
                "pending_question": "数据来源已变化，需要重新检索候选。",
                "resumable": False,
            }
        return request

    def turn(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        request = self.normalize_request(payload)
        assistant_mode = self._assistant_mode(request)
        project_response = self._project_response(request, assistant_mode)
        guidance = self._knowledge_guidance(request["q"]) if assistant_mode == "knowledge" else None
        return self._compose(request, assistant_mode, project_response, guidance)

    def turn_stream(self, request: dict[str, Any]) -> Iterator[dict[str, Any]]:
        assistant_mode = self._assistant_mode(request)
        project_response: dict[str, Any] | None = None
        meta_sent = False
        if assistant_mode not in {"help", "clarify"}:
            rag_payload = self._rag_payload(request, assistant_mode)
            for event in self.repository.rag_ask_contextual_stream(rag_payload, router_client=self.router_client):
                name = str(event.get("event") or "error")
                data = event.get("data") if isinstance(event.get("data"), dict) else {}
                if name == "meta" and not meta_sent:
                    yield {"event": "meta", "data": {**data, "assistant_mode": assistant_mode}}
                    meta_sent = True
                elif name == "final":
                    project_response = data
                elif name == "error":
                    yield {"event": "error", "data": {"message": "助手连接中断，请重试。"}}
                    return
        if not meta_sent:
            yield {
                "event": "meta",
                "data": {"query": request["q"], "assistant_mode": assistant_mode, "retrieval": {"mode": "not_run"}},
            }
        guidance = self._knowledge_guidance(request["q"]) if assistant_mode == "knowledge" else None
        response = self._compose(request, assistant_mode, project_response, guidance)
        if response.get("answer_mode") == "llm":
            for chunk in _chunks(str(response.get("answer") or ""), 180):
                yield {"event": "delta", "data": {"text": chunk}}
        yield {"event": "final", "data": response}

    def _assistant_mode(self, request: dict[str, Any]) -> str:
        query = request["q"].strip()
        normalized = query.casefold()
        state = request["state"]
        has_context = bool(state.get("resumable") and state.get("candidate_repository_ids"))
        if any(marker in normalized for marker in RESET_MARKERS):
            return "project_search"
        if has_context and any(marker in normalized for marker in CONTEXT_MARKERS):
            return "project_compare" if any(marker in normalized for marker in COMPARE_MARKERS) else "project_follow_up"
        if any(marker in normalized for marker in KNOWLEDGE_MARKERS):
            return "knowledge"
        if any(marker in normalized for marker in COMPARE_MARKERS):
            return "project_compare"
        if any(marker in normalized for marker in PROJECT_MARKERS):
            return "project_search"
        if normalized in HELP_MARKERS or GREETING_RE.fullmatch(query):
            return "help"
        return self._model_route(query, state)

    def _model_route(self, query: str, state: dict[str, Any]) -> str:
        status = self.router_client.status()
        if not status.get("configured"):
            return "clarify"
        try:
            raw = self.router_client.chat(assistant_route_messages(root=self.prompt_root, query=query, state=state))
            data = json.loads(_strip_code_fence(raw))
            mode = str(data.get("assistant_mode") or "") if isinstance(data, dict) else ""
            return mode if mode in ASSISTANT_MODES else "clarify"
        except (JsonError, LlmClientError, OSError, ValueError):
            return "clarify"

    def _project_response(self, request: dict[str, Any], assistant_mode: str) -> dict[str, Any] | None:
        if assistant_mode in {"help", "clarify"}:
            return None
        return self.repository.rag_ask_contextual(
            self._rag_payload(request, assistant_mode),
            router_client=self.router_client,
        )

    def _rag_payload(self, request: dict[str, Any], assistant_mode: str) -> dict[str, Any]:
        query = request["q"]
        if assistant_mode == "knowledge":
            query = "AI Agent"
            for language in ("Python", "TypeScript", "JavaScript", "Go", "Rust"):
                if language.casefold() in request["q"].casefold():
                    query = f"{query} {language}"
                    break
        return contextual_payload(request, query=query)

    def _knowledge_guidance(self, query: str) -> dict[str, Any]:
        status = self.model_client.status()
        if not status.get("configured"):
            return {
                "used": False,
                "content": "通用教学模型当前未配置；下面仅展示本地项目证据，不把规则降级结果伪装成完整教程。",
                "reason": "model_not_configured",
                "model_status": status,
            }
        try:
            content = self.model_client.chat(assistant_knowledge_messages(root=self.prompt_root, question=query))
            if not content or REPOSITORY_REFERENCE_RE.search(content):
                raise ValueError("general_guidance_contains_repository_reference")
            return {"used": True, "content": content, "reason": "", "model_status": status}
        except (LlmClientError, OSError, ValueError):
            return {
                "used": False,
                "content": "通用教学模型本轮不可用；下面仅展示本地项目证据，请稍后重试教学回答。",
                "reason": "model_unavailable",
                "model_status": status,
            }

    def _compose(
        self,
        request: dict[str, Any],
        assistant_mode: str,
        project_response: dict[str, Any] | None,
        guidance: dict[str, Any] | None,
    ) -> dict[str, Any]:
        project = dict(project_response or {})
        sections: list[dict[str, Any]] = []
        if assistant_mode == "help":
            sections.append({
                "kind": "guidance",
                "title": "我能帮助你的内容",
                "content": "我可以解释 AI Agent 学习路线，并基于本地 GitHub 归档推荐、比较和追问项目；当前版本只读，不执行任务、订阅或通知。",
                "citation_indexes": [],
            })
        elif assistant_mode == "clarify":
            sections.append({
                "kind": "limitations",
                "title": "请补充目标",
                "content": "请说明你想学习的 AI Agent 主题，或描述要寻找、比较的 GitHub 项目。",
                "citation_indexes": [],
            })
        if guidance:
            sections.append({
                "kind": "guidance" if guidance["used"] else "limitations",
                "title": "AI Agent 学习建议" if guidance["used"] else "教学能力状态",
                "content": guidance["content"],
                "citation_indexes": [],
            })
        project_answer = str(project.get("answer") or "").strip()
        citations = project.get("citations") if isinstance(project.get("citations"), list) else []
        if project_answer:
            sections.append({
                "kind": "project_evidence",
                "title": "证据支持的项目建议",
                "content": project_answer,
                "citation_indexes": [item.get("index") for item in citations if isinstance(item, dict) and item.get("index")],
            })
        answer = "\n\n".join(f"## {item['title']}\n\n{item['content']}" for item in sections)
        guidance_used = bool(guidance and guidance.get("used"))
        has_project_evidence = bool(citations or project.get("recommendations"))
        knowledge_basis = "mixed" if guidance_used and has_project_evidence else "model_general" if guidance_used else "project_evidence" if has_project_evidence else "none"
        quality = project.get("answer_quality") if isinstance(project.get("answer_quality"), dict) else {}
        response = {
            "query": request["q"],
            "resolved_query": str(project.get("resolved_query") or request["q"]),
            "answer": answer,
            "answer_mode": "llm" if guidance_used else str(project.get("answer_mode") or "fallback_rule"),
            "fallback_reason": str(project.get("fallback_reason") or (guidance or {}).get("reason") or ""),
            "assistant_mode": assistant_mode,
            "knowledge_basis": knowledge_basis,
            "sections": sections,
            "citations": citations,
            "evidence": project.get("evidence") if isinstance(project.get("evidence"), list) else [],
            "recommendations": project.get("recommendations") if isinstance(project.get("recommendations"), list) else [],
            "answer_quality": {**quality, "assistant_mode": assistant_mode, "general_knowledge_disclosed": guidance_used},
            "model_status": (guidance or {}).get("model_status") or project.get("model_status") or self.model_client.status(),
            "input_route": project.get("input_route") if isinstance(project.get("input_route"), dict) else {},
            "data_source": project.get("data_source") if isinstance(project.get("data_source"), dict) else {},
            "freshness": project.get("freshness") if isinstance(project.get("freshness"), dict) else {},
        }
        response["assistant_state"] = build_assistant_state(request, assistant_mode=assistant_mode, response=response)
        return response


JsonError = json.JSONDecodeError


def _strip_code_fence(value: str) -> str:
    text = value.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _chunks(value: str, size: int) -> Iterator[str]:
    for start in range(0, len(value), size):
        yield value[start : start + size]


def _source_matches(previous: dict[str, Any], current: Any) -> bool:
    if not isinstance(current, dict):
        return False
    previous_id = str(previous.get("source_id") or "")
    previous_date = str(previous.get("run_date") or "")
    if not previous_id and not previous_date:
        return False
    return previous_id == str(current.get("source_id") or "") and previous_date == str(current.get("run_date") or "")
