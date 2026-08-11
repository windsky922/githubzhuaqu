from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from scripts.project_match_fixture import write_project_match_fixture
from src.api.app import create_app
from src.api.repository import ApiRepository


FRESHNESS = {
    "source_latest_date": "2026-08-09",
    "corpus_latest_date": "2026-08-09",
    "embedding_latest_date": "2026-08-09",
    "stale_days": 0,
    "data_freshness": "fresh",
    "as_of": "2026-08-09",
    "stale_after_days": 30,
    "reasons": [],
}


def _client(root: Path) -> TestClient:
    db_path = root / "data" / "assistant.sqlite"
    ApiRepository(root=root, db_path=db_path).ensure_sqlite_index()
    app = create_app(root=root, db_path=db_path)
    app.state.assistant_repository.data_source = {
        **app.state.assistant_repository.data_source,
        "available": True,
        "kind": "weekly_snapshot",
        "source_id": "source:fixture",
        "run_date": "2026-08-09",
        "reason": "",
        "attestation": FRESHNESS,
        "read_only": True,
    }
    return TestClient(app)


def _sse_events(body: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    current = ""
    for line in body.splitlines():
        if line.startswith("event: "):
            current = line[7:]
        elif line.startswith("data: "):
            events.append({"event": current, "data": json.loads(line[6:])})
    return events


def _contains_key(value: object, forbidden: set[str]) -> bool:
    if isinstance(value, dict):
        return bool(forbidden.intersection(value)) or any(_contains_key(item, forbidden) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, forbidden) for item in value)
    return False


class _TeachingClient:
    def status(self):
        return {"provider": "test", "configured": True, "model": "test"}

    def chat(self, messages):
        return "ReAct 把推理与行动交替组织，并用观察结果修正下一步决策。"

    def stream_chat(self, messages):
        yield "ReAct 把推理与行动交替组织，"
        yield "并用观察结果修正下一步决策。"


