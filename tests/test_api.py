import importlib.util
import json
import shutil
import unittest
import uuid
from pathlib import Path

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
                {"profile": "agent_development", "sources": ["github_trending"], "dry_run": True}
            )

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
            self.assertFalse(health["capabilities"]["run_trigger_execute"])
            self.assertEqual(jobs["jobs"][0]["job_id"], "run:2026-05-09")
            self.assertTrue(job_detail["found"])
            self.assertEqual(job_detail["run_summary"]["run_date"], "2026-05-09")
            self.assertTrue(trigger["job_id"].startswith("preview:"))
            self.assertFalse(trigger["execution_supported"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    @unittest.skipUnless(_api_route_dependencies_installed(), "本地未安装 FastAPI 或 httpx，跳过 API 路由测试")
    def test_fastapi_routes_return_public_archive_data(self):
        from fastapi.testclient import TestClient
        from src.api.app import create_app

        root = Path.cwd() / f".tmp-api-route-test-{uuid.uuid4().hex}"
        try:
            _write_fixture(root)
            app = create_app(root=root, db_path=root / "data" / "github_weekly.sqlite")
            client = TestClient(app)

            health = client.get("/api/health")
            projects = client.get("/api/projects", params={"profile": "agent_development", "limit": 5})
            detail = client.get("/api/projects/owner/agent")
            latest = client.get("/api/weekly/latest")
            v1_health = client.get("/v1/health")
            v1_projects = client.get("/v1/projects", params={"profile": "agent_development", "limit": 5})
            v1_jobs = client.get("/v1/jobs")
            v1_trigger = client.post(
                "/v1/runs/trigger",
                json={"profile": "agent_development", "sources": ["github_trending"], "dry_run": True},
            )

            self.assertEqual(health.status_code, 200)
            self.assertEqual(projects.status_code, 200)
            self.assertEqual(detail.status_code, 200)
            self.assertEqual(latest.status_code, 200)
            self.assertEqual(v1_health.status_code, 200)
            self.assertEqual(v1_projects.status_code, 200)
            self.assertEqual(v1_jobs.status_code, 200)
            self.assertEqual(v1_trigger.status_code, 202)
            self.assertEqual(projects.json()["projects"][0]["full_name"], "owner/agent")
            self.assertEqual(detail.json()["history_count"], 2)
            self.assertEqual(latest.json()["run_date"], "2026-05-09")
            self.assertEqual(v1_projects.json()["projects"][0]["full_name"], "owner/agent")
            self.assertEqual(v1_jobs.json()["jobs"][0]["job_id"], "run:2026-05-09")
            self.assertFalse(v1_trigger.json()["execution_supported"])
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
