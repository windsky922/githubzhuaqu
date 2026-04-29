import json
import shutil
import unittest
import uuid
from pathlib import Path

from src.archive import write_raw_repositories, write_selected_repositories
from src.models import Repository
from src.settings import Settings


def settings(root):
    return Settings(
        root=Path(root),
        run_date="2026-04-28",
        since_date="2026-04-21",
        days_back=7,
        min_stars=20,
        max_projects=10,
        github_token="",
        kimi_api_key="",
        kimi_base_url="",
        kimi_model="",
        telegram_bot_token="",
        telegram_chat_id="",
        interests={},
    )


def repo(name):
    return Repository(
        full_name=name,
        html_url=f"https://github.com/{name}",
        description="desc",
        stargazers_count=100,
        forks_count=10,
        language="Python",
        created_at="2026-04-20T00:00:00Z",
        updated_at="2026-04-28T00:00:00Z",
        pushed_at="2026-04-28T00:00:00Z",
    )


class ArchiveTest(unittest.TestCase):
    def test_writes_raw_and_selected_to_separate_paths(self):
        root = Path.cwd() / f".tmp-archive-test-{uuid.uuid4().hex}"
        try:
            current_settings = settings(root)

            raw_path = write_raw_repositories([repo("owner/raw")], current_settings)
            selected_path = write_selected_repositories([repo("owner/selected")], current_settings)

            self.assertEqual(raw_path.relative_to(root).as_posix(), "data/raw/2026-04-28.json")
            self.assertEqual(selected_path.relative_to(root).as_posix(), "data/selected/2026-04-28.json")
            raw_data = json.loads(raw_path.read_text(encoding="utf-8"))
            selected_data = json.loads(selected_path.read_text(encoding="utf-8"))
            self.assertEqual(raw_data[0]["full_name"], "owner/raw")
            self.assertEqual(selected_data[0]["full_name"], "owner/selected")
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
