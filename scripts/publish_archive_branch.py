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
from src.public_archive_manifest import expected_paths, load_manifest, public_source_files, validate_tree_paths

_MANIFEST = load_manifest()
ARCHIVE_PATHS = tuple(
    dict.fromkeys(
        [PurePosixPath(path).parts[0] for path in _MANIFEST["root_files"]]
        + [PurePosixPath(path).parts[0] for path in _MANIFEST["recursive_paths"]]
    )
)
PUBLIC_DATA_DIRECTORIES = tuple(
    PurePosixPath(path).name
    for path in _MANIFEST["recursive_paths"]
    if path.startswith("data/")
)
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
        expected = _synchronize_archive_tree(worktree, public_sources)
        _stage_and_validate(worktree, expected)
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
    return public_source_files(root)


def _synchronize_archive_tree(worktree: Path, public_sources: list[Path], *, source_root: Path = ROOT) -> set[str]:
    source_root = source_root.resolve()
    expected = expected_paths(public_sources, source_root)
    for target in worktree.iterdir():
        if target.name == ".git":
            continue
        if target.is_symlink():
            raise ValueError(f"归档 worktree 拒绝符号链接：{target.name}")
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    for source in public_sources:
        relative = source.relative_to(source_root)
        target = worktree / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if _is_public_data_json(relative):
            _write_public_json_projection(source, relative, target)
        else:
            shutil.copy2(source, target)
    return expected


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


def _stage_and_validate(worktree: Path, expected: set[str] | None = None) -> None:
    _run(["git", "add", "-A"], cwd=worktree)
    _scan_staged_tree(worktree, expected)


def _scan_staged_tree(worktree: Path, expected: set[str] | None = None) -> None:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "-z"],
        cwd=worktree,
        check=True,
        capture_output=True,
    )
    staged = validate_tree_paths(value.decode("utf-8") for value in result.stdout.split(b"\0") if value)
    if expected is not None and staged != expected:
        missing = sorted(expected - staged)
        unexpected = sorted(staged - expected)
        raise ValueError(f"公开归档暂存 tree 与预期投影不一致：missing={missing}, unexpected={unexpected}")
    modes = subprocess.run(
        ["git", "ls-files", "--cached", "-s", "-z"],
        cwd=worktree,
        check=True,
        capture_output=True,
    )
    for entry in modes.stdout.split(b"\0"):
        if not entry:
            continue
        metadata, _, raw_path = entry.partition(b"\t")
        if metadata.split(b" ", 1)[0] == b"120000":
            raise ValueError(f"公开归档拒绝符号链接：{raw_path.decode('utf-8')}")
    for normalized in sorted(staged):
        relative = Path(normalized)
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
