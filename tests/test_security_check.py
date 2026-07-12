import shutil
import unittest
import uuid
from pathlib import Path

from scripts.security_check import scan_repository


class SecurityCheckTest(unittest.TestCase):
    def test_detects_github_token_like_secret(self):
        root = Path.cwd() / f".tmp-security-test-{uuid.uuid4().hex}"
        try:
            root.mkdir()
            (root / "bad.py").write_text("TOKEN = 'ghp_" + "A" * 36 + "'\n", encoding="utf-8")

            findings = scan_repository(root)

            self.assertTrue(any("github_token" in finding for finding in findings))
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_ignores_github_actions_secrets_reference(self):
        root = Path.cwd() / f".tmp-security-test-{uuid.uuid4().hex}"
        try:
            root.mkdir()
            (root / "workflow.yml").write_text(
                "token: ${{ secrets.GH_SEARCH_TOKEN }}\n",
                encoding="utf-8",
            )

            findings = scan_repository(root)

            self.assertEqual(findings, [])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_detects_secret_even_when_line_uses_env_fallback(self):
        root = Path.cwd() / f".tmp-security-test-{uuid.uuid4().hex}"
        try:
            root.mkdir()
            (root / "settings.py").write_text(
                "TOKEN = os.getenv('TOKEN', 'ghp_" + "B" * 36 + "')\n",
                encoding="utf-8",
            )

            findings = scan_repository(root)

            self.assertTrue(any("github_token" in finding for finding in findings))
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_ignores_generated_weekly_pages(self):
        root = Path.cwd() / f".tmp-security-test-{uuid.uuid4().hex}"
        try:
            weekly = root / "docs" / "weekly"
            weekly.mkdir(parents=True)
            (weekly / "2026-04-29.md").write_text("token: ghp_" + "C" * 36 + "\n", encoding="utf-8")

            findings = scan_repository(root)

            self.assertEqual(findings, [])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_ignores_untracked_node_dependencies(self):
        root = Path.cwd() / f".tmp-security-test-{uuid.uuid4().hex}"
        try:
            dependencies = root / "node_modules" / "package"
            dependencies.mkdir(parents=True)
            (dependencies / "README.md").write_text("token: ghp_" + "E" * 36 + "\n", encoding="utf-8")

            findings = scan_repository(root)

            self.assertEqual(findings, [])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_still_scans_regular_docs(self):
        root = Path.cwd() / f".tmp-security-test-{uuid.uuid4().hex}"
        try:
            docs = root / "docs"
            docs.mkdir(parents=True)
            (docs / "setup.md").write_text("token: ghp_" + "D" * 36 + "\n", encoding="utf-8")

            findings = scan_repository(root)

            self.assertTrue(any("docs/setup.md" in finding for finding in findings))
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_rejects_browser_admin_token_url_and_storage_transport(self):
        root = Path.cwd() / f".tmp-security-test-{uuid.uuid4().hex}"
        cases = {
            "query_read": 'const token = params.get("admin_token");',
            "storage_read": 'localStorage.getItem("github_weekly_admin_token");',
            "storage_write": 'localStorage.setItem("github_weekly_admin_token", token);',
            "query_write": 'url.searchParams.set("admin_token", token);',
            "literal_url": 'const href = "admin.html?admin_token=" + token;',
        }
        try:
            docs = root / "docs"
            docs.mkdir(parents=True)
            for name, source in cases.items():
                (docs / f"{name}.html").write_text(source, encoding="utf-8")

            findings = scan_repository(root)

            self.assertEqual(len(findings), len(cases))
            for name in cases:
                self.assertTrue(any(f"docs/{name}.html" in finding for finding in findings), findings)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_allows_legacy_cleanup_without_reading_value(self):
        root = Path.cwd() / f".tmp-security-test-{uuid.uuid4().hex}"
        try:
            docs = root / "docs"
            docs.mkdir(parents=True)
            (docs / "admin.html").write_text(
                """url.searchParams.has(\"admin_token\");
url.searchParams.delete(\"admin_token\");
localStorage.removeItem(\"github_weekly_admin_token\");""",
                encoding="utf-8",
            )

            findings = scan_repository(root)

            self.assertEqual(findings, [])
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
