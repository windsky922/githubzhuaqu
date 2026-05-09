import importlib.util
import json
import shutil
import unittest
import uuid
from pathlib import Path

from src.api.repository import ApiRepository


class ApiRepositoryTest(unittest.TestCase):
    def test_reads_projects_runs_profiles_and_latest_report(self):
        root = Path.cwd() / f".tmp-api-test-{uuid.uuid4().hex}"
        try:
            _write_fixture(root)
            repository = ApiRepository(root=root, db_path=root / "data" / "github_weekly.sqlite")

            projects = repository.projects(language="Python", source="github_trending", limit=10)
            runs = repository.runs()
            profiles = repository.profiles()
            latest = repository.latest_weekly()

            self.assertEqual(projects["schema_version"], 1)
            self.assertEqual(projects["count"], 1)
            self.assertEqual(projects["projects"][0]["full_name"], "owner/agent")
            self.assertEqual(runs["runs"][0]["run_date"], "2026-05-09")
            self.assertEqual(profiles["profiles"][0]["name"], "agent_development")
            self.assertEqual(latest["run_date"], "2026-05-09")
            self.assertIn("owner/agent", latest["markdown"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    @unittest.skipUnless(importlib.util.find_spec("fastapi"), "本地未安装 FastAPI，跳过 API 路由测试")
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
            latest = client.get("/api/weekly/latest")

            self.assertEqual(health.status_code, 200)
            self.assertEqual(projects.status_code, 200)
            self.assertEqual(latest.status_code, 200)
            self.assertEqual(projects.json()["projects"][0]["full_name"], "owner/agent")
            self.assertEqual(latest.json()["run_date"], "2026-05-09")
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
