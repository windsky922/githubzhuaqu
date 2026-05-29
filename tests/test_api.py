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
            recommendations = repository.recommendations(profile="agent_development", language="Python", limit=10)
            detail = repository.project_detail("owner/agent")
            runs = repository.runs()
            profiles = repository.profiles()
            created_subscription = repository.create_subscription(
                {
                    "name": "Agent 开发订阅",
                    "profile": "agent_development",
                    "language": "Python",
                    "query": "agent",
                    "channels": ["telegram", "unknown"],
                    "limit": 8,
                }
            )
            subscriptions = repository.subscriptions()
            subscription_recommendations = repository.subscription_recommendations(
                created_subscription["subscription"]["subscription_id"],
                limit=5,
            )
            subscription_trigger = repository.trigger_subscription_run(
                created_subscription["subscription"]["subscription_id"],
                {"requested_by": "unit-test-subscription", "sources": ["subscription"]},
            )
            missing_subscription_recommendations = repository.subscription_recommendations("sub:missing")
            updated_subscription = repository.update_subscription(
                created_subscription["subscription"]["subscription_id"],
                {"status": "disabled", "query": "workflow"},
            )
            disabled_subscription_trigger = repository.trigger_subscription_run(
                created_subscription["subscription"]["subscription_id"],
                {"requested_by": "unit-test-subscription"},
            )
            latest = repository.latest_weekly()
            health = repository.v1_health()
            jobs = repository.jobs(status="succeeded")
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
            database_summary = repository.database_summary()
            database_trends = repository.database_trends(limit=5)
            database_facets = repository.database_facets(limit=5)
            search = repository.search(query="agent workflow", language="Python", limit=5)
            rag_corpus = repository.rag_corpus(query="agent workflow", language="Python", limit=5)
            latest_rag_corpus = repository.rag_corpus(language="Python", limit=5)
            similar = repository.similar_projects("owner/agent", limit=5)
            comparison = repository.compare_projects(["owner/agent", "owner/agent-helper", "missing/repo"])
            preference_comparison = repository.compare_projects(
                ["owner/agent", "owner/agent-helper"],
                profile="agent_development",
                language="Python",
                query="agent",
            )

            self.assertEqual(projects["schema_version"], 1)
            self.assertGreaterEqual(projects["count"], 1)
            self.assertEqual(projects["projects"][0]["full_name"], "owner/agent")
            self.assertEqual(recommendations["schema_version"], 1)
            self.assertEqual(recommendations["profile"], "agent_development")
            self.assertGreaterEqual(recommendations["count"], 1)
            self.assertEqual(recommendations["recommendations"][0]["full_name"], "owner/agent")
            self.assertIn("profile=agent_development", recommendations["selection_summary"][0])
            self.assertTrue(detail["found"])
            self.assertEqual(detail["history_count"], 2)
            self.assertEqual(detail["total_star_growth"], 32)
            self.assertEqual(detail["best_trending_rank"], 1)
            self.assertIn("进入 GitHub Trending 周榜第 1 位。", detail["selection_reasons"])
            self.assertIn("历史入选 2 次，累计新增 Star 32。", detail["trend_summary"])
            self.assertIn("最好 GitHub Trending 排名为第 1 位。", detail["trend_summary"])
            self.assertEqual(detail["similar_projects"][0]["full_name"], "owner/agent-helper")
            self.assertEqual(runs["runs"][0]["run_date"], "2026-05-09")
            self.assertEqual(profiles["profiles"][0]["name"], "agent_development")
            self.assertTrue(health["capabilities"]["subscriptions"])
            self.assertTrue(created_subscription["created"])
            self.assertEqual(created_subscription["subscription"]["channels"], ["telegram"])
            self.assertEqual(created_subscription["subscription"]["limit"], 8)
            self.assertEqual(subscriptions["count"], 1)
            self.assertEqual(subscriptions["subscriptions"][0]["profile"], "agent_development")
            self.assertTrue(subscription_recommendations["found"])
            self.assertEqual(subscription_recommendations["subscription"]["subscription_id"], created_subscription["subscription"]["subscription_id"])
            self.assertEqual(subscription_recommendations["recommendations"][0]["full_name"], "owner/agent")
            self.assertIn("订阅 Agent 开发订阅 当前状态为 enabled", subscription_recommendations["selection_summary"][0])
            self.assertTrue(subscription_trigger["found"])
            self.assertTrue(subscription_trigger["accepted"])
            self.assertTrue(subscription_trigger["job_id"].startswith("preview:"))
            self.assertEqual(subscription_trigger["request"]["subscription_id"], created_subscription["subscription"]["subscription_id"])
            self.assertEqual(subscription_trigger["request"]["language"], "Python")
            self.assertEqual(subscription_trigger["request"]["query"], "agent")
            self.assertFalse(missing_subscription_recommendations["found"])
            self.assertTrue(updated_subscription["updated"])
            self.assertEqual(updated_subscription["subscription"]["status"], "disabled")
            self.assertEqual(updated_subscription["subscription"]["query"], "workflow")
            self.assertFalse(disabled_subscription_trigger["accepted"])
            self.assertIn("不是 enabled 状态", " ".join(disabled_subscription_trigger["blockers"]))
            self.assertEqual(latest["run_date"], "2026-05-09")
            self.assertIn("owner/agent", latest["markdown"])
            self.assertTrue(health["capabilities"]["jobs_query"])
            self.assertTrue(health["capabilities"]["recommendations"])
            self.assertTrue(health["capabilities"]["job_execution_check"])
            self.assertTrue(health["capabilities"]["job_retry"])
            self.assertTrue(health["capabilities"]["local_job_runner"])
            self.assertTrue(health["capabilities"]["run_trigger_execute"])
            self.assertTrue(health["capabilities"]["subscription_recommendations"])
            self.assertTrue(health["capabilities"]["subscription_trigger"])
            self.assertTrue(health["capabilities"]["database_summary"])
            self.assertTrue(health["capabilities"]["database_trends"])
            self.assertTrue(health["capabilities"]["database_facets"])
            self.assertTrue(health["capabilities"]["project_search"])
            self.assertTrue(health["capabilities"]["project_similarity"])
            self.assertTrue(health["capabilities"]["project_compare"])
            self.assertTrue(health["capabilities"]["rag_corpus"])
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
            self.assertGreaterEqual(database_summary["table_counts"]["repositories"], 1)
            self.assertGreaterEqual(database_summary["table_counts"]["project_corpus"], 1)
            self.assertGreaterEqual(database_summary["table_counts"]["project_corpus_fts"], 1)
            self.assertGreaterEqual(database_summary["table_counts"]["job_events"], 1)
            self.assertEqual(database_summary["latest_run"]["run_date"], "2026-05-09")
            self.assertIn("planned", database_summary["job_status_counts"])
            self.assertIn("disabled", database_summary["subscription_status_counts"])
            self.assertTrue(database_summary["rag_readiness"]["ready_for_text_index"])
            self.assertGreaterEqual(database_trends["count"], 2)
            self.assertEqual(database_trends["summary"]["latest_run_date"], "2026-05-09")
            self.assertGreaterEqual(database_trends["summary"]["total_selected_count"], 3)
            self.assertEqual(database_trends["points"][-1]["run_date"], "2026-05-09")
            self.assertEqual(database_facets["languages"][0]["name"], "Python")
            self.assertEqual(database_facets["categories"][0]["name"], "AI Agent")
            self.assertEqual(database_facets["sources"][0]["name"], "github_trending")
            self.assertEqual(database_facets["quality_levels"][0]["name"], "high")
            self.assertIn("none", [item["name"] for item in database_facets["risk_levels"]])
            self.assertIn("disabled", [item["name"] for item in database_facets["subscriptions"]["statuses"]])
            self.assertTrue(database_facets["rag_readiness"]["ready_for_personalized_filters"])
            self.assertTrue(database_facets["rag_readiness"]["ready_for_text_search"])
            self.assertEqual(search["schema_version"], 1)
            self.assertEqual(search["search_engine"], "fts5")
            self.assertGreaterEqual(search["count"], 1)
            self.assertIn("owner/agent", [item["full_name"] for item in search["results"]])
            self.assertIn("agent", search["results"][0]["snippet"].lower())
            self.assertEqual(rag_corpus["schema_version"], 1)
            self.assertEqual(rag_corpus["retrieval"]["mode"], "fts5")
            self.assertGreaterEqual(rag_corpus["count"], 1)
            self.assertIn("owner/agent", [item["metadata"]["full_name"] for item in rag_corpus["documents"]])
            self.assertTrue(rag_corpus["documents"][0]["text"])
            self.assertTrue(rag_corpus["documents"][0]["evidence"])
            self.assertTrue(rag_corpus["rag_readiness"]["ready_for_embedding"])
            self.assertEqual(latest_rag_corpus["retrieval"]["mode"], "latest")
            self.assertGreaterEqual(latest_rag_corpus["count"], 1)
            self.assertTrue(similar["found"])
            self.assertIn("fts5", similar["search_engine"])
            self.assertGreaterEqual(similar["count"], 1)
            self.assertEqual(similar["similar_projects"][0]["full_name"], "owner/agent-helper")
            self.assertGreater(similar["similar_projects"][0]["similarity_score"], 0)
            self.assertTrue(similar["similar_projects"][0]["similarity_reasons"])
            self.assertEqual(comparison["schema_version"], 1)
            self.assertEqual(comparison["count"], 2)
            self.assertEqual(comparison["missing"], ["missing/repo"])
            self.assertEqual(comparison["projects"][0]["full_name"], "owner/agent")
            self.assertIn("owner/agent", comparison["matrix"][0]["values"])
            self.assertEqual(comparison["best_by"]["highest_total_star_growth"], "owner/agent")
            self.assertEqual(comparison["recommendation"]["primary_project"], "owner/agent")
            self.assertEqual(comparison["recommendation"]["scoring_model"], "rule:v1")
            self.assertTrue(comparison["recommendation"]["reasons"])
            self.assertTrue(preference_comparison["preference"]["active"])
            self.assertEqual(preference_comparison["preference"]["language"], "Python")
            self.assertEqual(preference_comparison["recommendation"]["scoring_model"], "rule:v2-preference")
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
            v1_database_summary = client.get("/v1/database/summary")
            v1_database_trends = client.get("/v1/database/trends", params={"limit": 5})
            v1_database_facets = client.get("/v1/database/facets", params={"limit": 5})
            v1_search = client.get("/v1/search", params={"q": "agent workflow", "language": "Python", "limit": 5})
            v1_rag_corpus = client.get(
                "/v1/rag/corpus",
                params={"q": "agent workflow", "language": "Python", "limit": 5},
            )
            v1_similar = client.get("/v1/projects/owner/agent/similar", params={"limit": 5})
            v1_compare = client.get(
                "/v1/projects/compare",
                params={
                    "repos": "owner/agent,owner/agent-helper,missing/repo",
                    "profile": "agent_development",
                    "language": "Python",
                    "query": "agent",
                },
            )
            v1_projects = client.get("/v1/projects", params={"profile": "agent_development", "limit": 5})
            v1_recommendations = client.get(
                "/v1/recommendations",
                params={"profile": "agent_development", "language": "Python", "limit": 5},
            )
            v1_jobs = client.get("/v1/jobs", params={"status": "succeeded", "kind": "weekly_report", "limit": 5})
            v1_create_subscription = client.post(
                "/v1/subscriptions",
                json={
                    "name": "Agent 开发订阅",
                    "profile": "agent_development",
                    "language": "Python",
                    "channels": ["telegram", "secret-token"],
                },
            )
            subscription_id = v1_create_subscription.json()["subscription"]["subscription_id"]
            v1_subscriptions = client.get("/v1/subscriptions", params={"limit": 5})
            v1_subscription_recommendations = client.get(
                f"/v1/subscriptions/{subscription_id}/recommendations",
                params={"limit": 5},
            )
            v1_subscription_trigger = client.post(
                f"/v1/subscriptions/{subscription_id}/trigger",
                json={"requested_by": "route-subscription", "sources": ["subscription"]},
            )
            v1_update_subscription = client.patch(
                f"/v1/subscriptions/{subscription_id}",
                json={"status": "disabled"},
            )
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
            self.assertEqual(v1_database_summary.status_code, 200)
            self.assertEqual(v1_database_trends.status_code, 200)
            self.assertEqual(v1_database_facets.status_code, 200)
            self.assertEqual(v1_search.status_code, 200)
            self.assertEqual(v1_rag_corpus.status_code, 200)
            self.assertEqual(v1_similar.status_code, 200)
            self.assertEqual(v1_compare.status_code, 200)
            self.assertEqual(v1_projects.status_code, 200)
            self.assertEqual(v1_recommendations.status_code, 200)
            self.assertEqual(v1_jobs.status_code, 200)
            self.assertEqual(v1_create_subscription.status_code, 201)
            self.assertEqual(v1_subscriptions.status_code, 200)
            self.assertEqual(v1_subscription_recommendations.status_code, 200)
            self.assertEqual(v1_subscription_trigger.status_code, 202)
            self.assertEqual(v1_update_subscription.status_code, 200)
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
            self.assertGreaterEqual(v1_database_summary.json()["table_counts"]["repositories"], 1)
            self.assertTrue(v1_database_summary.json()["rag_readiness"]["ready_for_text_index"])
            self.assertGreaterEqual(v1_database_trends.json()["count"], 1)
            self.assertEqual(v1_database_facets.json()["languages"][0]["name"], "Python")
            self.assertEqual(v1_database_facets.json()["sources"][0]["name"], "github_trending")
            self.assertIn("owner/agent", [item["full_name"] for item in v1_search.json()["results"]])
            self.assertIn("owner/agent", [item["metadata"]["full_name"] for item in v1_rag_corpus.json()["documents"]])
            self.assertTrue(v1_rag_corpus.json()["rag_readiness"]["ready_for_embedding"])
            self.assertEqual(v1_similar.json()["similar_projects"][0]["full_name"], "owner/agent-helper")
            self.assertEqual(v1_compare.json()["count"], 2)
            self.assertEqual(v1_compare.json()["best_by"]["highest_total_star_growth"], "owner/agent")
            self.assertEqual(v1_compare.json()["recommendation"]["primary_project"], "owner/agent")
            self.assertEqual(v1_compare.json()["recommendation"]["scoring_model"], "rule:v2-preference")
            self.assertEqual(v1_projects.json()["projects"][0]["full_name"], "owner/agent")
            self.assertEqual(v1_recommendations.json()["recommendations"][0]["full_name"], "owner/agent")
            self.assertIn("profile=agent_development", v1_recommendations.json()["selection_summary"][0])
            self.assertEqual(v1_jobs.json()["jobs"][0]["job_id"], "run:2026-05-09")
            self.assertEqual(v1_subscriptions.json()["subscriptions"][0]["profile"], "agent_development")
            self.assertEqual(v1_create_subscription.json()["subscription"]["channels"], ["telegram"])
            self.assertTrue(v1_subscription_recommendations.json()["found"])
            self.assertEqual(v1_subscription_recommendations.json()["recommendations"][0]["full_name"], "owner/agent")
            self.assertTrue(v1_subscription_trigger.json()["accepted"])
            self.assertEqual(v1_subscription_trigger.json()["request"]["subscription_id"], subscription_id)
            self.assertEqual(v1_update_subscription.json()["subscription"]["status"], "disabled")
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
