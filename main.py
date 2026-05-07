from __future__ import annotations

import os
import sys

from src.archive import (
    sqlite_index_summary_path,
    sync_sqlite_index,
    write_raw_repositories,
    write_report,
    write_run_summary,
    write_selected_repositories,
    write_trend_summary,
)
from src.collector import collect_repositories, enrich_repositories_with_readmes
from src.models import RunSummary
from src.processor import process_repositories
from src.quality import apply_quality_signals
from src.reporter import generate_report
from src.security import apply_security_flags
from src.sender import explorer_url, report_url, send_report_to_channels
from src.settings import load_settings
from src.state import (
    load_sent_repository_names,
    load_star_history,
    write_sent_repositories,
    write_star_history,
)
from src.trends import build_trend_summary
from src.utils import clean_error, date_range

TRENDING_TOP_RANK_LIMIT = 10


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
        apply_quality_signals(selected)
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
        _apply_observability_metrics(summary, collected, selected, collector_stats, readme_fetched_count, sent_names)
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
        summary.telegram_explorer_url = explorer_url(settings)

        if _skip_telegram_send():
            summary.telegram_sent = False
            summary.telegram_error = "Telegram send skipped"
            summary.delivery_results = [
                {"channel": "telegram", "sent": False, "error": "Telegram send skipped", "skipped": True}
            ]
        else:
            delivery_results = send_report_to_channels(report, settings)
            summary.delivery_results = [result.to_dict() for result in delivery_results]
            telegram_result = next((result for result in delivery_results if result.channel == "telegram"), None)
            summary.telegram_sent = bool(telegram_result and telegram_result.sent)
            summary.telegram_error = telegram_result.error if telegram_result else "Telegram channel is disabled"
            if summary.telegram_sent and selected:
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
        summary.sqlite_index_path = summary.sqlite_index_path or sqlite_index_summary_path(settings)
        write_run_summary(summary, settings)
        sqlite_path, sqlite_error = sync_sqlite_index(settings)
        if sqlite_path or sqlite_error:
            summary.sqlite_index_path = sqlite_path
            summary.sqlite_error = sqlite_error
            write_run_summary(summary, settings)

    print(f"status={summary.status}")
    print(f"report={summary.report_path}")
    if summary.sqlite_error:
        print(f"sqlite={summary.sqlite_error}")
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


def _apply_observability_metrics(
    summary: RunSummary,
    collected,
    selected,
    collector_stats: list[dict],
    readme_fetched_count: int,
    sent_names: set[str],
) -> None:
    summary.collector_query_count = len(collector_stats)
    summary.collector_success_count = sum(1 for item in collector_stats if item.get("status") == "success")
    summary.collector_success_rate = _rate(summary.collector_success_count, summary.collector_query_count)
    summary.readme_fetch_rate = _rate(readme_fetched_count, len(selected))
    summary.previously_sent_selected_rate = _rate(summary.previously_sent_selected_count, len(selected))

    available_top10 = {repo.full_name for repo in collected if 0 < repo.trending_rank <= TRENDING_TOP_RANK_LIMIT}
    selected_top10 = {repo.full_name for repo in selected if 0 < repo.trending_rank <= TRENDING_TOP_RANK_LIMIT}
    summary.trending_top10_available_count = len(available_top10)
    summary.trending_top10_selected_count = len(selected_top10)
    target = min(len(available_top10), 7, len(selected) or 7)
    summary.trending_top10_fulfillment_rate = _rate(len(selected_top10), target)


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


if __name__ == "__main__":
    raise SystemExit(main())
