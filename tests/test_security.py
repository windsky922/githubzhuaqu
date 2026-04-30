import unittest

from src.models import Repository
from src.security import REDACTION_TEXT, apply_security_flags, redact_sensitive_text, security_flags


def repo(**kwargs):
    data = {
        "full_name": "owner/project",
        "html_url": "https://github.com/owner/project",
        "description": "Useful tool",
        "stargazers_count": 100,
        "forks_count": 10,
        "language": "Python",
        "created_at": "2026-04-25T00:00:00Z",
        "updated_at": "2026-04-28T00:00:00Z",
        "pushed_at": "2026-04-28T00:00:00Z",
        "license_name": "MIT",
    }
    data.update(kwargs)
    return Repository(**data)


class RepositorySecurityTest(unittest.TestCase):
    def test_flags_missing_license(self):
        flags = security_flags(repo(license_name=""))

        self.assertIn("未识别到许可证，复用代码前需要人工确认授权。", flags)

    def test_flags_risky_keywords(self):
        flags = security_flags(repo(description="crypto airdrop giveaway helper"))

        self.assertTrue(any("空投" in flag for flag in flags))
        self.assertTrue(any("赠送" in flag for flag in flags))

    def test_apply_security_flags_updates_repositories(self):
        repositories = [repo(license_name="")]

        apply_security_flags(repositories)

        self.assertTrue(repositories[0].security_flags)

    def test_flags_high_issue_load(self):
        flags = security_flags(repo(stargazers_count=500, open_issues_count=120))

        self.assertTrue(any("Open Issue 数量相对较高" in flag for flag in flags))

    def test_does_not_flag_low_issue_load(self):
        flags = security_flags(repo(stargazers_count=5000, open_issues_count=120))

        self.assertFalse(any("Open Issue 数量相对较高" in flag for flag in flags))

    def test_redacts_sensitive_token_like_text(self):
        telegram_token = "123456789:" + "a" * 31
        text = "token ghp_" + "A" * 36 + " bot " + telegram_token

        result = redact_sensitive_text(text)

        self.assertNotIn("ghp_", result)
        self.assertNotIn("123456789:", result)
        self.assertIn(REDACTION_TEXT, result)

    def test_redacts_generic_secret_assignments(self):
        api_key_name = "api" + "_key"
        password_name = "pass" + "word"
        api_value = "abc123456789xyz"
        password_value = "abcdef1234567890"
        text = f"example {api_key_name}={api_value} and {password_name}: {password_value}"

        result = redact_sensitive_text(text)

        self.assertNotIn(api_value, result)
        self.assertNotIn(password_value, result)
        self.assertIn(f"{api_key_name}={REDACTION_TEXT}", result)
        self.assertIn(f"{password_name}: {REDACTION_TEXT}", result)
        self.assertEqual(result.count(REDACTION_TEXT), 2)


if __name__ == "__main__":
    unittest.main()
