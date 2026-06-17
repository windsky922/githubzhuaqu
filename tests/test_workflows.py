from __future__ import annotations

import unittest
from pathlib import Path

from scripts import publish_archive_branch


ROOT = Path(__file__).resolve().parents[1]


class WorkflowTest(unittest.TestCase):
    def test_weekly_workflow_publishes_archive_to_separate_branch(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "weekly.yml").read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("profile:", workflow)
        self.assertIn("days_back:", workflow)
        self.assertIn("skip_main_delivery:", workflow)
        self.assertIn("plan_rag_maintenance:", workflow)
        self.assertIn("run_rag_evaluation:", workflow)
        self.assertIn("run_dev_context_index:", workflow)
        self.assertIn("ARCHIVE_BRANCH: weekly-archive", workflow)
        self.assertIn("scripts/publish_archive_branch.py", workflow)
        self.assertIn("git checkout \"origin/$ARCHIVE_BRANCH\" -- data reports || true", workflow)
        self.assertNotIn("git push\n", workflow)
        self.assertNotIn("git commit -m", workflow)

    def test_weekly_workflow_avoids_colon_sensitive_single_line_run_commands(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "weekly.yml").read_text(encoding="utf-8")

        for line in workflow.splitlines():
            if line.lstrip().startswith("run:") and "--message" in line:
                self.assertNotIn(": ", line.split("--message", 1)[1])

    def test_weekly_workflow_uses_job_runner_for_manual_runs(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "weekly.yml").read_text(encoding="utf-8")

        self.assertIn("scripts/create_planned_job.py", workflow)
        self.assertIn("--output .weekly-job.json", workflow)
        self.assertIn("scripts/run_planned_job.py --job-file .weekly-job.json", workflow)
        self.assertIn("inputs.send_link == 'true'", workflow)

    def test_weekly_workflow_creates_rag_maintenance_plan_before_pages(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "weekly.yml").read_text(encoding="utf-8")

        self.assertIn("scripts/plan_rag_maintenance.py", workflow)
        self.assertIn("RAG_MAINTENANCE_LIMIT", workflow)
        self.assertIn("--requested-by \"github_actions\"", workflow)
        self.assertLess(workflow.index("scripts/plan_rag_maintenance.py"), workflow.index("scripts/build_pages.py"))

    def test_weekly_workflow_runs_rag_evaluation_before_pages(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "weekly.yml").read_text(encoding="utf-8")

        self.assertIn("scripts/run_rag_search_evaluation.py", workflow)
        self.assertIn("RAG_EVALUATION_QUERIES", workflow)
        self.assertIn("RAG_EVALUATION_AUTO_BUILD", workflow)
        self.assertIn("WORKFLOW_RUN_RAG_EVALUATION", workflow)
        self.assertLess(workflow.index("scripts/run_rag_search_evaluation.py"), workflow.index("scripts/build_pages.py"))

    def test_weekly_workflow_refreshes_dev_context_before_pages(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "weekly.yml").read_text(encoding="utf-8")

        self.assertIn("scripts/plan_dev_context_index.py", workflow)
        self.assertIn("--run-checks false", workflow)
        self.assertIn("--output .dev-context-job.json", workflow)
        self.assertIn("scripts/run_planned_job.py --job-file .dev-context-job.json", workflow)
        self.assertLess(workflow.index("scripts/plan_dev_context_index.py"), workflow.index("scripts/build_pages.py"))
        self.assertLess(
            workflow.index("scripts/run_planned_job.py --job-file .dev-context-job.json"),
            workflow.index("scripts/build_pages.py"),
        )

    def test_archive_branch_publish_scope_is_limited_to_generated_archive(self) -> None:
        script = (ROOT / "scripts" / "publish_archive_branch.py").read_text(encoding="utf-8")

        self.assertEqual(publish_archive_branch.ARCHIVE_PATHS, ("docs", "reports", "data"))
        self.assertIn("git\", \"add\", *ARCHIVE_PATHS", script)
        self.assertNotIn("README.md", publish_archive_branch.ARCHIVE_PATHS)
        self.assertNotIn(".github", publish_archive_branch.ARCHIVE_PATHS)


if __name__ == "__main__":
    unittest.main()
