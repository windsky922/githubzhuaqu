from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_PATHS = ("docs", "reports", "data")


def main() -> int:
    parser = argparse.ArgumentParser(description="把生成的归档文件发布到独立归档分支。")
    parser.add_argument("--branch", default="weekly-archive", help="归档分支名，默认 weekly-archive。")
    parser.add_argument("--message", required=True, help="提交信息。")
    args = parser.parse_args()

    worktree = ROOT.parent / f"{ROOT.name}-archive-worktree"
    _remove_worktree(worktree)
    try:
        _prepare_worktree(worktree, args.branch)
        _copy_archive_paths(worktree)
        _commit_and_push(worktree, args.branch, args.message)
    finally:
        _remove_worktree(worktree)
    return 0


def _prepare_worktree(worktree: Path, branch: str) -> None:
    if _remote_branch_exists(branch):
        _run(["git", "fetch", "origin", branch])
        _run(["git", "worktree", "add", "-B", branch, str(worktree), f"origin/{branch}"])
        return

    _run(["git", "worktree", "add", "--detach", str(worktree)])
    _run(["git", "switch", "--orphan", branch], cwd=worktree)
    _run(["git", "rm", "-rf", "."], cwd=worktree, check=False)


def _remote_branch_exists(branch: str) -> bool:
    result = _run(
        ["git", "ls-remote", "--exit-code", "--heads", "origin", branch],
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def _copy_archive_paths(worktree: Path) -> None:
    for relative in ARCHIVE_PATHS:
        source = ROOT / relative
        target = worktree / relative
        if not source.exists():
            continue
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)


def _commit_and_push(worktree: Path, branch: str, message: str) -> None:
    _run(["git", "config", "user.name", "github-actions[bot]"], cwd=worktree)
    _run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], cwd=worktree)
    _run(["git", "add", *ARCHIVE_PATHS], cwd=worktree)
    if _run(["git", "diff", "--cached", "--quiet"], cwd=worktree, check=False).returncode == 0:
        print("没有需要提交的归档变更。")
        return
    _run(["git", "commit", "-m", message], cwd=worktree)
    _run(["git", "push", "origin", f"{branch}:{branch}"], cwd=worktree)


def _remove_worktree(worktree: Path) -> None:
    _run(["git", "worktree", "remove", "--force", str(worktree)], check=False)
    shutil.rmtree(worktree, ignore_errors=True)


def _run(
    command: list[str],
    *,
    cwd: Path = ROOT,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=check,
        text=True,
        capture_output=capture_output,
    )


if __name__ == "__main__":
    raise SystemExit(main())
