from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.manage_notifications import main


class NotificationCliTest(unittest.TestCase):
    def test_detect_and_build_persist_by_default(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory, patch(
            "scripts.manage_notifications.detect_subscription_events",
            return_value={"persisted_count": 1},
        ) as detect:
            code = main(["--root", directory, "detect", "--limit", "12"])
        self.assertEqual(code, 0)
        self.assertFalse(detect.call_args.kwargs["dry_run"])
        self.assertEqual(detect.call_args.kwargs["limit"], 12)

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory, patch(
            "scripts.manage_notifications.build_notification_candidates",
            return_value={"persisted_count": 2},
        ) as build:
            code = main(["--root", directory, "build", "--dry-run"])
        self.assertEqual(code, 0)
        self.assertTrue(build.call_args.kwargs["dry_run"])

    def test_deliver_defaults_to_preview_and_requires_explicit_real_flags(self):
        root = Path("C:/tmp/notification-cli-test")
        with patch("scripts.manage_notifications._settings", return_value=object()), patch(
            "scripts.manage_notifications.deliver_notification_candidate",
            return_value={"accepted": True, "executed": False},
        ) as deliver:
            code = main(["--root", str(root), "deliver", "candidate:1"])
        self.assertEqual(code, 0)
        self.assertTrue(deliver.call_args.kwargs["dry_run"])
        self.assertFalse(deliver.call_args.kwargs["confirm_delivery"])

        with patch("scripts.manage_notifications._settings", return_value=object()), patch(
            "scripts.manage_notifications.deliver_notification_candidate",
            return_value={"accepted": True, "executed": True},
        ) as deliver:
            code = main([
                "--root", str(root), "deliver", "--no-dry-run", "--confirm-delivery", "candidate:1"
            ])
        self.assertEqual(code, 0)
        self.assertFalse(deliver.call_args.kwargs["dry_run"])
        self.assertTrue(deliver.call_args.kwargs["confirm_delivery"])


if __name__ == "__main__":
    unittest.main()
