from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.commit()


def import_json_archive(root: Path, db_path: Path) -> dict[str, int]:
    with connect(db_path) as connection:
        initialize(connection)
        counts = {
            "runs": import_runs(connection, root),
            "selections": import_selections(connection, root),
            "trend_summaries": import_trend_summaries(connection, root),
            "sent_repositories": import_sent_repositories(connection, root),
            "star_history": import_star_history(connection, root),
        }
        connection.execute(
            """
            INSERT INTO migration_meta(key, value)
            VALUES('last_import_counts', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (_json_text(counts),),
        )
        connection.commit()
        return counts


def import_runs(connection: sqlite3.Connection, root: Path) -> int:
    count = 0
    for path in _json_files(root / "data" / "runs"):
        data = _read_json_object(path)
        if not data:
            continue
        upsert_run(connection, data)
        count += 1
    return count


def import_selections(connection: sqlite3.Connection, root: Path) -> int:
    count = 0
    for path in _json_files(root / "data" / "selected"):
        data = _read_json_list(path)
        run_date = path.stem
        for position, item in enumerate(data, start=1):
            if not isinstance(item, dict) or not item.get("full_name"):
                continue
            upsert_repository(connection, item)
            upsert_selection(connection, run_date, position, item)
            count += 1
    return count


def import_trend_summaries(connection: sqlite3.Connection, root: Path) -> int:
    count = 0
    for path in _json_files(root / "data" / "trends"):
        data = _read_json_object(path)
        if not data:
            continue
        upsert_trend_summary(connection, path.stem, data)
        count += 1
    return count


def import_sent_repositories(connection: sqlite3.Connection, root: Path) -> int:
    count = 0
    for item in _read_json_list(root / "data" / "state" / "sent_repos.json"):
        if isinstance(item, str):
            item = {"full_name": item, "html_url": "", "first_sent_at": ""}
        if not isinstance(item, dict) or not item.get("full_name"):
            continue
        connection.execute(
            """
            INSERT INTO sent_repositories(full_name, html_url, first_sent_at, payload_json)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(full_name) DO UPDATE SET
              html_url = excluded.html_url,
              first_sent_at = excluded.first_sent_at,
              payload_json = excluded.payload_json
            """,
            (
                str(item.get("full_name") or ""),
                str(item.get("html_url") or ""),
                str(item.get("first_sent_at") or ""),
                _json_text(item),
            ),
        )
        count += 1
    return count


def import_star_history(connection: sqlite3.Connection, root: Path) -> int:
    count = 0
    for item in _read_json_list(root / "data" / "state" / "star_history.json"):
        if not isinstance(item, dict) or not item.get("full_name"):
            continue
        connection.execute(
            """
            INSERT INTO star_history(full_name, html_url, stargazers_count, last_seen_at, payload_json)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(full_name) DO UPDATE SET
              html_url = excluded.html_url,
              stargazers_count = excluded.stargazers_count,
              last_seen_at = excluded.last_seen_at,
              payload_json = excluded.payload_json
            """,
            (
                str(item.get("full_name") or ""),
                str(item.get("html_url") or ""),
                _int_value(item.get("stargazers_count")),
                str(item.get("last_seen_at") or ""),
                _json_text(item),
            ),
        )
        count += 1
    return count


def upsert_run(connection: sqlite3.Connection, data: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO runs(
          run_date, status, collected_count, selected_count, previously_sent_selected_count,
          kimi_used, fallback_used, telegram_sent, report_path, telegram_report_url, payload_json
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_date) DO UPDATE SET
          status = excluded.status,
          collected_count = excluded.collected_count,
          selected_count = excluded.selected_count,
          previously_sent_selected_count = excluded.previously_sent_selected_count,
          kimi_used = excluded.kimi_used,
          fallback_used = excluded.fallback_used,
          telegram_sent = excluded.telegram_sent,
          report_path = excluded.report_path,
          telegram_report_url = excluded.telegram_report_url,
          payload_json = excluded.payload_json
        """,
        (
            str(data.get("run_date") or ""),
            str(data.get("status") or ""),
            _int_value(data.get("collected_count")),
            _int_value(data.get("selected_count")),
            _int_value(data.get("previously_sent_selected_count")),
            int(bool(data.get("kimi_used"))),
            int(bool(data.get("fallback_used"))),
            int(bool(data.get("telegram_sent"))),
            str(data.get("report_path") or ""),
            str(data.get("telegram_report_url") or ""),
            _json_text(data),
        ),
    )


