from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts import audit_public_archive, publish_archive_branch
from src.public_archive_manifest import is_allowed_path, load_manifest, public_source_files, validate_tree_paths


class PublicArchiveManifestTest(unittest.TestCase):
    def test_versioned_manifest_is_fail_closed_for_unknown_and_traversal_paths(self) -> None:
        self.assertEqual(load_manifest()["root_files"], load_manifest()["root_files"])
        self.assertTrue(is_allowed_path("docs/index.md"))
        self.assertTrue(is_allowed_path("data/runs/2026-07-16.json"))
        self.assertFalse(is_allowed_path("legacy/notes.txt"))
        self.assertFalse(is_allowed_path("data/github_weekly.sqlite3"))
        self.assertFalse(is_allowed_path("../private.env"))
        with self.assertRaisesRegex(ValueError, "未知路径"):
            validate_tree_paths(["docs/index.md", "legacy/notes.txt"])

    def test_publisher_cleans_root_residue_and_requires_exact_staged_projection(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="archive-manifest-test-"))
        worktree = root / "worktree"
        try:
            (root / "docs").mkdir()
            (root / "docs" / "index.md").write_text("public", encoding="utf-8")
            worktree.mkdir()
            subprocess.run(["git", "init"], cwd=worktree, check=True, capture_output=True)
            (worktree / "legacy.txt").write_text("old", encoding="utf-8")

            sources = public_source_files(root)
            expected = publish_archive_branch._synchronize_archive_tree(worktree, sources, source_root=root)
            self.assertFalse((worktree / "legacy.txt").exists())
            publish_archive_branch._stage_and_validate(worktree, expected)

            (worktree / "legacy.txt").write_text("new", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "未知路径"):
                publish_archive_branch._stage_and_validate(worktree, expected)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_remote_auditor_uses_manifest_rules_for_unknown_paths(self) -> None:
        class FakeApi:
            def get(self, path: str, params=None):
                if path.endswith("/branches/weekly-archive"):
                    return {"commit": {"sha": "head"}}
                if path.endswith("/git/trees/head"):
                    return {
                        "truncated": False,
                        "tree": [
                            {"path": "docs/index.md", "type": "blob", "mode": "100644"},
                            {"path": "legacy/notes.txt", "type": "blob", "mode": "100644"},
                            {"path": "docs/link.html", "type": "blob", "mode": "120000"},
                        ],
                    }
                raise AssertionError(path)

        summary = audit_public_archive.audit_archive(FakeApi(), "owner/repo", "weekly-archive")
        self.assertEqual(summary["latest_forbidden_paths"], ["docs/link.html", "legacy/notes.txt"])
