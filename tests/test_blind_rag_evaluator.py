from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from scripts.evaluate_blind_rag import (
    BlindBaselineError,
    PROJECT_ROOT,
    build_judgment_template,
    evaluate_blind_cases,
    load_blind_cases,
    main,
    offline_snapshot_environment,
    run_baseline,
    snapshot_tree_sha256,
    validate_output_path,
)
from src.rag.freshness_attestation import refresh_rag_freshness


EVALUATION_DATE = "2026-01-02"


def _write_policy(root: Path, *, frozen_at: str = "2026-01-01T00:00:00+00:00") -> Path:
    path = root / "policy.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "blind_rag_acceptance_policy",
                "policy_id": "test-policy-v1",
                "status": "frozen",
                "frozen_at": frozen_at,
                "thresholds": {
                    "minimum_candidate_recall": 0.9,
                    "minimum_data_freshness_accuracy": 0.9,
                    "minimum_top_1_acceptance": 0.8,
                    "minimum_top_1_coverage": 0.5,
                    "minimum_route_accuracy": 0.9,
                    "minimum_answer_quality": 0.9,
                    "maximum_hard_constraint_violation": 0.0,
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def _case(identifier: str, query: str = "找 Agent 项目") -> dict:
    return {
        "schema_version": 2,
        "id": identifier,
        "evaluation_date": EVALUATION_DATE,
        "request": {"q": query},
        "expected": {
            "answer_mode": "fallback_rule",
            "freshness_required": False,
            "data_freshness": "fresh",
            "evidence_coverage": "high",
            "input_route": {
                "route": "new_search",
                "candidate_scope": "archive",
                "clarification_required": False,
                "selected_repository_ids": [],
                "requirements": [],
            },
            "acceptable_primary_ids": ["private/good"],
            "relevant_repository_ids": ["private/good"],
            "candidate_eligibility": {"private/good": "eligible"},
            "quality_passed": True,
        },
        "categories": ["source-freshness", "freshness-not-required", "sse"],
    }


def _full_pack_cases(count: int = 20) -> list[dict]:
    cases: list[dict] = []
    for index in range(count):
        case = _case(f"private-{index}", f"agent workflow automation {index}")
        case["expected"]["evidence_coverage"] = "medium"
        case["expected"]["acceptable_primary_ids"] = []
        case["expected"]["relevant_repository_ids"] = ["private/agent"]
        case["expected"]["candidate_eligibility"] = {"private/agent": "eligible"}
        case["categories"] = ["sse"]
        cases.append(case)

    cases[0]["request"]["q"] = "最新的 agent workflow automation"
    cases[0]["expected"]["freshness_required"] = True
    cases[0]["categories"] = [
        "source-freshness",
        "freshness-required",
        "unseen-readme",
        "multi-clause",
        "cross-chunk",
        "zh-negation",
        "en-negation",
        "capability-scope",
        "comparison",
        "explanation",
        "sse",
    ]
    cases[1]["categories"] = ["freshness-not-required"]

    cases[2]["request"]["q"] = "更适合 Python 的"
    cases[2]["expected"].update(
        {
            "answer_mode": "clarification",
            "freshness_required": None,
            "data_freshness": "not_applicable",
            "evidence_coverage": "low",
            "input_route": {
                "route": "clarify",
                "candidate_scope": "none",
                "clarification_required": True,
                "selected_repository_ids": [],
                "requirements": [{"field": "language", "operator": "eq", "value": "Python", "hard": False}],
            },
            "acceptable_primary_ids": [],
            "relevant_repository_ids": [],
            "candidate_eligibility": {},
        }
    )
    cases[2]["categories"] = ["clarification"]

    cases[3]["request"]["q"] = "找一个必须使用 Swift 且必须提供 Kubernetes 运维能力的项目"
    cases[3]["expected"].update(
        {
            "answer_mode": "no_match",
            "evidence_coverage": "low",
            "input_route": {
                "route": "new_search",
                "candidate_scope": "archive",
                "clarification_required": False,
                "selected_repository_ids": [],
                "requirements": [
                    {"field": "language", "operator": "eq", "value": "Swift", "hard": True},
                    {"field": "tech_stack", "operator": "eq", "value": "Kubernetes", "hard": True},
                ],
            },
            "candidate_eligibility": {"private/agent": "rejected"},
        }
    )
    cases[3]["categories"] = ["no-match", "rejected"]

    cases[4]["request"]["q"] = "找 Agent workflow automation 项目，必须使用 MIT 许可证"
    cases[4]["expected"].update(
        {
            "quality_passed": False,
            "input_route": {
                "route": "new_search",
                "candidate_scope": "archive",
                "clarification_required": False,
                "selected_repository_ids": [],
                "requirements": [{"field": "license", "operator": "eq", "value": "MIT", "hard": True}],
            },
            "candidate_eligibility": {"private/agent": "unknown"},
        }
    )
    cases[4]["categories"] = ["unknown"]
    return cases


class _FakeRepository:
    def __init__(
        self,
        *,
        final_decision_id: str = "stable-decision",
        recommendations: list[dict] | None = None,
        coverage_label: str = "high",
    ) -> None:
        self.final_decision_id = final_decision_id
        self.recommendations = recommendations
        self.coverage_label = coverage_label
        self.payloads: list[dict] = []

    def _response(self, decision_id: str = "stable-decision") -> dict:
        return {
            "decision_id": decision_id,
            "answer_mode": "fallback_rule",
            "freshness_required": False,
            "evidence_coverage": self.coverage_label,
            "freshness": {"data_freshness": "fresh"},
            "answer_quality": {"passed": True, "data_freshness": "fresh"},
            "recommendations": self.recommendations if self.recommendations is not None else [
                {
                    "full_name": "private/good",
                    "eligibility": "eligible",
                    "current_eligible": True,
                    "requirement_evaluations": [],
                }
            ],
            "input_route": {
                "route": "new_search",
                "candidate_scope": "archive",
                "selected_repository_ids": [],
                "requirements": [],
            },
        }

    def rag_ask_contextual(self, payload: dict, *, router_client=None) -> dict:
        self.payloads.append(payload)
        return self._response()

    def rag_ask_contextual_stream(self, payload: dict, *, router_client=None):
        self.payloads.append(payload)
        yield {"event": "meta", "data": {"query": payload["q"]}}
        yield {"event": "final", "data": self._response(self.final_decision_id)}


class BlindRagEvaluatorTest(unittest.TestCase):
    def test_runner_controls_mode_model_limit_and_auto_build(self):
        repository = _FakeRepository()
        case = _case("runner-controls")
        case["request"].update({"mode": "fts5", "model": "private", "limit": 99, "auto_build": False})
        evaluate_blind_cases(repository, [case])  # type: ignore[arg-type]
        self.assertEqual(len(repository.payloads), 2)
        for payload in repository.payloads:
            self.assertEqual(
                {key: payload[key] for key in ("mode", "model", "limit", "auto_build")},
                {"mode": "hybrid", "model": "local-hash-v1", "limit": 3, "auto_build": True},
            )

    def test_full_chain_aggregates_do_not_leak_queries_labels_or_ids(self):
        cases = [_case("secret-case-1", "秘密需求甲"), _case("secret-case-2", "秘密需求乙")]
        report = evaluate_blind_cases(_FakeRepository(), cases)  # type: ignore[arg-type]
        self.assertEqual(report["case_count"], 2)
        self.assertEqual(report["metrics"]["primary_accuracy"], 1.0)
        self.assertEqual(report["metrics"]["recall_at_3"], 1.0)
        self.assertEqual(report["metrics"]["candidate_eligibility_accuracy"], 1.0)
        self.assertEqual(report["metrics"]["hard_constraint_violation_rate"], 0.0)
        self.assertEqual(report["metrics"]["sse_final_parity_rate"], 1.0)
        self.assertEqual(report["metrics"]["stream_contract_rate"], 1.0)
        rendered = json.dumps(report, ensure_ascii=False)
        for secret in ("秘密需求甲", "秘密需求乙", "secret-case-1", "secret-case-2", "private/good"):
            self.assertNotIn(secret, rendered)

    def test_hard_constraint_violation_uses_private_eligibility_label(self):
        case = _case("rejected-primary")
        case["expected"]["candidate_eligibility"] = {"private/good": "rejected"}
        report = evaluate_blind_cases(_FakeRepository(), [case])  # type: ignore[arg-type]
        self.assertEqual(report["metrics"]["hard_constraint_violation_rate"], 1.0)
        self.assertEqual(report["metrics"]["candidate_eligibility_accuracy"], 0.0)
        self.assertEqual(report["failure_category_counts"]["hard_constraint_violation"], 1)

    def test_missing_candidate_label_and_partial_recall_are_counted(self):
        case = _case("partial-recall")
        case["expected"]["relevant_repository_ids"] = ["private/good", "private/missing"]
        case["expected"]["candidate_eligibility"] = {
            "private/good": "eligible",
            "private/missing": "rejected",
        }
        report = evaluate_blind_cases(_FakeRepository(), [case])  # type: ignore[arg-type]
        self.assertEqual(report["metrics"]["recall_at_3"], 0.5)
        self.assertEqual(report["metrics"]["candidate_eligibility_accuracy"], 0.5)
        self.assertEqual(report["failure_category_counts"]["candidate_eligibility"], 1)

    def test_route_freshness_and_full_sse_final_are_scored(self):
        case = _case("contract-drift")
        case["expected"]["data_freshness"] = "stale"
        case["expected"]["input_route"]["route"] = "clarify"
        repository = _FakeRepository(final_decision_id="different-decision")
        report = evaluate_blind_cases(repository, [case])  # type: ignore[arg-type]
        self.assertEqual(report["metrics"]["data_freshness_exact_rate"], 0.0)
        self.assertEqual(report["metrics"]["input_route_exact_rate"], 0.0)
        self.assertEqual(report["metrics"]["sse_final_parity_rate"], 0.0)

    def test_untrusted_coverage_value_is_collapsed_to_fixed_unknown_bucket(self):
        case = _case("coverage-privacy")
        case["expected"]["evidence_coverage"] = "unknown"
        report = evaluate_blind_cases(_FakeRepository(coverage_label="private-value"), [case])  # type: ignore[arg-type]
        self.assertEqual(set(report["coverage_buckets"]), {"unknown"})
        self.assertNotIn("private-value", json.dumps(report))

    def test_pack_must_be_private_schema_v2_unique_and_large_enough(self):
        with tempfile.TemporaryDirectory() as directory:
            pack = Path(directory) / "blind.jsonl"
            valid_cases = _full_pack_cases()
            pack.write_text("\n".join(json.dumps(case, ensure_ascii=False) for case in valid_cases), encoding="utf-8")
            self.assertEqual(len(load_blind_cases(pack)), 20)

            pack.write_text(json.dumps(_case("one"), ensure_ascii=False) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "insufficient_cases"):
                load_blind_cases(pack)

            duplicate_id = _full_pack_cases()
            duplicate_id[1]["id"] = duplicate_id[0]["id"]
            pack.write_text("\n".join(json.dumps(case, ensure_ascii=False) for case in duplicate_id), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate_id"):
                load_blind_cases(pack)

            duplicate_query = _full_pack_cases()
            duplicate_query[0]["request"]["q"] = "  Same QUERY "
            duplicate_query[1]["request"]["q"] = "same   query"
            pack.write_text("\n".join(json.dumps(case, ensure_ascii=False) for case in duplicate_query), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate_query"):
                load_blind_cases(pack)
        with self.assertRaisesRegex(ValueError, "outside_repository"):
            load_blind_cases(PROJECT_ROOT / "evals" / "project_match_cases.jsonl", minimum_cases=1)

    def test_pack_requires_fixed_date_and_category_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            pack = Path(directory) / "blind.jsonl"
            cases = _full_pack_cases()
            cases[1]["evaluation_date"] = "2026-01-03"
            pack.write_text("\n".join(json.dumps(case) for case in cases), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "evaluation_date_mismatch"):
                load_blind_cases(pack, minimum_cases=1)

            cases = [_case("one", "query one")]
            pack.write_text(json.dumps(cases[0]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "category_coverage_incomplete"):
                load_blind_cases(pack, minimum_cases=1)

    def test_pack_rejects_runner_controlled_request_fields_and_duplicate_categories(self):
        with tempfile.TemporaryDirectory() as directory:
            pack = Path(directory) / "blind.jsonl"
            cases = _full_pack_cases()
            cases[0]["request"]["model"] = "private-override"
            pack.write_text("\n".join(json.dumps(case) for case in cases), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "request_fields_invalid"):
                load_blind_cases(pack)

            cases = _full_pack_cases()
            cases[0]["categories"].append(cases[0]["categories"][0])
            pack.write_text("\n".join(json.dumps(case) for case in cases), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "categories_invalid"):
                load_blind_cases(pack)

    def test_pack_requires_recall_and_answer_quality_denominators(self):
        with tempfile.TemporaryDirectory() as directory:
            pack = Path(directory) / "blind.jsonl"
            cases = _full_pack_cases()
            for case in cases:
                case["expected"]["relevant_repository_ids"] = []
            pack.write_text("\n".join(json.dumps(case) for case in cases), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "recall_labels_missing"):
                load_blind_cases(pack)

            cases = _full_pack_cases()
            for case in cases:
                case["expected"].pop("quality_passed", None)
            pack.write_text("\n".join(json.dumps(case) for case in cases), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "answer_quality_labels_missing"):
                load_blind_cases(pack)

            mutations = (
                ("recall_labels_missing", lambda case: case["expected"].__setitem__("relevant_repository_ids", [])),
                ("eligibility_labels_missing", lambda case: case["expected"].__setitem__("candidate_eligibility", {})),
                ("answer_quality_labels_missing", lambda case: case["expected"].pop("quality_passed", None)),
            )
            for code, mutate in mutations:
                cases = _full_pack_cases()
                for index, case in enumerate(cases):
                    if index not in {0, 1, 3, 4}:
                        mutate(case)
                pack.write_text("\n".join(json.dumps(case) for case in cases), encoding="utf-8")
                with self.subTest(code=code), self.assertRaisesRegex(ValueError, code):
                    load_blind_cases(pack)

    def test_baseline_cohort_must_match_source_freshness_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            pack = Path(directory) / "blind.jsonl"
            pack.write_text(
                "\n".join(json.dumps(case) for case in _full_pack_cases()),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "cohort_freshness_mismatch"):
                run_baseline(
                    pack=pack,
                    snapshot_root=Path(directory) / "missing",
                    cohort="stale",
                    policy=_write_policy(Path(directory)),
                )

    def test_runner_requires_policy_precommit_and_unchanged_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pack = root / "blind.jsonl"
            pack.write_text("\n".join(json.dumps(case) for case in _full_pack_cases()), encoding="utf-8")
            snapshot = root / "snapshot"
            (snapshot / "data" / "runs").mkdir(parents=True)
            (snapshot / "data" / "runs" / "frozen.json").write_text("{}", encoding="utf-8")

            future_policy = _write_policy(root, frozen_at="2999-01-01T00:00:00+00:00")
            with self.assertRaisesRegex(ValueError, "policy_not_precommitted"):
                run_baseline(pack=pack, snapshot_root=snapshot, cohort="fresh", policy=future_policy)

            policy = _write_policy(root)

            def mutate_policy(repository, loaded_cases, *, model_client=None):
                policy.write_text(policy.read_text(encoding="utf-8") + "\n", encoding="utf-8")
                return evaluate_blind_cases(_FakeRepository(), loaded_cases)

            with patch("scripts.evaluate_blind_rag.ApiRepository", return_value=_FakeRepository()), patch(
                "scripts.evaluate_blind_rag.evaluate_blind_cases", side_effect=mutate_policy
            ):
                with self.assertRaisesRegex(ValueError, "policy_mutated"):
                    run_baseline(pack=pack, snapshot_root=snapshot, cohort="fresh", policy=policy)

            policy = _write_policy(root)
            with patch("scripts.evaluate_blind_rag.ApiRepository", return_value=_FakeRepository()), patch(
                "scripts.evaluate_blind_rag._execution_manifest_sha256", side_effect=["a" * 64, "b" * 64]
            ):
                with self.assertRaisesRegex(ValueError, "execution_manifest_mutated"):
                    run_baseline(pack=pack, snapshot_root=snapshot, cohort="fresh", policy=policy)

    def test_pack_rejects_category_and_primary_label_mismatches(self):
        with tempfile.TemporaryDirectory() as directory:
            pack = Path(directory) / "blind.jsonl"
            cases = _full_pack_cases()
            cases[1]["categories"] = ["freshness-required"]
            pack.write_text("\n".join(json.dumps(case) for case in cases), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "category_contract_invalid"):
                load_blind_cases(pack)

            cases = _full_pack_cases()
            cases[1]["expected"]["acceptable_primary_ids"] = ["private/agent"]
            cases[1]["expected"]["candidate_eligibility"] = {"private/agent": "rejected"}
            pack.write_text("\n".join(json.dumps(case) for case in cases), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "primary_labels_inconsistent"):
                load_blind_cases(pack)

    def test_snapshot_hash_binds_fact_json_and_ignores_runtime_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            facts = root / "data" / "runs" / "2026-01-01.json"
            facts.parent.mkdir(parents=True)
            facts.write_text('{"status":"one"}', encoding="utf-8")
            first = snapshot_tree_sha256(root)

            runtime = root / "data" / "runs" / "runtime.sqlite"
            runtime.write_bytes(b"not part of frozen snapshot")
            self.assertEqual(first, snapshot_tree_sha256(root))
            facts.write_text('{"status":"two"}', encoding="utf-8")
            self.assertNotEqual(first, snapshot_tree_sha256(root))

    def test_output_cannot_overwrite_inputs_snapshot_or_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pack = root / "blind.jsonl"
            pack.write_text("private", encoding="utf-8")
            snapshot = root / "snapshot"
            (snapshot / "data" / "runs").mkdir(parents=True)
            (snapshot / "data" / "runs" / "frozen.json").write_text("{}", encoding="utf-8")
            safe = root / "baseline.json"
            self.assertEqual(validate_output_path(safe, pack=pack, snapshot_root=snapshot), safe.resolve())
            with self.assertRaisesRegex(ValueError, "conflicts_with_pack"):
                validate_output_path(pack, pack=pack, snapshot_root=snapshot)
            with self.assertRaisesRegex(ValueError, "inside_snapshot"):
                validate_output_path(snapshot / "data" / "runs" / "baseline.json", pack=pack, snapshot_root=snapshot)
            with self.assertRaisesRegex(ValueError, "outside_repository"):
                validate_output_path(PROJECT_ROOT / "output" / "blind.json", pack=pack, snapshot_root=snapshot)

    def test_main_redacts_untrusted_value_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pack = root / "blind.jsonl"
            pack.write_text("private", encoding="utf-8")
            snapshot = root / "snapshot"
            output = root / "baseline.json"
            policy = _write_policy(root)
            with patch.object(
                sys,
                "argv",
                [
                    "evaluate_blind_rag.py",
                    "--blind-pack",
                    str(pack),
                    "--snapshot-root",
                    str(snapshot),
                    "--cohort",
                    "fresh",
                    "--policy",
                    str(policy),
                    "--output",
                    str(output),
                ],
            ), patch("scripts.evaluate_blind_rag.run_baseline", side_effect=ValueError("秘密需求 C:/private/path")):
                with self.assertRaises(SystemExit) as caught:
                    main()
            self.assertEqual(str(caught.exception), "blind_baseline_runtime_error")
            self.assertNotIn("秘密需求", str(caught.exception))

    def test_main_removes_partial_baseline_when_judgment_output_conflicts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pack = root / "blind.jsonl"
            snapshot = root / "snapshot"
            policy = root / "policy.json"
            output = root / "baseline.json"
            judgment = root / "judgments.json"
            for path in (pack, policy):
                path.write_text("{}", encoding="utf-8")
            snapshot.mkdir()
            judgment.write_text("existing", encoding="utf-8")
            argv = [
                "evaluate_blind_rag.py", "--blind-pack", str(pack), "--snapshot-root", str(snapshot),
                "--cohort", "fresh", "--policy", str(policy), "--output", str(output),
                "--judgment-template", str(judgment),
            ]
            with patch.object(sys, "argv", argv), patch(
                "scripts.evaluate_blind_rag.run_baseline", return_value={"report": True}
            ), patch(
                "scripts.evaluate_blind_rag.build_judgment_template", return_value={"template": True}
            ):
                with self.assertRaisesRegex(SystemExit, "blind_baseline_io_error"):
                    main()
            self.assertFalse(output.exists())
            self.assertEqual(judgment.read_text(encoding="utf-8"), "existing")

    def test_offline_environment_blocks_socket_connection_variants(self):
        with tempfile.TemporaryDirectory() as directory:
            sock = socket.socket()
            try:
                with offline_snapshot_environment(Path(directory), date.fromisoformat(EVALUATION_DATE)):
                    calls = [
                        (sock.connect, (("127.0.0.1", 9),)),
                        (sock.connect_ex, (("127.0.0.1", 9),)),
                        (sock.sendto, (b"x", ("127.0.0.1", 9))),
                        (socket.create_connection, (("127.0.0.1", 9),)),
                        (socket.getaddrinfo, ("localhost", 9)),
                    ]
                    if hasattr(sock, "sendmsg"):
                        calls.append((sock.sendmsg, ([b"x"],)))
                    for call, arguments in calls:
                        with self.subTest(call=call.__name__), self.assertRaisesRegex(
                            BlindBaselineError, "blind_network_disabled"
                        ):
                            call(*arguments)
            finally:
                sock.close()

    def test_pack_mutation_during_run_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "snapshot"
            (snapshot / "data" / "runs").mkdir(parents=True)
            (snapshot / "data" / "runs" / "frozen.json").write_text("{}", encoding="utf-8")
            pack = root / "blind.jsonl"
            cases = [json.dumps(case) for case in _full_pack_cases()]
            pack.write_text("\n".join(cases) + "\n", encoding="utf-8")

            def mutate_then_evaluate(repository, loaded_cases, *, model_client=None):
                pack.write_text(pack.read_text(encoding="utf-8") + "\n", encoding="utf-8")
                return evaluate_blind_cases(_FakeRepository(), loaded_cases)

            with patch("scripts.evaluate_blind_rag.ApiRepository", return_value=_FakeRepository()), patch(
                "scripts.evaluate_blind_rag.evaluate_blind_cases", side_effect=mutate_then_evaluate
            ):
                with self.assertRaisesRegex(ValueError, "pack_mutated"):
                    run_baseline(pack=pack, snapshot_root=snapshot, cohort="fresh", policy=_write_policy(root))

    def test_run_baseline_uses_frozen_weekly_post_and_stream_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            private_root = Path(directory)
            snapshot = private_root / "snapshot"
            run_date = "2026-01-01"
            for name in ("runs", "raw", "selected"):
                (snapshot / "data" / name).mkdir(parents=True, exist_ok=True)
            (snapshot / "data" / "runs" / f"{run_date}.json").write_text(
                json.dumps({"run_date": run_date, "status": "success"}), encoding="utf-8"
            )
            (snapshot / "data" / "raw" / f"{run_date}.json").write_text("[]", encoding="utf-8")
            (snapshot / "data" / "selected" / f"{run_date}.json").write_text(
                json.dumps(
                    [
                        {
                            "full_name": "private/agent",
                            "html_url": "https://github.com/private/agent",
                            "description": "agent workflow automation",
                            "language": "Python",
                            "category": "AI Agent",
                            "sources": ["github_search"],
                            "selection_reasons": ["agent workflow"],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            refresh_rag_freshness(
                root=snapshot,
                db_path=private_root / "attestation.sqlite",
                run_date=run_date,
            )
            before_hash = snapshot_tree_sha256(snapshot)

            pack = private_root / "blind.jsonl"
            cases = [json.dumps(case, ensure_ascii=False) for case in _full_pack_cases()]
            pack.write_text("\n".join(cases) + "\n", encoding="utf-8")

            with patch.dict(os.environ, {"KIMI_API_KEY": "must-not-be-used"}):
                subjects: list[dict] = []
                report = run_baseline(
                    pack=pack,
                    snapshot_root=snapshot,
                    cohort="fresh",
                    policy=_write_policy(private_root),
                    subject_collector=subjects,
                )

            self.assertEqual(report["kind"], "blind_rag_full_chain_baseline")
            self.assertEqual(report["schema_version"], 4)
            self.assertEqual(report["cohort"], "fresh")
            self.assertEqual(report["case_count"], 20)
            self.assertEqual(report["evaluation_date"], EVALUATION_DATE)
            self.assertEqual(len(report["policy_sha256"]), 64)
            self.assertIn("+00:00", report["baseline_started_at"])
            self.assertEqual(report["metrics"]["primary_accuracy"], 1.0)
            self.assertEqual(report["metrics"]["recall_at_3"], 1.0)
            self.assertEqual(report["metrics"]["candidate_eligibility_accuracy"], 1.0)
            self.assertEqual(report["metrics"]["freshness_required_exact_rate"], 1.0)
            self.assertEqual(report["metrics"]["data_freshness_exact_rate"], 1.0)
            self.assertEqual(report["metrics"]["evidence_coverage_exact_rate"], 1.0)
            self.assertEqual(report["metrics"]["input_route_exact_rate"], 1.0)
            self.assertEqual(report["metrics"]["quality_gate_accuracy"], 1.0)
            self.assertEqual(report["metrics"]["sse_final_parity_rate"], 1.0)
            self.assertEqual(report["metrics"]["stream_contract_rate"], 1.0)
            self.assertEqual(report["metrics"]["top_1_coverage_rate"], 0.0)
            self.assertEqual(report["top_1_subject_count"], 20)
            self.assertEqual(report["top_1_emitted_count"], 0)
            self.assertEqual(len(report["runner_sha256"]), 64)
            self.assertEqual(report["metric_denominators"]["recall_at_3"], 19)
            self.assertEqual(report["metric_denominators"]["candidate_eligibility_accuracy"], 19)
            self.assertEqual(report["metric_numerators"]["recall_at_3"], 19.0)
            self.assertEqual(report["metric_numerators"]["hard_constraint_violation_rate"], 0)
            self.assertEqual(report["metric_numerators"]["top_1_coverage_rate"], 0)
            self.assertEqual(report["failure_category_counts"], {})
            template = build_judgment_template(report, subjects)
            self.assertEqual(template["status"], "draft")
            self.assertEqual(template["reviewer_count"], 0)
            self.assertTrue(all(item["judgment"] == "pending" for item in template["subjects"]))
            self.assertEqual(snapshot_tree_sha256(snapshot), before_hash)
            self.assertIsNone(report["threshold"])


if __name__ == "__main__":
    unittest.main()
