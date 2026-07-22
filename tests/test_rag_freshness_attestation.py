from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from src.rag.freshness import archive_freshness
from src.rag.freshness_attestation import finalize_attestation, refresh_rag_freshness


class RagFreshnessAttestationTest(unittest.TestCase):
    run_date = "2026-07-20"

    def make_source(self, root: Path, *, status: str = "success") -> Path:
        for directory in ("runs", "raw", "selected"):
            (root / "data" / directory).mkdir(parents=True, exist_ok=True)
        run_path = root / "data" / "runs" / f"{self.run_date}.json"
        run_path.write_text(json.dumps({"run_date": self.run_date, "status": status, "private": "keep-local"}), encoding="utf-8")
        (root / "data" / "raw" / f"{self.run_date}.json").write_text("[]", encoding="utf-8")
        (root / "data" / "selected" / f"{self.run_date}.json").write_text(
            json.dumps([{"full_name": "owner/agent", "html_url": "https://github.com/owner/agent", "description": "agent workflow"}]),
            encoding="utf-8",
        )
        return run_path

    def test_complete_refresh_is_atomic_and_makes_current_run_fresh(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_path = self.make_source(root)
            attestation = refresh_rag_freshness(root=root, db_path=root / "data" / "derived.sqlite", run_date=self.run_date)

            payload = json.loads(run_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["private"], "keep-local")
            self.assertEqual(payload["rag_freshness"], attestation)
            self.assertEqual(attestation["source_latest_date"], self.run_date)
            self.assertEqual(attestation["corpus_latest_date"], self.run_date)
            self.assertEqual(attestation["embedding_latest_date"], self.run_date)
            self.assertTrue(attestation["source_hash"])
            self.assertTrue(attestation["corpus_hash"])
            self.assertTrue(attestation["embedding_hash"])
            self.assertGreater(attestation["chunk_count"], 0)
            self.assertEqual(archive_freshness(root, as_of=date(2026, 7, 21))["data_freshness"], "fresh")

    def test_partial_failure_never_writes_an_attestation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_path = self.make_source(root)
            original = run_path.read_text(encoding="utf-8")
            with patch("src.rag.freshness_attestation.embedding_ready", side_effect=RuntimeError("embedding failed")):
                with self.assertRaisesRegex(RuntimeError, "embedding failed"):
                    refresh_rag_freshness(root=root, db_path=root / "data" / "derived.sqlite", run_date=self.run_date)
            self.assertEqual(run_path.read_text(encoding="utf-8"), original)
            self.assertNotIn("rag_freshness", json.loads(original))

    def test_finalize_rejects_mismatched_or_incomplete_stages_without_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_path = self.make_source(root)
            original = run_path.read_text(encoding="utf-8")
            source = {"run_date": self.run_date, "source_hash": "source"}
            corpus = {"run_date": self.run_date, "corpus_version": "v1", "corpus_hash": "corpus"}
            bad_embedding = {"run_date": "2026-07-19", "embedding_model": "model", "embedding_hash": "embedding"}
            with self.assertRaisesRegex(ValueError, "must match"):
                finalize_attestation(root=root, run_date=self.run_date, source=source, corpus=corpus, embedding=bad_embedding)
            self.assertEqual(run_path.read_text(encoding="utf-8"), original)
