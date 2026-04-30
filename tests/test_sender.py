import os
import unittest
from unittest.mock import patch

from src.sender import build_delivery_message, build_report_message, report_url, send_report
from src.settings import Settings


def settings(report_base_url=""):
    return Settings(
        root=None,
        run_date="2026-04-29",
        since_date="2026-04-22",
        days_back=7,
        min_stars=20,
        max_projects=10,
        github_token="",
        kimi_api_key="",
        kimi_base_url="",
        kimi_model="",
        telegram_bot_token="token",
        telegram_chat_id="chat",
        interests={},
        report_base_url=report_base_url,
    )


class SenderTest(unittest.TestCase):
    def test_builds_report_url_from_configured_base_url(self):
        result = report_url(settings("https://example.com/weekly/"))

        self.assertEqual(result, "https://example.com/weekly/2026-04-29.html")

    def test_builds_report_url_from_github_repository(self):
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "windsky922/githubzhuaqu"}):
            result = report_url(settings())

        self.assertEqual(result, "https://windsky922.github.io/githubzhuaqu/weekly/2026-04-29.html")

    def test_builds_short_report_message(self):
        message = build_report_message(settings("https://example.com/weekly"))

        self.assertIn("GitHub 每周热点项目周报 - 2026-04-29", message)
        self.assertIn('阅读链接：<a href="https://example.com/weekly/2026-04-29.html">打开本周周报</a>', message)

    def test_builds_channel_neutral_delivery_message(self):
        message = build_delivery_message(settings("https://example.com/weekly"))

        self.assertIsNotNone(message)
        self.assertEqual(message.title, "GitHub 每周热点项目周报 - 2026-04-29")
        self.assertEqual(message.url, "https://example.com/weekly/2026-04-29.html")
        self.assertIn("阅读链接：https://example.com/weekly/2026-04-29.html", message.text)
        self.assertIn('<a href="https://example.com/weekly/2026-04-29.html">打开本周周报</a>', message.html_text)

    def test_send_report_sends_link_message_only(self):
        with patch("src.sender._send_message") as send:
            sent, error = send_report("# long markdown", settings("https://example.com/weekly"))

        self.assertTrue(sent)
        self.assertEqual(error, "")
        self.assertEqual(send.call_count, 1)
        self.assertIn('<a href="https://example.com/weekly/2026-04-29.html">打开本周周报</a>', send.call_args.args[0])
        self.assertNotIn("# long markdown", send.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
