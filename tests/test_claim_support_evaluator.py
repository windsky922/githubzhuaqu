from __future__ import annotations

import unittest

from scripts.evaluate_claim_support import DEFAULT_CASES, evaluate, load_cases


class ClaimSupportEvaluatorTest(unittest.TestCase):
    def test_fixed_cases_pass_and_cover_mismatch_classes(self):
        cases = load_cases(DEFAULT_CASES)
        self.assertEqual(len(cases), 10)
        self.assertEqual(evaluate(cases)["metrics"]["exact_accuracy"], 1.0)
        self.assertEqual(evaluate(cases)["metrics"]["false_support_rate"], 0.0)
