from __future__ import annotations

import unittest
from pathlib import Path

from scripts import publish_archive_branch


ROOT = Path(__file__).resolve().parents[1]


class WorkflowTest(unittest.TestCase):
    def test_weekly_workflow_publishes_archive_to_separate_branch(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "weekly.yml").read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch:", workflow)
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

    def test_archive_branch_publish_scope_is_limited_to_generated_archive(self) -> None:
        script = (ROOT / "scripts" / "publish_archive_branch.py").read_text(encoding="utf-8")

        self.assertEqual(publish_archive_branch.ARCHIVE_PATHS, ("docs", "reports", "data"))
        self.assertIn("git\", \"add\", *ARCHIVE_PATHS", script)
        self.assertNotIn("README.md", publish_archive_branch.ARCHIVE_PATHS)
        self.assertNotIn(".github", publish_archive_branch.ARCHIVE_PATHS)


if __name__ == "__main__":
    unittest.main()
