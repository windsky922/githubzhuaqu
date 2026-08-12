from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from scripts.run_kimi_canary import run_canary
from src.llm.client import LlmClientError, LlmConfig


ROOT = Path(__file__).resolve().parents[1]


class _ExplodingEnvironment(dict[str, str]):
    def get(self, key: str, default: str = "") -> str:
        raise AssertionError(f"environment must not be read: {key}")


class _Client:
    def __init__(self, config: LlmConfig, response: str = "CANARY_OK", error: BaseException | None = None) -> None:
        self.config = config
        self.response = response
        self.error = error
        self.messages: list[dict[str, str]] = []

    def chat(self, messages: list[dict[str, str]]) -> str:
        self.messages = messages
        if self.error is not None:
            raise self.error
        return self.response


def _env(**overrides: str) -> dict[str, str]:
    return {
        "KIMI_CANARY_ENABLED": "1",
        "KIMI_API_KEY": "test-key",
        "KIMI_BASE_URL": "https://provider.invalid/v1",
        "KIMI_MODEL": "test-model",
        "KIMI_TIMEOUT_SECONDS": "120",
        "KIMI_MAX_RETRIES": "4",
        "KIMI_RETRY_SECONDS": "20",
        **overrides,
    }


class KimiCanaryTest(unittest.TestCase):
    def test_cli_confirmation_is_required_before_environment_access(self) -> None:
        result = run_canary(confirmed=False, env=_ExplodingEnvironment())
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["code"], "explicit_opt_in_required")
        self.assertFalse(result["request_sent"])

    def test_environment_opt_in_is_required_before_client_creation(self) -> None:
        def fail_factory(config: LlmConfig) -> _Client:
            raise AssertionError("client must not be created")

        result = run_canary(
            confirmed=True,
            env=_env(KIMI_CANARY_ENABLED="0"),
            client_factory=fail_factory,
        )
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["code"], "canary_env_opt_in_required")
        self.assertFalse(result["request_sent"])

    def test_missing_model_configuration_never_creates_client(self) -> None:
        def fail_factory(config: LlmConfig) -> _Client:
            raise AssertionError("client must not be created")

        result = run_canary(
            confirmed=True,
            env=_env(KIMI_API_KEY="", KIMI_MODEL=""),
            client_factory=fail_factory,
        )
        self.assertEqual(result["code"], "model_not_configured")
        self.assertFalse(result["configured"])
        self.assertFalse(result["request_sent"])

    def test_success_uses_one_short_fixed_prompt_and_no_retries(self) -> None:
        created: list[_Client] = []

        def factory(config: LlmConfig) -> _Client:
            client = _Client(config)
            created.append(client)
            return client

        times = iter((10.0, 10.125))
        result = run_canary(
            confirmed=True,
            env=_env(),
            client_factory=factory,
            clock=lambda: next(times),
        )

        self.assertEqual(result, {
            "schema_version": 1,
            "status": "passed",
            "code": "canary_passed",
            "configured": True,
            "request_sent": True,
            "latency_ms": 125,
        })
        self.assertEqual(created[0].config.timeout_seconds, 15)
        self.assertEqual(created[0].config.max_retries, 0)
        self.assertEqual(created[0].config.retry_seconds, 0)
        self.assertEqual(len(created[0].messages), 2)
        self.assertLess(sum(len(item["content"]) for item in created[0].messages), 200)

    def test_unexpected_response_is_not_returned(self) -> None:
        client = _Client(LlmConfig("", "", "", 1, 0, 0), response="private model body")
        result = run_canary(
            confirmed=True,
            env=_env(),
            client_factory=lambda config: client,
            clock=iter((1.0, 1.01)).__next__,
        )
        serialized = json.dumps(result)
        self.assertEqual(result["code"], "canary_unexpected_response")
        self.assertNotIn("private model body", serialized)

    def test_provider_failures_return_only_fixed_codes(self) -> None:
        cases = (
            (LlmClientError("HTTP 429 secret-key provider-body"), "canary_rate_limited"),
            (LlmClientError("request timeout secret-key provider-body"), "canary_timeout"),
            (LlmClientError("https://private.invalid secret-key provider-body"), "canary_provider_error"),
        )
        for error, code in cases:
            with self.subTest(code=code):
                client = _Client(LlmConfig("", "", "", 1, 0, 0), error=error)
                result = run_canary(
                    confirmed=True,
                    env=_env(),
                    client_factory=lambda config, value=client: value,
                    clock=iter((1.0, 1.02)).__next__,
                )
                serialized = json.dumps(result)
                self.assertEqual(result["code"], code)
                self.assertTrue(result["request_sent"])
                self.assertNotIn("secret-key", serialized)
                self.assertNotIn("provider-body", serialized)
                self.assertNotIn("private.invalid", serialized)

    def test_unexpected_runtime_error_returns_only_internal_code(self) -> None:
        client = _Client(
            LlmConfig("", "", "", 1, 0, 0),
            error=RuntimeError("secret-key provider-body https://private.invalid"),
        )
        result = run_canary(
            confirmed=True,
            env=_env(),
            client_factory=lambda config: client,
            clock=iter((1.0, 1.02)).__next__,
        )
        serialized = json.dumps(result)
        self.assertEqual(result["code"], "canary_internal_error")
        self.assertTrue(result["request_sent"])
        self.assertNotIn("secret-key", serialized)
        self.assertNotIn("provider-body", serialized)
        self.assertNotIn("private.invalid", serialized)

    def test_setup_runtime_error_returns_no_traceback_or_request(self) -> None:
        def fail_factory(config: LlmConfig) -> _Client:
            raise RuntimeError("C:/private/path secret-key provider-body")

        result = run_canary(confirmed=True, env=_env(), client_factory=fail_factory)
        serialized = json.dumps(result)
        self.assertEqual(result["code"], "canary_local_setup_error")
        self.assertFalse(result["request_sent"])
        self.assertNotIn("private/path", serialized)
        self.assertNotIn("secret-key", serialized)

    def test_fixed_ci_never_invokes_or_enables_real_canary(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        package = (ROOT / "package.json").read_text(encoding="utf-8")
        fixed_commands = f"{workflow}\n{package}"
        self.assertNotIn("run_kimi_canary.py", fixed_commands)
        self.assertIsNone(re.search(r"KIMI_CANARY_ENABLED\s*(?:=|:)\s*['\"]?1['\"]?", fixed_commands))


if __name__ == "__main__":
    unittest.main()
