from __future__ import annotations

import os


def fallback_delivery_block_reason(fallback_used: bool, report_error: str = "") -> str:
    if not fallback_used or _allow_fallback_delivery():
        return ""
    reason = "Kimi 未生成正式周报，已阻止 Telegram 推送降级版周报"
    if report_error:
        reason += f"；原因：{report_error}"
    return reason


def _allow_fallback_delivery() -> bool:
    return os.getenv("ALLOW_FALLBACK_TELEGRAM_SEND", "").lower() in {"1", "true", "yes"}
