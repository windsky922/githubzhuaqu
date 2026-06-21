from __future__ import annotations

import json
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from src.api.repository import ApiRepository
from src.notifications.service import build_notification_candidates, detect_subscription_events
from src.sender import DeliveryResult
from src.storage.sqlite_store import connect, initialize, table_count
from tests.test_api import _api_route_dependencies_installed


class NotificationServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path.cwd() / f".tmp-notification-service-{uuid.uuid4().hex}"
        self.db_path = self.root / "data" / "github_weekly.sqlite"
        connection = connect(self.db_path)
        try:
            initialize(connection)
            self._seed_snapshots(connection)
            self._seed_agent_run(connection)
            connection.commit()
        finally:
            connection.close()

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_detects_evidenced_events_and_is_idempotent(self):
        first = detect_subscription_events(self.db_path)
        second = detect_subscription_events(self.db_path)

        event_types = {item["event_type"] for item in first["events"]}
        self.assertEqual(event_types, {
            "trending_entered", "star_growth_spike", "quality_changed", "risk_added",
            "risk_resolved", "release_detected", "agent_decision_changed",
        })
        self.assertTrue(all(item["evidence"] and item["citations"] for item in first["events"]))
        self.assertEqual(first["detected_count"], 7)
        self.assertEqual(second["detected_count"], 0)
        connection = connect(self.db_path)
        try:
            self.assertEqual(table_count(connection, "subscription_events"), 7)
        finally:
            connection.close()

    def test_subscription_rules_build_only_new_pending_candidates(self):
        repository = ApiRepository(root=self.root, db_path=self.db_path)
        created = repository.create_subscription({
            "name": "高风险项目事件",
            "full_names": ["owner/repo"],
            "event_types": ["risk_added", "agent_decision_changed"],
            "min_severity": "high",
            "frequency": "daily",
            "channels": ["telegram", "feishu"],
        })
        subscription = created["subscription"]
        self.assertEqual(subscription["full_names"], ["owner/repo"])
        self.assertEqual(subscription["event_types"], ["risk_added", "agent_decision_changed"])
        self.assertEqual(subscription["frequency"], "daily")

        detect_subscription_events(self.db_path)
        first = build_notification_candidates(self.db_path)
        second = build_notification_candidates(self.db_path)
        recommendations = repository.recommendations(limit=10)

        self.assertEqual(first["created_count"], 2)
        self.assertEqual(second["created_count"], 0)
        self.assertTrue(all(item["status"] == "pending" for item in first["candidates"]))
        self.assertTrue(all(item["payload"]["requires_confirmation"] for item in first["candidates"]))
        recommendation = next(item for item in recommendations["recommendations"] if item["full_name"] == "owner/repo")
        self.assertGreater(recommendation["event_memory"]["count"], 0)
        self.assertIn("最近事件", recommendation["event_reason"])
        connection = connect(self.db_path)
        try:
            self.assertEqual(table_count(connection, "notification_candidates"), 2)
        finally:
            connection.close()

    def test_delivery_requires_confirmation_deduplicates_and_retries_failed_channel(self):
        repository, candidate_id = self._prepare_delivery_candidate()

        with patch("src.notifications.service.send_delivery_message") as send:
            preview = repository.deliver_notification_candidate(candidate_id, {})
            blocked = repository.deliver_notification_candidate(
                candidate_id, {"dry_run": False, "confirm_delivery": False}
            )
        self.assertTrue(preview["accepted"])
        self.assertFalse(preview["executed"])
        self.assertFalse(blocked["accepted"])
        send.assert_not_called()
        self.assertEqual(repository.notification_deliveries(candidate_id=candidate_id)["count"], 0)

        def first_attempt(message, settings, channels):
            channel = channels[0]
            if channel == "telegram":
                return [DeliveryResult(channel=channel, sent=True)]
            return [DeliveryResult(channel=channel, sent=False, error="expected failure")]

        with patch("src.notifications.service.send_delivery_message", side_effect=first_attempt) as send:
            delivered = repository.deliver_notification_candidate(
                candidate_id,
                {"dry_run": False, "confirm_delivery": True, "requested_by": "unit-test"},
            )
        self.assertTrue(delivered["executed"])
        self.assertEqual(delivered["candidate_status"], "partial")
        self.assertEqual(send.call_count, 2)

        with patch("src.notifications.service.send_delivery_message") as send:
            duplicate = repository.deliver_notification_candidate(
                candidate_id, {"dry_run": False, "confirm_delivery": True}
            )
        self.assertFalse(duplicate["executed"])
        self.assertEqual({item["status"] for item in duplicate["results"]}, {"already_succeeded", "retry_required"})
        send.assert_not_called()

        with patch(
            "src.notifications.service.send_delivery_message",
            return_value=[DeliveryResult(channel="feishu", sent=True)],
        ) as send:
            retried = repository.deliver_notification_candidate(
                candidate_id,
                {"dry_run": False, "confirm_delivery": True, "retry_failed": True},
            )
        self.assertTrue(retried["executed"])
        self.assertEqual(retried["candidate_status"], "delivered")
        self.assertEqual(send.call_args.args[2], ["feishu"])
        deliveries = repository.notification_deliveries(candidate_id=candidate_id)["deliveries"]
        self.assertEqual(len(deliveries), 2)
        self.assertEqual({item["channel"]: item["attempt_count"] for item in deliveries}, {"telegram": 1, "feishu": 2})
        events = repository.subscription_events(status="notified")["events"]
        self.assertTrue(events)
        rag = repository.rag_ask(query="owner/repo 为什么触发通知？", limit=5)
        self.assertGreater(rag["notification_memory"]["event_count"], 0)
        self.assertIn("通知记忆", rag["answer"])
        bundle = repository.project_rag_bundle("owner/repo", limit=5)
        self.assertTrue(bundle["found"])
        self.assertGreater(bundle["notification_memory"]["event_count"], 0)
        self.assertEqual(bundle["notification_memory"]["delivery_count"], 2)

    @unittest.skipUnless(_api_route_dependencies_installed(), "本地未安装 FastAPI 或 httpx")
    def test_notification_routes_require_admin_and_default_to_preview(self):
        import os
        from fastapi.testclient import TestClient
        from src.api.app import create_app

        _, candidate_id = self._prepare_delivery_candidate()
        client = TestClient(create_app(root=self.root, db_path=self.db_path))
        events = client.get("/v1/subscription-events")
        candidates = client.get("/v1/notification-candidates")
        with patch.dict(os.environ, {"ADMIN_API_TOKEN": "test"}, clear=False):
            blocked_detect = client.post("/v1/subscription-events/detect", json={"dry_run": True})
            blocked = client.post("/v1/notification-candidates/build", json={})
            blocked_deliver = client.post(
                f"/v1/notification-candidates/{candidate_id}/deliver", json={}
            )
            built = client.post(
                "/v1/notification-candidates/build", headers={"X-Admin-Token": "test"}, json={}
            )
            preview = client.post(
                f"/v1/notification-candidates/{candidate_id}/deliver",
                headers={"X-Admin-Token": "test"},
                json={},
            )
        deliveries = client.get("/v1/notification-deliveries")

        self.assertEqual(events.status_code, 200)
        self.assertEqual(candidates.status_code, 200)
        self.assertEqual(blocked_detect.status_code, 401)
        self.assertEqual(blocked.status_code, 401)
        self.assertEqual(blocked_deliver.status_code, 401)
        self.assertEqual(built.status_code, 200)
        self.assertTrue(preview.json()["dry_run"])
        self.assertFalse(preview.json()["executed"])
        self.assertEqual(deliveries.json()["count"], 0)

    def _prepare_delivery_candidate(self) -> tuple[ApiRepository, str]:
        repository = ApiRepository(root=self.root, db_path=self.db_path)
        repository.create_subscription({
            "name": "风险投递测试",
            "full_names": ["owner/repo"],
            "event_types": ["risk_added"],
            "min_severity": "high",
            "channels": ["telegram", "feishu"],
        })
        detect_subscription_events(self.db_path)
        built = build_notification_candidates(self.db_path)
        self.assertEqual(built["created_count"], 1)
        return repository, built["candidates"][0]["candidate_id"]

    @staticmethod
    def _seed_snapshots(connection) -> None:
        connection.execute(
            """
            INSERT INTO repositories(
              full_name, html_url, description, language, stargazers_count, forks_count,
              license_name, archived, fork, pushed_at, payload_json
            ) VALUES(
              'owner/repo', 'https://github.com/owner/repo', 'agent workflow toolkit', 'Python',
              1200, 120, 'MIT', 0, 0, '2026-06-21T00:00:00Z',
              '{"full_name":"owner/repo","html_url":"https://github.com/owner/repo","description":"agent workflow toolkit","language":"Python"}'
            )
            """
        )
        rows = [
            ("2026-06-14", 0, 100, 60, ["旧风险"], ["旧质量风险"], "v1.0.0"),
            ("2026-06-21", 1, 500, 80, ["新风险"], [], "v2.0.0"),
        ]
        for run_date, rank, growth, quality, security, quality_flags, release in rows:
            payload = {
                "full_name": "owner/repo", "html_url": "https://github.com/owner/repo",
                "language": "Python", "quality_score": quality, "quality_flags": quality_flags,
                "latest_release": release,
            }
            connection.execute(
                """
                INSERT INTO selections(
                  run_date, full_name, position, score, star_growth, trending_rank, category,
                  sources_json, selection_reasons_json, security_flags_json, payload_json
                ) VALUES(?, 'owner/repo', 1, 90, ?, ?, 'AI Agent', '[]', '[]', ?, ?)
                """,
                (run_date, growth, rank, json.dumps(security, ensure_ascii=False), json.dumps(payload, ensure_ascii=False)),
            )
        connection.execute(
            """
            INSERT INTO project_corpus(
              corpus_id, run_date, full_name, html_url, title, language, category,
              sources_json, search_text, payload_json
            ) VALUES('corpus:latest', '2026-06-21', 'owner/repo', 'https://github.com/owner/repo',
                     'Agent Repo', 'Python', 'AI Agent', '[]', 'agent workflow toolkit', '{}')
            """
        )

    @staticmethod
    def _seed_agent_run(connection) -> None:
        connection.execute(
            """
            INSERT INTO project_agent_tasks(task_id, full_name, profile, task_type, reason, dedupe_key)
            VALUES('task:notify', 'owner/repo', 'agent_development', 'notify', '重要变化值得通知', 'task:notify')
            """
        )
        evidence = [{
            "evidence_id": "agent-evidence:1", "source_type": "project_corpus", "source_id": "corpus:latest",
            "source_path": "https://github.com/owner/repo", "title": "Agent Repo", "excerpt": "重要变化", "observed_at": "2026-06-21",
        }]
        citations = [{
            "citation_id": "citation:agent:1", "evidence_id": "agent-evidence:1",
            "title": "Agent Repo", "source_path": "https://github.com/owner/repo",
        }]
        result = {
            "execution_summary": "已生成订阅候选。", "decision": "subscription_candidate",
            "evidence": evidence, "citations": citations,
            "subscription_candidate": {
                "eligible": True, "full_name": "owner/repo", "reason": "重要变化值得通知",
                "requires_confirmation": True,
            },
        }
        connection.execute(
            """
            INSERT INTO project_agent_task_runs(
              run_id, task_id, status, started_at, finished_at, evidence_json, citations_json, result_json
            ) VALUES('agent-run:notify', 'task:notify', 'succeeded', '2026-06-21T01:00:00Z',
                     '2026-06-21T01:01:00Z', ?, ?, ?)
            """,
            (json.dumps(evidence, ensure_ascii=False), json.dumps(citations, ensure_ascii=False), json.dumps(result, ensure_ascii=False)),
        )


if __name__ == "__main__":
    unittest.main()
