from __future__ import annotations

import html
import json
import os
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from .settings import Settings


@dataclass(frozen=True)
class DeliveryMessage:
    title: str
    url: str
    explorer_url: str
    runs_url: str
    subscriptions_url: str
    subscription_recommendation_urls: list[tuple[str, str]]
    text: str
    html_text: str
    markdown_text: str = ""


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
    return send_delivery_message(message, settings, configured_delivery_channels())


def send_delivery_message(
    message: DeliveryMessage | None,
    settings: Settings,
    channels: list[str],
) -> list[DeliveryResult]:
    results = []
    normalized_channels = []
    for value in channels:
        channel = _normalize_channel(str(value))
        if channel and channel not in normalized_channels:
            normalized_channels.append(channel)
    for channel in normalized_channels:
        if channel == "telegram":
            results.append(_send_telegram(message, settings))
        elif channel == "feishu":
            results.append(_send_feishu(message))
        elif channel == "wechat":
            results.append(_send_wechat(message))
        else:
            results.append(DeliveryResult(channel=channel, sent=False, error="Delivery channel is not supported", skipped=True))
    return results


def configured_delivery_channels() -> list[str]:
    raw = os.getenv("DELIVERY_CHANNELS", "telegram")
    channels = []
    for item in raw.split(","):
        channel = _normalize_channel(item)
        if channel and channel not in channels:
            channels.append(channel)
    return channels or ["telegram"]


def build_delivery_message(settings: Settings) -> DeliveryMessage | None:
    url = report_url(settings)
    if not url:
        return None
    project_url = explorer_url(settings)
    dashboard_url = runs_url(settings)
    subscription_page_url = subscriptions_url(settings)
    recommendation_links = subscription_recommendation_urls(settings)
    title = f"GitHub 每周热点项目周报 - {settings.run_date}"
    text_lines = [
        title,
        "",
        f"周报正文：{url}",
        f"项目筛选：{project_url}",
        f"运行状态：{dashboard_url}",
        f"订阅配置：{subscription_page_url}",
    ]
    html_lines = [
        title,
        "",
        f'周报正文：<a href="{html.escape(url, quote=True)}">打开周报正文</a>',
        f'项目筛选：<a href="{html.escape(project_url, quote=True)}">打开项目筛选</a>',
        f'运行状态：<a href="{html.escape(dashboard_url, quote=True)}">打开运行状态面板</a>',
        f'订阅配置：<a href="{html.escape(subscription_page_url, quote=True)}">打开订阅配置</a>',
    ]
    if recommendation_links:
        text_lines.append("")
        text_lines.append("订阅推荐：")
        html_lines.append("")
        html_lines.append("订阅推荐：")
        for label, link in recommendation_links:
            text_lines.append(f"- {label}：{link}")
            html_lines.append(f'- {html.escape(label)}：<a href="{html.escape(link, quote=True)}">打开推荐</a>')
    text = "\n".join(text_lines)
    html_text = "\n".join(html_lines)
    return DeliveryMessage(
        title=title,
        url=url,
        explorer_url=project_url,
        runs_url=dashboard_url,
        subscriptions_url=subscription_page_url,
        subscription_recommendation_urls=recommendation_links,
        text=text,
        html_text=html_text,
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


def explorer_url(settings: Settings) -> str:
    base_url = _site_base_url(settings)
    if not base_url:
        return ""
    date = urllib.parse.quote(settings.run_date)
    return f"{base_url}/explorer.html?date={date}"


def runs_url(settings: Settings) -> str:
    base_url = _site_base_url(settings)
    if not base_url:
        return ""
    return f"{base_url}/runs.html"


def subscriptions_url(settings: Settings) -> str:
    base_url = _site_base_url(settings)
    if not base_url:
        return ""
    return f"{base_url}/subscriptions.html"


def subscription_recommendation_urls(settings: Settings, limit: int = 3) -> list[tuple[str, str]]:
    base_url = _site_base_url(settings)
    root = getattr(settings, "root", None)
    if not base_url or not root:
        return []
    db_path = root / "data" / "github_weekly.sqlite"
    if not db_path.exists():
        return []
    try:
        with sqlite3.connect(db_path) as connection:
            connection.row_factory = sqlite3.Row
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'subscriptions'"
            ).fetchone()
            if not table:
                return []
            rows = connection.execute(
                """
                SELECT name, profile, language, category, query, sort
                FROM subscriptions
                WHERE status = 'enabled'
                ORDER BY updated_at DESC, created_at DESC, subscription_id DESC
                LIMIT ?
                """,
                (max(1, min(limit, 10)),),
            ).fetchall()
    except sqlite3.Error:
        return []
    output = []
    for row in rows:
        link = _subscription_recommendation_url(base_url, row)
        if link:
            output.append((str(row["name"] or row["profile"] or row["language"] or "订阅推荐"), link))
    return output


