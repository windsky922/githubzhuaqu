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
CONTINUATION_MARKERS = ("继续", "接着说", "展开", "还有吗", "还有呢", "然后呢")
KNOWLEDGE_FOLLOW_UP_MARKERS = ("继续", "接着", "展开", "举例", "例子", "为什么", "换种说法", "换个说法", "回到")
KNOWLEDGE_MARKERS = ("学习", "知识", "概念", "原理", "路线", "教程", "怎么入门", "如何入门", "开发方向", "实践方法")
PROJECT_MARKERS = ("项目", "仓库", "github", "推荐", "比较", "对比", "适合", "选择")
NON_PROJECT_CONTEXT_MARKERS = ("不涉及具体仓库", "不涉及仓库", "无需具体仓库", "不需要具体仓库")
HARD_REQUIREMENT_MARKERS = ("必须", "完全离线", "离线", "无需", "不需要", "不能", "只允许", "仅限", "api key", "apikey")
COMPARE_MARKERS = ("比较", "对比", "区别", "差异", "哪个好", "更适合")
HELP_MARKERS = ("你能做什么", "怎么使用", "帮助", "功能介绍")
GREETING_RE = re.compile(r"^(你好|您好|hi|hello|嗨)[！!。.]?$", re.IGNORECASE)
REPOSITORY_REFERENCE_RE = re.compile(r"\b[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\b")
OUTLINE_LINE_RE = re.compile(r"^\s*(?:[-*]\s*)?(?:第)?([一二三四五六七八九十\d]+)(?:点|[、.)）:：])\s*(.+?)\s*$")
ORDINALS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


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
        guidance = self._knowledge_guidance(request) if assistant_mode == "knowledge" else None
        project_unavailable = False
        if assistant_mode == "knowledge":
            try:
                project_response = self._project_response(request, assistant_mode)
            except (OSError, ValueError):
                project_response = None
                project_unavailable = True
        else:
            project_response = self._project_response(request, assistant_mode)
        return self._compose(
            request,
            assistant_mode,
            project_response,
            guidance,
            project_unavailable=project_unavailable,
        )

    def turn_stream(self, request: dict[str, Any]) -> Iterator[dict[str, Any]]:
        assistant_mode = self._assistant_mode(request)
        project_response: dict[str, Any] | None = None
        guidance = self._knowledge_guidance(request) if assistant_mode == "knowledge" else None
        project_unavailable = False
        meta_sent = False
        if assistant_mode not in {"help", "clarify"}:
            rag_payload = self._rag_payload(request, assistant_mode)
            try:
                for event in self.repository.rag_ask_contextual_stream(rag_payload, router_client=self.router_client):
                    name = str(event.get("event") or "error")
                    data = event.get("data") if isinstance(event.get("data"), dict) else {}
                    if name == "meta" and not meta_sent:
                        yield {"event": "meta", "data": {**data, "assistant_mode": assistant_mode}}
                        meta_sent = True
                    elif name == "final":
                        project_response = data
                    elif name == "error":
                        if assistant_mode == "knowledge":
                            project_unavailable = True
                            break
                        yield {"event": "error", "data": {"message": "助手连接中断，请重试。"}}
                        return
            except (OSError, ValueError):
                if assistant_mode != "knowledge":
                    yield {"event": "error", "data": {"message": "助手连接中断，请重试。"}}
                    return
                project_unavailable = True
        if not meta_sent:
            yield {
                "event": "meta",
                "data": {
                    "query": request["q"],
                    "assistant_mode": assistant_mode,
                    "retrieval": {"mode": "optional_failed" if project_unavailable else "not_run"},
                },
            }
        response = self._compose(
            request,
            assistant_mode,
            project_response,
            guidance,
            project_unavailable=project_unavailable,
        )
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
        if _is_knowledge_follow_up(query, state):
            return "knowledge"
        if has_context and any(marker in normalized for marker in CONTEXT_MARKERS):
            return "project_compare" if any(marker in normalized for marker in COMPARE_MARKERS) else "project_follow_up"
        if has_context and normalized in CONTINUATION_MARKERS:
            return "project_follow_up"
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
        preserve_requirements = _has_project_intent(request["q"]) and _has_hard_requirements(request["q"])
        if assistant_mode == "knowledge" and not preserve_requirements:
            query = "AI Agent"
            for language in ("Python", "TypeScript", "JavaScript", "Go", "Rust"):
                if language.casefold() in request["q"].casefold():
                    query = f"{query} {language}"
                    break
        return contextual_payload(request, query=query)

    def _knowledge_guidance(self, request: dict[str, Any]) -> dict[str, Any]:
        query = request["q"]
        knowledge_context = _resolved_knowledge_context(query, request["state"].get("knowledge_context"))
        status = self.model_client.status()
        if not status.get("configured"):
            return {
                "used": False,
                "content": "通用教学模型当前未配置；下面仅展示本地项目证据，不把规则降级结果伪装成完整教程。",
                "reason": "model_not_configured",
                "model_status": status,
                "knowledge_context": knowledge_context,
            }
        try:
            content = self.model_client.chat(assistant_knowledge_messages(
                root=self.prompt_root,
                question=query,
                knowledge_context=knowledge_context,
            ))
            if not content or REPOSITORY_REFERENCE_RE.search(content):
                raise ValueError("general_guidance_contains_repository_reference")
            if not knowledge_context["outline"]:
                knowledge_context = {
                    "topic": query[:200],
                    "outline": _extract_outline(content),
                    "focus_id": "",
                }
            return {
                "used": True,
                "content": content,
                "reason": "",
                "model_status": status,
                "knowledge_context": knowledge_context,
            }
        except (LlmClientError, OSError, ValueError):
            return {
                "used": False,
                "content": "通用教学模型本轮不可用；下面仅展示本地项目证据，请稍后重试教学回答。",
                "reason": "model_unavailable",
                "model_status": status,
                "knowledge_context": knowledge_context,
            }

    def _compose(
        self,
        request: dict[str, Any],
        assistant_mode: str,
        project_response: dict[str, Any] | None,
        guidance: dict[str, Any] | None,
        *,
        project_unavailable: bool = False,
    ) -> dict[str, Any]:
        project = dict(project_response or {})
        project_clarification = bool(
            project.get("answer_mode") == "clarification" or project.get("clarification_required") is True
        )
        effective_mode = "clarify" if project_clarification else assistant_mode
        sections: list[dict[str, Any]] = []
        if effective_mode == "help":
            sections.append({
                "kind": "guidance",
                "title": "我能帮助你的内容",
                "content": "我可以解释 AI Agent 学习路线，并基于本地 GitHub 归档推荐、比较和追问项目；当前版本只读，不执行任务、订阅或通知。",
                "citation_indexes": [],
            })
        elif effective_mode == "clarify":
            clarification_text = str(
                project.get("clarification_question")
                or project.get("answer")
                or "请说明你想学习的 AI Agent 主题，或描述要寻找、比较的 GitHub 项目。"
            ).strip()
            sections.append({
                "kind": "limitations",
                "title": "请补充目标",
                "content": clarification_text,
                "citation_indexes": [],
            })
        if guidance:
            sections.append({
                "kind": "guidance" if guidance["used"] else "limitations",
                "title": "AI Agent 学习建议" if guidance["used"] else "教学能力状态",
                "content": guidance["content"],
                "citation_indexes": [],
            })
        if project_unavailable:
            sections.append({
                "kind": "limitations",
                "title": "项目证据状态",
                "content": "项目证据暂不可用；通用教学仍可继续。具体仓库判断请稍后重试。",
                "citation_indexes": [],
            })
        project_answer = str(project.get("answer") or "").strip()
        citations = [] if project_clarification else project.get("citations") if isinstance(project.get("citations"), list) else []
        recommendations = [] if project_clarification else project.get("recommendations") if isinstance(project.get("recommendations"), list) else []
        evidence = [] if project_clarification else project.get("evidence") if isinstance(project.get("evidence"), list) else []
        if project_answer and not project_clarification:
            sections.append({
                "kind": "project_evidence",
                "title": "证据支持的项目建议",
                "content": project_answer,
                "citation_indexes": [item.get("index") for item in citations if isinstance(item, dict) and item.get("index")],
            })
        answer = "\n\n".join(f"## {item['title']}\n\n{item['content']}" for item in sections)
        guidance_used = bool(guidance and guidance.get("used"))
        has_project_evidence = bool(citations or recommendations)
        knowledge_basis = "mixed" if guidance_used and has_project_evidence else "model_general" if guidance_used else "project_evidence" if has_project_evidence else "none"
        quality = project.get("answer_quality") if isinstance(project.get("answer_quality"), dict) else {}
        response = {
            "query": request["q"],
            "resolved_query": str(project.get("resolved_query") or request["q"]),
            "answer": answer,
            "answer_mode": "clarification" if effective_mode == "clarify" else "llm" if guidance_used else str(project.get("answer_mode") or "fallback_rule"),
            "fallback_reason": str(
                project.get("fallback_reason")
                or (guidance or {}).get("reason")
                or ("project_enhancement_unavailable" if project_unavailable else "")
            ),
            "assistant_mode": effective_mode,
            "knowledge_basis": knowledge_basis,
            "sections": sections,
            "citations": citations,
            "evidence": evidence,
            "recommendations": recommendations,
            "answer_quality": {**quality, "assistant_mode": effective_mode, "general_knowledge_disclosed": guidance_used},
            "model_status": (guidance or {}).get("model_status") or project.get("model_status") or self.model_client.status(),
            "input_route": project.get("input_route") if isinstance(project.get("input_route"), dict) else {},
            "data_source": project.get("data_source") if isinstance(project.get("data_source"), dict) else {},
            "freshness": project.get("freshness") if isinstance(project.get("freshness"), dict) else {},
        }
        if effective_mode == "clarify":
            route = response["input_route"]
            response["clarification_required"] = True
            response["clarification_question"] = sections[0]["content"]
            response["input_route"] = {
                **route,
                "route": "clarify",
                "retrieval_performed": bool(route.get("retrieval_performed", False)),
                "candidate_scope": "none",
                "requirements": route.get("requirements") if isinstance(route.get("requirements"), list) else [],
            }
        state_response = {
            **response,
            "knowledge_context": (guidance or {}).get("knowledge_context"),
        }
        response["assistant_state"] = build_assistant_state(
            request,
            assistant_mode=effective_mode,
            response=state_response,
        )
        return response


