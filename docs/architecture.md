# GitHub Weekly Agent Architecture

This document tracks the implementation architecture for the MVP.

## Runtime Flow

```text
main.py
-> src.settings.load_settings
-> src.collector.collect_repositories
-> src.processor.process_repositories
-> src.reporter.generate_report
-> src.archive.archive_run
-> src.sender.send_report
-> src.archive.write_run_summary
```

## MVP Scope

Implemented in the first development stage:

1. GitHub Search API collection.
2. Repository filtering, deduplication, scoring, and ranking.
3. Kimi chat-completions report generation.
4. Fallback Markdown report when Kimi is unavailable.
5. Telegram chunked sending.
6. Markdown report archive in `reports/`.
7. Run summary archive in `data/runs/`.
8. GitHub Actions weekly schedule and manual trigger.

Deferred:

1. README deep fetching.
2. SQLite history.
3. Web dashboard.
4. Published Skill package.
5. Telegram interactive bot.