def _site_base_url(settings: Settings) -> str:
    base_url = settings.report_base_url.strip().rstrip("/")
    if base_url.endswith("/weekly"):
        return base_url[: -len("/weekly")]
    if base_url:
        return base_url
    repository = _github_repository()
    if not repository:
        return ""
    owner, name = repository.split("/", 1)
    return f"https://{owner}.github.io/{name}"


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


def _send_feishu(message: DeliveryMessage | None) -> DeliveryResult:
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return DeliveryResult(channel="feishu", sent=False, error="Feishu webhook is not configured", skipped=True)
    if not message:
        return DeliveryResult(channel="feishu", sent=False, error="Report URL is not configured", skipped=True)
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": message.title},
                "template": "blue",
            },
            "elements": [
                {"tag": "markdown", "content": _delivery_markdown(message)},
            ],
        },
    }
    try:
        _post_json(webhook_url, payload, "Feishu")
    except Exception as error:
        return DeliveryResult(channel="feishu", sent=False, error=str(error))
    return DeliveryResult(channel="feishu", sent=True)


def _send_wechat(message: DeliveryMessage | None) -> DeliveryResult:
    webhook_url = os.getenv("WECHAT_WEBHOOK_URL", "").strip() or os.getenv("WECOM_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return DeliveryResult(channel="wechat", sent=False, error="WeChat webhook is not configured", skipped=True)
    if not message:
        return DeliveryResult(channel="wechat", sent=False, error="Report URL is not configured", skipped=True)
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": f"**{message.title}**\n\n{_delivery_markdown(message)}",
        },
    }
    try:
        _post_json(webhook_url, payload, "WeChat")
    except Exception as error:
        return DeliveryResult(channel="wechat", sent=False, error=str(error))
    return DeliveryResult(channel="wechat", sent=True)


def _normalize_channel(value: str) -> str:
    channel = value.strip().lower()
    aliases = {
        "lark": "feishu",
        "wecom": "wechat",
        "weixin": "wechat",
    }
    return aliases.get(channel, channel)


def _delivery_markdown(message: DeliveryMessage) -> str:
    if message.markdown_text:
        return message.markdown_text
    lines = [
        f"周报正文：[打开周报正文]({message.url})",
        f"项目筛选：[打开项目筛选]({message.explorer_url})",
        f"运行状态：[打开运行状态面板]({message.runs_url})",
        f"订阅配置：[打开订阅配置]({message.subscriptions_url})",
    ]
    if message.subscription_recommendation_urls:
        lines.append("")
        lines.append("订阅推荐：")
        for label, link in message.subscription_recommendation_urls:
            lines.append(f"- {label}：[打开推荐]({link})")
    return "\n\n".join(lines)


def _subscription_recommendation_url(base_url: str, row: sqlite3.Row) -> str:
    params = {}
    for key in ("profile", "language", "category", "sort"):
        value = str(row[key] or "").strip()
        if value:
            params[key] = value
    query = str(row["query"] or "").strip()
    if query:
        params["q"] = query
    suffix = urllib.parse.urlencode(params)
    return f"{base_url}/recommendations.html?{suffix}" if suffix else f"{base_url}/recommendations.html"


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


def _post_json(url: str, payload: dict, service_name: str) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{service_name} webhook error {error.code}: {body}") from error

    try:
        response_data = json.loads(body)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{service_name} webhook returned non-JSON response") from error

    if _webhook_response_ok(response_data):
        return
    raise RuntimeError(f"{service_name} webhook returned failure: {_safe_response_summary(response_data)}")


def _webhook_response_ok(data: dict) -> bool:
    for key in ("errcode", "code", "StatusCode"):
        if key in data:
            try:
                return int(data.get(key) or 0) == 0
            except (TypeError, ValueError):
                return False
    return bool(data.get("ok"))


def _safe_response_summary(data: dict) -> str:
    safe = {}
    for key in ("errcode", "errmsg", "code", "msg", "StatusCode", "StatusMessage"):
        if key in data:
            safe[key] = data[key]
    return json.dumps(safe or {"response": "unexpected"}, ensure_ascii=False)