JsonError = json.JSONDecodeError


def _has_project_intent(query: str) -> bool:
    normalized = query.casefold()
    if any(marker in normalized for marker in NON_PROJECT_CONTEXT_MARKERS):
        return False
    return any(marker in normalized for marker in PROJECT_MARKERS)


def _has_hard_requirements(query: str) -> bool:
    normalized = query.casefold()
    return any(marker in normalized for marker in HARD_REQUIREMENT_MARKERS)


def _is_knowledge_follow_up(query: str, state: dict[str, Any]) -> bool:
    context = state.get("knowledge_context")
    if not isinstance(context, dict) or not (context.get("topic") or context.get("outline")):
        return False
    normalized = query.casefold()
    if _has_project_intent(query):
        return False
    if any(marker in normalized for marker in KNOWLEDGE_FOLLOW_UP_MARKERS):
        return True
    return _ordinal_index(normalized) is not None


def _resolved_knowledge_context(query: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"topic": "", "outline": [], "focus_id": ""}
    topic = str(value.get("topic") or "")[:200]
    outline = [
        {"id": str(item.get("id") or "")[:24], "title": str(item.get("title") or "")[:120]}
        for item in value.get("outline", [])[:12]
        if isinstance(item, dict) and item.get("id") and item.get("title")
    ]
    focus_id = str(value.get("focus_id") or "")[:24]
    ordinal = _ordinal_index(query)
    if ordinal is not None and 0 <= ordinal < len(outline):
        focus_id = outline[ordinal]["id"]
    else:
        for item in outline:
            if item["title"] and item["title"] in query:
                focus_id = item["id"]
                break
    if focus_id not in {item["id"] for item in outline}:
        focus_id = ""
    return {"topic": topic, "outline": outline, "focus_id": focus_id}


def _ordinal_index(value: str) -> int | None:
    match = re.search(r"第\s*([一二三四五六七八九十]|\d{1,2})\s*点", value)
    if not match:
        return None
    raw = match.group(1)
    number = int(raw) if raw.isdigit() else ORDINALS.get(raw, 0)
    return number - 1 if number > 0 else None


def _extract_outline(content: str) -> list[dict[str, str]]:
    titles: list[str] = []
    for line in content.splitlines():
        match = OUTLINE_LINE_RE.match(line)
        if match:
            title = match.group(2).strip().rstrip("。；;")[:120]
            if title and title not in titles:
                titles.append(title)
    if len(titles) < 2:
        first_paragraph = next((part.strip() for part in content.splitlines() if part.strip()), "")
        for part in re.split(r"[、，；;。]", first_paragraph):
            title = re.sub(r"^(先|再|然后|最后|需要|可以|建议)\s*", "", part).strip()[:120]
            if 1 < len(title) <= 120 and title not in titles:
                titles.append(title)
    return [{"id": f"k{index}", "title": title} for index, title in enumerate(titles[:12], start=1)]


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
