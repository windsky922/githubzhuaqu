"""Read-only, redacted structure audit for historical public archive databases."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import tempfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
API_BASE = "https://api.github.com"
DATABASE_SUFFIXES = (".sqlite", ".sqlite3", ".db", ".db3")
SQLITE_MAGIC = b"SQLite format 3\x00"
TIME_COLUMN_PATTERN = re.compile(r"(?:^|_)(?:created|updated|sent|run|started|finished|timestamp|date|time)(?:_at)?$", re.IGNORECASE)
RISK_PATTERNS = {
    "credential_named_field": re.compile(r"(?:api[_-]?key|secret|token|password|webhook)", re.IGNORECASE),
    "user_input_named_field": re.compile(r"(?:query|note|prompt|message|conversation|feedback)", re.IGNORECASE),
    "notification_or_subscription_field": re.compile(r"(?:subscription|notification|delivery|recipient|chat[_-]?id)", re.IGNORECASE),
    "task_runtime_field": re.compile(r"(?:task|job|run|state|error)", re.IGNORECASE),
}


class ArchiveApi(Protocol):
    def get(self, path: str, params: dict[str, str | int] | None = None) -> Any: ...

    def get_bytes(self, path: str) -> bytes: ...


class GitHubArchiveApi:
    def __init__(self, token: str | None = None) -> None:
        self.token = token or os.getenv("GITHUB_TOKEN")

    def get(self, path: str, params: dict[str, str | int] | None = None) -> Any:
        url = f"{API_BASE}/{path.lstrip('/')}"
        if params:
            url = f"{url}?{urlencode(params)}"
        return self._request(url, decode_json=True)

    def get_bytes(self, path: str) -> bytes:
        data = self.get(path)
        if not isinstance(data, dict) or data.get("encoding") != "base64" or not isinstance(data.get("content"), str):
            raise RuntimeError("无法读取 GitHub 公开归档数据库。")
        try:
            return base64.b64decode(data["content"], validate=True)
        except (ValueError, binascii.Error) as error:
            raise RuntimeError("无法读取 GitHub 公开归档数据库。") from error

    def _request(self, url: str, *, decode_json: bool) -> Any:
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            with urlopen(Request(url, headers=headers), timeout=20) as response:
                data = response.read()
        except (HTTPError, URLError) as error:
            raise RuntimeError("无法读取 GitHub 公开归档元数据。") from error
        if not decode_json:
            return data
        return json.loads(data.decode("utf-8"))


def _repository_from_environment() -> str:
    repository = os.getenv("GITHUB_REPOSITORY", "").strip()
    if repository:
        return repository
    try:
        remote = subprocess.check_output(["git", "remote", "get-url", "origin"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError("无法从 origin 推导 GitHub 仓库名；请显式传入 --repo。") from error
    match = re.search(r"github\.com[/:]([^/]+/[^/]+?)(?:\.git)?$", remote)
    if not match:
        raise RuntimeError("无法从 origin 推导 GitHub 仓库名；请显式传入 --repo。")
    return match.group(1)


def _history(api: ArchiveApi, repository: str, branch: str, limit: int) -> list[dict[str, Any]]:
    commits: list[dict[str, Any]] = []
    page = 1
    while True:
        remaining = limit - len(commits) if limit else 100
        if limit and remaining <= 0:
            break
        batch = api.get(
            f"repos/{repository}/commits",
            {"sha": branch, "per_page": min(100, remaining), "page": page},
        )
        if not isinstance(batch, list) or not batch:
            break
        commits.extend(item for item in batch if isinstance(item, dict) and item.get("sha"))
        if len(batch) < min(100, remaining):
            break
        page += 1
    return commits[:limit] if limit else commits


def _tree(api: ArchiveApi, repository: str, sha: str) -> list[dict[str, Any]]:
    data = api.get(f"repos/{repository}/git/trees/{sha}", {"recursive": 1})
    tree = data.get("tree", []) if isinstance(data, dict) else []
    return [entry for entry in tree if isinstance(entry, dict)]


def _database_entries(tree: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        entry
        for entry in tree
        if entry.get("type") == "blob" and str(entry.get("path", "")).lower().endswith(DATABASE_SUFFIXES)
    ]


def enumerate_history(api: ArchiveApi, repository: str, branch: str, history_limit: int = 0) -> dict[str, Any]:
    commits = _history(api, repository, branch, history_limit)
    blobs: dict[str, dict[str, Any]] = {}
    for commit in commits:
        commit_sha = str(commit["sha"])
        for entry in _database_entries(_tree(api, repository, commit_sha)):
            blob_sha = str(entry.get("sha") or "")
            path = str(entry.get("path") or "")
            if not blob_sha or not path:
                continue
            item = blobs.setdefault(
                blob_sha,
                {
                    "blob_sha": blob_sha,
                    "paths": set(),
                    "occurrences": 0,
                    "first_seen_newest": commit_sha,
                    "last_seen_oldest": commit_sha,
                },
            )
            item["paths"].add(path)
            item["occurrences"] += 1
            item["last_seen_oldest"] = commit_sha
    databases = [
        {
            "blob_sha": item["blob_sha"],
            "paths": sorted(item["paths"]),
            "occurrences": item["occurrences"],
            "first_seen_newest": item["first_seen_newest"],
            "last_seen_oldest": item["last_seen_oldest"],
        }
        for item in blobs.values()
    ]
    return {
        "schema_version": 1,
        "repository": repository,
        "branch": branch,
        "history_commits_scanned": len(commits),
        "database_blob_count": len(databases),
        "databases": sorted(databases, key=lambda item: (item["paths"], item["blob_sha"])),
    }


def _quoted_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _normalized_time(value: Any) -> str | None:
    if isinstance(value, (int, float)) and 0 <= value <= 4_102_444_800:
        return datetime.fromtimestamp(value, tz=UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return None


def _risk_categories(table: str, columns: list[str]) -> list[str]:
    names = " ".join([table, *columns])
    return sorted(category for category, pattern in RISK_PATTERNS.items() if pattern.search(names))


def _inspect_database(data: bytes, metadata: dict[str, Any]) -> dict[str, Any]:
    result = {**metadata, "sha256": hashlib.sha256(data).hexdigest(), "sqlite_magic": data.startswith(SQLITE_MAGIC)}
    if not result["sqlite_magic"]:
        return {**result, "structure_status": "not_sqlite"}
    with tempfile.TemporaryDirectory(prefix="archive-structure-audit-") as directory:
        database_path = Path(directory) / "archive.sqlite"
        database_path.write_bytes(data)
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(f"{database_path.as_uri()}?mode=ro&immutable=1", uri=True)
            tables = [
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                )
            ]
            structures = []
            for table in tables:
                column_rows = connection.execute(f"PRAGMA table_info({_quoted_identifier(table)})").fetchall()
                columns = [str(row[1]) for row in column_rows]
                declared_columns = [
                    {"name": str(row[1]), "declared_type": str(row[2] or "")}
                    for row in column_rows
                ]
                row_count = int(connection.execute(f"SELECT COUNT(*) FROM {_quoted_identifier(table)}").fetchone()[0])
                time_ranges = []
                for column in columns:
                    if not TIME_COLUMN_PATTERN.search(column):
                        continue
                    minimum, maximum = connection.execute(
                        f"SELECT MIN({_quoted_identifier(column)}), MAX({_quoted_identifier(column)}) FROM {_quoted_identifier(table)}"
                    ).fetchone()
                    normalized_minimum = _normalized_time(minimum)
                    normalized_maximum = _normalized_time(maximum)
                    if normalized_minimum or normalized_maximum:
                        time_ranges.append(
                            {"column": column, "minimum": normalized_minimum, "maximum": normalized_maximum}
                        )
                structures.append(
                    {
                        "table": table,
                        "columns": declared_columns,
                        "row_count": row_count,
                        "time_ranges": time_ranges,
                        "risk_categories": _risk_categories(table, columns),
                    }
                )
            return {**result, "structure_status": "ok", "tables": structures}
        except sqlite3.DatabaseError:
            return {**result, "structure_status": "structure_unavailable"}
        finally:
            if connection is not None:
                connection.close()


def _report_directory(requested_root: Path, run_id: str) -> Path:
    private_root = (ROOT / "tmp").resolve()
    candidate = (requested_root if requested_root.is_absolute() else ROOT / requested_root).resolve()
    try:
        candidate.relative_to(private_root)
    except ValueError as error:
        raise ValueError("报告目录必须位于 tmp/ 下。") from error
    return candidate / run_id


def structure_scan(api: ArchiveApi, inventory: dict[str, Any]) -> dict[str, Any]:
    databases = []
    for metadata in inventory["databases"]:
        blob = api.get_bytes(f"repos/{inventory['repository']}/git/blobs/{metadata['blob_sha']}")
        databases.append(_inspect_database(blob, metadata))
    return {**inventory, "structure_scan": True, "databases": databases}


def _write_report(summary: dict[str, Any], requested_root: Path) -> Path:
    run_id = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    directory = _report_directory(requested_root, run_id)
    directory.mkdir(parents=True, exist_ok=False)
    path = directory / "summary.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _require_structure_token() -> None:
    if not os.getenv("GITHUB_TOKEN"):
        raise RuntimeError("结构扫描需要 GITHUB_TOKEN；未下载任何数据库内容。")


def main() -> int:
    parser = argparse.ArgumentParser(description="只读审计公开归档历史数据库结构；不输出数据库内容。")
    parser.add_argument("--repo", help="owner/repository；默认从 GITHUB_REPOSITORY 或 origin 推导。")
    parser.add_argument("--branch", default="weekly-archive")
    parser.add_argument("--history-limit", type=int, default=0, help="扫描最新 N 个提交；0 表示全部可达历史。")
    parser.add_argument("--dry-run", action="store_true", help="只枚举数据库路径、提交和 blob SHA。")
    parser.add_argument("--confirm-structure-scan", action="store_true", help="确认下载临时副本并执行仅结构扫描。")
    parser.add_argument("--report-root", type=Path, default=ROOT / "tmp" / "archive-audit")
    args = parser.parse_args()
    if args.history_limit < 0:
        parser.error("--history-limit 不能为负数。")
    if args.dry_run and args.confirm_structure_scan:
        parser.error("--dry-run 与 --confirm-structure-scan 不能同时使用。")

    inventory = enumerate_history(GitHubArchiveApi(), args.repo or _repository_from_environment(), args.branch, args.history_limit)
    if args.dry_run:
        print(json.dumps(inventory, ensure_ascii=False, sort_keys=True))
        return 0
    if not args.confirm_structure_scan:
        parser.error("结构扫描需要显式传入 --confirm-structure-scan；可先使用 --dry-run。")
    _require_structure_token()
    summary = structure_scan(GitHubArchiveApi(), inventory)
    report_path = _write_report(summary, args.report_root)
    print(json.dumps({"database_blob_count": summary["database_blob_count"], "report_path": str(report_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
