from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from .settings import Settings
from .utils import chunk_text


def send_report(report: str, settings: Settings) -> tuple[bool, str]:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return False, "Telegram is not configured"

    chunks = chunk_text(report, limit=3500)
    for index, chunk in enumerate(chunks, start=1):
        prefix = f"GitHub 每周热点项目周报 ({index}/{len(chunks)})\n\n" if len(chunks) > 1 else ""
        try:
            _send_message(prefix + chunk, settings)
        except Exception as error:
            return False, str(error)
    return True, ""


def _send_message(text: str, settings: Settings) -> None:
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = urllib.parse.urlencode(
        {
            "chat_id": settings.telegram_chat_id,
            "text": text,
            "disable_web_page_preview": "true",
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

