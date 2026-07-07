import json
import unittest
from unittest.mock import patch

from src.llm.client import KimiChatClient, LlmConfig, LlmClientError


class _Response:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class LlmClientTest(unittest.TestCase):
    def test_env_config_requires_key_and_model(self):
        config = LlmConfig.from_env({})

        self.assertFalse(config.configured)
        self.assertEqual(config.base_url, "https://api.moonshot.cn/v1")
        self.assertEqual(config.timeout_seconds, 120)

    def test_chat_extracts_content_from_kimi_response(self):
        config = LlmConfig(
            api_key="x",
            base_url="https://api.example.com/v1",
            model="moonshot-test",
            timeout_seconds=3,
            max_retries=0,
            retry_seconds=0,
        )
        client = KimiChatClient(config)
        payload = {"choices": [{"message": {"content": "回答 [1]"}}]}

        with patch("urllib.request.urlopen", return_value=_Response(payload)) as urlopen:
            answer = client.chat([{"role": "user", "content": "hi"}])

        self.assertEqual(answer, "回答 [1]")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.example.com/v1/chat/completions")

    def test_unconfigured_client_fails_without_network(self):
        client = KimiChatClient(LlmConfig.from_env({}))

        with self.assertRaises(LlmClientError):
            client.chat([{"role": "user", "content": "hi"}])


if __name__ == "__main__":
    unittest.main()
