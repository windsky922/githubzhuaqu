from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from scripts.check_assistant_readiness import _human_lines, safe_check_readiness
from src.api.app import create_app
from src.api.readiness import build_assistant_readiness


FRESHNESS = {
    "source_latest_date": "2026-08-11",
    "corpus_latest_date": "2026-08-11",
    "embedding_latest_date": "2026-08-11",
    "stale_days": 0,
    "data_freshness": "fresh",
    "as_of": "2026-08-12",
    "stale_after_days": 30,
    "reasons": [],
}


class _Model:
    def __init__(self, configured: bool, **extra: object) -> None:
        self.configured = configured
        self.extra = extra

    def status(self) -> dict[str, object]:
        return {
            "provider": "kimi",
            "configured": self.configured,
            "model": "moonshot-safe" if self.configured else "",
            **self.extra,
        }


class _Repository:
    def __init__(
        self,
        root: Path,
        source: dict[str, object],
        *,
        sqlite_rag: bool = False,
        json_rag: bool = False,
        sqlite_row: bool = True,
        json_payload: str | None = None,
    ) -> None:
        self.root = root
        self.data_source = source
        self.local_read_only = bool(source.get("read_only"))
        self.local_json_archive = source.get("kind") == "local_archive_json"
        self.db_path = root / "data" / "assistant.sqlite"
        if sqlite_rag:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.db_path)
            connection.execute("CREATE TABLE rag_chunks (chunk_id TEXT PRIMARY KEY, full_name TEXT, chunk_text TEXT)")
            if sqlite_row:
                connection.execute(
                    "INSERT INTO rag_chunks (chunk_id, full_name, chunk_text) VALUES (?, ?, ?)",
                    ("chunk:1", "owner/project", "Python Agent project evidence"),
                )
            connection.commit()
            connection.close()
        if json_rag:
            selected = root / "data" / "selected"
            selected.mkdir(parents=True, exist_ok=True)
            (selected / "2026-08-11.json").write_text(
                json_payload if json_payload is not None else '[{"full_name":"owner/project"}]',
                encoding="utf-8",
            )


def _source(
    *,
    available: bool = True,
    kind: str = "weekly_snapshot",
    freshness: str = "fresh",
    history_only: bool = False,
    read_only: bool = True,
    reason: str = "",
) -> dict[str, object]:
    return {
        "available": available,
        "kind": kind,
        "root": Path("C:/private/not-public"),
        "source_id": "fixture:weekly:2026-08-11",
        "run_date": "2026-08-11",
        "reason": reason,
        "attestation": {**FRESHNESS, "data_freshness": freshness},
        "history_only": history_only,
        "read_only": read_only,
    }


def _readiness(repository: _Repository, model: _Model) -> dict[str, object]:
    return build_assistant_readiness(repository, model, api_responded=True)


