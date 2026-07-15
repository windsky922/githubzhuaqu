from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.public_archive import project_archive_json
ARCHIVE_PATHS = ("docs", "reports", "data")
PUBLIC_DATA_DIRECTORIES = ("raw", "runs", "selected", "trends")
PUBLIC_DOC_FILES = (
    "index.md",
    "projects.md",
    "admin.html",
    "admin-auth.js",
    "agent.html",
    "explorer.html",
    "recommendations.html",
    "subscriptions.html",
    "compare.html",
    "project.html",
    "runs.html",
    "jobs.html",
    "job.html",
    "projects.json",
    "runs.json",
    "jobs.json",
    "profiles.json",
    "profiles.html",
    "feed.xml",
)
PUBLIC_APP_SUFFIXES = frozenset({".css", ".gif", ".html", ".ico", ".jpg", ".jpeg", ".js", ".json", ".map", ".png", ".svg", ".webp", ".woff", ".woff2"})
PUBLIC_WEEKLY_SUFFIXES = frozenset({".html", ".md"})
FORBIDDEN_PATH_PATTERN = re.compile(r"\.sqlite(?:-|$)", re.IGNORECASE)
FORBIDDEN_CONTENT_PATTERN = re.compile(
    rb"(?:archive-(?:secret|query|note)-canary|(?:api[_-]?key|secret|token|password|webhook)\\s*[:=])",
    re.IGNORECASE,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="把公共归档文件发布到独立归档分支。")
    parser.add_argument("--branch", default="weekly-archive", help="归档分支名，默认 weekly-archive。")
    parser.add_argument("--message", required=True, help="提交信息。")
    parser.add_argument("--dry-run", action="store_true", help="只验证并输出待发布文件数量，不创建 worktree 或推送。")
    args = parser.parse_args()

    public_sources = _public_sources(ROOT)
    if args.dry_run:
        _validate_public_json_projections(public_sources, ROOT)
        print(f"dry-run: {len(public_sources)} 个公共文件将发布。")
        return 0

    worktree = ROOT.parent / f"{ROOT.name}-archive-worktree"
    _remove_worktree(worktree)
    try:
        _prepare_worktree(worktree, args.branch)
        _synchronize_archive_tree(worktree, public_sources)
        _stage_and_validate(worktree)
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


def _public_sources(root: Path) -> list[Path]:
    root = root.resolve()
    sources: list[Path] = []
    for name in PUBLIC_DOC_FILES:
        candidate = root / "docs" / name
        if candidate.exists():
            sources.append(_validated_source(candidate, root))
    sources.extend(_public_files_in(root / "docs" / "weekly", root, PUBLIC_WEEKLY_SUFFIXES))
    sources.extend(_public_files_in(root / "docs" / "app", root, PUBLIC_APP_SUFFIXES))
    sources.extend(_public_files_in(root / "reports", root, {".md"}))
    for directory in PUBLIC_DATA_DIRECTORIES:
        sources.extend(_public_files_in(root / "data" / directory, root, {".json"}))
    return sorted(sources, key=lambda path: path.relative_to(root).as_posix())


def _public_files_in(directory: Path, root: Path, suffixes: set[str] | frozenset[str]) -> list[Path]:
    if not directory.exists():
        return []
    files: list[Path] = []
    for candidate in directory.rglob("*"):
        if candidate.name == ".gitkeep" and candidate.is_file():
            continue
        if candidate.is_symlink():
            raise ValueError(f"公开归档拒绝符号链接：{candidate.relative_to(root).as_posix()}")
        if candidate.is_dir():
            continue
        if not candidate.is_file() or candidate.suffix.lower() not in suffixes:
            raise ValueError(f"公开归档拒绝未知文件：{candidate.relative_to(root).as_posix()}")
        files.append(_validated_source(candidate, root))
    return files


def _validated_source(source: Path, root: Path) -> Path:
    if source.is_symlink():
        raise ValueError(f"公开归档拒绝符号链接：{source.relative_to(root).as_posix()}")
    resolved = source.resolve(strict=True)
    try:
        relative = resolved.relative_to(root)
    except ValueError as error:
        raise ValueError("公开归档拒绝工作区外文件。") from error
    _validate_relative_path(relative)
    return resolved


def _validate_relative_path(relative: Path) -> None:
    parts = PurePosixPath(relative.as_posix()).parts
    if relative.is_absolute() or not parts or any(part in {"", ".", ".."} for part in parts):
        raise ValueError("公开归档拒绝绝对路径或路径穿越。")


def _synchronize_archive_tree(worktree: Path, public_sources: list[Path], *, source_root: Path = ROOT) -> None:
    source_root = source_root.resolve()
    for relative in ARCHIVE_PATHS:
        target = worktree / relative
        if target.is_symlink():
            raise ValueError(f"归档 worktree 拒绝符号链接：{relative}")
        if target.exists():
            shutil.rmtree(target)
    for source in public_sources:
        relative = source.relative_to(source_root)
        _validate_relative_path(relative)
        target = worktree / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if _is_public_data_json(relative):
            _write_public_json_projection(source, relative, target)
        else:
            shutil.copy2(source, target)


def _write_public_json_projection(source: Path, relative: Path, target: Path) -> None:
    projected = _public_json_projection(source, relative)
    target.write_text(json.dumps(projected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _validate_public_json_projections(public_sources: list[Path], source_root: Path) -> None:
    source_root = source_root.resolve()
    for source in public_sources:
        relative = source.relative_to(source_root)
        if _is_public_data_json(relative):
            _public_json_projection(source, relative)


def _public_json_projection(source: Path, relative: Path) -> object:
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"public archive rejects invalid JSON: {relative.as_posix()}") from error
    return project_archive_json(PurePosixPath(relative.as_posix()), payload)


def _is_public_data_json(relative: Path) -> bool:
    return len(relative.parts) >= 3 and relative.parts[:2] in {
        ("data", "raw"),
        ("data", "runs"),
        ("data", "selected"),
        ("data", "trends"),
    }


def _stage_and_validate(worktree: Path) -> None:
    _run(["git", "add", "-A"], cwd=worktree)
    _scan_staged_tree(worktree)


def _scan_staged_tree(worktree: Path) -> None:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "-z"],
        cwd=worktree,
        check=True,
        capture_output=True,
    )
    for value in result.stdout.split(b"\0"):
        if not value:
            continue
        relative = Path(value.decode("utf-8"))
        _validate_relative_path(relative)
        normalized = relative.as_posix()
        if FORBIDDEN_PATH_PATTERN.search(normalized):
            raise ValueError("公开归档暂存区包含 SQLite 文件。")
        path = worktree / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError("公开归档暂存区包含无效文件。")
        if FORBIDDEN_CONTENT_PATTERN.search(path.read_bytes()):
            raise ValueError("公开归档暂存区包含敏感内容标记。")


def _commit_and_push(worktree: Path, branch: str, message: str) -> None:
    _run(["git", "config", "user.name", "github-actions[bot]"], cwd=worktree)
    _run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], cwd=worktree)
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
