import unittest

from src.models import Repository
from src.security import apply_security_flags, security_flags


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


if __name__ == "__main__":
    unittest.main()
