from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.llm.client import KimiChatClient, LlmClientError, LlmConfig


_CONFIG_KEYS = (
    "KIMI_API_KEY",
    "KIMI_BASE_URL",
    "KIMI_MODEL",
    "KIMI_TIMEOUT_SECONDS",
    "KIMI_MAX_RETRIES",
    "KIMI_RETRY_SECONDS",
)


def _result(
    status: str,
    code: str,
    *,
    configured: bool,
    request_sent: bool,
    latency_ms: int | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": status,
        "code": code,
        "configured": configured,
        "request_sent": request_sent,
        "latency_ms": latency_ms,
    }


def _messages(prompt_root: Path) -> list[dict[str, str]]:
    system = (prompt_root / "prompts" / "kimi_canary_system.txt").read_text(encoding="utf-8").strip()
    user = (prompt_root / "prompts" / "kimi_canary_user.txt").read_text(encoding="utf-8").strip()
    if not system or not user or len(system) > 200 or len(user) > 200:
        raise ValueError("invalid canary prompt")
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _failure_code(error: BaseException) -> str:
    try:
        message = str(error).lower()
    except Exception:
        return "canary_provider_error"
    if "429" in message or "rate limit" in message or "too many requests" in message:
        return "canary_rate_limited"
    if "timeout" in message or "timed out" in message or "超时" in message:
        return "canary_timeout"
    return "canary_provider_error"


def _latency_ms(clock: Callable[[], float], started: float) -> int | None:
    try:
        return max(0, round((clock() - started) * 1000))
    except Exception:
        return None


def run_canary(
    *,
    confirmed: bool,
    env: Mapping[str, str] | None = None,
    client_factory: Callable[[LlmConfig], Any] = KimiChatClient,
    clock: Callable[[], float] = time.monotonic,
    prompt_root: Path = ROOT,
) -> dict[str, Any]:
    """Run one real Kimi request only after both explicit opt-in gates pass."""

    if not confirmed:
        return _result(
            "refused",
            "explicit_opt_in_required",
            configured=False,
            request_sent=False,
        )
    values = env if env is not None else os.environ
    if str(values.get("KIMI_CANARY_ENABLED", "")).strip() != "1":
        return _result(
            "refused",
            "canary_env_opt_in_required",
            configured=False,
            request_sent=False,
        )

    config_values = {key: str(values.get(key, "")) for key in _CONFIG_KEYS}
    base_config = LlmConfig.from_env(config_values)
    if not base_config.configured:
        return _result(
            "failed",
            "model_not_configured",
            configured=False,
            request_sent=False,
        )
    config = replace(
        base_config,
        timeout_seconds=min(base_config.timeout_seconds, 15),
        max_retries=0,
        retry_seconds=0,
    )
    try:
        messages = _messages(prompt_root)
        client = client_factory(config)
    except Exception:
        return _result(
            "failed",
            "canary_local_setup_error",
            configured=True,
            request_sent=False,
        )

    try:
        started = clock()
    except Exception:
        return _result(
            "failed",
            "canary_local_setup_error",
            configured=True,
            request_sent=False,
        )
    try:
        response = client.chat(messages)
        latency_ms = _latency_ms(clock, started)
        if str(response).strip() != "CANARY_OK":
            return _result(
                "failed",
                "canary_unexpected_response",
                configured=True,
                request_sent=True,
                latency_ms=latency_ms,
            )
        return _result(
            "passed",
            "canary_passed",
            configured=True,
            request_sent=True,
            latency_ms=latency_ms,
        )
    except (LlmClientError, OSError, TimeoutError, ValueError) as error:
        return _result(
            "failed",
            _failure_code(error),
            configured=True,
            request_sent=True,
            latency_ms=_latency_ms(clock, started),
        )
    except Exception:
        return _result(
            "failed",
            "canary_internal_error",
            configured=True,
            request_sent=True,
            latency_ms=_latency_ms(clock, started),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one explicitly authorized real Kimi canary request.")
    parser.add_argument(
        "--confirm-real-kimi",
        action="store_true",
        help="Confirm that one external request may be sent and billed.",
    )
    args = parser.parse_args()
    result = run_canary(confirmed=args.confirm_real_kimi)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if result["status"] == "passed" else 2 if result["status"] == "refused" else 1


if __name__ == "__main__":
    raise SystemExit(main())
