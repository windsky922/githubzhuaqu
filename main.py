from __future__ import annotations

import sys

from src.weekly_run import run_weekly_report


def main() -> int:
    summary = run_weekly_report()
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


if __name__ == "__main__":
    raise SystemExit(main())
