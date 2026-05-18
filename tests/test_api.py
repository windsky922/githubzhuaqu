import importlib.util
import json
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from src.api.repository import ApiRepository


def _api_route_dependencies_installed() -> bool:
    return bool(importlib.util.find_spec("fastapi") and importlib.util.find_spec("httpx"))


class ApiRepositoryTest(unittest.TestCase):
    def test_reads_projects_runs_profiles_and_latest_report(self):
        root = Path.cwd() / f".tmp-api-test-{uuid.uuid4().hex}"
        try:
            _write_fixture(root)
            repository = ApiRepository(root=root, db_path=root / "data" / "github_weekly.sqlite")

            projects = repository.projects(language="Python", source="github_trending", limit=10)
            detail = repository.project_detail("owner/agent")
            runs = repository.runs()
            profiles = repository.profiles()
            latest = repository.latest_weekly()
            health = repository.v1_health()
            jobs = repository.jobs()
            job_detail = repository.job_detail("run:2026-05-09")
            trigger = repository.trigger_run_preview(
                {
                    "profile": "agent_development",
                    "sources": ["github_trending"],
                    "dry_run": True,
                    "days_back": 3,
                    "trigger_source": "test",
                    "requested_by": "unit-test",
                }
            )
            duplicate_trigger = repository.trigger_run_preview(
                {
                    "profile": "agent_development",
                    "sources": ["github_trending"],
                    "dry_run": True,
                    "days_back": 3,
                    "trigger_source": "test",
                    "requested_by": "unit-test-duplicate",
                }
            )
            unsafe_trigger = repository.trigger_run_preview({"dry_run": "false", "confirm_delivery": False})
            confirmed_trigger = repository.trigger_run_preview({"dry_run": "false", "confirm_delivery": True})
            failed_job = {
                "job_id": "preview:failed",
                "kind": "weekly_report",
                "status": "failed",
                "run_date": "",
                "submitted_at": "2026-05-09T00:00:00Z",
                "started_at": "2026-05-09T00:01:00Z",
                "finished_at": "2026-05-09T00:02:00Z",
                "request": {
                    "profile": "python",
                    "sources": ["github_search"],
                    "dry_run": True,
                    "days_back": 7,
                    "trigger_source": "test",
                    "requested_by": "unit-test",
                },
                "result": {},
                "error": "unit test failure",
            }
            repository._persist_preview_job(failed_job)
            preview_detail = repository.job_detail(trigger["job_id"])
            execution_check = repository.job_execution_check(trigger["job_id"])
            completed_execution_check = repository.job_execution_check("run:2026-05-09")
            missing_execution_check = repository.job_execution_check("missing")
            blocked_execution = repository.execute_job(trigger["job_id"], {})
            completed_execution = repository.execute_job("run:2026-05-09", {"confirm_execution": True})
            retry = repository.retry_job("preview:failed", {"requested_by": "unit-test-retry"})
            retry_blocked = repository.retry_job(trigger["job_id"], {"requested_by": "unit-test-retry"})
            with patch(
                "src.api.repository.run_planned_job",
                return_value={"executed": True, "job_id": trigger["job_id"], "status": "succeeded"},
            ) as runner:
                accepted_execution = repository.execute_job(trigger["job_id"], {"confirm_execution": True})
            job_events = repository.job_events(trigger["job_id"])
            retry_events = repository.job_events("preview:failed")
            retry_job_detail = repository.job_detail(retry["job_id"])
            planned_jobs = repository.jobs(status="planned", profile="agent_development", query="github_trending")
            audit_jobs = repository.jobs(status="planned", query="unit-test")
            succeeded_jobs = repository.jobs(status="succeeded", kind="weekly_report", query="2026-05-09")

            self.assertEqual(projects["schema_version"], 1)
            self.assertGreaterEqual(projects["count"], 1)
            self.assertEqual(projects["projects"][0]["full_name"], "owner/agent")
            self.assertTrue(detail["found"])
            self.assertEqual(detail["history_count"], 2)
            self.assertEqual(detail["total_star_growth"], 32)
            self.assertEqual(detail["best_trending_rank"], 1)
            self.assertEqual(detail["similar_projects"][0]["full_name"], "owner/agent-helper")
            self.assertEqual(runs["runs"][0]["run_date"], "2026-05-09")
            self.assertEqual(profiles["profiles"][0]["name"], "agent_development")
            self.assertEqual(latest["run_date"], "2026-05-09")
            self.assertIn("owner/agent", latest["markdown"])
            self.assertTrue(health["capabilities"]["jobs_query"])
            self.assertTrue(health["capabilities"]["job_execution_check"])
            self.assertTrue(health["capabilities"]["job_retry"])
            self.assertTrue(health["capabilities"]["local_job_runner"])
            self.assertTrue(health["capabilities"]["run_trigger_execute"])
            self.assertEqual(jobs["jobs"][0]["job_id"], "run:2026-05-09")
            self.assertTrue(job_detail["found"])
            self.assertEqual(job_detail["run_summary"]["run_date"], "2026-05-09")
            self.assertTrue(trigger["job_id"].startswith("preview:"))
            self.assertFalse(trigger["execution_supported"])
            self.assertFalse(trigger["http_execution_supported"])
            self.assertTrue(trigger["planned_job_created"])
            self.assertEqual(trigger["execution_path"], "scripts/run_planned_job.py")
            self.assertEqual(trigger["request"]["days_back"], 3)
            self.assertEqual(trigger["request"]["trigger_source"], "test")
            self.assertEqual(trigger["request"]["requested_by"], "unit-test")
            self.assertEqual(duplicate_trigger["job_id"], trigger["job_id"])
            self.assertFalse(duplicate_trigger["planned_job_created"])
            self.assertEqual(duplicate_trigger["duplicate_of"], trigger["job_id"])
            self.assertIn("未重复创建", " ".join(duplicate_trigger["safety_warnings"]))
            self.assertTrue(unsafe_trigger["request"]["dry_run"])
            self.assertTrue(unsafe_trigger["safety_warnings"])
            self.assertFalse(confirmed_trigger["request"]["dry_run"])
            self.assertTrue(confirmed_trigger["request"]["delivery_allowed"])
            self.assertTrue(preview_detail["found"])
            self.assertEqual(preview_detail["job"]["status"], "planned")
            self.assertTrue(execution_check["executable"])
            self.assertIn("scripts/run_planned_job.py", execution_check["next_command"])
            self.assertFalse(completed_execution_check["executable"])
            self.assertIn("只有 planned 任务可以被执行器消费", completed_execution_check["blockers"][0])
            self.assertFalse(missing_execution_check["found"])
            self.assertFalse(missing_execution_check["executable"])
            self.assertFalse(blocked_execution["accepted"])
            self.assertFalse(blocked_execution["executed"])
            self.assertIn("confirm_execution=true", " ".join(blocked_execution["blockers"]))
            self.assertFalse(completed_execution["accepted"])
            self.assertFalse(completed_execution["executed"])
            self.assertTrue(accepted_execution["accepted"])
            self.assertTrue(accepted_execution["executed"])
            self.assertEqual(accepted_execution["status"], "succeeded")
            runner.assert_called_once()
            self.assertTrue(retry["accepted"])
            self.assertTrue(retry["retry_created"])
            self.assertTrue(retry["job_id"].startswith("retry:"))
            self.assertEqual(retry["retry_job"]["request"]["retry_of"], "preview:failed")
            self.assertEqual(retry["retry_job"]["request"]["requested_by"], "unit-test-retry")
            self.assertFalse(retry_blocked["accepted"])
            self.assertFalse(retry_blocked["retry_created"])
            self.assertIn("只有 failed 任务可以重试", " ".join(retry_blocked["blockers"]))
            self.assertTrue(retry_job_detail["found"])
            self.assertEqual(retry_job_detail["job"]["status"], "planned")
            event_types = [event["event_type"] for event in job_events["events"]]
            self.assertIn("job_created", event_types)
            self.assertIn("duplicate_trigger_ignored", event_types)
            self.assertIn("execution_requested", event_types)
            self.assertIn("execution_blocked", event_types)
            self.assertIn("execution_started", event_types)
            self.assertIn("execution_finished", event_types)
            self.assertEqual(job_events["job_id"], trigger["job_id"])
            retry_event_types = [event["event_type"] for event in retry_events["events"]]
            self.assertIn("retry_requested", retry_event_types)
            self.assertIn("retry_created", retry_event_types)
            self.assertEqual(planned_jobs["count"], 1)
            self.assertEqual(planned_jobs["jobs"][0]["job_id"], trigger["job_id"])
            self.assertIn(trigger["job_id"], [job["job_id"] for job in audit_jobs["jobs"]])
            self.assertEqual(succeeded_jobs["count"], 1)
            self.assertEqual(succeeded_jobs["jobs"][0]["job_id"], "run:2026-05-09")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    @unittest.skipUnless(_api_route_dependencies_installed(), "本地未安装 FastAPI 或 httpx，跳过 API 路由测试")
    def test_fastapi_routes_return_public_archive_data(self):
        from fastapi.testclient import TestClient
        from src.api.app import create_app

        root = Path.cwd() / f".tmp-api-route-test-{uuid.uuid4().hex}"
        try:
            _write_fixture(root)
            setup_repository = ApiRepository(root=root, db_path=root / "data" / "github_weekly.sqlite")
            setup_repository._persist_preview_job(
                {
                    "job_id": "preview:route-failed",
                    "kind": "weekly_report",
                    "status": "failed",
                    "submitted_at": "2026-05-09T00:00:00Z",
                    "request": {"profile": "python", "sources": ["github_search"], "dry_run": True},
                    "result": {},
                    "error": "route failure",
                }
            )
            app = create_app(root=root, db_path=root / "data" / "github_weekly.sqlite")
            client = TestClient(app)

            health = client.get("/api/health")
            projects = client.get("/api/projects", params={"profile": "agent_development", "limit": 5})
            detail = client.get("/api/projects/owner/agent")
            latest = client.get("/api/weekly/latest")
            v1_health = client.get("/v1/health")
            v1_projects = client.get("/v1/projects", params={"profile": "agent_development", "limit": 5})
            v1_jobs = client.get("/v1/jobs", params={"status": "succeeded", "kind": "weekly_report", "limit": 5})
            v1_trigger = client.post(
                "/v1/runs/trigger",
                json={"profile": "agent_development", "sources": ["github_trending"], "dry_run": True, "days_back": 3},
            )
            v1_execution_check = client.get(
                "/v1/job-execution-check",
                params={"job_id": v1_trigger.json()["job_id"]},
            )
            v1_blocked_execute = client.post(f"/v1/jobs/{v1_trigger.json()['job_id']}/execute", json={})
            with patch(
                "src.api.repository.run_planned_job",
                return_value={"executed": True, "job_id": v1_trigger.json()["job_id"], "status": "succeeded"},
            ):
                v1_execute = client.post(
                    f"/v1/jobs/{v1_trigger.json()['job_id']}/execute",
                    json={"confirm_execution": True},
                )
            v1_events = client.get(f"/v1/jobs/{v1_trigger.json()['job_id']}/events")
            v1_retry = client.post("/v1/jobs/preview:route-failed/retry", json={"requested_by": "route-test"})
            v1_retry_events = client.get("/v1/jobs/preview:route-failed/events")
            v1_planned_jobs = client.get(
                "/v1/jobs",
                params={"status": "planned", "profile": "agent_development", "query": "github_trending"},
            )
            admin_page = client.get("/admin.html", params={"api": "1"})
            home = client.get("/", follow_redirects=False)

            self.assertEqual(health.status_code, 200)
            self.assertEqual(projects.status_code, 200)
            self.assertEqual(detail.status_code, 200)
            self.assertEqual(latest.status_code, 200)
            self.assertEqual(v1_health.status_code, 200)
            self.assertEqual(v1_projects.status_code, 200)
            self.assertEqual(v1_jobs.status_code, 200)
            self.assertEqual(v1_trigger.status_code, 202)
            self.assertEqual(v1_execution_check.status_code, 200)
            self.assertEqual(v1_blocked_execute.status_code, 200)
            self.assertEqual(v1_execute.status_code, 200)
            self.assertEqual(v1_events.status_code, 200)
            self.assertEqual(v1_retry.status_code, 200)
            self.assertEqual(v1_retry_events.status_code, 200)
            self.assertEqual(v1_planned_jobs.status_code, 200)
            self.assertEqual(admin_page.status_code, 200)
            self.assertIn("text/html", admin_page.headers["content-type"])
            self.assertIn("GitHub 周报本地管理首页", admin_page.text)
            self.assertEqual(home.status_code, 307)
            self.assertEqual(home.headers["location"], "/admin.html?api=1")
            self.assertEqual(projects.json()["projects"][0]["full_name"], "owner/agent")
            self.assertEqual(detail.json()["history_count"], 2)
            self.assertEqual(latest.json()["run_date"], "2026-05-09")
            self.assertEqual(v1_projects.json()["projects"][0]["full_name"], "owner/agent")
            self.assertEqual(v1_jobs.json()["jobs"][0]["job_id"], "run:2026-05-09")
            self.assertFalse(v1_trigger.json()["execution_supported"])
            self.assertTrue(v1_execution_check.json()["executable"])
            self.assertFalse(v1_blocked_execute.json()["accepted"])
            self.assertTrue(v1_execute.json()["accepted"])
            self.assertTrue(v1_execute.json()["executed"])
            self.assertGreaterEqual(v1_events.json()["count"], 4)
            self.assertIn("execution_finished", [event["event_type"] for event in v1_events.json()["events"]])
            self.assertTrue(v1_retry.json()["retry_created"])
            self.assertTrue(v1_retry.json()["job_id"].startswith("retry:"))
            self.assertIn("retry_created", [event["event_type"] for event in v1_retry_events.json()["events"]])
            self.assertEqual(v1_planned_jobs.json()["count"], 1)
        finally:
            shutil.rmtree(root, ignore_errors=True)


