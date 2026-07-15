from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
        self.assertIn("build_notification_candidates:", workflow)
        self.assertIn("send_event_notifications:", workflow)
        self.assertIn("ARCHIVE_BRANCH: weekly-archive", workflow)
        self.assertIn("scripts/publish_archive_branch.py", workflow)
        self.assertIn("scripts/audit_public_archive.py", workflow)
        self.assertIn("git checkout \"origin/$ARCHIVE_BRANCH\" -- reports data/raw data/runs data/selected data/trends || true", workflow)
        self.assertNotIn('git checkout "origin/$ARCHIVE_BRANCH" -- data reports || true', workflow)
        self.assertLess(workflow.rindex("scripts/publish_archive_branch.py"), workflow.index("scripts/audit_public_archive.py"))
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

    def test_weekly_workflow_checks_and_builds_react_workbench_before_publish(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "weekly.yml").read_text(encoding="utf-8")

        self.assertIn("actions/setup-node@v6", workflow)
        self.assertIn("npm ci", workflow)
        self.assertIn("npm run lint && npm run test", workflow)
        self.assertIn("npm run build", workflow)
        self.assertLess(workflow.index("python scripts/build_pages.py"), workflow.index("npm run build"))
        self.assertLess(workflow.index("npm run build"), workflow.index("scripts/publish_archive_branch.py"))

    def test_weekly_workflow_builds_candidates_and_gates_real_delivery(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "weekly.yml").read_text(encoding="utf-8")

        self.assertIn("scripts/manage_notifications.py detect", workflow)
        self.assertIn("scripts/manage_notifications.py build", workflow)
        self.assertIn("WORKFLOW_SEND_EVENT_NOTIFICATIONS", workflow)
        self.assertIn("--no-dry-run", workflow)
        self.assertIn("--confirm-delivery", workflow)
        self.assertIn("continue-on-error: true", workflow)
        self.assertLess(workflow.index("scripts/manage_notifications.py detect"), workflow.index("scripts/build_pages.py"))

    def test_archive_branch_publish_scope_is_limited_to_generated_archive(self) -> None:
        script = (ROOT / "scripts" / "publish_archive_branch.py").read_text(encoding="utf-8")

        self.assertEqual(publish_archive_branch.ARCHIVE_PATHS, ("docs", "reports", "data"))
        self.assertEqual(publish_archive_branch.PUBLIC_DATA_DIRECTORIES, ("raw", "runs", "selected", "trends"))
        self.assertIn('"git", "add", "-A"', script)
        self.assertNotIn("README.md", publish_archive_branch.ARCHIVE_PATHS)
        self.assertNotIn(".github", publish_archive_branch.ARCHIVE_PATHS)

    def test_public_archive_copy_removes_old_sqlite_and_keeps_allowlisted_files(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="archive-publisher-test-"))
        worktree = root / "worktree"
        try:
            (root / "docs" / "weekly").mkdir(parents=True)
            (root / "docs" / "weekly" / "2026-07-14.html").write_text("public", encoding="utf-8")
            (root / "reports").mkdir()
            (root / "reports" / "2026-07-14.md").write_text("report", encoding="utf-8")
            (root / "data" / "runs").mkdir(parents=True)
            (root / "data" / "runs" / "2026-07-14.json").write_text("{}", encoding="utf-8")
            local_sqlite = root / "data" / "github_weekly.sqlite"
            local_sqlite.write_bytes(b"local sqlite")
            local_sqlite_before = local_sqlite.read_bytes()
            (root / "data" / "state").mkdir()
            (root / "data" / "state" / "private.json").write_text("{}", encoding="utf-8")
            (worktree / "data").mkdir(parents=True)
            (worktree / "data" / "github_weekly.sqlite").write_bytes(b"old sqlite")
            subprocess.run(["git", "init"], cwd=worktree, check=True, capture_output=True)
            subprocess.run(["git", "add", "data/github_weekly.sqlite"], cwd=worktree, check=True, capture_output=True)
            subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-m", "seed"], cwd=worktree, check=True, capture_output=True)

            sources = publish_archive_branch._public_sources(root)
            publish_archive_branch._synchronize_archive_tree(worktree, sources, source_root=root)
            publish_archive_branch._stage_and_validate(worktree)

            self.assertTrue((worktree / "docs" / "weekly" / "2026-07-14.html").exists())
            self.assertTrue((worktree / "reports" / "2026-07-14.md").exists())
            self.assertTrue((worktree / "data" / "runs" / "2026-07-14.json").exists())
            self.assertFalse((worktree / "data" / "github_weekly.sqlite").exists())
            self.assertFalse((worktree / "data" / "state").exists())
            self.assertEqual(local_sqlite.read_bytes(), local_sqlite_before)
            staged = subprocess.run(["git", "diff", "--cached", "--name-status"], cwd=worktree, check=True, text=True, capture_output=True).stdout
            self.assertIn("D\tdata/github_weekly.sqlite", staged)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_public_archive_rejects_symbolic_link_candidate(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="archive-publisher-test-"))
        try:
            candidate = root / "data" / "runs" / "2026-07-14.json"
            candidate.parent.mkdir(parents=True)
            candidate.write_text("{}", encoding="utf-8")
            with patch.object(Path, "is_symlink", return_value=True):
                with self.assertRaisesRegex(ValueError, "符号链接"):
                    publish_archive_branch._public_sources(root)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_public_archive_rejects_unknown_file_and_sensitive_canary(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="archive-publisher-test-"))
        try:
            (root / "data" / "runs").mkdir(parents=True)
            unknown = root / "data" / "runs" / "unknown.txt"
            unknown.write_text("private", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "未知文件"):
                publish_archive_branch._public_sources(root)
            unknown.unlink()
            canary = root / "data" / "runs" / "2026-07-14.json"
            canary.write_text('{"status":"archive-query-canary"}', encoding="utf-8")
            worktree = root / "worktree"
            worktree.mkdir()
            subprocess.run(["git", "init"], cwd=worktree, check=True, capture_output=True)
            sources = publish_archive_branch._public_sources(root)
            publish_archive_branch._synchronize_archive_tree(worktree, sources, source_root=root)
            with self.assertRaisesRegex(ValueError, "敏感内容标记"):
                publish_archive_branch._stage_and_validate(worktree)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_public_archive_projects_private_json_fields_before_staging(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="archive-publisher-test-"))
        worktree = root / "worktree"
        try:
            (root / "data" / "selected").mkdir(parents=True)
            (root / "data" / "runs").mkdir(parents=True)
            (root / "data" / "trends").mkdir(parents=True)
            (root / "data" / "selected" / "2026-07-14.json").write_text(
                '[{"full_name":"owner/public","description":"public description","readme_summary":"public summary",'
                '"query":"archive-query-canary","note":"archive-note-canary","payload":{"token":"archive-secret-canary"}}]',
                encoding="utf-8",
            )
            (root / "data" / "runs" / "2026-07-14.json").write_text(
                '{"run_date":"2026-07-14","status":"success","selected_count":1,'
                '"queries":["archive-query-canary"],"collector_errors":["archive-note-canary"],'
                '"delivery_results":[{"token":"archive-secret-canary"}],"state_path":"private"}',
                encoding="utf-8",
            )
            (root / "data" / "trends" / "2026-07-14.json").write_text(
                '{"total_projects":1,"top_languages":[{"name":"Python","count":1,"note":"archive-note-canary"}]}',
                encoding="utf-8",
            )
            worktree.mkdir()
            subprocess.run(["git", "init"], cwd=worktree, check=True, capture_output=True)

            sources = publish_archive_branch._public_sources(root)
            publish_archive_branch._synchronize_archive_tree(worktree, sources, source_root=root)
            publish_archive_branch._stage_and_validate(worktree)

            selected = (worktree / "data" / "selected" / "2026-07-14.json").read_text(encoding="utf-8")
            run = (worktree / "data" / "runs" / "2026-07-14.json").read_text(encoding="utf-8")
            trend = (worktree / "data" / "trends" / "2026-07-14.json").read_text(encoding="utf-8")
            staged = "\n".join((selected, run, trend))
            self.assertIn("public description", selected)
            self.assertIn('\"selected_count\": 1', run)
            self.assertIn('\"name\": \"Python\"', trend)
            self.assertNotIn("archive-query-canary", staged)
            self.assertNotIn("archive-note-canary", staged)
            self.assertNotIn("archive-secret-canary", staged)
            self.assertNotIn('\"query\"', staged)
            self.assertNotIn('\"queries\"', staged)
            self.assertNotIn('\"delivery_results\"', staged)
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