def upsert_repository(connection: sqlite3.Connection, data: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO repositories(
          full_name, html_url, description, language, stargazers_count,
          forks_count, license_name, archived, fork, pushed_at, payload_json
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(full_name) DO UPDATE SET
          html_url = excluded.html_url,
          description = excluded.description,
          language = excluded.language,
          stargazers_count = excluded.stargazers_count,
          forks_count = excluded.forks_count,
          license_name = excluded.license_name,
          archived = excluded.archived,
          fork = excluded.fork,
          pushed_at = excluded.pushed_at,
          payload_json = excluded.payload_json
        """,
        (
            str(data.get("full_name") or ""),
            str(data.get("html_url") or ""),
            str(data.get("description") or ""),
            str(data.get("language") or ""),
            _int_value(data.get("stargazers_count")),
            _int_value(data.get("forks_count")),
            str(data.get("license_name") or ""),
            int(bool(data.get("archived"))),
            int(bool(data.get("fork"))),
            str(data.get("pushed_at") or data.get("updated_at") or ""),
            _json_text(data),
        ),
    )


def upsert_selection(connection: sqlite3.Connection, run_date: str, position: int, data: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO selections(
          run_date, full_name, position, score, star_growth, trending_rank, category,
          sources_json, selection_reasons_json, security_flags_json, payload_json
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_date, full_name) DO UPDATE SET
          position = excluded.position,
          score = excluded.score,
          star_growth = excluded.star_growth,
          trending_rank = excluded.trending_rank,
          category = excluded.category,
          sources_json = excluded.sources_json,
          selection_reasons_json = excluded.selection_reasons_json,
          security_flags_json = excluded.security_flags_json,
          payload_json = excluded.payload_json
        """,
        (
            run_date,
            str(data.get("full_name") or ""),
            position,
            _float_value(data.get("score")),
            _int_value(data.get("star_growth")),
            _int_value(data.get("trending_rank")),
            str(data.get("category") or "Other"),
            _json_text(data.get("sources") or []),
            _json_text(data.get("selection_reasons") or []),
            _json_text(data.get("security_flags") or []),
            _json_text(data),
        ),
    )


def upsert_trend_summary(connection: sqlite3.Connection, run_date: str, data: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO trend_summaries(run_date, total_projects, trending_project_count, total_star_growth, payload_json)
        VALUES(?, ?, ?, ?, ?)
        ON CONFLICT(run_date) DO UPDATE SET
          total_projects = excluded.total_projects,
          trending_project_count = excluded.trending_project_count,
          total_star_growth = excluded.total_star_growth,
          payload_json = excluded.payload_json
        """,
        (
            run_date,
            _int_value(data.get("total_projects")),
            _int_value(data.get("trending_project_count")),
            _int_value(data.get("total_star_growth")),
            _json_text(data),
        ),
    )


def table_count(connection: sqlite3.Connection, table_name: str) -> int:
    if table_name not in {
        "runs",
        "repositories",
        "selections",
        "trend_summaries",
        "sent_repositories",
        "star_history",
    }:
        raise ValueError(f"不支持的表名：{table_name}")
    row = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
    return int(row["count"])


def _json_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(item for item in path.glob("*.json") if item.is_file())


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _read_json_list(path: Path) -> list[Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def _json_text(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _float_value(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0
