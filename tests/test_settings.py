import json
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

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

            with patch.dict("os.environ", {"INTEREST_PROFILE": ""}):
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

            with patch.dict("os.environ", {"INTEREST_PROFILE": ""}):
                interests = load_project_interests(root)

            self.assertEqual(interests["preferred_topics"], ["example"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_load_project_interests_applies_env_profiles(self):
        root = Path.cwd() / f".tmp-settings-test-{uuid.uuid4().hex}"
        try:
            config_dir = root / "config"
            config_dir.mkdir(parents=True)
            (config_dir / "interests.example.json").write_text(
                json.dumps({"preferred_topics": ["base"], "preferred_languages": ["Python"]}),
                encoding="utf-8",
            )
            (config_dir / "profiles.example.json").write_text(
                json.dumps(
                    {
                        "java": {
                            "profile_label": "Java",
                            "preferred_topics": ["spring"],
                            "preferred_languages": ["Java"],
                        },
                        "agent_development": {
                            "profile_label": "Agent 开发",
                            "preferred_topics": ["agent"],
                        },
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"INTEREST_PROFILE": "java,agent_development"}):
                interests = load_project_interests(root)

            self.assertEqual(interests["preferred_topics"], ["base", "spring", "agent"])
            self.assertEqual(interests["preferred_languages"], ["Python", "Java"])
            self.assertEqual(interests["active_profiles"], ["java", "agent_development"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_load_project_interests_applies_config_profile_when_env_absent(self):
        root = Path.cwd() / f".tmp-settings-test-{uuid.uuid4().hex}"
        try:
            config_dir = root / "config"
            config_dir.mkdir(parents=True)
            (config_dir / "interests.example.json").write_text(
                json.dumps({"active_profile": "python", "preferred_topics": ["base"]}),
                encoding="utf-8",
            )
            (config_dir / "profiles.example.json").write_text(
                json.dumps({"python": {"preferred_topics": ["automation"]}}),
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"INTEREST_PROFILE": ""}):
                interests = load_project_interests(root)

            self.assertEqual(interests["preferred_topics"], ["base", "automation"])
            self.assertEqual(interests["active_profiles"], ["python"])
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
