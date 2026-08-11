from __future__ import annotations

import unittest
from pathlib import Path

from src.assistant import AssistantOrchestrator
from src.llm.client import LlmClientError


class _Client:
    def __init__(self, *, configured: bool = True, answer: str = "先理解模型、工具、状态和反馈循环，再完成一个带评估的最小 Agent。") -> None:
        self.configured = configured
        self.answer = answer
        self.calls = 0

    def status(self):
        return {"provider": "test", "configured": self.configured, "model": "test" if self.configured else ""}

    def chat(self, messages):
        self.calls += 1
        return self.answer


class _FailingClient(_Client):
    def __init__(self, error: Exception) -> None:
        super().__init__()
        self.error = error

    def chat(self, messages):
        self.calls += 1
        raise self.error


class _TeachingClient(_Client):
    def __init__(self) -> None:
        super().__init__()
        self.messages = []
        self.answers = [
            "1. 模型与推理\n2. 工具与行动\n3. 记忆与反馈",
            "第三点关注如何保存最小状态并根据反馈修正行为。",
            "例如只保存主题、提纲和当前焦点，不保存整段历史回答。",
            "换句话说，记住导航坐标，不复制整本对话记录。",
            "第一点是模型如何理解目标并选择下一步推理。",
        ]

    def chat(self, messages):
        self.messages.append(messages)
        self.calls += 1
        return self.answers[min(self.calls - 1, len(self.answers) - 1)]


class _Repository:
    def __init__(self) -> None:
        self.payloads = []
        self.data_source = {"source_id": "source:1", "run_date": "2026-08-09"}

    def rag_ask_contextual(self, payload, *, router_client=None):
        self.payloads.append(payload)
        return _project_response()

    def rag_ask_contextual_stream(self, payload, *, router_client=None):
        self.payloads.append(payload)
        yield {"event": "meta", "data": {"query": payload["q"], "retrieval": {"mode": "hybrid"}}}
        yield {"event": "delta", "data": {"text": "旧 RAG 草稿"}}
        yield {"event": "final", "data": _project_response()}


class _FailingRepository(_Repository):
    def rag_ask_contextual(self, payload, *, router_client=None):
        self.payloads.append(payload)
        raise OSError("secret repository failure")

    def rag_ask_contextual_stream(self, payload, *, router_client=None):
        self.payloads.append(payload)
        raise OSError("secret repository stream failure")


def _project_response():
    return {
        "query": "AI Agent 学习项目",
        "answer": "基于证据可先研究 owner/agent。[1]",
        "answer_mode": "fallback_rule",
        "fallback_reason": "",
        "citations": [{"index": 1, "full_name": "owner/agent"}],
        "evidence": [{"chunk_id": "chunk:1", "full_name": "owner/agent"}],
        "recommendations": [
            {"full_name": "owner/agent", "eligibility": "eligible", "current_eligible": True},
            {"full_name": "owner/other", "eligibility": "eligible", "current_eligible": False},
        ],
        "answer_quality": {"passed": True},
        "input_route": {"route": "new_search", "resolved_query": "AI Agent 学习项目", "requirements": []},
        "resolved_query": "AI Agent 学习项目",
        "data_source": {"kind": "verified_snapshot", "source_id": "source:1", "run_date": "2026-08-09"},
        "freshness": {"data_freshness": "fresh", "as_of": "2026-08-09"},
        "contexts": [{"private": "must not escape"}],
        "prompt_context": "must not escape",
        "explanation": {"internal": True},
    }


