from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.storage.sqlite_store import (
    connect,
    initialize,
    table_count,
    upsert_notification_candidate,
    upsert_notification_delivery,
    upsert_subscription_event,
)


class NotificationStorageTest(unittest.TestCase):
    def test_stores_event_candidate_and_delivery_audit_records(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            connection = connect(Path(directory) / "events.sqlite")
            try:
                initialize(connection)
                upsert_subscription_event(connection, {
                    "event_id": "event:1", "event_type": "risk_added", "full_name": "owner/repo",
                    "source_run_id": "agent-run:1", "severity": "high", "status": "detected",
                    "title": "新增风险", "summary": "发现新的安全风险。", "dedupe_key": "risk:owner/repo:1",
                    "detected_at": "2026-06-21T00:00:00Z", "updated_at": "2026-06-21T00:00:00Z",
                    "evidence": [{"evidence_id": "evidence:1"}],
                    "citations": [{"citation_id": "citation:1", "evidence_id": "evidence:1"}],
                    "payload": {"risk": "unsafe install"},
                })
                upsert_notification_candidate(connection, {
                    "candidate_id": "candidate:1", "subscription_id": "sub:1", "event_id": "event:1",
                    "full_name": "owner/repo", "status": "pending", "channels": ["telegram"],
                    "title": "项目风险变化", "message": "owner/repo 新增风险。",
                    "dedupe_key": "sub:1:event:1", "created_at": "2026-06-21T00:00:00Z",
                    "updated_at": "2026-06-21T00:00:00Z", "payload": {"severity": "high"},
                })
                upsert_notification_delivery(connection, {
                    "delivery_id": "delivery:1", "candidate_id": "candidate:1", "subscription_id": "sub:1",
                    "event_id": "event:1", "channel": "telegram", "status": "succeeded",
                    "attempt_count": 1, "started_at": "2026-06-21T00:00:01Z",
                    "finished_at": "2026-06-21T00:00:02Z", "dedupe_key": "sub:1:event:1:telegram",
                    "response": {"ok": True}, "payload": {"dry_run": False},
                })
                connection.commit()

                self.assertEqual(table_count(connection, "subscription_events"), 1)
                self.assertEqual(table_count(connection, "notification_candidates"), 1)
                self.assertEqual(table_count(connection, "notification_deliveries"), 1)
                event = connection.execute("SELECT * FROM subscription_events").fetchone()
                delivery = connection.execute("SELECT * FROM notification_deliveries").fetchone()
                self.assertIn("evidence:1", event["evidence_json"])
                self.assertEqual(delivery["attempt_count"], 1)
                self.assertIn('"ok": true', delivery["response_json"])
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