def _write_fixture(root: Path) -> None:
    (root / "reports").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    (root / "data" / "runs").mkdir(parents=True)
    (root / "data" / "selected").mkdir(parents=True)
    (root / "data" / "trends").mkdir(parents=True)
    (root / "data" / "state").mkdir(parents=True)
    (root / "config").mkdir(parents=True)

    (root / "reports" / "2026-05-09.md").write_text("# 周报\n\n- owner/agent", encoding="utf-8")
    (root / "docs" / "admin.html").write_text(
        "<!doctype html><html lang=\"zh-CN\"><body>GitHub 周报本地管理首页</body></html>",
        encoding="utf-8",
    )
    (root / "docs" / "runs.json").write_text(
        json.dumps({"schema_version": 1, "count": 1, "runs": [{"run_date": "2026-05-09"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (root / "docs" / "profiles.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "count": 1,
                "profiles": [{"name": "agent_development", "label": "Agent 开发"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / "data" / "runs" / "2026-05-09.json").write_text(
        json.dumps({"run_date": "2026-05-09", "status": "success", "selected_count": 1}, ensure_ascii=False),
        encoding="utf-8",
    )
    (root / "data" / "runs" / "2026-05-08.json").write_text(
        json.dumps({"run_date": "2026-05-08", "status": "success", "selected_count": 2}, ensure_ascii=False),
        encoding="utf-8",
    )
    (root / "data" / "selected" / "2026-05-09.json").write_text(
        json.dumps(
            [
                {
                    "full_name": "owner/agent",
                    "html_url": "https://github.com/owner/agent",
                    "description": "agent workflow automation",
                    "language": "Python",
                    "stargazers_count": 100,
                    "forks_count": 10,
                    "score": 0.8,
                    "star_growth": 20,
                    "trending_rank": 1,
                    "category": "AI Agent",
                    "sources": ["github_trending"],
                    "selection_reasons": ["进入 GitHub Trending 周榜第 1 位。"],
                    "security_flags": [],
                    "quality_score": 92,
                    "quality_level": "high",
                    "quality_flags": [],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / "data" / "selected" / "2026-05-08.json").write_text(
        json.dumps(
            [
                {
                    "full_name": "owner/agent",
                    "html_url": "https://github.com/owner/agent",
                    "description": "agent workflow automation",
                    "language": "Python",
                    "stargazers_count": 80,
                    "forks_count": 8,
                    "score": 0.7,
                    "star_growth": 12,
                    "trending_rank": 3,
                    "category": "AI Agent",
                    "sources": ["github_trending"],
                    "selection_reasons": ["进入 GitHub Trending 周榜第 3 位。"],
                    "security_flags": ["未识别到许可证。"],
                    "quality_score": 86,
                    "quality_level": "high",
                    "quality_flags": ["README 摘要偏短。"],
                },
                {
                    "full_name": "owner/agent-helper",
                    "html_url": "https://github.com/owner/agent-helper",
                    "description": "agent helper workflow",
                    "language": "Python",
                    "stargazers_count": 40,
                    "forks_count": 4,
                    "score": 0.6,
                    "star_growth": 9,
                    "trending_rank": 4,
                    "category": "AI Agent",
                    "sources": ["github_trending"],
                    "selection_reasons": ["匹配 Agent 开发方向。"],
                    "security_flags": [],
                    "quality_score": 80,
                    "quality_level": "medium",
                    "quality_flags": [],
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / "data" / "trends" / "2026-05-09.json").write_text(
        json.dumps({"total_projects": 1, "trending_project_count": 1, "total_star_growth": 20}, ensure_ascii=False),
        encoding="utf-8",
    )
    (root / "data" / "state" / "sent_repos.json").write_text("[]", encoding="utf-8")
    (root / "data" / "state" / "star_history.json").write_text("[]", encoding="utf-8")
    (root / "config" / "profiles.example.json").write_text(
        json.dumps(
            {
                "agent_development": {
                    "profile_label": "Agent 开发",
                    "preferred_languages": ["Python"],
                    "preferred_topics": ["agent"],
                    "search_topics": ["llm"],
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
