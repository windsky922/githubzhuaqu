from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from src.security import redact_sensitive_text


@dataclass(frozen=True)
class LlmConfig:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: int
    max_retries: int
    retry_seconds: int

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model)

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "LlmConfig":
        values = env if env is not None else os.environ
        return cls(
            api_key=values.get("KIMI_API_KEY", ""),
            base_url=values.get("KIMI_BASE_URL") or "https://api.moonshot.cn/v1",
            model=values.get("KIMI_MODEL", ""),
            timeout_seconds=_int_value(values.get("KIMI_TIMEOUT_SECONDS"), 120, minimum=1),
            max_retries=_int_value(values.get("KIMI_MAX_RETRIES"), 2, minimum=0),
            retry_seconds=_int_value(values.get("KIMI_RETRY_SECONDS"), 20, minimum=0),
        )


class LlmClientError(RuntimeError):
    """LLM 请求失败，错误消息必须可安全写入响应或日志。"""


class KimiChatClient:
    def __init__(self, config: LlmConfig | None = None) -> None:
        self.config = config or LlmConfig.from_env()

    def status(self) -> dict[str, Any]:
        return {
            "provider": "kimi",
            "configured": self.config.configured,
            "model": self.config.model if self.config.configured else "",
            "base_url_configured": bool(self.config.base_url),
            "timeout_seconds": self.config.timeout_seconds,
            "max_retries": self.config.max_retries,
        }

    def chat(self, messages: list[dict[str, str]]) -> str:
        if not self.config.configured:
            raise LlmClientError("Kimi API 未配置")
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": 1,
        }
        data = self._post_with_retries(payload)
        content = _extract_content(data)
        if not content.strip():
            raise LlmClientError(f"Kimi API 返回空内容，响应结构：{_response_shape(data)}")
        return redact_sensitive_text(content).strip()

    def _post_with_retries(self, payload: dict[str, Any]) -> dict[str, Any]:
        errors: list[str] = []
        for attempt in range(self.config.max_retries + 1):
            try:
                request = _request(self._chat_url(), payload, self.config.api_key)
                with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                body = error.read().decode("utf-8", errors="replace")
                message = redact_sensitive_text(f"Kimi API error {error.code}: {body}")
                if not _is_transient_error(error.code, body) or attempt >= self.config.max_retries:
                    raise LlmClientError("; ".join(errors + [message])) from error
                errors.append(f"{message}; retry_after={self.config.retry_seconds}s")
                time.sleep(self.config.retry_seconds)
            except (TimeoutError, urllib.error.URLError, json.JSONDecodeError) as error:
                message = redact_sensitive_text(f"Kimi API transient request error: {error}")
                if attempt >= self.config.max_retries:
                    raise LlmClientError("; ".join(errors + [message])) from error
                errors.append(f"{message}; retry_after={self.config.retry_seconds}s")
                time.sleep(self.config.retry_seconds)
        raise LlmClientError("; ".join(errors) or "Kimi API request failed")

    def _chat_url(self) -> str:
        base_url = self.config.base_url.rstrip("/")
        return base_url if base_url.endswith("/chat/completions") else base_url + "/chat/completions"


def _request(url: str, payload: dict[str, Any], api_key: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )


def _extract_content(data: dict[str, Any]) -> str:
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    for key in ("reasoning_content", "text", "output_text"):
        value = message.get(key) or choice.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _response_shape(data: dict[str, Any]) -> str:
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    return json.dumps(
        {
            "top_level_keys": sorted(data.keys()),
            "choice_keys": sorted(choice.keys()),
            "message_keys": sorted(message.keys()),
            "finish_reason": choice.get("finish_reason"),
            "content_type": type(message.get("content")).__name__,
        },
        ensure_ascii=False,
    )


def _is_transient_error(status_code: int, body: str) -> bool:
    lower_body = body.lower()
    return status_code in {429, 500, 502, 503, 504} or "engine_overloaded" in lower_body or "rate limit" in lower_body


def _int_value(value: str | None, default: int, *, minimum: int) -> int:
    try:
        parsed = int(value or "")
    except ValueError:
        return default
    return max(minimum, parsed)

