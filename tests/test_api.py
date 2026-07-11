import importlib.util
import json
import os
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from src.api.repository import ApiRepository
from src.storage.sqlite_store import connect


def _api_route_dependencies_installed() -> bool:
    return bool(importlib.util.find_spec("fastapi") and importlib.util.find_spec("httpx"))


class ApiRepositoryTest(unittest.TestCase):
    def test_projects_returns_pagination_metadata(self):
        root = Path.cwd() / f".tmp-api-test-{uuid.uuid4().hex}"
        try:
            _write_fixture(root)
            repository = ApiRepository(root=root, db_path=root / "data" / "github_weekly.sqlite")
            page = repository.projects(limit=1, offset=1)

            self.assertEqual(page["count"], 1)
            self.assertEqual(page["total"], 3)
            self.assertEqual(page["offset"], 1)
            self.assertEqual(page["limit"], 1)
            self.assertTrue(page["has_more"])
            self.assertIn("full_name", page["projects"][0])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    @unittest.skipUnless(_api_route_dependencies_installed(), "本地未安装 FastAPI 或 httpx，跳过 API 路由测试")
    def test_project_pagination_routes_are_consistent(self):
        from fastapi.testclient import TestClient
        from src.api.app import create_app

        root = Path.cwd() / f".tmp-api-test-{uuid.uuid4().hex}"
        try:
            _write_fixture(root)
            client = TestClient(create_app(root=root, db_path=root / "data" / "github_weekly.sqlite"))
            legacy = client.get("/api/projects", params={"limit": 1, "offset": 1})
            versioned = client.get("/v1/projects", params={"limit": 1, "offset": 1})

            self.assertEqual(legacy.status_code, 200)
            self.assertEqual(versioned.status_code, 200)
            for payload in (legacy.json(), versioned.json()):
                self.assertEqual(payload["offset"], 1)
                self.assertEqual(payload["limit"], 1)
                self.assertEqual(payload["total"], 3)
                self.assertEqual(payload["count"], 1)
                self.assertTrue(payload["has_more"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

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
            created_feedback = repository.create_project_feedback(
                {
                    "full_name": "owner/agent",
                    "profile": "agent_development",
                    "rating": 2,
                    "labels": ["useful", "agent"],
                    "note": "适合继续跟踪。",
                    "source": "unit-test",
                }
            )
            project_feedback = repository.project_feedback(full_name="owner/agent", limit=5)
            profile_feedback = repository.project_feedback(profile="agent_development", limit=5)
            missing_feedback = repository.create_project_feedback({"rating": 1})
            feedback_recommendations = repository.recommendations(
                profile="agent_development",
                language="Python",
                limit=10,
            )
            (root / "README.md").write_text(
                "# 测试项目\n\n开发上下文 RAG 需要记录反馈入口、RAG 维护和最近测试失败原因。",
                encoding="utf-8",
            )
            (root / "docs" / "api.md").write_text(
                "POST /v1/dev-context/index\nGET /v1/dev-context/search?q=反馈入口",
                encoding="utf-8",
            )
            (root / "docs" / "data-contracts.md").write_text(
                "dev_corpus dev_chunks dev_embeddings dev_runs",
                encoding="utf-8",
            )
            (root / "docs" / "operation-log.md").write_text(
                "# 操作日志\n\n最近测试失败需要通过开发上下文 RAG 检索。",
                encoding="utf-8",
            )
            dev_index = repository.dev_context_index({"run_checks": False})
            dev_search = repository.dev_context_search(query="反馈入口", limit=5)
            dev_ask = repository.dev_context_ask({"question": "最近测试为什么失败？", "limit": 5})
            dev_plan = repository.plan_dev_context_index(
                {"run_checks": False, "requested_by": "test", "trigger_source": "test"}
            )
            dev_plan_check = repository.job_execution_check(dev_plan["job_id"])
            dev_plan_execute = repository.execute_job(
                dev_plan["job_id"],
                {"confirm_execution": True, "requested_by": "test"},
            )
            dev_plan_jobs = repository.jobs(kind="dev_context_index", status="succeeded", limit=5)
            dev_run = repository.dev_context_run(dev_index["run_id"])
            dev_database_summary = repository.database_summary()
            latest = repository.latest_weekly()
            health = repository.v1_health()
            jobs = repository.jobs(status="succeeded", kind="weekly_report")
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
            rag_retrieve = repository.rag_retrieve(query="agent workflow", language="Python", limit=5)
            rag_vector_search = repository.rag_vector_search(
                query="agent workflow",
                language="Python",
                limit=5,
                auto_build=True,
            )
            rag_hybrid_search = repository.rag_hybrid_search(
                query="agent workflow",
                language="Python",
                limit=5,
                auto_build=True,
            )
            rag_search_compare = repository.rag_search_compare(
                query="agent workflow",
                language="Python",
                limit=5,
                auto_build=True,
            )
            rag_search_evaluation = repository.rag_search_evaluation(
                queries=["agent workflow", "python automation"],
                language="Python",
                limit=5,
                auto_build=True,
            )
            rag_search_evaluation_blocked = repository.persist_rag_search_evaluation(
                {"queries": ["agent workflow"], "language": "Python", "requested_by": "test"}
            )
            rag_search_evaluation_job = repository.persist_rag_search_evaluation(
                {
                    "queries": ["agent workflow", "python automation"],
                    "language": "Python",
                    "limit": 5,
                    "auto_build": True,
                    "confirm_execution": True,
                    "requested_by": "test",
                }
            )
            rag_search_evaluation_jobs = repository.jobs(kind="rag_search_evaluation", status="succeeded", limit=5)
            rag_search_evaluation_events = repository.job_events(rag_search_evaluation_job["job_id"], limit=5)
            rag_search_evaluation_trends = repository.rag_search_evaluation_trends(limit=5)
            rag_search_evaluation_plan = repository.plan_rag_search_evaluation(
                {"queries": ["agent workflow"], "language": "Python", "limit": 5, "requested_by": "test"}
            )
            rag_search_evaluation_plan_check = repository.job_execution_check(rag_search_evaluation_plan["job_id"])
            rag_search_evaluation_plan_execute = repository.execute_job(
                rag_search_evaluation_plan["job_id"], {"confirm_execution": True, "requested_by": "test"}
            )
            rag_explain = repository.rag_explain(query="agent workflow", language="Python", limit=5)
            rag_ask = repository.rag_ask(query="agent workflow", language="Python", limit=5)
            rag_hybrid_explain = repository.rag_explain(
                query="agent workflow",
                language="Python",
                limit=5,
                mode="hybrid",
                auto_build=True,
            )
            rag_hybrid_ask = repository.rag_ask(
                query="agent workflow",
                language="Python",
                limit=5,
                mode="hybrid",
                auto_build=True,
            )
            rag_explanations = repository.rag_explanations(query="agent", limit=5)
            project_rag_explanations = repository.rag_explanations(repo="owner/agent", limit=5)
            project_rag_bundle = repository.project_rag_bundle("owner/agent", limit=5, explanation_limit=5)
            rag_quality_summary = repository.rag_quality_summary(limit=5)
            rag_coverage = repository.rag_coverage(limit=5)
            rag_diagnostics = repository.rag_diagnostics(limit=5)
            rag_backfill_preview = repository.backfill_rag_explanations_from_payload({"limit": 1, "dry_run": True})
            rag_backfill_jobs = repository.jobs(kind="rag_backfill", status="succeeded", limit=5)
            rag_backfill_events = repository.job_events(rag_backfill_preview["job_id"])
            rag_backfill_plan = repository.plan_rag_backfill({"limit": 1, "dry_run": True, "requested_by": "test"})
            rag_backfill_precheck = repository.job_execution_check(rag_backfill_plan["job_id"])
            rag_backfill_execute = repository.execute_job(
                rag_backfill_plan["job_id"],
                {"confirm_execution": True, "requested_by": "test"},
            )
            rag_maintenance_plan = repository.plan_rag_maintenance(
                {"limit": 1, "dry_run": True, "requested_by": "test"}
            )
            rag_maintenance_duplicate = repository.plan_rag_maintenance(
                {"limit": 1, "dry_run": True, "requested_by": "test"}
            )
            rag_maintenance_report = repository.rag_maintenance_report(limit=5)
            database_summary_after_explain = repository.database_summary()
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
            self.assertTrue(created_feedback["accepted"])
            self.assertTrue(created_feedback["created"])
            self.assertEqual(created_feedback["feedback"]["full_name"], "owner/agent")
            self.assertEqual(created_feedback["feedback"]["rating"], 2)
            self.assertEqual(created_feedback["feedback"]["labels"], ["useful", "agent"])
            self.assertFalse(missing_feedback["accepted"])
            self.assertEqual(project_feedback["count"], 1)
            self.assertEqual(project_feedback["feedback"][0]["feedback_id"], created_feedback["feedback"]["feedback_id"])
            self.assertEqual(project_feedback["summary"]["average_rating"], 2)
            self.assertTrue(project_feedback["summary"]["ready_for_preference_memory"])
            self.assertEqual(profile_feedback["count"], 1)
            self.assertEqual(feedback_recommendations["feedback_memory"]["record_count"], 1)
            self.assertEqual(feedback_recommendations["recommendations"][0]["feedback_memory"]["average_rating"], 2)
            self.assertGreater(feedback_recommendations["recommendations"][0]["preference_score"], 0)
            self.assertEqual(dev_index["status"], "succeeded")
            self.assertGreaterEqual(dev_index["source_count"], 6)
            self.assertGreater(dev_index["chunk_count"], 0)
            self.assertEqual(dev_index["embedding_count"], dev_index["chunk_count"])
            self.assertGreater(dev_search["count"], 0)
            self.assertEqual(dev_search["results"][0]["source_type"], "document")
            self.assertIn("answer", dev_ask)
            self.assertEqual(dev_ask["question_type"], "test_diagnosis")
            self.assertTrue(dev_ask["evidence"])
            self.assertTrue(dev_ask["citations"])
            self.assertIn(dev_ask["confidence"], {"low", "medium", "high"})
            self.assertTrue(dev_ask["next_actions"])
            self.assertTrue(dev_plan["planned_job_created"])
            self.assertEqual(dev_plan["job"]["kind"], "dev_context_index")
            self.assertTrue(dev_plan_check["executable"])
            self.assertEqual(dev_plan_check["kind"], "dev_context_index")
            self.assertFalse(dev_plan_check["request"]["run_checks"])
            self.assertTrue(dev_plan_execute["executed"])
            self.assertEqual(dev_plan_execute["status"], "succeeded")
            self.assertGreater(dev_plan_execute["runner_result"]["result"]["chunk_count"], 0)
            self.assertTrue(dev_plan_jobs["jobs"])
            self.assertEqual(dev_plan_jobs["jobs"][0]["kind"], "dev_context_index")
            self.assertTrue(dev_run["found"])
            self.assertEqual(dev_run["run"]["run_id"], dev_index["run_id"])
            self.assertGreaterEqual(dev_database_summary["table_counts"]["dev_corpus"], 1)
            self.assertGreaterEqual(dev_database_summary["table_counts"]["dev_chunks"], 1)
            self.assertGreaterEqual(dev_database_summary["table_counts"]["dev_embeddings"], 1)
            self.assertGreaterEqual(dev_database_summary["table_counts"]["dev_runs"], 1)
            self.assertTrue(dev_database_summary["rag_readiness"]["ready_for_dev_context_search"])
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
            self.assertTrue(health["capabilities"]["project_feedback"])
            self.assertTrue(health["capabilities"]["feedback_memory"])
            self.assertTrue(health["capabilities"]["database_summary"])
            self.assertTrue(health["capabilities"]["database_trends"])
            self.assertTrue(health["capabilities"]["database_facets"])
            self.assertTrue(health["capabilities"]["dev_context_index"])
            self.assertTrue(health["capabilities"]["dev_context_index_jobs"])
            self.assertTrue(health["capabilities"]["dev_context_index_plan"])
            self.assertTrue(health["capabilities"]["dev_context_search"])
            self.assertTrue(health["capabilities"]["dev_context_ask"])
            self.assertTrue(health["capabilities"]["dev_context_runs"])
            self.assertTrue(health["capabilities"]["project_search"])
            self.assertTrue(health["capabilities"]["project_similarity"])
            self.assertTrue(health["capabilities"]["project_compare"])
            self.assertTrue(health["capabilities"]["rag_corpus"])
            self.assertTrue(health["capabilities"]["rag_retrieve"])
            self.assertTrue(health["capabilities"]["rag_vector_search"])
            self.assertTrue(health["capabilities"]["rag_hybrid_search"])
            self.assertTrue(health["capabilities"]["rag_search_compare"])
            self.assertTrue(health["capabilities"]["rag_search_evaluation"])
            self.assertTrue(health["capabilities"]["rag_search_evaluation_jobs"])
            self.assertTrue(health["capabilities"]["rag_search_evaluation_trends"])
            self.assertTrue(health["capabilities"]["rag_search_evaluation_plan"])
            self.assertTrue(health["capabilities"]["rag_explain"])
            self.assertTrue(health["capabilities"]["rag_ask"])
            self.assertTrue(health["capabilities"]["rag_project_explanations"])
            self.assertTrue(health["capabilities"]["rag_project_bundle"])
            self.assertTrue(health["capabilities"]["rag_quality_summary"])
            self.assertTrue(health["capabilities"]["rag_coverage"])
            self.assertTrue(health["capabilities"]["rag_diagnostics"])
            self.assertTrue(health["capabilities"]["rag_backfill_explanations"])
            self.assertTrue(health["capabilities"]["rag_maintenance_plan"])
            self.assertTrue(health["capabilities"]["rag_maintenance_report"])
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
            self.assertGreaterEqual(database_summary["table_counts"]["rag_chunks"], 1)
            self.assertGreaterEqual(database_summary["table_counts"]["rag_chunks_fts"], 1)
            self.assertEqual(database_summary["table_counts"]["project_feedback"], 1)
            self.assertGreaterEqual(database_summary["table_counts"]["job_events"], 1)
            self.assertEqual(database_summary["latest_run"]["run_date"], "2026-05-09")
            self.assertIn("planned", database_summary["job_status_counts"])
            self.assertIn("disabled", database_summary["subscription_status_counts"])
            self.assertTrue(database_summary["rag_readiness"]["ready_for_text_index"])
            self.assertTrue(database_summary["rag_readiness"]["ready_for_chunk_retrieval"])
            self.assertTrue(database_summary["rag_readiness"]["ready_for_feedback_memory"])
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
            self.assertEqual(rag_retrieve["schema_version"], 1)
            self.assertEqual(rag_retrieve["retrieval"]["mode"], "fts5")
            self.assertGreaterEqual(rag_retrieve["count"], 1)
            self.assertIn("owner/agent", [item["metadata"]["full_name"] for item in rag_retrieve["contexts"]])
            self.assertTrue(rag_retrieve["citations"])
            self.assertIn("owner/agent", rag_retrieve["prompt_context"])
            self.assertEqual(rag_vector_search["retrieval"]["mode"], "vector")
            self.assertEqual(rag_vector_search["retrieval"]["model"], "local-hash-v1")
            self.assertGreaterEqual(rag_vector_search["count"], 1)
            self.assertIn("owner/agent", [item["metadata"]["full_name"] for item in rag_vector_search["contexts"]])
            self.assertTrue(rag_vector_search["citations"])
            self.assertEqual(rag_explain["schema_version"], 1)
            self.assertTrue(rag_explain["explanation_id"].startswith("ragx:"))
            self.assertTrue(rag_explain["cached"])
            self.assertGreaterEqual(rag_explain["quality"]["score"], 1)
            self.assertIn(rag_explain["quality"]["level"], {"low", "medium", "high"})
            self.assertGreaterEqual(rag_explain["count"], 1)
            self.assertEqual(rag_explain["explanation"]["scoring_model"], "rule:rag-explain-v1")
            self.assertIn("owner/agent", rag_explain["explanation"]["answer"])
            self.assertTrue(rag_explain["explanation"]["why_recommended"])
            self.assertTrue(rag_explain["explanation"]["evidence"])
            self.assertTrue(rag_explain["explanation"]["next_steps"])
            self.assertEqual(rag_ask["schema_version"], 1)
            self.assertEqual(rag_ask["answer_model"], "rule:rag-ask-v1")
            self.assertIn("owner/agent", rag_ask["answer"])
            self.assertTrue(rag_ask["citations"])
            self.assertIn("answer_quality", rag_ask)
            self.assertTrue(rag_ask["answer_quality"]["passed"])
            self.assertTrue(rag_ask["next_actions"])
            self.assertTrue(rag_ask["source_explanation_id"].startswith("ragx:"))
            self.assertGreaterEqual(rag_hybrid_search["count"], 1)
            self.assertEqual(rag_hybrid_search["retrieval"]["mode"], "hybrid")
            self.assertIn("text", rag_hybrid_search["contexts"][0]["retrieval_sources"])
            self.assertIn("vector", rag_hybrid_search["contexts"][0]["retrieval_sources"])
            self.assertTrue(rag_hybrid_search["citations"])
            self.assertEqual(rag_search_compare["schema_version"], 1)
            self.assertEqual(rag_search_compare["modes"]["fts5"]["mode"], "fts5")
            self.assertEqual(rag_search_compare["modes"]["vector"]["mode"], "vector")
            self.assertEqual(rag_search_compare["modes"]["hybrid"]["mode"], "hybrid")
            self.assertIn("owner/agent", rag_search_compare["modes"]["hybrid"]["repositories"])
            self.assertIn(rag_search_compare["recommendation"]["preferred_mode"], {"fts5", "vector", "hybrid", "none"})
            self.assertGreaterEqual(rag_search_compare["overlap"]["repository_count"], 1)
            self.assertEqual(rag_search_evaluation["schema_version"], 1)
            self.assertEqual(rag_search_evaluation["sample_count"], 2)
            self.assertIn("hybrid", rag_search_evaluation["aggregate"]["modes"])
            self.assertGreaterEqual(rag_search_evaluation["aggregate"]["repository_count"], 1)
            self.assertTrue(rag_search_evaluation["summary"])
            self.assertFalse(rag_search_evaluation_blocked["accepted"])
            self.assertFalse(rag_search_evaluation_blocked["executed"])
            self.assertIn("confirm_execution=true", " ".join(rag_search_evaluation_blocked["blockers"]))
            self.assertTrue(rag_search_evaluation_job["accepted"])
            self.assertTrue(rag_search_evaluation_job["executed"])
            self.assertEqual(rag_search_evaluation_job["status"], "succeeded")
            self.assertEqual(rag_search_evaluation_jobs["jobs"][0]["kind"], "rag_search_evaluation")
            self.assertEqual(rag_search_evaluation_jobs["jobs"][0]["job_id"], rag_search_evaluation_job["job_id"])
            self.assertTrue(
                any(event["event_type"] == "rag_search_evaluation_succeeded" for event in rag_search_evaluation_events["events"])
            )
            self.assertEqual(rag_search_evaluation_trends["schema_version"], 1)
            self.assertGreaterEqual(rag_search_evaluation_trends["count"], 1)
            self.assertEqual(rag_search_evaluation_trends["jobs"][0]["job_id"], rag_search_evaluation_job["job_id"])
            self.assertGreaterEqual(rag_search_evaluation_trends["aggregate"]["job_count"], 1)
            self.assertTrue(rag_search_evaluation_trends["summary"])
            self.assertTrue(rag_search_evaluation_plan["planned_job_created"])
            self.assertTrue(rag_search_evaluation_plan["job_id"].startswith("rag-search-eval-plan:"))
            self.assertTrue(rag_search_evaluation_plan_check["executable"])
            self.assertEqual(rag_search_evaluation_plan_check["kind"], "rag_search_evaluation")
            self.assertTrue(rag_search_evaluation_plan_execute["executed"])
            self.assertEqual(rag_search_evaluation_plan_execute["status"], "succeeded")
            self.assertEqual(rag_search_evaluation_plan_execute["runner_result"]["result"]["sample_count"], 1)
            self.assertEqual(rag_hybrid_explain["retrieval"]["mode"], "hybrid")
            self.assertIn("owner/agent", rag_hybrid_explain["explanation"]["answer"])
            self.assertEqual(rag_hybrid_ask["retrieval"]["mode"], "hybrid")
            self.assertIn("owner/agent", rag_hybrid_ask["answer"])
            self.assertGreaterEqual(rag_explanations["count"], 1)
            self.assertIn(
                rag_explain["explanation_id"],
                [item["explanation_id"] for item in rag_explanations["explanations"]],
            )
            self.assertIn("owner/agent", rag_explanations["explanations"][0]["answer"])
            matching_explanation = next(
                item for item in rag_explanations["explanations"] if item["explanation_id"] == rag_explain["explanation_id"]
            )
            self.assertEqual(matching_explanation["quality_score"], rag_explain["quality"]["score"])
            self.assertEqual(matching_explanation["quality_level"], rag_explain["quality"]["level"])
            self.assertEqual(project_rag_explanations["repo"], "owner/agent")
            self.assertGreaterEqual(project_rag_explanations["count"], 1)
            self.assertIn("owner/agent", project_rag_explanations["explanations"][0]["repositories"])
            self.assertTrue(project_rag_bundle["found"])
            self.assertEqual(project_rag_bundle["full_name"], "owner/agent")
            self.assertEqual(project_rag_bundle["feedback_memory"]["count"], 1)
            self.assertEqual(project_rag_bundle["feedback_memory"]["summary"]["average_rating"], 2)
            self.assertIn("project_profile", project_rag_bundle)
            self.assertIn("project_positioning", project_rag_bundle["project_profile"])
            self.assertIn("agent_judgement", project_rag_bundle["project_profile"])
            self.assertIn("tracking_reason", project_rag_bundle["project_profile"])
            self.assertGreaterEqual(project_rag_bundle["explanation_summary"]["count"], 1)
            self.assertIn("owner/agent", project_rag_bundle["explanations"][0]["repositories"])
            self.assertIn("contexts", project_rag_bundle)
            self.assertIn("project_profile", project_rag_bundle["contexts"][0]["metadata"])
            self.assertGreaterEqual(rag_quality_summary["total_count"], 1)
            self.assertGreaterEqual(rag_quality_summary["average_quality_score"], 1)
            self.assertIn(rag_explain["quality"]["level"], rag_quality_summary["quality_levels"])
            self.assertTrue(rag_quality_summary["recommendations"])
            self.assertGreaterEqual(rag_coverage["total_projects"], 1)
            self.assertIn("coverage_rate", rag_coverage)
            self.assertTrue(rag_coverage["recommendations"])
            self.assertIn("gap_reasons", rag_coverage["gaps"][0])
            self.assertEqual(rag_diagnostics["schema_version"], 1)
            self.assertIn(rag_diagnostics["level"], {"low", "medium", "high"})
            self.assertIn("ready_for_answering", rag_diagnostics["signals"])
            self.assertGreaterEqual(rag_diagnostics["table_counts"]["rag_chunks"], 1)
            self.assertTrue(rag_diagnostics["signals"]["corpus_version_current"])
            self.assertFalse(rag_diagnostics["corpus_versions"]["needs_corpus_rebuild"])
            self.assertTrue(rag_diagnostics["next_actions"])
            self.assertEqual(rag_backfill_preview["schema_version"], 1)
            self.assertTrue(rag_backfill_preview["accepted"])
            self.assertTrue(rag_backfill_preview["dry_run"])
            self.assertTrue(rag_backfill_preview["job_id"].startswith("rag-backfill:"))
            self.assertLessEqual(rag_backfill_preview["processed_count"], 1)
            self.assertEqual(rag_backfill_jobs["jobs"][0]["kind"], "rag_backfill")
            self.assertEqual(rag_backfill_jobs["jobs"][0]["status"], "succeeded")
            self.assertEqual(rag_backfill_jobs["jobs"][0]["job_id"], rag_backfill_preview["job_id"])
            self.assertEqual(
                [event["event_type"] for event in rag_backfill_events["events"]],
                ["rag_backfill_started", "rag_backfill_completed"],
            )
            self.assertTrue(rag_backfill_plan["job_id"].startswith("rag-backfill-plan:"))
            self.assertTrue(rag_backfill_precheck["executable"])
            self.assertEqual(rag_backfill_precheck["kind"], "rag_backfill")
            self.assertTrue(rag_backfill_execute["executed"])
            self.assertEqual(rag_backfill_execute["status"], "succeeded")
            self.assertIn("processed_count", rag_backfill_execute["runner_result"]["result"])
            self.assertEqual(rag_maintenance_plan["reason"], "rag_coverage_gap_detected")
            self.assertTrue(rag_maintenance_plan["planned_job_created"])
            self.assertEqual(rag_maintenance_plan["job"]["kind"], "rag_backfill")
            self.assertIn("diagnostics", rag_maintenance_plan)
            self.assertIn("ready_for_answering", rag_maintenance_plan["diagnostics"]["signals"])
            self.assertFalse(rag_maintenance_duplicate["planned_job_created"])
            self.assertEqual(rag_maintenance_duplicate["duplicate_of"], rag_maintenance_plan["job_id"])
            self.assertIn("diagnostics", rag_maintenance_duplicate)
            self.assertEqual(rag_maintenance_report["schema_version"], 1)
            self.assertGreaterEqual(rag_maintenance_report["count"], 1)
            self.assertIn("rag_backfill", rag_maintenance_report["kind_counts"])
            self.assertIn("rag_search_evaluation", rag_maintenance_report["kind_counts"])
            self.assertIn("rag_search_evaluation", [item["kind"] for item in rag_maintenance_report["by_kind"]])
            self.assertTrue(
                any(job["kind"] == "rag_search_evaluation" for job in rag_maintenance_report["recent_jobs"])
            )
            self.assertTrue(rag_maintenance_report["latest_success"]["job_id"])
            self.assertTrue(rag_maintenance_report["recommendations"])
            self.assertGreaterEqual(database_summary_after_explain["table_counts"]["rag_explanations"], 1)
            self.assertTrue(database_summary_after_explain["rag_readiness"]["ready_for_explanation_history"])
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

    def test_feedback_drives_recommendation_ranking_and_explanations(self):
        root = Path.cwd() / f".tmp-api-feedback-ranking-{uuid.uuid4().hex}"
        try:
            _write_fixture(root)
            repository = ApiRepository(root=root, db_path=root / "data" / "github_weekly.sqlite")

            baseline = repository.recommendations(profile="agent_development", language="Python", limit=10)
            self.assertEqual(baseline["recommendations"][0]["full_name"], "owner/agent")
            baseline_agent = baseline["recommendations"][0]
            self.assertIn("recommendation_score", baseline_agent)
            self.assertIn("ranking_factors", baseline_agent)
            self.assertIn("rag_reason", baseline_agent)
            self.assertIn("project_profile", baseline_agent)
            self.assertIn("项目 RAG 档案显示", baseline_agent["rag_reason"])
            self.assertIn("feedback_reason", baseline_agent)
            self.assertIn("recommendation_reason", baseline_agent)
            self.assertEqual(
                baseline_agent["recommendation_score"],
                sum(baseline_agent["ranking_factors"].values()),
            )

            root_risk = Path.cwd() / f".tmp-api-feedback-risk-{uuid.uuid4().hex}"
            _write_fixture(root_risk)
            _append_risky_fixture_project(root_risk)
            try:
                risk_repository = ApiRepository(root=root_risk, db_path=root_risk / "data" / "github_weekly.sqlite")
                risk_recommendations = risk_repository.recommendations(
                    profile="agent_development",
                    language="Python",
                    limit=10,
                )
                risky_project = next(
                    item for item in risk_recommendations["recommendations"] if item["full_name"] == "owner/risky-agent"
                )
                self.assertLess(risky_project["ranking_factors"]["risk_penalty"], 0)
                self.assertIn("存在风险扣分", risky_project["recommendation_reason"])
            finally:
                shutil.rmtree(root_risk, ignore_errors=True)

            repository.create_project_feedback(
                {
                    "full_name": "owner/agent-helper",
                    "profile": "agent_development",
                    "rating": 2,
                    "labels": ["useful"],
                    "source": "unit-test",
                }
            )
            positive = repository.recommendations(profile="agent_development", language="Python", limit=10)
            self.assertEqual(positive["recommendations"][0]["full_name"], "owner/agent-helper")
            self.assertGreater(positive["recommendations"][0]["ranking_factors"]["preference_score"], 0)
            self.assertIn("排序被提升", positive["recommendations"][0]["feedback_reason"])

            repository.create_project_feedback(
                {
                    "full_name": "owner/agent",
                    "profile": "agent_development",
                    "rating": -2,
                    "labels": ["not_fit"],
                    "source": "unit-test",
                }
            )
            negative = repository.recommendations(profile="agent_development", language="Python", limit=10)
            agent_after_negative = next(item for item in negative["recommendations"] if item["full_name"] == "owner/agent")
            helper_after_negative = next(
                item for item in negative["recommendations"] if item["full_name"] == "owner/agent-helper"
            )
            self.assertLess(agent_after_negative["recommendation_score"], helper_after_negative["recommendation_score"])
            self.assertLess(agent_after_negative["ranking_factors"]["preference_score"], 0)
            self.assertIn("排序被降低", agent_after_negative["feedback_reason"])

            root_watch = Path.cwd() / f".tmp-api-feedback-watch-{uuid.uuid4().hex}"
            _write_fixture(root_watch)
            try:
                watch_repository = ApiRepository(root=root_watch, db_path=root_watch / "data" / "github_weekly.sqlite")
                watch_repository.create_project_feedback(
                    {
                        "full_name": "owner/agent",
                        "profile": "agent_development",
                        "rating": 1,
                        "labels": ["watch"],
                        "source": "unit-test",
                    }
                )
                watched = watch_repository.recommendations(profile="agent_development", language="Python", limit=10)
                self.assertEqual(watched["recommendations"][0]["full_name"], "owner/agent")
                self.assertEqual(watched["recommendations"][0]["ranking_factors"]["tracking_score"], 12)
            finally:
                shutil.rmtree(root_watch, ignore_errors=True)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_project_agent_task_loop_updates_recommendations_and_rag(self):
        root = Path.cwd() / f".tmp-api-agent-task-{uuid.uuid4().hex}"
        try:
            _write_fixture(root)
            repository = ApiRepository(root=root, db_path=root / "data" / "github_weekly.sqlite")

            recommendations = repository.recommendations(profile="agent_development", language="Python", limit=10)
            project = next(item for item in recommendations["recommendations"] if item["full_name"] == "owner/agent")
            self.assertTrue(project["next_actions"])
            self.assertIn("agent_task_summary", recommendations)

            created = repository.create_project_agent_task(
                "owner/agent",
                {
                    "task_type": "deep_analysis",
                    "priority": 2,
                    "reason": "验证项目级 Agent 任务闭环。",
                    "source": "unit-test",
                    "payload": {"subscription_action": "notify"},
                },
            )
            self.assertTrue(created["created"])
            task_id = created["task"]["task_id"]

            duplicate = repository.create_project_agent_task(
                "owner/agent",
                {
                    "task_type": "deep_analysis",
                    "priority": 2,
                    "reason": "验证项目级 Agent 任务闭环。",
                    "source": "unit-test",
                    "payload": {"subscription_action": "notify"},
                },
            )
            self.assertFalse(duplicate["created"])
            self.assertTrue(duplicate["deduplicated"])

            started = repository.update_project_agent_task(task_id, {"status": "in_progress"})
            self.assertEqual(started["task"]["status"], "in_progress")
            completed = repository.update_project_agent_task(
                task_id,
                {"status": "completed", "result_summary": "验证任务闭环完成，继续进入订阅候选。"},
            )
            self.assertEqual(completed["task"]["status"], "completed")
            self.assertTrue(completed["task"]["finished_at"])

            tasks = repository.project_agent_tasks(full_name="owner/agent", limit=20)
            self.assertTrue(any(item["task_id"] == task_id for item in tasks["tasks"]))
            self.assertGreaterEqual(tasks["summary"]["repository_count"], 1)

            rag = repository.project_rag_bundle("owner/agent", limit=8)
            self.assertTrue(rag["agent_tasks"]["tasks"])
            self.assertTrue(rag["next_actions"])
            connection = connect(repository.db_path)
            try:
                memory_text = " ".join(
                    row["chunk_text"]
                    for row in connection.execute(
                        "SELECT chunk_text FROM rag_chunks WHERE full_name = ? AND source_type = 'agent_memory'",
                        ("owner/agent",),
                    )
                )
            finally:
                connection.close()
            self.assertIn("验证任务闭环完成", memory_text)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_rag_maintenance_plan_creates_corpus_rebuild_before_backfill(self):
        root = Path.cwd() / f".tmp-api-empty-rag-{uuid.uuid4().hex}"
        try:
            root.mkdir(parents=True)
            repository = ApiRepository(root=root, db_path=root / "data" / "github_weekly.sqlite")

            plan = repository.plan_rag_maintenance({"limit": 5, "dry_run": True, "requested_by": "test"})

            self.assertTrue(plan["accepted"])
            self.assertTrue(plan["planned_job_created"])
            self.assertEqual(plan["reason"], "rag_diagnostics_needs_corpus")
            self.assertEqual(plan["diagnostics"]["status"], "needs_corpus")
            self.assertFalse(plan["diagnostics"]["signals"]["has_corpus"])
            self.assertEqual(plan["job"]["kind"], "rag_corpus_rebuild")
            self.assertTrue(plan["job_id"].startswith("rag-corpus-plan:"))
            precheck = repository.job_execution_check(plan["job_id"])
            self.assertTrue(precheck["executable"])
            execute = repository.execute_job(plan["job_id"], {"confirm_execution": True, "requested_by": "test"})
            self.assertTrue(execute["executed"])
            self.assertEqual(execute["status"], "succeeded")
            self.assertTrue(execute["runner_result"]["result"]["dry_run"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_rag_maintenance_plan_creates_search_evaluation_when_coverage_is_healthy(self):
        root = Path.cwd() / f".tmp-api-rag-evaluation-plan-{uuid.uuid4().hex}"
        try:
            _write_fixture(root)
            repository = ApiRepository(root=root, db_path=root / "data" / "github_weekly.sqlite")
            repository.rag_vector_search(query="agent workflow", language="Python", limit=5, auto_build=True)
            repository.backfill_rag_explanations_from_payload(
                {
                    "limit": 20,
                    "dry_run": False,
                    "confirm_execution": True,
                    "auto_build": True,
                    "requested_by": "test",
                }
            )

            plan = repository.plan_rag_maintenance(
                {
                    "limit": 3,
                    "evaluation_limit": 4,
                    "min_gap_count": 999,
                    "auto_build": True,
                    "requested_by": "test",
                }
            )

            self.assertTrue(plan["accepted"])
            self.assertTrue(plan["planned_job_created"])
            self.assertEqual(plan["reason"], "rag_coverage_healthy_search_evaluation")
            self.assertEqual(plan["job"]["kind"], "rag_search_evaluation")
            self.assertEqual(plan["request"]["limit"], 4)
            self.assertTrue(plan["request"]["auto_build"])
            precheck = repository.job_execution_check(plan["job_id"])
            self.assertTrue(precheck["executable"])
            self.assertEqual(precheck["kind"], "rag_search_evaluation")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_rag_search_evaluation_plan_deduplicates_by_query_set(self):
        root = Path.cwd() / f".tmp-api-rag-query-dedupe-{uuid.uuid4().hex}"
        try:
            _write_fixture(root)
            repository = ApiRepository(root=root, db_path=root / "data" / "github_weekly.sqlite")

            first = repository.plan_rag_search_evaluation(
                {"queries": ["agent workflow"], "language": "Python", "limit": 5, "requested_by": "test"}
            )
            second = repository.plan_rag_search_evaluation(
                {"queries": ["python automation"], "language": "Python", "limit": 5, "requested_by": "test"}
            )
            duplicate = repository.plan_rag_search_evaluation(
                {"queries": ["agent workflow"], "language": "Python", "limit": 5, "requested_by": "test"}
            )

            self.assertTrue(first["planned_job_created"])
            self.assertTrue(second["planned_job_created"])
            self.assertNotEqual(first["job_id"], second["job_id"])
            self.assertFalse(duplicate["planned_job_created"])
            self.assertEqual(duplicate["duplicate_of"], first["job_id"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_rag_maintenance_plan_creates_embedding_build_before_backfill(self):
        root = Path.cwd() / f".tmp-api-rag-embedding-{uuid.uuid4().hex}"
        try:
            _write_fixture(root)
            repository = ApiRepository(root=root, db_path=root / "data" / "github_weekly.sqlite")

            plan = repository.plan_rag_maintenance({"limit": 5, "dry_run": True, "requested_by": "test"})

            self.assertTrue(plan["accepted"])
            self.assertTrue(plan["planned_job_created"])
            self.assertEqual(plan["reason"], "rag_diagnostics_needs_embeddings")
            self.assertTrue(plan["diagnostics"]["signals"]["has_corpus"])
            self.assertFalse(plan["diagnostics"]["signals"]["has_embeddings"])
            self.assertEqual(plan["job"]["kind"], "rag_embedding_build")
            self.assertTrue(plan["job_id"].startswith("rag-embedding-plan:"))
            precheck = repository.job_execution_check(plan["job_id"])
            self.assertTrue(precheck["executable"])
            execute = repository.execute_job(plan["job_id"], {"confirm_execution": True, "requested_by": "test"})
            self.assertTrue(execute["executed"])
            self.assertEqual(execute["status"], "succeeded")
            self.assertTrue(execute["runner_result"]["result"]["dry_run"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    @unittest.skipUnless(_api_route_dependencies_installed(), "本地未安装 FastAPI 或 httpx，跳过 API 路由测试")
    def test_fastapi_management_writes_require_admin_token(self):
        from fastapi.testclient import TestClient
        from src.api.app import create_app

        root = Path.cwd() / f".tmp-api-auth-test-{uuid.uuid4().hex}"
        try:
            _write_fixture(root)
            app = create_app(root=root, db_path=root / "data" / "github_weekly.sqlite")
            client = TestClient(app)

            read_response = client.get("/v1/health")
            self.assertEqual(read_response.status_code, 200)

            with patch.dict(os.environ, {}, clear=True):
                unconfigured = client.post(
                    "/v1/feedback",
                    json={"full_name": "owner/agent", "rating": 1, "source": "route-test"},
                )
                unconfigured_dev_context = client.post("/v1/dev-context/index", json={"run_checks": False})
                unconfigured_dev_context_plan = client.post("/v1/dev-context/index-plan", json={"run_checks": False})
                unconfigured_agent_task = client.post(
                    "/v1/projects/owner/agent/agent-tasks",
                    json={"task_type": "observe", "reason": "route auth test"},
                )
            self.assertEqual(unconfigured.status_code, 403)
            self.assertEqual(unconfigured_dev_context.status_code, 403)
            self.assertEqual(unconfigured_dev_context_plan.status_code, 403)
            self.assertEqual(unconfigured_agent_task.status_code, 403)

            with patch.dict(os.environ, {"ADMIN_API_TOKEN": "test"}, clear=False):
                missing = client.post(
                    "/v1/feedback",
                    json={"full_name": "owner/agent", "rating": 1, "source": "route-test"},
                )
                missing_dev_context = client.post("/v1/dev-context/index", json={"run_checks": False})
                missing_dev_context_plan = client.post("/v1/dev-context/index-plan", json={"run_checks": False})
                invalid = client.post(
                    "/v1/feedback",
                    headers={"X-Admin-Token": "bad"},
                    json={"full_name": "owner/agent", "rating": 1, "source": "route-test"},
                )
                valid = client.post(
                    "/v1/feedback",
                    headers={"X-Admin-Token": "test"},
                    json={"full_name": "owner/agent", "rating": 1, "source": "route-test"},
                )
                valid_dev_context = client.post(
                    "/v1/dev-context/index",
                    headers={"X-Admin-Token": "test"},
                    json={"run_checks": False},
                )
                valid_dev_context_plan = client.post(
                    "/v1/dev-context/index-plan",
                    headers={"X-Admin-Token": "test"},
                    json={"run_checks": False},
                )
                valid_agent_task = client.post(
                    "/v1/projects/owner/agent/agent-tasks",
                    headers={"X-Admin-Token": "test"},
                    json={"task_type": "observe", "priority": 3, "reason": "route auth test"},
                )
                bearer_valid = client.post(
                    "/v1/runs/trigger",
                    headers={"Authorization": "Bearer test"},
                    json={"profile": "agent_development", "sources": ["github_trending"], "dry_run": True},
                )

            self.assertEqual(missing.status_code, 401)
            self.assertEqual(missing_dev_context.status_code, 401)
            self.assertEqual(missing_dev_context_plan.status_code, 401)
            self.assertEqual(invalid.status_code, 401)
            self.assertEqual(valid.status_code, 201)
            self.assertEqual(valid_dev_context.status_code, 202)
            self.assertEqual(valid_dev_context_plan.status_code, 202)
            self.assertEqual(valid_agent_task.status_code, 201)
            self.assertTrue(valid_agent_task.json()["created"])
            task_id = valid_agent_task.json()["task"]["task_id"]
            task_list = client.get("/v1/projects/owner/agent/agent-tasks")
            self.assertEqual(task_list.status_code, 200)
            self.assertTrue(task_list.json()["tasks"])
            with patch.dict(os.environ, {"ADMIN_API_TOKEN": "test"}, clear=False):
                task_update = client.patch(
                    f"/v1/agent-tasks/{task_id}",
                    headers={"X-Admin-Token": "test"},
                    json={"status": "in_progress"},
                )
            self.assertEqual(task_update.status_code, 200)
            self.assertEqual(task_update.json()["task"]["status"], "in_progress")
            self.assertTrue(valid.json()["created"])
            self.assertEqual(bearer_valid.status_code, 202)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    @unittest.skipUnless(_api_route_dependencies_installed(), "本地未安装 FastAPI 或 httpx，跳过 API 路由测试")
    def test_fastapi_routes_return_public_archive_data(self):
        from fastapi.testclient import TestClient
        from src.api.app import create_app

        root = Path.cwd() / f".tmp-api-route-test-{uuid.uuid4().hex}"
        admin_token_patcher = patch.dict(os.environ, {"ADMIN_API_TOKEN": "test"}, clear=False)
        try:
            _write_fixture(root)
            (root / "README.md").write_text(
                "# 路由测试\n\n开发上下文 RAG 需要检索反馈入口和 RAG 维护。",
                encoding="utf-8",
            )
            (root / "docs" / "api.md").write_text(
                "POST /v1/dev-context/index\nGET /v1/dev-context/search?q=反馈入口",
                encoding="utf-8",
            )
            (root / "docs" / "data-contracts.md").write_text("dev_corpus dev_chunks dev_runs", encoding="utf-8")
            (root / "docs" / "operation-log.md").write_text("反馈入口 已接入推荐页。", encoding="utf-8")
            admin_token_patcher.start()
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
            client.headers.update({"X-Admin-Token": "test"})

            health = client.get("/api/health")
            projects = client.get("/api/projects", params={"profile": "agent_development", "limit": 5})
            detail = client.get("/api/projects/owner/agent")
            latest = client.get("/api/weekly/latest")
            v1_health = client.get("/v1/health")
            v1_database_summary = client.get("/v1/database/summary")
            v1_database_trends = client.get("/v1/database/trends", params={"limit": 5})
            v1_database_facets = client.get("/v1/database/facets", params={"limit": 5})
            v1_dev_context_index = client.post("/v1/dev-context/index", json={"run_checks": False})
            v1_dev_context_plan = client.post("/v1/dev-context/index-plan", json={"run_checks": False})
            v1_dev_context_plan_check = client.get(
                "/v1/job-execution-check",
                params={"job_id": v1_dev_context_plan.json()["job_id"]},
            )
            v1_dev_context_plan_execute = client.post(
                f"/v1/jobs/{v1_dev_context_plan.json()['job_id']}/execute",
                json={"confirm_execution": True, "requested_by": "route-test"},
            )
            v1_dev_context_jobs = client.get(
                "/v1/jobs",
                params={"kind": "dev_context_index", "status": "succeeded", "limit": 5},
            )
            v1_dev_context_search = client.get("/v1/dev-context/search", params={"q": "反馈入口", "limit": 5})
            v1_dev_context_ask = client.post(
                "/v1/dev-context/ask",
                json={"question": "哪些 API 和数据契约相关？", "limit": 5},
            )
            v1_dev_context_run = client.get(f"/v1/dev-context/runs/{v1_dev_context_index.json()['run_id']}")
            v1_search = client.get("/v1/search", params={"q": "agent workflow", "language": "Python", "limit": 5})
            v1_rag_corpus = client.get(
                "/v1/rag/corpus",
                params={"q": "agent workflow", "language": "Python", "limit": 5},
            )
            v1_rag_retrieve = client.get(
                "/v1/rag/retrieve",
                params={"q": "agent workflow", "language": "Python", "limit": 5},
            )
            v1_rag_vector_search = client.get(
                "/v1/rag/vector-search",
                params={"q": "agent workflow", "language": "Python", "limit": 5, "auto_build": True},
            )
            v1_rag_hybrid_search = client.get(
                "/v1/rag/hybrid-search",
                params={"q": "agent workflow", "language": "Python", "limit": 5, "auto_build": True},
            )
            v1_rag_search_compare = client.get(
                "/v1/rag/search-compare",
                params={"q": "agent workflow", "language": "Python", "limit": 5, "auto_build": True},
            )
            v1_rag_search_evaluation = client.get(
                "/v1/rag/search-evaluation",
                params=[
                    ("q", "agent workflow"),
                    ("q", "python automation"),
                    ("language", "Python"),
                    ("limit", "5"),
                    ("auto_build", "true"),
                ],
            )
            v1_rag_search_evaluation_blocked = client.post(
                "/v1/rag/search-evaluation",
                json={"queries": ["agent workflow"], "language": "Python", "requested_by": "route-test"},
            )
            v1_rag_search_evaluation_job = client.post(
                "/v1/rag/search-evaluation",
                json={
                    "queries": ["agent workflow", "python automation"],
                    "language": "Python",
                    "limit": 5,
                    "auto_build": True,
                    "confirm_execution": True,
                    "requested_by": "route-test",
                },
            )
            v1_rag_search_evaluation_jobs = client.get(
                "/v1/jobs",
                params={"kind": "rag_search_evaluation", "status": "succeeded", "limit": 5},
            )
            v1_rag_search_evaluation_trends = client.get(
                "/v1/rag/search-evaluation-trends",
                params={"limit": 5},
            )
            v1_rag_search_evaluation_plan = client.post(
                "/v1/rag/search-evaluation-plan",
                json={"queries": ["agent workflow"], "language": "Python", "limit": 5, "requested_by": "route-test"},
            )
            v1_rag_search_evaluation_plan_check = client.get(
                "/v1/job-execution-check",
                params={"job_id": v1_rag_search_evaluation_plan.json()["job_id"]},
            )
            v1_rag_search_evaluation_plan_execute = client.post(
                f"/v1/jobs/{v1_rag_search_evaluation_plan.json()['job_id']}/execute",
                json={"confirm_execution": True, "requested_by": "route-test"},
            )
            v1_rag_explain = client.get(
                "/v1/rag/explain",
                params={"q": "agent workflow", "language": "Python", "limit": 5},
            )
            v1_rag_hybrid_explain = client.get(
                "/v1/rag/explain",
                params={
                    "q": "agent workflow",
                    "language": "Python",
                    "limit": 5,
                    "mode": "hybrid",
                    "auto_build": True,
                },
            )
            v1_rag_ask = client.get(
                "/v1/rag/ask",
                params={"q": "agent workflow", "language": "Python", "limit": 5},
            )
            v1_rag_hybrid_ask = client.get(
                "/v1/rag/ask",
                params={
                    "q": "agent workflow",
                    "language": "Python",
                    "limit": 5,
                    "mode": "hybrid",
                    "auto_build": True,
                },
            )
            v1_rag_ask_stream = client.get(
                "/v1/rag/ask/stream",
                params={"q": "agent workflow", "language": "Python", "limit": 5},
            )
            v1_rag_explanations = client.get(
                "/v1/rag/explanations",
                params={"q": "agent", "limit": 5},
            )
            v1_project_rag_explanations = client.get(
                "/v1/rag/explanations",
                params={"repo": "owner/agent", "limit": 5},
            )
            v1_project_rag = client.get(
                "/v1/projects/owner/agent/rag",
                params={"limit": 5, "explanation_limit": 5},
            )
            v1_rag_quality_summary = client.get("/v1/rag/quality-summary", params={"limit": 5})
            v1_rag_coverage = client.get("/v1/rag/coverage", params={"limit": 5})
            v1_rag_diagnostics = client.get("/v1/rag/diagnostics", params={"limit": 5})
            v1_rag_backfill = client.post("/v1/rag/backfill-explanations", json={"limit": 1, "dry_run": True})
            v1_rag_backfill_plan = client.post(
                "/v1/rag/backfill-plan",
                json={"limit": 1, "dry_run": True, "requested_by": "test"},
            )
            v1_rag_backfill_plan_check = client.get(
                "/v1/job-execution-check",
                params={"job_id": v1_rag_backfill_plan.json()["job_id"]},
            )
            v1_rag_backfill_plan_execute = client.post(
                f"/v1/jobs/{v1_rag_backfill_plan.json()['job_id']}/execute",
                json={"confirm_execution": True, "requested_by": "test"},
            )
            v1_rag_maintenance_plan = client.post(
                "/v1/rag/maintenance-plan",
                json={"limit": 1, "dry_run": True, "requested_by": "test"},
            )
            v1_rag_backfill_jobs = client.get(
                "/v1/jobs",
                params={"status": "succeeded", "kind": "rag_backfill", "limit": 5},
            )
            v1_rag_corpus_jobs = client.get(
                "/v1/jobs",
                params={"kind": "rag_corpus_rebuild", "limit": 5},
            )
            v1_rag_backfill_events = client.get(
                f"/v1/jobs/{v1_rag_backfill.json()['job_id']}/events",
                params={"limit": 5},
            )
            v1_rag_maintenance_report = client.get("/v1/rag/maintenance-report", params={"limit": 5})
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
            v1_create_feedback = client.post(
                "/v1/feedback",
                json={
                    "full_name": "owner/agent",
                    "profile": "agent_development",
                    "rating": 2,
                    "labels": ["useful", "agent"],
                    "note": "Good fit for agent workflow tracking.",
                    "source": "route-test",
                },
            )
            v1_feedback = client.get("/v1/feedback", params={"full_name": "owner/agent", "limit": 5})
            v1_profile_feedback = client.get(
                "/v1/feedback",
                params={"profile": "agent_development", "limit": 5},
            )
            v1_recommendations_after_feedback = client.get(
                "/v1/recommendations",
                params={"profile": "agent_development", "language": "Python", "limit": 5},
            )
            v1_project_rag_after_feedback = client.get(
                "/v1/projects/owner/agent/rag",
                params={"limit": 5, "explanation_limit": 5},
            )
            v1_database_summary_after_feedback = client.get("/v1/database/summary")
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
            self.assertEqual(v1_dev_context_index.status_code, 202)
            self.assertEqual(v1_dev_context_plan.status_code, 202)
            self.assertEqual(v1_dev_context_plan_check.status_code, 200)
            self.assertEqual(v1_dev_context_plan_execute.status_code, 200)
            self.assertEqual(v1_dev_context_jobs.status_code, 200)
            self.assertEqual(v1_dev_context_search.status_code, 200)
            self.assertEqual(v1_dev_context_ask.status_code, 200)
            self.assertEqual(v1_dev_context_run.status_code, 200)
            self.assertEqual(v1_search.status_code, 200)
            self.assertEqual(v1_rag_corpus.status_code, 200)
            self.assertEqual(v1_rag_retrieve.status_code, 200)
            self.assertEqual(v1_rag_vector_search.status_code, 200)
            self.assertEqual(v1_rag_hybrid_search.status_code, 200)
            self.assertEqual(v1_rag_search_compare.status_code, 200)
            self.assertEqual(v1_rag_search_evaluation.status_code, 200)
            self.assertEqual(v1_rag_search_evaluation_blocked.status_code, 202)
            self.assertEqual(v1_rag_search_evaluation_job.status_code, 202)
            self.assertEqual(v1_rag_search_evaluation_jobs.status_code, 200)
            self.assertEqual(v1_rag_search_evaluation_trends.status_code, 200)
            self.assertEqual(v1_rag_search_evaluation_plan.status_code, 202)
            self.assertEqual(v1_rag_search_evaluation_plan_check.status_code, 200)
            self.assertEqual(v1_rag_search_evaluation_plan_execute.status_code, 200)
            self.assertEqual(v1_rag_explain.status_code, 200)
            self.assertEqual(v1_rag_hybrid_explain.status_code, 200)
            self.assertEqual(v1_rag_ask.status_code, 200)
            self.assertEqual(v1_rag_hybrid_ask.status_code, 200)
            self.assertEqual(v1_rag_ask_stream.status_code, 200)
            self.assertIn("text/event-stream", v1_rag_ask_stream.headers["content-type"])
            self.assertIn("event: meta", v1_rag_ask_stream.text)
            self.assertIn("event: final", v1_rag_ask_stream.text)
            self.assertIn('"answer_mode": "fallback_rule"', v1_rag_ask_stream.text)
            self.assertIn('"evidence_coverage":', v1_rag_ask_stream.text)
            self.assertIn('"match_confidence": "unknown"', v1_rag_ask_stream.text)
            self.assertIn('"evidence_relevance": "not_evaluated"', v1_rag_ask_stream.text)
            self.assertIn('"recommendations":', v1_rag_ask_stream.text)
            self.assertEqual(v1_rag_explanations.status_code, 200)
            self.assertEqual(v1_project_rag_explanations.status_code, 200)
            self.assertEqual(v1_project_rag.status_code, 200)
            self.assertEqual(v1_rag_quality_summary.status_code, 200)
            self.assertEqual(v1_rag_coverage.status_code, 200)
            self.assertEqual(v1_rag_diagnostics.status_code, 200)
            self.assertEqual(v1_rag_maintenance_report.status_code, 200)
            self.assertEqual(v1_rag_backfill.status_code, 202)
            self.assertEqual(v1_rag_backfill_plan.status_code, 202)
            self.assertEqual(v1_rag_backfill_plan_check.status_code, 200)
            self.assertEqual(v1_rag_backfill_plan_execute.status_code, 200)
            self.assertEqual(v1_rag_maintenance_plan.status_code, 202)
            self.assertEqual(v1_rag_backfill_jobs.status_code, 200)
            self.assertEqual(v1_rag_corpus_jobs.status_code, 200)
            self.assertEqual(v1_rag_backfill_events.status_code, 200)
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
            self.assertEqual(v1_create_feedback.status_code, 201)
            self.assertEqual(v1_feedback.status_code, 200)
            self.assertEqual(v1_profile_feedback.status_code, 200)
            self.assertEqual(v1_recommendations_after_feedback.status_code, 200)
            self.assertEqual(v1_project_rag_after_feedback.status_code, 200)
            self.assertEqual(v1_database_summary_after_feedback.status_code, 200)
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
            self.assertTrue(v1_database_summary.json()["rag_readiness"]["ready_for_chunk_retrieval"])
            self.assertEqual(v1_dev_context_index.json()["status"], "succeeded")
            self.assertGreater(v1_dev_context_index.json()["chunk_count"], 0)
            self.assertTrue(v1_dev_context_plan.json()["planned_job_created"])
            self.assertEqual(v1_dev_context_plan.json()["job"]["kind"], "dev_context_index")
            self.assertTrue(v1_dev_context_plan_check.json()["executable"])
            self.assertEqual(v1_dev_context_plan_check.json()["kind"], "dev_context_index")
            self.assertTrue(v1_dev_context_plan_execute.json()["executed"])
            self.assertEqual(v1_dev_context_plan_execute.json()["status"], "succeeded")
            self.assertGreater(v1_dev_context_plan_execute.json()["runner_result"]["result"]["chunk_count"], 0)
            self.assertEqual(v1_dev_context_jobs.json()["jobs"][0]["kind"], "dev_context_index")
            self.assertGreater(v1_dev_context_search.json()["count"], 0)
            self.assertIn("answer", v1_dev_context_ask.json())
            self.assertEqual(v1_dev_context_ask.json()["question_type"], "api_contract")
            self.assertTrue(v1_dev_context_ask.json()["evidence"])
            self.assertTrue(v1_dev_context_ask.json()["citations"])
            self.assertTrue(v1_dev_context_ask.json()["next_actions"])
            self.assertTrue(v1_dev_context_run.json()["found"])
            self.assertGreaterEqual(v1_database_trends.json()["count"], 1)
            self.assertEqual(v1_database_facets.json()["languages"][0]["name"], "Python")
            self.assertEqual(v1_database_facets.json()["sources"][0]["name"], "github_trending")
            self.assertIn("owner/agent", [item["full_name"] for item in v1_search.json()["results"]])
            self.assertIn("owner/agent", [item["metadata"]["full_name"] for item in v1_rag_corpus.json()["documents"]])
            self.assertTrue(v1_rag_corpus.json()["rag_readiness"]["ready_for_embedding"])
            self.assertIn("owner/agent", [item["metadata"]["full_name"] for item in v1_rag_retrieve.json()["contexts"]])
            self.assertTrue(v1_rag_retrieve.json()["citations"])
            self.assertIn("owner/agent", [item["metadata"]["full_name"] for item in v1_rag_vector_search.json()["contexts"]])
            self.assertTrue(v1_rag_vector_search.json()["citations"])
            self.assertIn("owner/agent", [item["metadata"]["full_name"] for item in v1_rag_hybrid_search.json()["contexts"]])
            self.assertEqual(v1_rag_hybrid_search.json()["retrieval"]["mode"], "hybrid")
            self.assertTrue(v1_rag_hybrid_search.json()["citations"])
            self.assertEqual(v1_rag_search_compare.json()["modes"]["hybrid"]["mode"], "hybrid")
            self.assertIn("owner/agent", v1_rag_search_compare.json()["modes"]["hybrid"]["repositories"])
            self.assertTrue(v1_rag_search_compare.json()["summary"])
            self.assertEqual(v1_rag_search_evaluation.json()["sample_count"], 2)
            self.assertIn("hybrid", v1_rag_search_evaluation.json()["aggregate"]["modes"])
            self.assertTrue(v1_rag_search_evaluation.json()["summary"])
            self.assertFalse(v1_rag_search_evaluation_blocked.json()["accepted"])
            self.assertTrue(v1_rag_search_evaluation_job.json()["executed"])
            self.assertEqual(v1_rag_search_evaluation_jobs.json()["jobs"][0]["kind"], "rag_search_evaluation")
            self.assertGreaterEqual(v1_rag_search_evaluation_trends.json()["count"], 1)
            self.assertTrue(v1_rag_search_evaluation_trends.json()["summary"])
            self.assertTrue(v1_rag_search_evaluation_plan.json()["planned_job_created"])
            self.assertTrue(v1_rag_search_evaluation_plan.json()["job_id"].startswith("rag-search-eval-plan:"))
            self.assertTrue(v1_rag_search_evaluation_plan_check.json()["executable"])
            self.assertEqual(v1_rag_search_evaluation_plan_check.json()["kind"], "rag_search_evaluation")
            self.assertTrue(v1_rag_search_evaluation_plan_execute.json()["executed"])
            self.assertEqual(v1_rag_search_evaluation_plan_execute.json()["status"], "succeeded")
            self.assertEqual(v1_rag_explain.json()["explanation"]["scoring_model"], "rule:rag-explain-v1")
            self.assertTrue(v1_rag_explain.json()["explanation_id"].startswith("ragx:"))
            self.assertGreaterEqual(v1_rag_explain.json()["quality"]["score"], 1)
            self.assertIn("owner/agent", v1_rag_explain.json()["explanation"]["answer"])
            self.assertEqual(v1_rag_hybrid_explain.json()["retrieval"]["mode"], "hybrid")
            self.assertIn("owner/agent", v1_rag_hybrid_explain.json()["explanation"]["answer"])
            self.assertEqual(v1_rag_ask.json()["answer_model"], "rule:rag-ask-v1")
            self.assertIn("owner/agent", v1_rag_ask.json()["answer"])
            self.assertTrue(v1_rag_ask.json()["next_actions"])
            self.assertEqual(v1_rag_ask.json()["evidence_coverage"], v1_rag_ask.json()["confidence"])
            self.assertEqual(v1_rag_ask.json()["match_confidence"], "unknown")
            self.assertIn("citation_validity", v1_rag_ask.json()["answer_quality"])
            self.assertEqual(v1_rag_ask.json()["recommendations"][0]["full_name"], "owner/agent")
            self.assertEqual(v1_rag_ask.json()["recommendations"][0]["eligibility"], "eligible")
            stream_final = json.loads(
                next(
                    line.removeprefix("data: ")
                    for block in v1_rag_ask_stream.text.split("\n\n")
                    if block.startswith("event: final")
                    for line in block.splitlines()
                    if line.startswith("data: ")
                )
            )
            self.assertEqual(stream_final["recommendations"], v1_rag_ask.json()["recommendations"])
            self.assertEqual(v1_rag_hybrid_ask.json()["retrieval"]["mode"], "hybrid")
            self.assertIn("owner/agent", v1_rag_hybrid_ask.json()["answer"])
            self.assertIn("ready_for_answering", v1_rag_diagnostics.json()["signals"])
            self.assertTrue(v1_rag_diagnostics.json()["next_actions"])
            self.assertEqual(v1_rag_maintenance_report.json()["schema_version"], 1)
            self.assertIn("rag_backfill", v1_rag_maintenance_report.json()["kind_counts"])
            self.assertTrue(v1_rag_maintenance_report.json()["recommendations"])
            self.assertGreaterEqual(v1_rag_explanations.json()["count"], 1)
            self.assertIn("quality_score", v1_rag_explanations.json()["explanations"][0])
            self.assertIn("owner/agent", v1_rag_explanations.json()["explanations"][0]["answer"])
            self.assertEqual(v1_project_rag_explanations.json()["repo"], "owner/agent")
            self.assertIn("owner/agent", v1_project_rag_explanations.json()["explanations"][0]["repositories"])
            self.assertTrue(v1_project_rag.json()["found"])
            self.assertEqual(v1_project_rag.json()["full_name"], "owner/agent")
            self.assertGreaterEqual(v1_project_rag.json()["explanation_summary"]["count"], 1)
            self.assertGreaterEqual(v1_rag_quality_summary.json()["total_count"], 1)
            self.assertTrue(v1_rag_quality_summary.json()["recommendations"])
            self.assertGreaterEqual(v1_rag_coverage.json()["total_projects"], 1)
            self.assertIn("coverage_rate", v1_rag_coverage.json())
            self.assertTrue(v1_rag_backfill.json()["accepted"])
            self.assertTrue(v1_rag_backfill.json()["dry_run"])
            self.assertTrue(v1_rag_backfill.json()["job_id"].startswith("rag-backfill:"))
            self.assertLessEqual(v1_rag_backfill.json()["processed_count"], 1)
            self.assertTrue(v1_rag_backfill_plan.json()["job_id"].startswith("rag-backfill-plan:"))
            self.assertTrue(v1_rag_backfill_plan_check.json()["executable"])
            self.assertTrue(v1_rag_backfill_plan_execute.json()["executed"])
            self.assertEqual(v1_rag_backfill_plan_execute.json()["status"], "succeeded")
            self.assertTrue(v1_rag_maintenance_plan.json()["accepted"])
            self.assertEqual(v1_rag_maintenance_plan.json()["reason"], "rag_coverage_gap_detected")
            self.assertIn("diagnostics", v1_rag_maintenance_plan.json())
            self.assertEqual(v1_rag_backfill_jobs.json()["jobs"][0]["kind"], "rag_backfill")
            self.assertIn(
                v1_rag_backfill.json()["job_id"],
                [job["job_id"] for job in v1_rag_backfill_jobs.json()["jobs"]],
            )
            self.assertEqual(v1_rag_backfill_events.json()["events"][-1]["event_type"], "rag_backfill_completed")
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
            self.assertTrue(v1_health.json()["capabilities"]["project_feedback"])
            self.assertTrue(v1_create_feedback.json()["accepted"])
            self.assertTrue(v1_create_feedback.json()["created"])
            self.assertEqual(v1_create_feedback.json()["feedback"]["rating"], 2)
            self.assertEqual(v1_feedback.json()["count"], 1)
            self.assertTrue(v1_feedback.json()["summary"]["ready_for_preference_memory"])
            self.assertEqual(v1_profile_feedback.json()["count"], 1)
            self.assertEqual(v1_recommendations_after_feedback.json()["feedback_memory"]["record_count"], 1)
            self.assertEqual(
                v1_recommendations_after_feedback.json()["recommendations"][0]["feedback_memory"]["latest_rating"],
                2,
            )
            self.assertIn("project_profile", v1_recommendations_after_feedback.json()["recommendations"][0])
            self.assertIn(
                "项目 RAG 档案显示",
                v1_recommendations_after_feedback.json()["recommendations"][0]["rag_reason"],
            )
            self.assertEqual(v1_project_rag_after_feedback.json()["feedback_memory"]["count"], 1)
            self.assertIn("project_profile", v1_project_rag_after_feedback.json())
            self.assertIn("agent_judgement", v1_project_rag_after_feedback.json()["project_profile"])
            self.assertEqual(v1_database_summary_after_feedback.json()["table_counts"]["project_feedback"], 1)
            self.assertTrue(v1_database_summary_after_feedback.json()["rag_readiness"]["ready_for_feedback_memory"])
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
            admin_token_patcher.stop()
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


def _append_risky_fixture_project(root: Path) -> None:
    selected_path = root / "data" / "selected" / "2026-05-09.json"
    projects = json.loads(selected_path.read_text(encoding="utf-8"))
    projects.append(
        {
            "full_name": "owner/risky-agent",
            "html_url": "https://github.com/owner/risky-agent",
            "description": "agent workflow automation with risky setup",
            "language": "Python",
            "stargazers_count": 300,
            "forks_count": 30,
            "score": 95,
            "star_growth": 240,
            "trending_rank": 2,
            "category": "AI Agent",
            "sources": ["github_trending"],
            "selection_reasons": ["进入 GitHub Trending 周榜第 2 位。"],
            "security_flags": ["未识别到许可证。", "README 提到需要私有 Token。"],
            "quality_score": 88,
            "quality_level": "high",
            "quality_flags": [],
        }
    )
    selected_path.write_text(json.dumps(projects, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
