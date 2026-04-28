import json
import shutil
import unittest
import uuid
from pathlib import Path

from scripts.build_pages import build_pages


class BuildPagesTest(unittest.TestCase):
    def test_builds_index_and_weekly_report_pages(self):
        root = Path.cwd() / f".tmp-pages-test-{uuid.uuid4().hex}"
        try:
            (root / "reports").mkdir(parents=True)
            (root / "data" / "runs").mkdir(parents=True)
            (root / "reports" / "2026-04-28.md").write_text("# 周报", encoding="utf-8")
            (root / "data" / "runs" / "2026-04-28.json").write_text(
                json.dumps({"selected_count": 10, "kimi_used": True, "telegram_sent": True}),
                encoding="utf-8",
            )

            written = build_pages(root)

            self.assertIn(root / "docs" / "index.md", written)
            self.assertEqual((root / "docs" / "weekly" / "2026-04-28.md").read_text(encoding="utf-8"), "# 周报")
            index = (root / "docs" / "index.md").read_text(encoding="utf-8")
            self.assertIn("[2026-04-28](weekly/2026-04-28.md)", index)
            self.assertIn("10 个项目", index)
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
