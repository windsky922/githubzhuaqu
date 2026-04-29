import json
import shutil
import unittest
import uuid
from pathlib import Path

from src.models import Repository
from src.settings import Settings
from src.state import (
    filter_unsent_repositories,
    load_sent_repository_names,
    load_star_history,
    write_sent_repositories,
    write_star_history,
)


def repo(name):
    return Repository(
        full_name=name,
        html_url=f"https://github.com/{name}",
        description="desc",
        stargazers_count=100,
        forks_count=10,
        language="Python",
        created_at="2026-04-25T00:00:00Z",
        updated_at="2026-04-25T00:00:00Z",
        pushed_at="2026-04-25T00:00:00Z",
    )


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


class StateTest(unittest.TestCase):
    def test_records_and_loads_sent_repositories(self):
        root = Path.cwd() / f".tmp-state-test-{uuid.uuid4().hex}"
        try:
            root.mkdir()
            current_settings = settings(root)

            path = write_sent_repositories([repo("owner/one")], current_settings)
            names = load_sent_repository_names(current_settings)

            self.assertEqual(path, "data/state/sent_repos.json")
            self.assertEqual(names, {"owner/one"})
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_filters_unsent_repositories(self):
        repositories = [repo("owner/one"), repo("owner/two")]

        result = filter_unsent_repositories(repositories, {"owner/one"})

        self.assertEqual([item.full_name for item in result], ["owner/two"])

    def test_keeps_sent_top_trending_repositories(self):
        trending = repo("owner/trending")
        trending.trending_rank = 3
        repositories = [repo("owner/one"), trending]

        result = filter_unsent_repositories(repositories, {"owner/one", "owner/trending"})

        self.assertEqual([item.full_name for item in result], ["owner/trending"])

    def test_loads_legacy_string_state(self):
        root = Path.cwd() / f".tmp-state-test-{uuid.uuid4().hex}"
        try:
            state_dir = root / "data" / "state"
            state_dir.mkdir(parents=True)
            (state_dir / "sent_repos.json").write_text(json.dumps(["owner/one"]), encoding="utf-8")

            names = load_sent_repository_names(settings(root))

            self.assertEqual(names, {"owner/one"})
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_records_and_loads_star_history(self):
        root = Path.cwd() / f".tmp-state-test-{uuid.uuid4().hex}"
        try:
            root.mkdir()
            current_settings = settings(root)

            path, count = write_star_history([repo("owner/one")], current_settings)
            history = load_star_history(current_settings)

            self.assertEqual(path, "data/state/star_history.json")
            self.assertEqual(count, 1)
            self.assertEqual(history, {"owner/one": 100})
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
