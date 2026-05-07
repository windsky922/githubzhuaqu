import os
import unittest
from unittest.mock import MagicMock, patch

from src.sender import (
    build_delivery_message,
    build_report_message,
    configured_delivery_channels,
    explorer_url,
    report_url,
    runs_url,
    send_report,
    send_report_to_channels,
)
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

    def test_builds_explorer_url_from_report_base_url(self):
        result = explorer_url(settings("https://example.com/weekly/"))

        self.assertEqual(result, "https://example.com/explorer.html?date=2026-04-29")

    def test_builds_explorer_url_from_github_repository(self):
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "windsky922/githubzhuaqu"}):
            result = explorer_url(settings())

        self.assertEqual(result, "https://windsky922.github.io/githubzhuaqu/explorer.html?date=2026-04-29")

    def test_builds_runs_url_from_report_base_url(self):
        result = runs_url(settings("https://example.com/weekly/"))

        self.assertEqual(result, "https://example.com/runs.html")

    def test_builds_short_report_message(self):
        message = build_report_message(settings("https://example.com/weekly"))

        self.assertIn("GitHub 每周热点项目周报 - 2026-04-29", message)
        self.assertIn('周报正文：<a href="https://example.com/weekly/2026-04-29.html">打开周报正文</a>', message)
        self.assertIn('项目筛选：<a href="https://example.com/explorer.html?date=2026-04-29">打开项目筛选</a>', message)
        self.assertIn('运行状态：<a href="https://example.com/runs.html">打开运行状态面板</a>', message)

    def test_builds_channel_neutral_delivery_message(self):
        message = build_delivery_message(settings("https://example.com/weekly"))

        self.assertIsNotNone(message)
        self.assertEqual(message.title, "GitHub 每周热点项目周报 - 2026-04-29")
        self.assertEqual(message.url, "https://example.com/weekly/2026-04-29.html")
        self.assertEqual(message.explorer_url, "https://example.com/explorer.html?date=2026-04-29")
        self.assertEqual(message.runs_url, "https://example.com/runs.html")
        self.assertIn("周报正文：https://example.com/weekly/2026-04-29.html", message.text)
        self.assertIn("项目筛选：https://example.com/explorer.html?date=2026-04-29", message.text)
        self.assertIn("运行状态：https://example.com/runs.html", message.text)
        self.assertIn('<a href="https://example.com/weekly/2026-04-29.html">打开周报正文</a>', message.html_text)
        self.assertIn('<a href="https://example.com/explorer.html?date=2026-04-29">打开项目筛选</a>', message.html_text)
        self.assertIn('<a href="https://example.com/runs.html">打开运行状态面板</a>', message.html_text)

    def test_send_report_sends_link_message_only(self):
        with patch("src.sender._send_message") as send:
            sent, error = send_report("# long markdown", settings("https://example.com/weekly"))

        self.assertTrue(sent)
        self.assertEqual(error, "")
        self.assertEqual(send.call_count, 1)
        self.assertIn('<a href="https://example.com/weekly/2026-04-29.html">打开周报正文</a>', send.call_args.args[0])
        self.assertIn('<a href="https://example.com/explorer.html?date=2026-04-29">打开项目筛选</a>', send.call_args.args[0])
        self.assertIn('<a href="https://example.com/runs.html">打开运行状态面板</a>', send.call_args.args[0])
        self.assertNotIn("# long markdown", send.call_args.args[0])

    def test_configured_delivery_channels_defaults_to_telegram(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(configured_delivery_channels(), ["telegram"])

    def test_configured_delivery_channels_removes_duplicates_and_normalizes_aliases(self):
        with patch.dict(os.environ, {"DELIVERY_CHANNELS": "telegram, lark, feishu, wecom, wechat"}):
            self.assertEqual(configured_delivery_channels(), ["telegram", "feishu", "wechat"])

    def test_send_report_to_channels_sends_configured_webhooks(self):
        env = {
            "DELIVERY_CHANNELS": "telegram,feishu,wechat",
            "FEISHU_WEBHOOK_URL": "https://example.com/feishu",
            "WECHAT_WEBHOOK_URL": "https://example.com/wechat",
        }
        with patch.dict(os.environ, env), patch("src.sender._send_message"), patch("src.sender._post_json") as post_json:
            results = send_report_to_channels("# long markdown", settings("https://example.com/weekly"))

        self.assertEqual([result.channel for result in results], ["telegram", "feishu", "wechat"])
        self.assertTrue(results[0].sent)
        self.assertTrue(results[1].sent)
        self.assertTrue(results[2].sent)
        self.assertEqual(post_json.call_count, 2)
        feishu_payload = post_json.call_args_list[0].args[1]
        wechat_payload = post_json.call_args_list[1].args[1]
        self.assertEqual(feishu_payload["msg_type"], "interactive")
        self.assertIn("打开周报正文", feishu_payload["card"]["elements"][0]["content"])
        self.assertIn("打开项目筛选", feishu_payload["card"]["elements"][0]["content"])
        self.assertIn("打开运行状态面板", feishu_payload["card"]["elements"][0]["content"])
        self.assertEqual(wechat_payload["msgtype"], "markdown")
        self.assertIn("打开周报正文", wechat_payload["markdown"]["content"])
        self.assertIn("打开项目筛选", wechat_payload["markdown"]["content"])
        self.assertIn("打开运行状态面板", wechat_payload["markdown"]["content"])

    def test_send_report_to_channels_skips_unconfigured_webhooks(self):
        with patch.dict(os.environ, {"DELIVERY_CHANNELS": "feishu,wechat"}, clear=True):
            results = send_report_to_channels("# long markdown", settings("https://example.com/weekly"))

        self.assertEqual([result.channel for result in results], ["feishu", "wechat"])
        self.assertTrue(results[0].skipped)
        self.assertEqual(results[0].error, "Feishu webhook is not configured")
        self.assertTrue(results[1].skipped)
        self.assertEqual(results[1].error, "WeChat webhook is not configured")

    def test_post_json_accepts_success_response(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"errcode":0,"errmsg":"ok"}'
        with patch("urllib.request.urlopen", return_value=response):
            from src.sender import _post_json

            _post_json("https://example.com/webhook", {"msgtype": "markdown"}, "WeChat")


if __name__ == "__main__":
    unittest.main()
