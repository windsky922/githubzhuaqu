from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from src.sender import configured_delivery_channels


@dataclass(frozen=True)
class ChannelCheck:
    channel: str
    configured: bool
    required: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    note: str = ""

    def status_text(self) -> str:
        if self.configured:
            return "已配置"
        return "未配置"


def check_delivery_channels() -> list[ChannelCheck]:
    checks = []
    for channel in configured_delivery_channels():
        checks.append(_check_channel(channel))
    return checks


def has_delivery_config_error(checks: list[ChannelCheck]) -> bool:
    return any(not check.configured for check in checks)


def _check_channel(channel: str) -> ChannelCheck:
    if channel == "telegram":
        required = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
        missing = _missing(required)
        return ChannelCheck(channel=channel, configured=not missing, required=required, missing=missing)
    if channel == "feishu":
        required = ["FEISHU_WEBHOOK_URL"]
        missing = _missing(required)
        return ChannelCheck(channel=channel, configured=not missing, required=required, missing=missing)
    if channel == "wechat":
        options = ["WECHAT_WEBHOOK_URL", "WECOM_WEBHOOK_URL"]
        configured = any(os.getenv(name) for name in options)
        missing = [] if configured else options
        return ChannelCheck(
            channel=channel,
            configured=configured,
            required=options,
            missing=missing,
            note="WECHAT_WEBHOOK_URL 和 WECOM_WEBHOOK_URL 任意配置一个即可",
        )
    return ChannelCheck(
        channel=channel,
        configured=False,
        required=[],
        missing=[],
        note="不支持的推送通道",
    )


def _missing(names: list[str]) -> list[str]:
    return [name for name in names if not os.getenv(name)]


def main() -> int:
    parser = argparse.ArgumentParser(description="检查推送通道配置，不发送真实消息。")
    parser.add_argument("--strict", action="store_true", help="启用通道缺少配置时返回失败。")
    args = parser.parse_args()

    checks = check_delivery_channels()
    print("推送通道配置检查：")
    for check in checks:
        line = f"- {check.channel}: {check.status_text()}"
        if check.missing:
            line += f"，缺少 {', '.join(check.missing)}"
        if check.note:
            line += f"，说明：{check.note}"
        print(line)

    if args.strict and has_delivery_config_error(checks):
        print("存在未正确配置的推送通道。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
