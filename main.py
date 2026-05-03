from __future__ import annotations

import os
import sys

from src.archive import (
    write_raw_repositories,
    write_report,
    write_run_summary,
    write_selected_repositories,
    write_trend_summary,
)
from src.collector import collect_repositories, enrich_repositories_with_readmes
from src.models import RunSummary
from src.processor import process_repositories
from src.reporter import generate_report
from src.security import apply_security_flags
from src.sender import report_url, send_report
from src.settings import load_settings
from src.state import (
    load_sent_repository_names,
    load_star_history,
    write_sent_repositories,
    write_star_history,
)
from src.trends import build_trend_summary
from src.utils import clean_error, date_range


def main() -> int:
    days_back = _days_back()
    run_date, since_date = date_range(days_back)
    settings = load_settings(run_date=run_date, since_date=since_date)
    summary = RunSummary(run_date=settings.run_date)

    try:
        collected, queries, collector_errors, collector_stats = collect_repositories(settings)
        sent_names = load_sent_repository_names(settings)
        star_history = load_star_history(settings)
        selected = process_repositories(collected, settings, star_history, previously_sent_names=sent_names)
        readme_fetched_count = enrich_repositories_with_readmes(selected, settings)
        apply_security_flags(selected)
        trend_summary = build_trend_summary(selected)
        report, fallback_used, report_error = generate_report(selected, queries, settings, trend_summary)

        report_path = write_report(report, settings)
        raw_path = write_raw_repositories(collected, settings)
        selected_path = write_selected_repositories(selected, settings)
        trend_summary_path = write_trend_summary(trend_summary, settings)
        star_history_path, star_history_updated_count = write_star_history(collected, settings)

        summary.queries = queries
        summary.collected_count = len(collected)
        summary.selected_count = len(selected)
        summary.skipped_sent_count = 0
        summary.previously_sent_selected_count = len({repo.full_name for repo in selected if repo.full_name in sent_names})
        summary.collector_errors = collector_errors
        summary.collector_stats = collector_stats
        summary.readme_fetched_count = readme_fetched_count
        summary.star_history_updated_count = star_history_updated_count
        summary.report_path = report_path.relative_to(settings.root).as_posix()
        summary.raw_repositories_path = raw_path.relative_to(settings.root).as_posix()
        summary.selected_repositories_path = selected_path.relative_to(settings.root).as_posix()
        summary.trend_summary_path = trend_summary_path.relative_to(settings.root).as_posix()
        summary.star_history_path = star_history_path
        summary.fallback_used = fallback_used
        summary.kimi_used = not fallback_used
        summary.report_error = report_error
        summary.telegram_report_url = report_url(settings)

        if _skip_telegram_send():
            summary.telegram_sent = False
            summary.telegram_error = "Telegram send skipped"
        else:
            sent, send_error = send_report(report, settings)
            summary.telegram_sent = sent
            summary.telegram_error = send_error
            if sent and selected:
                summary.state_path = write_sent_repositories(selected, settings)
        summary.status = "success" if selected else "empty"
    except Exception as error:
        summary.status = "failed"
        summary.error = clean_error(error)
        fallback_report = (
            f"# GitHub 每周热点项目周报 - {settings.run_date}\n\n"
            "本次运行失败，未能完成 GitHub 热点项目采集。\n\n"
            f"错误摘要：{summary.error}\n"
        )
        report_path = write_report(fallback_report, settings)
        summary.report_path = report_path.relative_to(settings.root).as_posix()
        summary.fallback_used = True
    finally:
        write_run_summary(summary, settings)

    print(f"status={summary.status}")
    print(f"report={summary.report_path}")
    if summary.telegram_error:
        print(f"telegram={summary.telegram_error}")
    if summary.error:
        print(f"error={summary.error}", file=sys.stderr)
        return 1
    return 0


def _days_back() -> int:
    try:
        return int(os.getenv("DAYS_BACK", "7"))
    except ValueError:
        return 7


def _skip_telegram_send() -> bool:
    return os.getenv("SKIP_TELEGRAM_SEND", "").lower() in {"1", "true", "yes"}


if __name__ == "__main__":
    raise SystemExit(main())
