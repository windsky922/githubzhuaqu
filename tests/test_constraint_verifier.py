import json
import tempfile
import unittest
from pathlib import Path

from scripts.evaluate_project_match import write_fixture
from src.api.repository import ApiRepository
from src.rag.constraint_verifier import classify_text_evidence, verify_project_requirements
from src.storage.sqlite_store import connect


class ConstraintVerifierTest(unittest.TestCase):
    def test_uses_canonical_metadata_and_non_model_clean_chunks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root)
            repository = ApiRepository(root=root, db_path=root / "data" / "github_weekly.sqlite")
            repository.ensure_sqlite_index()
            connection = connect(repository.db_path)
            try:
                connection.execute(
                    "UPDATE repositories SET license_name=?, payload_json=? WHERE full_name=?",
                    ("MIT License", json.dumps({"topics": ["Docker", "agents"]}), "eval/agent-orchestrator"),
                )
                chunk = connection.execute(
                    "SELECT * FROM rag_chunks WHERE full_name=? ORDER BY chunk_index LIMIT 1",
                    ("eval/agent-orchestrator",),
                ).fetchone()
                connection.execute(
                    "UPDATE rag_chunks SET chunk_text=?, source_type='readme' WHERE chunk_id=?",
                    ("支持 self-hosted 本地部署，并提供免费使用版本。", chunk["chunk_id"]),
                )
                connection.execute(
                    """INSERT INTO rag_chunks(
                         chunk_id,corpus_id,chunk_index,run_date,full_name,html_url,language,category,sources_json,
                         chunk_text,token_estimate,corpus_version,cleaner_version,content_hash,is_untrusted,source_type,payload_json
                       ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        "model-only", chunk["corpus_id"], 999, chunk["run_date"], chunk["full_name"], chunk["html_url"],
                        chunk["language"], chunk["category"], chunk["sources_json"], "仅云端 SaaS，必须购买付费版本。",
                        10, chunk["corpus_version"], chunk["cleaner_version"], "model-only", 1, "model_enrichment", "{}",
                    ),
                )
                connection.commit()
            finally:
                connection.close()
            result = verify_project_requirements(
                repository.db_path,
                ["eval/agent-orchestrator"],
                [
                    _requirement("language", "Python"),
                    _requirement("license", "MIT"),
                    _requirement("tech_stack", "Docker"),
                    _requirement("deployment", "local"),
                    _requirement("cost", "free"),
                ],
            )["eval/agent-orchestrator"]
        self.assertEqual(result["unmet_requirements"], [])
        self.assertEqual(result["unknown_requirements"], [])
        self.assertIn("语言=Python", result["matched_requirements"])
        self.assertIn("许可证=MIT", result["matched_requirements"])
        self.assertIn("技术栈=Docker", result["matched_requirements"])
        self.assertIn("部署方式=local", result["matched_requirements"])
        self.assertIn("成本=free", result["matched_requirements"])
        self.assertNotIn("model-only", result["evidence_chunk_ids"])

    def test_unknown_when_no_deterministic_evidence_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root)
            repository = ApiRepository(root=root, db_path=root / "data" / "github_weekly.sqlite")
            repository.ensure_sqlite_index()
            result = verify_project_requirements(
                repository.db_path,
                ["eval/rag-platform"],
                [_requirement("cost", "paid")],
            )["eval/rag-platform"]
        self.assertEqual(result["unknown_requirements"], ["成本=paid"])

    def test_contains_operator_uses_deterministic_topics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root)
            repository = ApiRepository(root=root, db_path=root / "data" / "github_weekly.sqlite")
            repository.ensure_sqlite_index()
            connection = connect(repository.db_path)
            try:
                connection.execute(
                    "UPDATE repositories SET payload_json=? WHERE full_name=?",
                    (json.dumps({"topics": ["FastAPI"]}), "eval/agent-orchestrator"),
                )
                connection.commit()
            finally:
                connection.close()
            result = verify_project_requirements(
                repository.db_path,
                ["eval/agent-orchestrator"],
                [_requirement("tech_stack", "Fast", operator="contains")],
            )["eval/agent-orchestrator"]
        self.assertEqual(result["matched_requirements"], ["技术栈包含Fast"])

    def test_external_inference_rejects_local_and_offline_requirements(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root)
            repository = ApiRepository(root=root, db_path=root / "data" / "github_weekly.sqlite")
            repository.ensure_sqlite_index()
            connection = connect(repository.db_path)
            try:
                connection.execute(
                    "UPDATE rag_chunks SET chunk_text=?, source_type='readme' WHERE full_name=?",
                    ("支持 self-hosted UI，但推理依赖托管推理并且必须联网。", "eval/agent-orchestrator"),
                )
                connection.commit()
            finally:
                connection.close()
            result = verify_project_requirements(
                repository.db_path,
                ["eval/agent-orchestrator"],
                [_requirement("deployment", "local"), _requirement("deployment", "offline")],
            )["eval/agent-orchestrator"]
        self.assertEqual(result["matched_requirements"], [])
        self.assertEqual(result["unmet_requirements"], ["部署方式=local", "部署方式=offline"])


class TextEvidenceClassifierTest(unittest.TestCase):
    def test_distinguishes_support_conflict_and_uncertainty(self):
        cases = [
            ("deployment", "offline", "可完全离线运行，无需联网。", "supports"),
            ("deployment", "offline", "This project does not support offline mode.", "contradicts"),
            ("deployment", "offline", "The UI is self-hosted but uses hosted inference.", "external_dependency"),
            ("deployment", "offline", "Offline mode is available only if an extra package is installed.", "conditional"),
            ("deployment", "local", "支持私有化部署。", "supports"),
            ("cost", "free", "提供 14 天免费试用。", "trial_only"),
            ("cost", "free", "Requires a paid plan.", "contradicts"),
            ("cost", "free", "社区版完全免费。", "supports"),
            ("cost", "free", "价格请咨询销售。", "unknown"),
        ]
        for field, value, sentence, expected in cases:
            with self.subTest(sentence=sentence):
                self.assertEqual(classify_text_evidence(field, value, sentence), expected)


def _requirement(field, value, operator="eq"):
    return {"field": field, "operator": operator, "value": value, "hard": True}


if __name__ == "__main__":
    unittest.main()
