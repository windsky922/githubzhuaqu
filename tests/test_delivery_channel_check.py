import os
import unittest
from unittest.mock import patch

from scripts.check_delivery_channels import check_delivery_channels, has_delivery_config_error


class DeliveryChannelCheckTest(unittest.TestCase):
    def test_reports_configured_telegram(self):
        env = {
            "DELIVERY_CHANNELS": "telegram",
            "TELEGRAM_BOT_TOKEN": "token",
            "TELEGRAM_CHAT_ID": "chat",
        }
        with patch.dict(os.environ, env, clear=True):
            checks = check_delivery_channels()

        self.assertEqual(checks[0].channel, "telegram")
        self.assertTrue(checks[0].configured)
        self.assertEqual(checks[0].missing, [])
        self.assertFalse(has_delivery_config_error(checks))

    def test_reports_missing_feishu_webhook(self):
        with patch.dict(os.environ, {"DELIVERY_CHANNELS": "feishu"}, clear=True):
            checks = check_delivery_channels()

        self.assertEqual(checks[0].channel, "feishu")
        self.assertFalse(checks[0].configured)
        self.assertEqual(checks[0].missing, ["FEISHU_WEBHOOK_URL"])
        self.assertTrue(has_delivery_config_error(checks))

    def test_accepts_either_wechat_webhook_name(self):
        env = {
            "DELIVERY_CHANNELS": "wechat",
            "WECOM_WEBHOOK_URL": "https://example.com/wecom",
        }
        with patch.dict(os.environ, env, clear=True):
            checks = check_delivery_channels()

        self.assertEqual(checks[0].channel, "wechat")
        self.assertTrue(checks[0].configured)
        self.assertEqual(checks[0].missing, [])

    def test_reports_unsupported_channel(self):
        with patch.dict(os.environ, {"DELIVERY_CHANNELS": "telegram,email"}, clear=True):
            checks = check_delivery_channels()

        self.assertEqual(checks[1].channel, "email")
        self.assertFalse(checks[1].configured)
        self.assertEqual(checks[1].note, "不支持的推送通道")


if __name__ == "__main__":
    unittest.main()
