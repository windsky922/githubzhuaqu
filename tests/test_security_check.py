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


if __name__ == "__main__":
    unittest.main()
