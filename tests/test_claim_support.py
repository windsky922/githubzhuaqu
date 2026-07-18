from __future__ import annotations

import unittest

from src.rag.claim_support import compare_facts
from src.rag.answer_quality import validate_rag_answer


def _fact(**overrides):
    fact = {
        "subject": "owner/agent",
        "component": "inference",
        "phase": "runtime",
        "predicate": "network_required",
        "value": True,
        "modality": "required",
        "edition": "all editions",
        "condition": None,
        "temporal": None,
        "quantity": None,
    }
    fact.update(overrides)
    return fact


QUOTE = "The inference runtime requires network access for all editions."


class ClaimSupportTest(unittest.TestCase):
    def test_exact_structured_fact_is_supported(self):
        result = compare_facts(claim=_fact(), evidence=_fact(), quote=QUOTE)
        self.assertEqual(result["polarity_status"], "matched")
        self.assertEqual(result["scope_status"], "matched")
        self.assertEqual(result["semantic_support_status"], "supported")

    def test_predicate_component_phase_modality_edition_condition_and_quantity_mismatch_fail_closed(self):
        cases = {
            "predicate": _fact(predicate="offline_capable"),
            "component": _fact(component="ui"),
            "phase": _fact(phase="setup"),
            "modality": _fact(modality="optional"),
            "edition": _fact(edition="free tier"),
            "condition": _fact(condition="when cached"),
            "temporal": _fact(temporal="2026"),
            "quantity": _fact(quantity=2),
        }
        for field, claim in cases.items():
            with self.subTest(field=field):
                result = compare_facts(claim=claim, evidence=_fact(), quote=QUOTE)
                self.assertNotEqual(result["semantic_support_status"], "supported")
                self.assertTrue(result["reason"].startswith(field))

    def test_polarity_and_unanchored_evidence_fail_closed(self):
        contradicted = compare_facts(claim=_fact(value=False), evidence=_fact(), quote=QUOTE)
        self.assertEqual(contradicted["polarity_status"], "contradicted")
        unanchored = compare_facts(claim=_fact(), evidence=_fact(component="engine"), quote=QUOTE)
        self.assertEqual(unanchored["semantic_support_status"], "insufficient")
        self.assertEqual(unanchored["reason"], "unanchored_component")

    def test_answer_quality_requires_registered_and_semantically_supported_facts(self):
        context = {
            "chunk_id": "chunk:1",
            "text": QUOTE,
            "metadata": {"full_name": "owner/agent"},
        }
        citation = [{"index": 1, "full_name": "owner/agent", "chunk_id": "chunk:1"}]
        fact = _fact()
        ledger = {
            "schema_version": 2,
            "claims": [{
                "id": "claim-1",
                "kind": "project_fact",
                "text": "owner/agent inference runtime requires network access for all editions.",
                "subjects": ["owner/agent"],
                "facts": [fact],
                "citation_indexes": [1],
                "evidence_refs": [{
                    "citation_index": 1,
                    "chunk_id": "chunk:1",
                    "repository": "owner/agent",
                    "quote": QUOTE,
                    "fact": dict(fact),
                }],
            }],
        }
        import json

        answer = f'{ledger["claims"][0]["text"]} [1]\n<claim_ledger>{json.dumps(ledger)}</claim_ledger>'
        passed = validate_rag_answer(answer=answer, citations=citation, contexts=[context])
        self.assertTrue(passed["passed"])
        self.assertEqual(passed["claim_checks"][0]["binding_status"], "valid")
        self.assertEqual(passed["claim_checks"][0]["semantic_support_status"], "supported")

        import copy

        mismatched_ledger = copy.deepcopy(ledger)
        mismatched_ledger["claims"][0]["facts"][0]["phase"] = "setup"
        mismatched_answer = f'{mismatched_ledger["claims"][0]["text"]} [1]\n<claim_ledger>{json.dumps(mismatched_ledger)}</claim_ledger>'
        failed = validate_rag_answer(answer=mismatched_answer, citations=citation, contexts=[context])
        self.assertFalse(failed["passed"])
        self.assertEqual(failed["claim_checks"][0]["binding_status"], "valid")
        self.assertEqual(failed["claim_checks"][0]["scope_status"], "mismatched")

        unregistered_answer = (
            f'{ledger["claims"][0]["text"]} [1] owner/agent is offline capable. [1]\n'
            f'<claim_ledger>{json.dumps(ledger)}</claim_ledger>'
        )
        unregistered = validate_rag_answer(answer=unregistered_answer, citations=citation, contexts=[context])
        self.assertFalse(unregistered["passed"])
        self.assertIn("unregistered_factual_sentence", [item["reason"] for item in unregistered["claim_checks"]])
