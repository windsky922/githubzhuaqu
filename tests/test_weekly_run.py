from __future__ import annotations

import os
import unittest
from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

import main
from src.models import RunSummary
from src.weekly_run import _apply_observability_metrics, _days_back, _rate, _skip_telegram_send


class WeeklyRunTest(unittest.TestCase):
    def test_rate_handles_zero_denominator(self) -> None:
        self.assertEqual(_rate(1, 0), 0.0)
        self.assertEqual(_rate(1, 4), 0.25)

    def test_env_helpers_parse_safe_defaults(self) -> None:
        with patch.dict(os.environ, {"DAYS_BACK": "bad", "SKIP_TELEGRAM_SEND": "yes"}, clear=False):
            self.assertEqual(_days_back(), 7)
            self.assertTrue(_skip_telegram_send())

    def test_apply_observability_metrics_counts_trending_top10(self) -> None:
        summary = RunSummary(run_date="2026-05-11", previously_sent_selected_count=1)
        collected = [
            SimpleNamespace(full_name="owner/a", trending_rank=1),
            SimpleNamespace(full_name="owner/b", trending_rank=8),
            SimpleNamespace(full_name="owner/c", trending_rank=12),
        ]
        selected = [
            SimpleNamespace(full_name="owner/a", trending_rank=1),
            SimpleNamespace(full_name="owner/c", trending_rank=12),
        ]

        _apply_observability_metrics(
            summary,
            collected,
            selected,
            [{"status": "success"}, {"status": "failed"}],
            readme_fetched_count=1,
            sent_names={"owner/a"},
        )

        self.assertEqual(summary.collector_query_count, 2)
        self.assertEqual(summary.collector_success_count, 1)
        self.assertEqual(summary.collector_success_rate, 0.5)
        self.assertEqual(summary.readme_fetch_rate, 0.5)
        self.assertEqual(summary.previously_sent_selected_rate, 0.5)
        self.assertEqual(summary.trending_top10_available_count, 2)
        self.assertEqual(summary.trending_top10_selected_count, 1)
        self.assertEqual(summary.trending_top10_fulfillment_rate, 0.5)

    def test_main_delegates_to_weekly_run_use_case(self) -> None:
        summary = RunSummary(run_date="2026-05-11", status="success", report_path="reports/2026-05-11.md")
        with patch.object(main, "run_weekly_report", return_value=summary) as run:
            with redirect_stdout(StringIO()):
                self.assertEqual(main.main(), 0)
        run.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
