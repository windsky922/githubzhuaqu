from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.api.repository import ApiRepository
from src.rag.data_source import resolve_verified_weekly_source
from src.rag.freshness import is_time_sensitive_query


def _write_verified_run(root: Path, run_date: str = "2026-07-22") -> None:
    run_dir = root / "data" / "runs"
    run_dir.mkdir(parents=True)
    attestation = {
        "schema_version": 1,
        "source_latest_date": run_date,
        "corpus_latest_date": run_date,
        "embedding_latest_date": run_date,
        "source_hash": "source", "corpus_version": "v1", "corpus_hash": "corpus",
        "embedding_model": "test", "embedding_hash": "embedding", "chunk_count": 1,
        "embedding_count": 1, "dimensions": 1,
    }
    (run_dir / f"{run_date}.json").write_text(json.dumps({"run_date": run_date, "rag_freshness": attestation}), encoding="utf-8")


class P1DataTrustTest(unittest.TestCase):
    def test_explicit_verified_snapshot_has_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_verified_run(root)
            source = resolve_verified_weekly_source(app_root=root, explicit_root=root)
            self.assertTrue(source["available"])
            self.assertEqual(source["kind"], "explicit_local")
            self.assertEqual(source["run_date"], "2026-07-22")

    def test_missing_attestation_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            source = resolve_verified_weekly_source(app_root=Path(temp), explicit_root=Path(temp))
            self.assertFalse(source["available"])
            self.assertEqual(source["kind"], "unknown")

    def test_freshness_requirement_markers(self):
        self.assertTrue(is_time_sensitive_query("本周最新的项目"))
        self.assertTrue(is_time_sensitive_query("current project"))
        self.assertFalse(is_time_sensitive_query("解释 RAG 的工作方式"))

    def test_query_feedback_is_server_bound_and_redacted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_verified_run(root)
            repository = ApiRepository(root=root, db_path=root / "private.sqlite")
            decision_id = repository._record_query_decision({
                "query": "  find  a  project ", "freshness": {"data_freshness": "fresh"},
                "freshness_required": True, "answer_mode": "fallback_rule",
                "answer_quality": {"passed": True},
                "recommendations": [{"rank": 1, "full_name": "owner/repo", "eligibility": "eligible", "citation_indexes": [1]}],
            })
            result = repository.create_query_feedback({"decision_id": decision_id, "rating": 1, "note": "token" + "=secret-value"})
            self.assertTrue(result["accepted"])
            self.assertIn("[REDACTED]", result["feedback"]["note"])
            stored = repository.query_feedback(decision_id=decision_id)
            self.assertEqual(stored["count"], 1)
            self.assertEqual(stored["feedback"][0]["query"], "find a project")
            self.assertFalse(repository.create_query_feedback({"decision_id": "0" * 32, "rating": 1})["accepted"])

    def test_explicit_local_mode_uses_history_without_reclassifying_it_as_weekly_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            selected = root / "data" / "selected"
            selected.mkdir(parents=True)
            (selected / "2026-06-03.json").write_text(json.dumps([{
                "full_name": "owner/local-agent", "description": "local agent workflow", "language": "Python",
            }]), encoding="utf-8")
            with patch("src.api.repository.ROOT", root), patch.dict("os.environ", {"GITHUB_WEEKLY_DATA_MODE": "local"}, clear=False):
                repository = ApiRepository(root=root)
                answer = repository.rag_ask(query="当前 local agent 项目", mode="fts5")
            self.assertEqual(repository.data_source["kind"], "local_archive_json")
            self.assertTrue(repository.local_read_only)
            self.assertTrue(answer["data_source"]["history_only"])
            self.assertIn("无法确认当前状态", answer["answer"])
            self.assertEqual(answer["recommendations"][0]["source_kind"], "local_archive_json")
            self.assertFalse(answer["recommendations"][0]["current_eligible"])
