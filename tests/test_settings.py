import json
import shutil
import unittest
import uuid
from pathlib import Path

from src.settings import load_project_interests


class SettingsTest(unittest.TestCase):
    def test_load_project_interests_prefers_custom_config(self):
        root = Path.cwd() / f".tmp-settings-test-{uuid.uuid4().hex}"
        try:
            config_dir = root / "config"
            config_dir.mkdir(parents=True)
            (config_dir / "interests.example.json").write_text(
                json.dumps({"preferred_topics": ["example"]}),
                encoding="utf-8",
            )
            (config_dir / "interests.json").write_text(
                json.dumps({"preferred_topics": ["custom"]}),
                encoding="utf-8",
            )

            interests = load_project_interests(root)

            self.assertEqual(interests["preferred_topics"], ["custom"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_load_project_interests_falls_back_to_example(self):
        root = Path.cwd() / f".tmp-settings-test-{uuid.uuid4().hex}"
        try:
            config_dir = root / "config"
            config_dir.mkdir(parents=True)
            (config_dir / "interests.example.json").write_text(
                json.dumps({"preferred_topics": ["example"]}),
                encoding="utf-8",
            )

            interests = load_project_interests(root)

            self.assertEqual(interests["preferred_topics"], ["example"])
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
