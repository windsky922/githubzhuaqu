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
            (root / "data" / "trends").mkdir(parents=True)
            (root / "reports" / "2026-04-28.md").write_text("# 周报", encoding="utf-8")
            (root / "data" / "runs" / "2026-04-28.json").write_text(
                json.dumps({"selected_count": 10, "collected_count": 100, "kimi_used": True, "telegram_sent": True}),
                encoding="utf-8",
            )
            (root / "data" / "trends" / "2026-04-28.json").write_text(
                json.dumps({"summary_points": ["Python 是本期主要语言。"]}, ensure_ascii=False),
                encoding="utf-8",
            )

            written = build_pages(root)

            self.assertIn(root / "docs" / "index.md", written)
            self.assertEqual((root / "docs" / "weekly" / "2026-04-28.md").read_text(encoding="utf-8"), "# 周报")
            index = (root / "docs" / "index.md").read_text(encoding="utf-8")
            self.assertIn("[2026-04-28](weekly/2026-04-28.md)", index)
            self.assertIn("10 个项目", index)
            self.assertIn("最新运行摘要", index)
            self.assertIn("采集候选：100 个", index)
            self.assertIn("Python 是本期主要语言。", index)
            self.assertIn("[未来更新规划](future-plan.md)", index)
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
