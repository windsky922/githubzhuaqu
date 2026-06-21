from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.api.repository import ApiRepository
from src.notifications.service import (
    build_notification_candidates,
    deliver_notification_candidate,
    detect_subscription_events,
)
from src.settings import load_settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="检测项目事件、构建候选并安全投递通知。")
    parser.add_argument("--root", type=Path, default=ROOT, help="项目根目录。")
    parser.add_argument("--db", type=Path, default=None, help="SQLite 路径。")
    subparsers = parser.add_subparsers(dest="command", required=True)

    detect = subparsers.add_parser("detect", help="检测项目变化事件。")
    detect.add_argument("--full-name", default="", help="只检测指定 owner/repo。")
    detect.add_argument("--limit", type=int, default=500)
    detect.add_argument("--dry-run", action="store_true", help="只预览，不写数据库。")

    build = subparsers.add_parser("build", help="按启用订阅构建推送候选。")
    build.add_argument("--limit", type=int, default=500)
    build.add_argument("--dry-run", action="store_true", help="只预览，不写数据库。")

    preview = subparsers.add_parser("preview", help="预览单个候选的逐渠道发送计划。")
    preview.add_argument("candidate_id")
    preview.add_argument("--channel", action="append", default=[])

    deliver = subparsers.add_parser("deliver", help="投递单个候选；默认仍是 dry-run。")
    _delivery_arguments(deliver)
    deliver.add_argument("candidate_id")

    pending = subparsers.add_parser("deliver-pending", help="批量预览或投递待确认候选。")
    _delivery_arguments(pending)
    pending.add_argument("--limit", type=int, default=20)

    args = parser.parse_args(argv)
    db_path = args.db or args.root / "data" / "github_weekly.sqlite"
    if args.command == "detect":
        result = detect_subscription_events(
            db_path, full_name=args.full_name, limit=args.limit, dry_run=args.dry_run
        )
    elif args.command == "build":
        result = build_notification_candidates(db_path, limit=args.limit, dry_run=args.dry_run)
    else:
        settings = _settings(args.root)
        if args.command == "preview":
            result = deliver_notification_candidate(
                db_path, settings, args.candidate_id, dry_run=True,
                confirm_delivery=False, channels=args.channel or None, requested_by="notification_cli",
            )
        elif args.command == "deliver":
            result = _deliver_one(db_path, settings, args, args.candidate_id)
        else:
            result = _deliver_pending(args.root, db_path, settings, args)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return _exit_code(result)


def _delivery_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dry-run", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--confirm-delivery", action="store_true")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--channel", action="append", default=[])
    parser.add_argument("--requested-by", default="notification_cli")


def _deliver_one(db_path: Path, settings: Any, args: argparse.Namespace, candidate_id: str) -> dict[str, Any]:
    return deliver_notification_candidate(
        db_path,
        settings,
        candidate_id,
        dry_run=args.dry_run,
        confirm_delivery=args.confirm_delivery,
        channels=args.channel or None,
        retry_failed=args.retry_failed,
        requested_by=args.requested_by,
    )


def _deliver_pending(root: Path, db_path: Path, settings: Any, args: argparse.Namespace) -> dict[str, Any]:
    repository = ApiRepository(root=root, db_path=db_path)
    statuses = ["pending"]
    if args.retry_failed:
        statuses.extend(["failed", "partial"])
    candidates = []
    for status in statuses:
        candidates.extend(repository.notification_candidates(status=status, limit=args.limit).get("candidates", []))
    seen = set()
    results = []
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id") or "")
        if not candidate_id or candidate_id in seen or len(results) >= max(1, min(args.limit, 100)):
            continue
        seen.add(candidate_id)
        results.append(_deliver_one(db_path, settings, args, candidate_id))
    return {
        "schema_version": 1,
        "dry_run": args.dry_run,
        "confirm_delivery": args.confirm_delivery,
        "candidate_count": len(results),
        "executed_count": sum(1 for item in results if item.get("executed")),
        "results": results,
    }


def _settings(root: Path):
    today = datetime.now(UTC).date().isoformat()
    return load_settings(today, today, root=root)


def _exit_code(result: dict[str, Any]) -> int:
    if result.get("accepted") is False:
        return 2
    nested = result.get("results") if isinstance(result.get("results"), list) else []
    if any(item.get("accepted") is False for item in nested if isinstance(item, dict)):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