class AssistantOrchestratorTest(unittest.TestCase):
    def test_knowledge_turn_separates_guidance_and_project_evidence(self):
        repository = _Repository()
        client = _Client()
        assistant = AssistantOrchestrator(repository, prompt_root=Path.cwd(), model_client=client)

        result = assistant.turn({"q": "我想学习 AI Agent 开发方向的知识"})

        self.assertEqual(result["assistant_mode"], "knowledge")
        self.assertEqual(result["knowledge_basis"], "mixed")
        self.assertEqual([section["kind"] for section in result["sections"]], ["guidance", "project_evidence"])
        self.assertIn("最小 Agent", result["answer"])
        self.assertEqual(result["assistant_state"]["candidate_repository_ids"], ["owner/agent"])
        self.assertEqual(result["assistant_state"]["primary_repository_id"], "owner/agent")
        self.assertTrue(result["assistant_state"]["resumable"])
        self.assertEqual(repository.payloads[0]["q"], "AI Agent")
        self.assertFalse(repository.payloads[0]["auto_build"])
        for forbidden in ("contexts", "prompt_context", "explanation"):
            self.assertNotIn(forbidden, result)

    def test_pure_teaching_survives_repository_failure_in_turn_and_stream(self):
        payload = {"q": "解释 ReAct 的原理"}
        normal_repository = _FailingRepository()
        normal = AssistantOrchestrator(
            normal_repository, prompt_root=Path.cwd(), model_client=_Client()
        ).turn(payload)
        stream_repository = _FailingRepository()
        stream_assistant = AssistantOrchestrator(
            stream_repository, prompt_root=Path.cwd(), model_client=_Client()
        )
        events = list(stream_assistant.turn_stream(stream_assistant.normalize_request(payload)))
        final = events[-1]["data"]

        self.assertEqual(normal, final)
        self.assertEqual(normal["answer_mode"], "llm")
        self.assertEqual(normal["knowledge_basis"], "model_general")
        self.assertEqual(normal["fallback_reason"], "project_enhancement_unavailable")
        self.assertEqual([section["kind"] for section in normal["sections"]], ["guidance", "limitations"])
        self.assertNotIn("secret repository", str(normal))
        self.assertEqual([event["event"] for event in events if event["event"] in {"meta", "final"}], ["meta", "final"])
        self.assertNotIn("error", [event["event"] for event in events])

    def test_knowledge_follow_up_without_repository_context_stays_pure_teaching(self):
        repository = _FailingRepository()
        assistant = AssistantOrchestrator(repository, prompt_root=Path.cwd(), model_client=_TeachingClient())
        first = assistant.turn({"q": "解释 ReAct 的原理"})
        follow_up = assistant.turn({
            "q": "继续，并举一个不涉及具体仓库的例子",
            "state": first["assistant_state"],
        })

        self.assertEqual(follow_up["assistant_mode"], "knowledge")
        self.assertEqual(follow_up["knowledge_basis"], "model_general")
        self.assertEqual(repository.payloads[-1]["q"], "AI Agent")
        self.assertEqual(follow_up["assistant_state"]["candidate_repository_ids"], [])

    def test_mixed_teaching_project_query_preserves_original_hard_requirements(self):
        query = "我想学习一个必须完全离线、无需 API Key 的 Python Agent 项目"
        repository = _Repository()
        project = _project_response()
        project.update({
            "answer": "没有符合全部硬约束的候选。",
            "citations": [],
            "evidence": [],
            "recommendations": [
                {"full_name": "owner/conflict", "eligibility": "rejected", "current_eligible": False}
            ],
            "input_route": {
                "route": "new_search",
                "resolved_query": query,
                "requirements": [
                    {"field": "offline_capable", "operator": "eq", "value": True, "hard": True},
                    {"field": "api_key_required", "operator": "eq", "value": False, "hard": True},
                    {"field": "language", "operator": "eq", "value": "Python", "hard": True},
                ],
            },
            "resolved_query": query,
        })
        repository.rag_ask_contextual = lambda payload, router_client=None: (
            repository.payloads.append(payload) or project
        )
        assistant = AssistantOrchestrator(repository, prompt_root=Path.cwd(), model_client=_Client())

        result = assistant.turn({"q": query})

        self.assertEqual(result["assistant_mode"], "knowledge")
        self.assertEqual(repository.payloads[-1]["q"], query)
        self.assertEqual(
            {item["field"] for item in result["input_route"]["requirements"] if item["hard"]},
            {"offline_capable", "api_key_required", "language"},
        )
        self.assertEqual(result["assistant_state"]["candidate_repository_ids"], [])
        self.assertFalse(result["assistant_state"]["resumable"])

    def test_concrete_project_request_still_fails_closed(self):
        repository = _FailingRepository()
        assistant = AssistantOrchestrator(repository, prompt_root=Path.cwd(), model_client=_Client())

        with self.assertRaises(OSError):
            assistant.turn({"q": "推荐一个 Agent 项目"})
        events = list(assistant.turn_stream(assistant.normalize_request({"q": "推荐一个 Agent 项目"})))
        self.assertEqual(events[-1]["event"], "error")
        self.assertNotIn("final", [event["event"] for event in events])
        self.assertNotIn("secret repository", str(events))

    def test_unconfigured_model_is_disclosed_without_fake_tutorial(self):
        assistant = AssistantOrchestrator(_Repository(), prompt_root=Path.cwd(), model_client=_Client(configured=False))
        result = assistant.turn({"q": "我想学习 AI Agent 的原理"})
        self.assertEqual(result["answer_mode"], "fallback_rule")
        self.assertEqual(result["knowledge_basis"], "project_evidence")
        self.assertIn("模型当前未配置", result["sections"][0]["content"])

    def test_stream_emits_one_meta_then_authoritative_final(self):
        assistant = AssistantOrchestrator(_Repository(), prompt_root=Path.cwd(), model_client=_Client())
        request = assistant.normalize_request({"q": "我想学习 AI Agent 开发方向的知识"})
        events = list(assistant.turn_stream(request))
        self.assertEqual(events[0]["event"], "meta")
        self.assertEqual(events[-1]["event"], "final")
        self.assertEqual(sum(event["event"] == "meta" for event in events), 1)
        self.assertNotIn("旧 RAG 草稿", "".join(str(event.get("data")) for event in events))

    def test_turn_and_stream_final_are_equivalent(self):
        payload = {"q": "推荐适合学习的 Agent 项目"}
        normal = AssistantOrchestrator(
            _Repository(), prompt_root=Path.cwd(), model_client=_Client(configured=False)
        ).turn(payload)
        stream_assistant = AssistantOrchestrator(
            _Repository(), prompt_root=Path.cwd(), model_client=_Client(configured=False)
        )
        request = stream_assistant.normalize_request(payload)
        final = list(stream_assistant.turn_stream(request))[-1]["data"]
        self.assertEqual(normal, final)

    def test_configured_knowledge_model_failures_are_safe(self):
        for answer in ("", "请学习 owner/private-repo", LlmClientError("secret provider body"), OSError("secret socket")):
            with self.subTest(answer=answer):
                client = _FailingClient(answer) if isinstance(answer, Exception) else _Client(answer=answer)
                assistant = AssistantOrchestrator(_Repository(), prompt_root=Path.cwd(), model_client=client)
                result = assistant.turn({"q": "我想学习 AI Agent 原理"})
                self.assertEqual(result["knowledge_basis"], "project_evidence")
                self.assertEqual(result["fallback_reason"], "model_unavailable")
                rendered = str(result)
                self.assertNotIn("secret provider body", rendered)
                self.assertNotIn("secret socket", rendered)

    def test_router_bad_output_falls_back_to_clarify(self):
        for answer in ("not-json", '{"assistant_mode":"unknown"}', LlmClientError("secret route")):
            with self.subTest(answer=answer):
                client = _FailingClient(answer) if isinstance(answer, Exception) else _Client(answer=answer)
                assistant = AssistantOrchestrator(_Repository(), prompt_root=Path.cwd(), model_client=client)
                result = assistant.turn({"q": "继续说说"})
                self.assertEqual(result["assistant_mode"], "clarify")
                self.assertEqual(result["answer_mode"], "clarification")
                self.assertTrue(result["clarification_required"])
                self.assertFalse(result["input_route"]["retrieval_performed"])
                self.assertEqual(result["recommendations"], [])
                self.assertNotIn("secret route", str(result))

    def test_short_continuation_with_candidates_never_depends_on_model_route(self):
        repository = _Repository()
        client = _Client(configured=False)
        assistant = AssistantOrchestrator(repository, prompt_root=Path.cwd(), model_client=client)
        state = {
            "goal": "找 AI Agent 项目",
            "candidate_repository_ids": ["owner/agent"],
            "primary_repository_id": "owner/agent",
            "source_identity": {"source_id": "source:1", "run_date": "2026-08-09"},
            "resumable": True,
        }

        for query in ("继续", "接着说", "展开", "还有吗"):
            with self.subTest(query=query):
                result = assistant.turn({"q": query, "state": state})
                self.assertEqual(result["assistant_mode"], "project_follow_up")
                self.assertEqual(repository.payloads[-1]["context"]["candidate_repository_ids"], ["owner/agent"])
        self.assertEqual(client.calls, 0)

    def test_project_clarification_is_normalized_and_stream_equivalent(self):
        project = _project_response()
        project.update({
            "answer": "请补充必须支持的部署方式。",
            "answer_mode": "clarification",
            "clarification_required": True,
            "clarification_question": "请补充必须支持的部署方式。",
            "input_route": {
                "route": "clarify",
                "retrieval_performed": True,
                "candidate_scope": "archive",
                "requirements": [{"field": "deployment", "operator": "eq", "value": "local", "hard": True}],
            },
        })
        repository = _Repository()
        repository.rag_ask_contextual = lambda payload, router_client=None: project
        repository.rag_ask_contextual_stream = lambda payload, router_client=None: iter([
            {"event": "meta", "data": {"query": payload["q"]}},
            {"event": "final", "data": project},
        ])
        assistant = AssistantOrchestrator(repository, prompt_root=Path.cwd(), model_client=_Client(configured=False))
        payload = {"q": "哪个项目更适合"}

        normal = assistant.turn(payload)
        final = list(assistant.turn_stream(assistant.normalize_request(payload)))[-1]["data"]

        self.assertEqual(normal, final)
        self.assertEqual(normal["assistant_mode"], "clarify")
        self.assertEqual(normal["answer_mode"], "clarification")
        self.assertTrue(normal["clarification_required"])
        self.assertEqual(normal["clarification_question"], "请补充必须支持的部署方式。")
        self.assertEqual([section["kind"] for section in normal["sections"]], ["limitations"])
        self.assertEqual(normal["citations"], [])
        self.assertEqual(normal["evidence"], [])
        self.assertEqual(normal["recommendations"], [])
        self.assertEqual(normal["input_route"]["candidate_scope"], "none")
        self.assertTrue(normal["input_route"]["retrieval_performed"])
        self.assertEqual(normal["input_route"]["requirements"], project["input_route"]["requirements"])
        self.assertFalse(normal["assistant_state"]["resumable"])

    def test_state_rejects_invalid_mode_and_sanitizes_primary(self):
        assistant = AssistantOrchestrator(_Repository(), prompt_root=Path.cwd(), model_client=_Client())
        with self.assertRaisesRegex(ValueError, "mode"):
            assistant.normalize_request({"q": "推荐项目", "mode": "invalid"})
        request = assistant.normalize_request({
            "q": "继续",
            "state": {
                "goal": "找 Agent 项目",
                "candidate_repository_ids": ["owner/agent", "bad"],
                "primary_repository_id": "owner/other",
                "source_identity": {"source_id": "source:1", "run_date": "2026-08-09"},
                "resumable": True,
            },
        })
        self.assertEqual(request["state"]["candidate_repository_ids"], ["owner/agent"])
        self.assertEqual(request["state"]["primary_repository_id"], "")

    def test_changed_source_invalidates_resumable_candidates(self):
        assistant = AssistantOrchestrator(_Repository(), prompt_root=Path.cwd(), model_client=_Client())
        request = assistant.normalize_request({
            "q": "继续",
            "state": {
                "goal": "找 Agent 项目",
                "candidate_repository_ids": ["owner/agent"],
                "primary_repository_id": "owner/agent",
                "source_identity": {"source_id": "source:old", "run_date": "2026-08-08"},
                "resumable": True,
            },
        })
        self.assertEqual(request["state"]["candidate_repository_ids"], [])
        self.assertFalse(request["state"]["resumable"])
        self.assertIn("重新检索", request["state"]["pending_question"])

    def test_missing_source_invalidates_resumable_candidates(self):
        assistant = AssistantOrchestrator(_Repository(), prompt_root=Path.cwd(), model_client=_Client())
        request = assistant.normalize_request({
            "q": "继续",
            "state": {
                "goal": "找 Agent 项目",
                "candidate_repository_ids": ["owner/agent"],
                "primary_repository_id": "owner/agent",
                "resumable": True,
            },
        })
        self.assertEqual(request["state"]["candidate_repository_ids"], [])
        self.assertFalse(request["state"]["resumable"])

    def test_quality_or_freshness_failure_does_not_create_resumable_state(self):
        for mutation in (
            {"answer_quality": {"passed": False}},
            {"freshness": {"data_freshness": "stale", "as_of": "2026-07-01"}},
        ):
            with self.subTest(mutation=mutation):
                response = _project_response()
                response.update(mutation)
                repository = _Repository()
                repository.rag_ask_contextual = lambda payload, router_client=None: response
                assistant = AssistantOrchestrator(repository, prompt_root=Path.cwd(), model_client=_Client(configured=False))
                result = assistant.turn({"q": "推荐 Agent 项目"})
                self.assertEqual(result["assistant_state"]["candidate_repository_ids"], [])
                self.assertEqual(result["assistant_state"]["primary_repository_id"], "")
                self.assertFalse(result["assistant_state"]["resumable"])

    def test_state_sanitizes_limits_and_untrusted_fields(self):
        assistant = AssistantOrchestrator(_Repository(), prompt_root=Path.cwd(), model_client=_Client())
        candidates = [f"owner/repo-{index}" for index in range(12)]
        request = assistant.normalize_request({
            "q": "这些项目哪个更适合",
            "state": {
                "schema_version": 999,
                "revision": -20,
                "goal": "g" * 2500,
                "constraints": [{"kind": "language", "value": "Python"}] * 25,
                "candidate_repository_ids": ["bad", candidates[0], candidates[0], *candidates[1:]],
                "primary_repository_id": "owner/not-present",
                "source_identity": {"source_id": "source:1", "run_date": "2026-08-09"},
                "resumable": True,
                "forbidden_history": "must be dropped",
            },
        })
        state = request["state"]
        self.assertEqual(state["schema_version"], 2)
        self.assertEqual(state["revision"], 0)
        self.assertEqual(len(state["goal"]), 2000)
        self.assertEqual(len(state["constraints"]), 20)
        self.assertEqual(state["candidate_repository_ids"], candidates[:10])
        self.assertEqual(state["primary_repository_id"], "")
        self.assertNotIn("forbidden_history", state)

    def test_schema_v1_input_is_upgraded_and_knowledge_context_is_sanitized(self):
        assistant = AssistantOrchestrator(_Repository(), prompt_root=Path.cwd(), model_client=_Client())
        request = assistant.normalize_request({
            "q": "继续",
            "state": {
                "schema_version": 1,
                "goal": "学习 Agent",
                "knowledge_context": {
                    "topic": "t" * 250,
                    "outline": [
                        {"id": "k1", "title": "第一点"},
                        {"id": "bad id", "title": "丢弃"},
                        {"id": "k1", "title": "重复"},
                        {"id": "k2", "title": "x" * 150},
                    ],
                    "focus_id": "missing",
                    "history": "不得保留",
                },
            },
        })
        state = request["state"]
        self.assertEqual(state["schema_version"], 2)
        self.assertEqual(len(state["knowledge_context"]["topic"]), 200)
        self.assertEqual([item["id"] for item in state["knowledge_context"]["outline"]], ["k1", "k2"])
        self.assertEqual(len(state["knowledge_context"]["outline"][1]["title"]), 120)
        self.assertEqual(state["knowledge_context"]["focus_id"], "")
        self.assertNotIn("history", state["knowledge_context"])

    def test_five_turn_knowledge_context_keeps_outline_and_switches_focus(self):
        repository = _Repository()
        client = _TeachingClient()
        assistant = AssistantOrchestrator(repository, prompt_root=Path.cwd(), model_client=client)
        questions = [
            "我想学习 AI Agent 的核心组成",
            "把第三点展开",
            "继续，并举例",
            "换种说法",
            "回到第一点",
        ]
        state = None
        results = []
        for question in questions:
            payload = {"q": question, **({"state": state} if state else {})}
            result = assistant.turn(payload)
            results.append(result)
            state = result["assistant_state"]

        self.assertTrue(all(result["assistant_mode"] == "knowledge" for result in results))
        first_outline = results[0]["assistant_state"]["knowledge_context"]["outline"]
        self.assertEqual([item["id"] for item in first_outline], ["k1", "k2", "k3"])
        self.assertEqual(results[1]["assistant_state"]["knowledge_context"]["focus_id"], "k3")
        self.assertEqual(results[2]["assistant_state"]["knowledge_context"]["focus_id"], "k3")
        self.assertEqual(results[3]["assistant_state"]["knowledge_context"]["focus_id"], "k3")
        self.assertEqual(results[4]["assistant_state"]["knowledge_context"]["focus_id"], "k1")
        self.assertTrue(all(result["assistant_state"]["candidate_repository_ids"] == ["owner/agent"] for result in results))
        self.assertIn('\"focus_id\": \"k3\"', client.messages[2][1]["content"])
        self.assertNotIn(client.answers[0], client.messages[1][1]["content"])


if __name__ == "__main__":
    unittest.main()
