from __future__ import annotations

import os
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from src.agent.task_executor import HANDLERS, batch_execute_project_agent_tasks
from src.api.repository import ApiRepository
from tests.test_api import _api_route_dependencies_installed, _write_fixture


class ProjectAgentTaskExecutorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path.cwd() / f".tmp-agent-executor-{uuid.uuid4().hex}"
        _write_fixture(self.root)
        self.db_path = self.root / "data" / "github_weekly.sqlite"
        self.repository = ApiRepository(root=self.root, db_path=self.db_path)

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def _create_task(self, task_type: str = "deep_analysis", priority: int = 2) -> str:
        result = self.repository.create_project_agent_task(
            "owner/agent",
            {
                "task_type": task_type,
                "priority": priority,
                "reason": f"executor test {uuid.uuid4().hex}",
                "source": "unit-test",
            },
        )
        self.assertTrue(result["created"])
        return str(result["task"]["task_id"])

    def test_execute_is_audited_and_completed_task_cannot_repeat(self):
        task_id = self._create_task()

        check = self.repository.project_agent_task_execution_check(task_id)
        dry_run = self.repository.execute_project_agent_task(task_id, dry_run=True)
        executed = self.repository.execute_project_agent_task(task_id)
        repeated = self.repository.execute_project_agent_task(task_id)
        runs = self.repository.project_agent_task_runs(task_id=task_id)
        rag = self.repository.project_rag_bundle("owner/agent", limit=8)

        self.assertTrue(check["executable"])
        self.assertFalse(dry_run["executed"])
        self.assertTrue(executed["executed"])
        self.assertEqual(executed["status"], "succeeded")
        self.assertEqual(set(executed["result"]), {
            "execution_summary", "decision", "confidence", "evidence", "citations",
            "changes", "risk_changes", "recommended_actions", "subscription_candidate",
        })
        self.assertTrue(executed["result"]["evidence"])
        self.assertTrue(executed["result"]["citations"])
        self.assertFalse(repeated["executed"])
        self.assertFalse(repeated["executable"])
        self.assertEqual(runs["count"], 1)
        self.assertEqual(runs["runs"][0]["status"], "succeeded")
        self.assertTrue(rag["agent_task_runs"]["runs"])

    def test_failure_preserves_evidence_and_requires_explicit_retry(self):
        task_id = self._create_task(task_type="observe")

        def fail_handler(*args, **kwargs):
            raise RuntimeError("expected handler failure")

        with patch.dict(HANDLERS, {"observe": fail_handler}):
            failed = self.repository.execute_project_agent_task(task_id)

        blocked = self.repository.execute_project_agent_task(task_id)
        retry_check = self.repository.project_agent_task_execution_check(task_id, retry=True)
        retried = self.repository.execute_project_agent_task(task_id, retry=True)
        runs = self.repository.project_agent_task_runs(task_id=task_id)

        self.assertEqual(failed["status"], "failed")
        self.assertTrue(failed["evidence"])
        self.assertFalse(blocked["executed"])
        self.assertTrue(retry_check["executable"])
        self.assertEqual(retried["status"], "succeeded")
        self.assertEqual([item["status"] for item in runs["runs"]], ["succeeded", "failed"])
        self.assertTrue(runs["runs"][1]["evidence"])
        self.assertEqual(runs["runs"][1]["input"]["task_id"], task_id)
        self.assertIn("expected handler failure", runs["runs"][1]["error"])

    def test_batch_only_selects_planned_tasks_within_priority_limit(self):
        selected = self._create_task(task_type="ignore", priority=2)
        deferred = self._create_task(task_type="notify", priority=3)

        result = batch_execute_project_agent_tasks(
            self.root,
            self.db_path,
            limit=10,
            priority=2,
            task_type="ignore",
            dry_run=True,
        )

        selected_ids = [item["task_id"] for item in result["results"]]
        self.assertIn(selected, selected_ids)
        self.assertNotIn(deferred, selected_ids)
        self.assertEqual(result["executed_count"], 0)

    @unittest.skipUnless(_api_route_dependencies_installed(), "本地未安装 FastAPI 或 httpx")
    def test_execution_routes_require_admin_token(self):
        from fastapi.testclient import TestClient
        from src.api.app import create_app

        task_id = self._create_task(task_type="continue_tracking")
        client = TestClient(create_app(root=self.root, db_path=self.db_path))

        check = client.get(f"/v1/agent-tasks/{task_id}/execution-check")
        with patch.dict(os.environ, {"ADMIN_API_TOKEN": "test"}, clear=False):
            blocked = client.post(f"/v1/agent-tasks/{task_id}/execute", json={})
            executed = client.post(
                f"/v1/agent-tasks/{task_id}/execute",
                headers={"X-Admin-Token": "test"},
                json={},
            )
        runs = client.get(f"/v1/agent-tasks/{task_id}/runs")

        self.assertEqual(check.status_code, 200)
        self.assertTrue(check.json()["executable"])
        self.assertEqual(blocked.status_code, 401)
        self.assertEqual(executed.status_code, 200)
        self.assertTrue(executed.json()["executed"])
        self.assertEqual(runs.status_code, 200)
        self.assertEqual(runs.json()["count"], 1)


if __name__ == "__main__":
    unittest.main()
