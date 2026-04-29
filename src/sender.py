from __future__ import annotations

import html
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from .settings import Settings


def send_report(report: str, settings: Settings) -> tuple[bool, str]:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return False, "Telegram is not configured"
    message = build_report_message(settings)
    if not message:
        return False, "Report URL is not configured"

    try:
        _send_message(message, settings)
    except Exception as error:
        return False, str(error)
    return True, ""


def build_report_message(settings: Settings) -> str:
    url = report_url(settings)
    if not url:
        return ""
    return "\n".join(
        [
            f"GitHub 每周热点项目周报 - {settings.run_date}",
            "",
            f'阅读链接：<a href="{html.escape(url, quote=True)}">打开本周周报</a>',
        ]
    )


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
