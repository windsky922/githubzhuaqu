from __future__ import annotations

import unittest

from scripts.audit_public_archive import audit_archive


class FakeGitHubApi:
    def __init__(self) -> None:
        self.paths: list[str] = []

    def get(self, path: str, params=None):
        self.paths.append(path)
        if path.endswith("/branches/weekly-archive"):
            return {"commit": {"sha": "head"}}
        if path.endswith("/commits"):
            return [
                {"sha": "new", "commit": {"tree": {"sha": "tree-new"}}},
                {"sha": "old", "commit": {"tree": {"sha": "tree-old"}}},
            ]
        trees = {
            "head": [{"path": "docs/index.html", "type": "blob"}, {"path": "data/github_weekly.sqlite", "type": "blob"}],
            "tree-new": [{"path": "data/github_weekly.sqlite", "type": "blob"}],
            "tree-old": [{"path": "data/github_weekly.sqlite", "type": "blob"}, {"path": "data/legacy.db3", "type": "blob"}],
        }
        for sha, tree in trees.items():
            if path.endswith(f"/git/trees/{sha}"):
                return {"truncated": False, "tree": tree}
        raise AssertionError(path)


class AuditPublicArchiveTest(unittest.TestCase):
    def test_latest_tree_reports_forbidden_paths_without_reading_blob_content(self) -> None:
        api = FakeGitHubApi()

        summary = audit_archive(api, "owner/repo", "weekly-archive")

        self.assertEqual(summary["latest_forbidden_paths"], ["data/github_weekly.sqlite"])
        self.assertEqual(summary["latest_file_count"], 2)
        self.assertFalse(any("/git/blobs/" in path for path in api.paths))

    def test_history_reports_first_and_last_occurrence(self) -> None:
        api = FakeGitHubApi()

        summary = audit_archive(api, "owner/repo", "weekly-archive", history_limit=2)

        findings = {item["path"]: item for item in summary["history_forbidden_paths"]}
        self.assertEqual(summary["history_commits_scanned"], 2)
        self.assertEqual(findings["data/github_weekly.sqlite"], {"path": "data/github_weekly.sqlite", "occurrences": 2, "last_seen_newest": "new", "first_seen_oldest": "old"})
        self.assertEqual(findings["data/legacy.db3"]["occurrences"], 1)
        self.assertFalse(any("/git/blobs/" in path for path in api.paths))
