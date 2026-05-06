from __future__ import annotations

import html
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from .settings import Settings


@dataclass(frozen=True)
class DeliveryMessage:
    title: str
    url: str
    text: str
    html_text: str


@dataclass(frozen=True)
class DeliveryResult:
    channel: str
    sent: bool
    error: str = ""
    skipped: bool = False

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "channel": self.channel,
            "sent": self.sent,
            "error": self.error,
            "skipped": self.skipped,
        }


def send_report(report: str, settings: Settings) -> tuple[bool, str]:
    result = _send_telegram(build_delivery_message(settings), settings)
    return result.sent, result.error


def build_report_message(settings: Settings) -> str:
    message = build_delivery_message(settings)
    return message.html_text if message else ""


def send_report_to_channels(report: str, settings: Settings) -> list[DeliveryResult]:
    message = build_delivery_message(settings)
    results = []
    for channel in configured_delivery_channels():
        if channel == "telegram":
            results.append(_send_telegram(message, settings))
        else:
            results.append(DeliveryResult(channel=channel, sent=False, error="Delivery channel is not implemented", skipped=True))
    return results


def configured_delivery_channels() -> list[str]:
    raw = os.getenv("DELIVERY_CHANNELS", "telegram")
    channels = []
    for item in raw.split(","):
        channel = item.strip().lower()
        if channel and channel not in channels:
            channels.append(channel)
    return channels or ["telegram"]


def build_delivery_message(settings: Settings) -> DeliveryMessage | None:
    url = report_url(settings)
    if not url:
        return None
    title = f"GitHub 每周热点项目周报 - {settings.run_date}"
    text = "\n".join(
        [
            title,
            "",
            f"阅读链接：{url}",
        ]
    )
    html_text = "\n".join(
        [
            title,
            "",
            f'阅读链接：<a href="{html.escape(url, quote=True)}">打开本周周报</a>',
        ]
    )
    return DeliveryMessage(title=title, url=url, text=text, html_text=html_text)


def report_url(settings: Settings) -> str:
    base_url = settings.report_base_url.strip().rstrip("/")
    if not base_url:
        repository = _github_repository()
        if not repository:
            return ""
        owner, name = repository.split("/", 1)
        base_url = f"https://{owner}.github.io/{name}/weekly"
    return f"{base_url}/{settings.run_date}.html"


def _github_repository() -> str:
    value = os.getenv("GITHUB_REPOSITORY", "")
    return value if "/" in value else ""


def _send_telegram(message: DeliveryMessage | None, settings: Settings) -> DeliveryResult:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return DeliveryResult(channel="telegram", sent=False, error="Telegram is not configured", skipped=True)
    if not message:
        return DeliveryResult(channel="telegram", sent=False, error="Report URL is not configured", skipped=True)
    try:
        _send_message(message.html_text, settings)
    except Exception as error:
        return DeliveryResult(channel="telegram", sent=False, error=str(error))
    return DeliveryResult(channel="telegram", sent=True)


def _send_message(text: str, settings: Settings) -> None:
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = urllib.parse.urlencode(
        {
            "chat_id": settings.telegram_chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
    ).encode("utf-8")
    request = urllib.request.Request(url, data=payload, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram API error {error.code}: {body}") from error
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API returned failure: {data}")
