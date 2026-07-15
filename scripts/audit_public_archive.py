from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_BASE = "https://api.github.com"
FORBIDDEN_SUFFIXES = (".sqlite", ".sqlite3", ".db", ".db3", "-wal", "-shm", ".env", ".pem", ".key", ".log")


class GitHubApi:
    def __init__(self, token: str | None = None) -> None:
        self.token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")

    def get(self, path: str, params: dict[str, str | int] | None = None) -> Any:
        url = f"{API_BASE}/{path.lstrip('/')}"
        if params:
            url = f"{url}?{urlencode(params)}"
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            with urlopen(Request(url, headers=headers), timeout=20) as response:
                return json.load(response)
        except (HTTPError, URLError) as error:
            raise RuntimeError("无法读取 GitHub 公开归档元数据。") from error


def _repository_from_environment() -> str:
    repository = os.getenv("GITHUB_REPOSITORY", "").strip()
    if repository:
        return repository
    remote = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    normalized = remote.removesuffix(".git")
    if normalized.startswith("git@github.com:"):
        return normalized.removeprefix("git@github.com:")
    if normalized.startswith("https://github.com/"):
        return normalized.removeprefix("https://github.com/")
    raise RuntimeError("无法从 origin 推导 GitHub 仓库名；请显式传入 --repo。").with_traceback(None)


def _forbidden_paths(tree: list[dict[str, Any]]) -> list[str]:
    return sorted(
        entry["path"]
        for entry in tree
        if entry.get("type") == "blob" and entry.get("path", "").lower().endswith(FORBIDDEN_SUFFIXES)
    )


def _tree(api: GitHubApi, repository: str, sha: str) -> list[dict[str, Any]]:
    payload = api.get(f"repos/{repository}/git/trees/{sha}", {"recursive": 1})
    if payload.get("truncated"):
        raise RuntimeError("归档 tree 过大且 GitHub API 返回截断结果，拒绝给出不完整证明。")
    return payload.get("tree", [])


def _history(api: GitHubApi, repository: str, branch: str, limit: int) -> list[dict[str, Any]]:
    commits: list[dict[str, Any]] = []
    page = 1
    while len(commits) < limit:
        batch = api.get(f"repos/{repository}/commits", {"sha": branch, "per_page": min(100, limit - len(commits)), "page": page})
        if not batch:
            break
        commits.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return commits[:limit]


def audit_archive(api: GitHubApi, repository: str, branch: str, history_limit: int = 0) -> dict[str, Any]:
    branch_payload = api.get(f"repos/{repository}/branches/{branch}")
    head_sha = branch_payload["commit"]["sha"]
    latest_tree = _tree(api, repository, head_sha)
    summary: dict[str, Any] = {
        "repository": repository,
        "branch": branch,
        "head_sha": head_sha,
        "latest_file_count": sum(entry.get("type") == "blob" for entry in latest_tree),
        "latest_forbidden_paths": _forbidden_paths(latest_tree),
    }
    if history_limit <= 0:
        return summary

    findings: dict[str, dict[str, Any]] = defaultdict(lambda: {"occurrences": 0})
    commits = _history(api, repository, branch, history_limit)
    for commit in commits:
        sha = commit["sha"]
        tree_sha = commit["commit"]["tree"]["sha"]
        for path in _forbidden_paths(_tree(api, repository, tree_sha)):
            finding = findings[path]
            finding["occurrences"] += 1
            finding.setdefault("last_seen_newest", sha)
            finding["first_seen_oldest"] = sha
    summary["history_commits_scanned"] = len(commits)
    summary["history_forbidden_paths"] = [
        {"path": path, **findings[path]} for path in sorted(findings)
    ]
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="只读审计 GitHub 公开归档 tree；不下载文件内容。")
    parser.add_argument("--repo", help="owner/repository；默认从 GITHUB_REPOSITORY 或 origin 推导。")
    parser.add_argument("--branch", default="weekly-archive")
    parser.add_argument("--history-limit", type=int, default=0, help="额外审计最新 N 个历史提交的 tree。")
    parser.add_argument("--verify-latest", action="store_true", help="最新 tree 含禁止文件时返回非零。")
    args = parser.parse_args()
    if args.history_limit < 0:
        parser.error("--history-limit 不能为负数。")
    summary = audit_archive(GitHubApi(), args.repo or _repository_from_environment(), args.branch, args.history_limit)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 2 if args.verify_latest and summary["latest_forbidden_paths"] else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
