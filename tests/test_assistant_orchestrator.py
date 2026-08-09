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
        self.assertEqual(state["schema_version"], 1)
        self.assertEqual(state["revision"], 0)
        self.assertEqual(len(state["goal"]), 2000)
        self.assertEqual(len(state["constraints"]), 20)
        self.assertEqual(state["candidate_repository_ids"], candidates[:10])
        self.assertEqual(state["primary_repository_id"], "")
        self.assertNotIn("forbidden_history", state)


if __name__ == "__main__":
    unittest.main()
