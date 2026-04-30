from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from src.sender import report_url, send_report
from src.settings import ROOT, load_settings
from src.state import write_sent_repositories
from src.models import Repository
from src.delivery_policy import fallback_delivery_block_reason


def main() -> int:
    run_date = _latest_run_date(ROOT)
    if not run_date:
        print("没有找到可发送的运行摘要。")
        return 1

    settings = load_settings(run_date=run_date, since_date="")
    run_summary = _run_summary(ROOT, run_date)
    block_reason = fallback_delivery_block_reason(
        bool(run_summary.get("fallback_used")),
        str(run_summary.get("report_error") or ""),
    )
    url = report_url(settings)
    if block_reason:
        _update_run_summary(ROOT, run_date, False, block_reason, "", url)
        print("telegram_sent=False")
        print(f"telegram_error={block_reason}")
        return 0

    sent, error = send_report("", settings)
    selected = _selected_repositories(ROOT, run_date)
    state_path = ""
    if sent and selected:
        state_path = write_sent_repositories(selected, settings)
    _update_run_summary(ROOT, run_date, sent, error, state_path, url)

    print(f"telegram_sent={sent}")
    if error:
        print(f"telegram_error={error}")
    return 0


def _latest_run_date(root: Path) -> str:
    runs_dir = root / "data" / "runs"
    if not runs_dir.exists():
        return ""
    runs = sorted((path for path in runs_dir.glob("*.json")), key=lambda path: path.stem, reverse=True)
    return runs[0].stem if runs else ""


def _selected_repositories(root: Path, run_date: str) -> list[Repository]:
    path = root / "data" / "selected" / f"{run_date}.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    repositories = []
    for item in data:
        if isinstance(item, dict):
            repositories.append(Repository(**item))
    return repositories


def _run_summary(root: Path, run_date: str) -> dict:
    path = root / "data" / "runs" / f"{run_date}.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _update_run_summary(root: Path, run_date: str, sent: bool, error: str, state_path: str, report_url: str = "") -> None:
    path = root / "data" / "runs" / f"{run_date}.json"
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    if not isinstance(data, dict):
        return
    data["telegram_sent"] = sent
    data["telegram_error"] = error
    if report_url:
        data["telegram_report_url"] = report_url
    if state_path:
        data["state_path"] = state_path
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
