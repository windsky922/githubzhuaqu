import json
import shutil
import unittest
import uuid
from pathlib import Path

from scripts.send_report_link import _latest_run_date, _selected_repositories, _update_run_summary


class SendReportLinkScriptTest(unittest.TestCase):
    def test_loads_latest_run_date(self):
        root = Path.cwd() / f".tmp-send-link-test-{uuid.uuid4().hex}"
        try:
            runs = root / "data" / "runs"
            runs.mkdir(parents=True)
            (runs / "2026-04-28.json").write_text("{}", encoding="utf-8")
            (runs / "2026-04-29.json").write_text("{}", encoding="utf-8")

            self.assertEqual(_latest_run_date(root), "2026-04-29")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_loads_selected_repositories(self):
        root = Path.cwd() / f".tmp-send-link-test-{uuid.uuid4().hex}"
        try:
            selected = root / "data" / "selected"
            selected.mkdir(parents=True)
            (selected / "2026-04-29.json").write_text(
                json.dumps(
                    [
                        {
                            "full_name": "owner/project",
                            "html_url": "https://github.com/owner/project",
                            "description": "desc",
                            "stargazers_count": 100,
                            "forks_count": 10,
                            "language": "Python",
                            "created_at": "2026-04-20T00:00:00Z",
                            "updated_at": "2026-04-29T00:00:00Z",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            repositories = _selected_repositories(root, "2026-04-29")

            self.assertEqual(repositories[0].full_name, "owner/project")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_updates_run_summary_delivery_status(self):
        root = Path.cwd() / f".tmp-send-link-test-{uuid.uuid4().hex}"
        try:
            runs = root / "data" / "runs"
            runs.mkdir(parents=True)
            path = runs / "2026-04-29.json"
            path.write_text(json.dumps({"telegram_sent": False}), encoding="utf-8")

            _update_run_summary(
                root,
                "2026-04-29",
                True,
                "",
                "data/state/sent_repos.json",
                "https://example.com/weekly/2026-04-29.html",
            )

            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(data["telegram_sent"])
            self.assertEqual(data["telegram_error"], "")
            self.assertEqual(data["telegram_report_url"], "https://example.com/weekly/2026-04-29.html")
            self.assertEqual(data["state_path"], "data/state/sent_repos.json")
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