class AssistantReadinessTest(unittest.TestCase):
    def test_preflight_setup_failure_is_fixed_and_redacted(self) -> None:
        def fail() -> dict[str, object]:
            raise RuntimeError("C:/private/path secret-key provider-body")

        result = safe_check_readiness(fail)  # type: ignore[arg-type]
        serialized = json.dumps(result)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["components"]["api"]["code"], "preflight_setup_error")
        self.assertNotIn("private/path", serialized)
        self.assertNotIn("secret-key", serialized)
        self.assertTrue(any("api: unavailable" in line for line in _human_lines(result)))

    def test_ready_requires_model_fresh_snapshot_readonly_rag(self) -> None:
        with tempfile.TemporaryDirectory(prefix="assistant-readiness-ready-") as directory:
            repository = _Repository(Path(directory), _source(), sqlite_rag=True)
            result = _readiness(repository, _Model(True))

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["components"]["rag"]["mode"], "sqlite")
        self.assertEqual(
            result["capabilities"],
            {
                "can_chat": True,
                "knowledge_available": True,
                "project_available": True,
                "current_project_available": True,
            },
        )

    def test_missing_model_keeps_project_chain_degraded(self) -> None:
        with tempfile.TemporaryDirectory(prefix="assistant-readiness-no-model-") as directory:
            result = _readiness(
                _Repository(Path(directory), _source(), sqlite_rag=True),
                _Model(False),
            )

        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["components"]["model"]["code"], "model_not_configured")
        self.assertFalse(result["capabilities"]["knowledge_available"])
        self.assertTrue(result["capabilities"]["project_available"])
        self.assertTrue(result["capabilities"]["can_chat"])

    def test_missing_snapshot_keeps_knowledge_chain_degraded(self) -> None:
        source = _source(
            available=False,
            freshness="unknown",
            reason="missing_verified_weekly_snapshot",
        )
        with tempfile.TemporaryDirectory(prefix="assistant-readiness-no-snapshot-") as directory:
            result = _readiness(_Repository(Path(directory), source), _Model(True))

        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["components"]["snapshot"]["code"], "missing_verified_weekly_snapshot")
        self.assertTrue(result["capabilities"]["knowledge_available"])
        self.assertFalse(result["capabilities"]["project_available"])
        self.assertTrue(result["capabilities"]["can_chat"])

    def test_missing_model_and_snapshot_is_unavailable(self) -> None:
        source = _source(
            available=False,
            freshness="unknown",
            reason="missing_verified_weekly_snapshot",
        )
        with tempfile.TemporaryDirectory(prefix="assistant-readiness-none-") as directory:
            result = _readiness(_Repository(Path(directory), source), _Model(False))

        self.assertEqual(result["status"], "unavailable")
        self.assertFalse(result["capabilities"]["can_chat"])

    def test_stale_snapshot_is_queryable_but_not_current(self) -> None:
        with tempfile.TemporaryDirectory(prefix="assistant-readiness-stale-") as directory:
            result = _readiness(
                _Repository(Path(directory), _source(freshness="stale"), sqlite_rag=True),
                _Model(True),
            )

        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["components"]["snapshot"]["code"], "snapshot_stale")
        self.assertTrue(result["capabilities"]["project_available"])
        self.assertFalse(result["capabilities"]["current_project_available"])

    def test_explicit_json_history_is_read_only_and_never_current(self) -> None:
        source = _source(
            kind="local_archive_json",
            freshness="stale",
            history_only=True,
        )
        with tempfile.TemporaryDirectory(prefix="assistant-readiness-history-") as directory:
            result = _readiness(
                _Repository(Path(directory), source, json_rag=True),
                _Model(False),
            )

        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["components"]["rag"]["mode"], "local_archive_json")
        self.assertTrue(result["capabilities"]["project_available"])
        self.assertFalse(result["capabilities"]["current_project_available"])

    def test_non_readonly_repository_fails_closed_for_project_capability(self) -> None:
        with tempfile.TemporaryDirectory(prefix="assistant-readiness-access-") as directory:
            result = _readiness(
                _Repository(Path(directory), _source(read_only=False), sqlite_rag=True),
                _Model(True),
            )

        self.assertEqual(result["components"]["access"]["code"], "assistant_not_read_only")
        self.assertFalse(result["capabilities"]["project_available"])
        self.assertEqual(result["status"], "degraded")

    def test_response_omits_paths_credentials_and_base_url(self) -> None:
        with tempfile.TemporaryDirectory(prefix="assistant-readiness-redaction-") as directory:
            result = _readiness(
                _Repository(Path(directory), _source(), sqlite_rag=True),
                _Model(
                    True,
                    **{
                        "api" + "_key": "never-return-this-key",
                        "base" + "_url": "https://secret-provider.invalid/private",
                        "exception": "provider raw body",
                    },
                ),
            )
            serialized = json.dumps(result, ensure_ascii=False)

        self.assertNotIn(directory, serialized)
        self.assertNotIn("never-return-this-key", serialized)
        self.assertNotIn("secret-provider.invalid", serialized)
        self.assertNotIn("provider raw body", serialized)

    def test_empty_or_malformed_sqlite_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="assistant-readiness-empty-sqlite-") as directory:
            empty = _readiness(
                _Repository(Path(directory), _source(), sqlite_rag=True, sqlite_row=False),
                _Model(True),
            )
        with tempfile.TemporaryDirectory(prefix="assistant-readiness-bad-sqlite-") as directory:
            repository = _Repository(Path(directory), _source())
            repository.db_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(repository.db_path)
            connection.execute("CREATE TABLE rag_chunks (chunk_id TEXT PRIMARY KEY)")
            connection.execute("INSERT INTO rag_chunks (chunk_id) VALUES ('chunk:1')")
            connection.commit()
            connection.close()
            malformed = _readiness(repository, _Model(True))

        for result in (empty, malformed):
            self.assertEqual(result["components"]["rag"]["code"], "rag_source_unavailable")
            self.assertFalse(result["capabilities"]["project_available"])
            self.assertEqual(result["status"], "degraded")

    def test_empty_or_malformed_json_fails_closed(self) -> None:
        source = _source(kind="local_archive_json", freshness="stale", history_only=True)
        for payload in ("{}", "[]", "not-json", '[{"full_name":"invalid"}]'):
            with self.subTest(payload=payload), tempfile.TemporaryDirectory(prefix="assistant-readiness-bad-json-") as directory:
                result = _readiness(
                    _Repository(Path(directory), source, json_rag=True, json_payload=payload),
                    _Model(False),
                )
                self.assertEqual(result["components"]["rag"]["code"], "rag_source_unavailable")
                self.assertFalse(result["capabilities"]["project_available"])
                self.assertEqual(result["status"], "unavailable")

    def test_cli_context_does_not_claim_api_listener_is_running(self) -> None:
        with tempfile.TemporaryDirectory(prefix="assistant-readiness-cli-") as directory:
            result = build_assistant_readiness(
                _Repository(Path(directory), _source(), sqlite_rag=True),
                _Model(True),
            )

        self.assertEqual(result["components"]["api"]["status"], "degraded")
        self.assertEqual(result["components"]["api"]["code"], "api_listener_not_checked")
        self.assertEqual(result["status"], "degraded")

    def test_model_status_exception_is_redacted_and_fails_closed(self) -> None:
        class _FailingModel(_Model):
            def status(self) -> dict[str, object]:
                raise RuntimeError("secret-key https://private.invalid provider-body")

        with tempfile.TemporaryDirectory(prefix="assistant-readiness-model-status-") as directory:
            result = _readiness(
                _Repository(Path(directory), _source(), sqlite_rag=True),
                _FailingModel(False),
            )
            serialized = json.dumps(result)

        self.assertEqual(result["components"]["model"]["code"], "model_not_configured")
        self.assertNotIn("secret-key", serialized)
        self.assertNotIn("private.invalid", serialized)

    def test_http_probe_never_calls_model(self) -> None:
        class _NoNetworkModel(_Model):
            def chat(self, messages: object) -> str:
                raise AssertionError("readiness must not call the model")

        with tempfile.TemporaryDirectory(prefix="assistant-readiness-api-") as directory, patch.dict(
            "os.environ",
            {
                "KIMI_API_KEY": "",
                "KIMI_MODEL": "",
                "GITHUB_WEEKLY_SNAPSHOT_ROOT": "",
                "GITHUB_WEEKLY_DATA_MODE": "",
            },
            clear=False,
        ):
            app = create_app(root=Path(directory), db_path=Path(directory) / "data" / "assistant.sqlite")
            app.state.assistant.model_client = _NoNetworkModel(False)
            response = TestClient(app).get("/v1/assistant/readiness")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "unavailable")
        self.assertEqual(response.json()["components"]["api"]["status"], "ready")
        self.assertEqual(response.json()["components"]["api"]["code"], "api_process_ready")


if __name__ == "__main__":
    unittest.main()
