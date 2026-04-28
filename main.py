from __future__ import annotations

import sys
import os

from src.archive import write_raw_repositories, write_report, write_run_summary
from src.collector import collect_repositories, enrich_repositories_with_readmes
from src.models import RunSummary
from src.processor import process_repositories
from src.reporter import generate_report
from src.sender import send_report
from src.settings import load_settings
from src.state import filter_unsent_repositories, load_sent_repository_names, write_sent_repositories
from src.utils import clean_error, date_range


def main() -> int:
    days_back = _days_back()
    run_date, since_date = date_range(days_back)
    settings = load_settings(run_date=run_date, since_date=since_date)
    summary = RunSummary(run_date=settings.run_date)

    try:
        collected, queries = collect_repositories(settings)
        sent_names = load_sent_repository_names(settings)
        unsent_collected = filter_unsent_repositories(collected, sent_names)
        selected = process_repositories(unsent_collected, settings)
        readme_fetched_count = enrich_repositories_with_readmes(selected, settings)
        report, fallback_used, report_error = generate_report(selected, queries, settings)

        report_path = write_report(report, settings)
        write_raw_repositories(selected, settings)

        summary.queries = queries
        summary.collected_count = len(collected)
        summary.selected_count = len(selected)
        summary.skipped_sent_count = len({repo.full_name for repo in collected if repo.full_name in sent_names})
        summary.readme_fetched_count = readme_fetched_count
        summary.report_path = report_path.relative_to(settings.root).as_posix()
        summary.fallback_used = fallback_used
        summary.kimi_used = not fallback_used
        summary.report_error = report_error

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


if __name__ == "__main__":
    raise SystemExit(main())
