import os
import unittest
from unittest.mock import patch

from src.delivery_policy import fallback_delivery_block_reason


class DeliveryPolicyTest(unittest.TestCase):
    def test_blocks_fallback_delivery_by_default(self):
        with patch.dict(os.environ, {"ALLOW_FALLBACK_TELEGRAM_SEND": ""}):
            reason = fallback_delivery_block_reason(True, "Kimi API error 429")

        self.assertIn("已阻止 Telegram 推送降级版周报", reason)
        self.assertIn("Kimi API error 429", reason)

    def test_allows_normal_report_delivery(self):
        reason = fallback_delivery_block_reason(False, "")

        self.assertEqual(reason, "")

    def test_allows_fallback_delivery_when_explicitly_enabled(self):
        with patch.dict(os.environ, {"ALLOW_FALLBACK_TELEGRAM_SEND": "true"}):
            reason = fallback_delivery_block_reason(True, "Kimi API error 429")

        self.assertEqual(reason, "")


if __name__ == "__main__":
    unittest.main()