class AssistantApiTest(unittest.TestCase):
    def test_pure_teaching_api_returns_final_when_project_rag_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="assistant-api-teaching-") as directory:
            root = Path(directory)
            client = TestClient(create_app(root=root, db_path=root / "data" / "assistant.sqlite"))
            client.app.state.assistant.model_client = _TeachingClient()
            repository = client.app.state.assistant_repository
            with patch.object(
                repository,
                "rag_ask_contextual",
                side_effect=OSError("secret repository failure"),
            ), patch.object(
                repository,
                "rag_ask_contextual_stream",
                side_effect=OSError("secret repository stream failure"),
            ):
                normal = client.post("/v1/assistant/turn", json={"q": "解释 ReAct 的原理"})
                stream = client.post("/v1/assistant/turn/stream", json={"q": "解释 ReAct 的原理"})

        self.assertEqual(normal.status_code, 200)
        self.assertEqual(normal.json()["knowledge_basis"], "model_general")
        self.assertEqual(normal.json()["fallback_reason"], "project_enhancement_unavailable")
        self.assertNotIn("secret repository", normal.text)
        events = _sse_events(stream.text)
        self.assertEqual(events[0]["event"], "meta")
        self.assertEqual(events[-1]["event"], "final")
        self.assertEqual(
            [event["data"]["text"] for event in events if event["event"] == "delta"],
            ["ReAct 把推理与行动交替组织，", "并用观察结果修正下一步决策。"],
        )
        self.assertNotIn("error", [event["event"] for event in events])
        self.assertEqual(events[-1]["data"], normal.json())

    def test_mixed_teaching_project_api_preserves_hard_requirements(self) -> None:
        query = "我想学习一个必须完全离线、无需 API Key 的 Python Agent 项目"
        with tempfile.TemporaryDirectory(prefix="assistant-api-constraints-") as directory:
            root = Path(directory)
            write_project_match_fixture(root, include_e2e_capabilities=True)
            with patch.dict(
                os.environ,
                {"KIMI_API_KEY": "", "KIMI_MODEL": "", "KIMI_BASE_URL": ""},
                clear=False,
            ):
                client = _client(root)
                client.app.state.assistant.model_client = _TeachingClient()
                with patch("src.api.repository.archive_freshness", return_value=FRESHNESS):
                    response = client.post("/v1/assistant/turn", json={"q": query, "mode": "hybrid"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["assistant_mode"], "knowledge")
        self.assertEqual(body["resolved_query"], query)
        self.assertEqual(
            {
                (item["field"], item["value"])
                for item in body["input_route"]["requirements"]
                if item["hard"]
            },
            {("language", "Python"), ("offline_capable", True), ("api_key_required", False)},
        )
        self.assertEqual(body["recommendations"], [])
        self.assertEqual(body["assistant_state"]["candidate_repository_ids"], [])
        self.assertFalse(body["assistant_state"]["resumable"])

    def test_turn_and_stream_keep_compatible_final_shape(self) -> None:
        with tempfile.TemporaryDirectory(prefix="assistant-api-") as directory:
            root = Path(directory)
            write_project_match_fixture(root, include_e2e_capabilities=True)
            with patch.dict(os.environ, {"KIMI_API_KEY": "", "KIMI_MODEL": "", "KIMI_BASE_URL": ""}, clear=False):
                client = _client(root)
                payload = {"q": "推荐适合学习的 AI Agent 项目", "mode": "hybrid", "limit": 3}
                with patch("src.api.repository.archive_freshness", return_value=FRESHNESS), patch(
                    "src.api.repository.ApiRepository.ensure_sqlite_index",
                    side_effect=AssertionError("assistant must not initialize SQLite"),
                ):
                    normal = client.post("/v1/assistant/turn", json=payload)
                    stream = client.post("/v1/assistant/turn/stream", json=payload)

            self.assertEqual(normal.status_code, 200)
            body = normal.json()
            self.assertEqual(body["assistant_mode"], "knowledge")
            self.assertIn("assistant_state", body)
            self.assertEqual(body["assistant_state"]["schema_version"], 2)
            self.assertEqual(
                set(body["assistant_state"]["knowledge_context"]),
                {"topic", "outline", "focus_id"},
            )
            self.assertIn("sections", body)
            self.assertIn("recommendations", body)
            self.assertEqual(stream.status_code, 200)
            self.assertIn("text/event-stream", stream.headers["content-type"])
            self.assertTrue(stream.text.startswith("event: meta"))
            self.assertIn("event: final", stream.text)
            self.assertIn('"assistant_state":', stream.text)
            events = _sse_events(stream.text)
            final = next(event["data"] for event in events if event["event"] == "final")
            self.assertFalse(_contains_key(body, {"contexts", "prompt_context", "explanation"}))
            self.assertFalse(_contains_key(final, {"contexts", "prompt_context", "explanation"}))
            stable_fields = (
                "assistant_mode",
                "knowledge_basis",
                "answer",
                "answer_mode",
                "fallback_reason",
                "sections",
                "citations",
                "evidence",
                "recommendations",
                "answer_quality",
                "input_route",
                "freshness",
                "data_source",
                "assistant_state",
            )
            self.assertEqual(
                {key: body.get(key) for key in stable_fields},
                {key: final.get(key) for key in stable_fields},
            )

    def test_invalid_assistant_request_returns_422_before_streaming(self) -> None:
        with tempfile.TemporaryDirectory(prefix="assistant-api-invalid-") as directory:
            root = Path(directory)
            client = TestClient(create_app(root=root, db_path=root / "data" / "assistant.sqlite"))
            response = client.post("/v1/assistant/turn/stream", json={"q": "", "mode": "hybrid"})
            self.assertEqual(response.status_code, 422)
            self.assertIn("application/json", response.headers["content-type"])

    def test_invalid_state_types_return_422(self) -> None:
        with tempfile.TemporaryDirectory(prefix="assistant-api-invalid-state-") as directory:
            root = Path(directory)
            client = TestClient(create_app(root=root, db_path=root / "data" / "assistant.sqlite"))
            for state in ("history", [], {"constraints": "Python"}, {"source_identity": "old"}):
                with self.subTest(state=state):
                    response = client.post("/v1/assistant/turn", json={"q": "继续", "state": state})
                    self.assertEqual(response.status_code, 422)

    def test_assistant_rejects_auto_build(self) -> None:
        with tempfile.TemporaryDirectory(prefix="assistant-api-auto-build-") as directory:
            root = Path(directory)
            client = TestClient(create_app(root=root, db_path=root / "data" / "assistant.sqlite"))
            for value in (True, False, "false"):
                with self.subTest(value=value):
                    response = client.post("/v1/assistant/turn", json={"q": "推荐项目", "auto_build": value})
                    self.assertEqual(response.status_code, 422)

    def test_natural_follow_up_stays_inside_previous_candidates_until_reset(self) -> None:
        with tempfile.TemporaryDirectory(prefix="assistant-api-follow-up-") as directory:
            root = Path(directory)
            write_project_match_fixture(root, include_e2e_capabilities=True)
            with patch.dict(os.environ, {"KIMI_API_KEY": "", "KIMI_MODEL": "", "KIMI_BASE_URL": ""}, clear=False):
                client = _client(root)
                with patch("src.api.repository.archive_freshness", return_value=FRESHNESS):
                    first = client.post("/v1/assistant/turn", json={
                        "q": "我想学习 AI Agent 开发方向的知识，请推荐适合入门和实践的项目",
                        "mode": "hybrid",
                    }).json()
                    previous = set(first["assistant_state"]["candidate_repository_ids"])
                    follow_up = client.post("/v1/assistant/turn", json={
                        "q": "在刚才推荐的项目里，我应该先从哪个项目开始学习，为什么？",
                        "state": first["assistant_state"],
                        "mode": "hybrid",
                    }).json()
                    reset = client.post("/v1/assistant/turn", json={
                        "q": "重新搜索适合 Python 的项目",
                        "state": follow_up["assistant_state"],
                        "mode": "hybrid",
                    }).json()

            self.assertTrue(previous)
            self.assertEqual(follow_up["input_route"]["candidate_scope"], "previous_candidates")
            self.assertLessEqual({item["full_name"] for item in follow_up["recommendations"]}, previous)
            self.assertEqual(reset["input_route"]["candidate_scope"], "archive")


if __name__ == "__main__":
    unittest.main()
