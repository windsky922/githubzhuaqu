from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.rag.answering import answer_rag_question, stream_rag_answer_question
from src.rag.freshness import archive_freshness


class _FakeClient:
    def __init__(self) -> None:
        self.calls = 0

    def status(self):
        return {"provider": "test", "configured": True, "model": "test", "base_url_configured": True, "timeout_seconds": 1, "max_retries": 0}

    def stream_chat(self, messages):
        self.calls += 1
        yield "unused"

    def chat(self, messages):
        self.calls += 1
        return "unused"


class RagFreshnessTest(unittest.TestCase):
    def write_run(self, root: Path, run_date: str, freshness: dict | None = None) -> None:
        directory = root / "data" / "runs"
        directory.mkdir(parents=True, exist_ok=True)
        payload = {"run_date": run_date}
        if freshness is not None:
            payload["rag_freshness"] = {
                "schema_version": 1,
                "source_hash": "source",
                "corpus_version": "corpus-v1",
                "corpus_hash": "corpus",
                "chunk_count": 1,
                "embedding_model": "local-hash-v1",
                "embedding_hash": "embedding",
                "embedding_count": 1,
                "dimensions": 64,
                **freshness,
            }
        (directory / f"{run_date}.json").write_text(json.dumps(payload), encoding="utf-8")

    def test_distinguishes_lagging_and_stale_layers(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_run(root, "2026-07-09", {"source_latest_date": "2026-07-09", "corpus_latest_date": "2026-07-09", "embedding_latest_date": "2026-07-09"})
            self.write_run(root, "2026-07-16")
            source_new = archive_freshness(root, as_of=date(2026, 7, 18))
            self.assertEqual(source_new["data_freshness"], "lagging")
            self.assertIn("corpus_behind_source", source_new["reasons"])

            self.write_run(root, "2026-07-16", {"source_latest_date": "2026-07-16", "corpus_latest_date": "2026-07-16", "embedding_latest_date": "2026-07-09"})
            embedding_old = archive_freshness(root, as_of=date(2026, 7, 18))
            self.assertEqual(embedding_old["data_freshness"], "lagging")
            self.assertIn("embedding_behind_corpus", embedding_old["reasons"])

    def test_missing_or_inconsistent_attestation_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_run(root, "2026-07-17")
            missing = archive_freshness(root, as_of="2026-07-18")
            self.assertEqual(missing["data_freshness"], "unknown")
            self.assertIn("missing_corpus_latest_date", missing["reasons"])

            (root / "data" / "runs" / "2026-07-16.json").write_text(json.dumps({"run_date": "2026-07-15"}), encoding="utf-8")
            inconsistent = archive_freshness(root, as_of="2026-07-18")
            self.assertEqual(inconsistent["data_freshness"], "unknown")
            self.assertIn("invalid_source_run", inconsistent["reasons"])

    def test_schema_less_or_partial_attestation_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_run(
                root,
                "2026-07-17",
                {
                    "schema_version": 0,
                    "source_hash": "",
                    "source_latest_date": "2026-07-17",
                    "corpus_latest_date": "2026-07-17",
                    "embedding_latest_date": "2026-07-17",
                },
            )
            result = archive_freshness(root, as_of="2026-07-18")
            self.assertEqual(result["data_freshness"], "unknown")
            self.assertIn("invalid_freshness_attestation", result["reasons"])

    def test_marks_aligned_old_data_stale_and_complete_data_fresh(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_run(root, "2026-07-01", {"source_latest_date": "2026-07-01", "corpus_latest_date": "2026-07-01", "embedding_latest_date": "2026-07-01"})
            stale = archive_freshness(root, as_of="2026-07-18")
            self.assertEqual(stale["data_freshness"], "stale")
            self.assertEqual(stale["stale_days"], 17)

            fresh_root = Path(temp) / "fresh"
            self.write_run(fresh_root, "2026-07-17", {"source_latest_date": "2026-07-17", "corpus_latest_date": "2026-07-17", "embedding_latest_date": "2026-07-17"})
            fresh = archive_freshness(fresh_root, as_of="2026-07-18")
            self.assertEqual(fresh["data_freshness"], "fresh")
            self.assertEqual(fresh["stale_days"], 1)

    def test_time_sensitive_lagging_request_never_calls_provider_or_emits_delta(self):
        client = _FakeClient()
        retrieval = {
            "query": "当前最新情况",
            "contexts": [{"chunk_id": "chunk:1", "metadata": {"full_name": "owner/agent", "run_date": "2026-07-09"}, "text": "agent workflow"}],
            "citations": [{"index": 1, "full_name": "owner/agent", "chunk_id": "chunk:1", "run_date": "2026-07-09"}],
            "prompt_context": "[1] owner/agent",
            "freshness": {"source_latest_date": "2026-07-16", "corpus_latest_date": "2026-07-09", "embedding_latest_date": "2026-07-09", "stale_days": 9, "data_freshness": "lagging", "as_of": "2026-07-18", "reasons": ["corpus_behind_source"]},
        }
        events = list(stream_rag_answer_question(root=Path.cwd(), query="当前最新情况", retrieval=retrieval, client=client))
        self.assertEqual([event["event"] for event in events], ["meta", "final"])
        self.assertEqual(client.calls, 0)
        final = events[-1]["data"]
        self.assertEqual(final["answer_mode"], "fallback_rule")
        self.assertFalse(final["answer_quality"]["passed"])
        self.assertEqual(final["answer_quality"]["data_freshness"], "lagging")
        self.assertIn("data_freshness:lagging", final["fallback_reason"])
        post = answer_rag_question(root=Path.cwd(), query="当前最新情况", retrieval=retrieval, client=client)
        self.assertEqual(client.calls, 0)
        self.assertEqual(post, final)


if __name__ == "__main__":
    unittest.main()
