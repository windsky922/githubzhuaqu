"""Shared, fail-closed path policy for the public weekly archive."""

from __future__ import annotations

import json
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "config" / "public-archive-manifest.json"
SUPPORTED_SCHEMA_VERSION = 1


@lru_cache(maxsize=1)
def load_manifest() -> dict[str, object]:
    """Load and validate the versioned public archive path policy."""
    try:
        payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("公开归档 manifest 无法读取或不是有效 JSON。") from error
    if not isinstance(payload, dict) or payload.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        raise ValueError("公开归档 manifest schema_version 不受支持。")
    root_files = payload.get("root_files")
    recursive_paths = payload.get("recursive_paths")
    forbidden_suffixes = payload.get("forbidden_suffixes")
    if not isinstance(root_files, list) or not isinstance(recursive_paths, dict) or not isinstance(forbidden_suffixes, list):
        raise ValueError("公开归档 manifest 结构无效。")
    normalized_root_files = tuple(_relative_path(item) for item in root_files)
    if len(set(normalized_root_files)) != len(normalized_root_files):
        raise ValueError("公开归档 manifest 包含重复 root_files。")
    normalized_recursive: dict[str, frozenset[str]] = {}
    for directory, suffixes in recursive_paths.items():
        normalized_directory = _relative_path(directory)
        if not isinstance(suffixes, list) or not suffixes or not all(isinstance(item, str) and item.startswith(".") for item in suffixes):
            raise ValueError("公开归档 manifest recursive_paths 无效。")
        normalized_recursive[normalized_directory] = frozenset(item.lower() for item in suffixes)
    if len(set(normalized_recursive)) != len(normalized_recursive):
        raise ValueError("公开归档 manifest 包含重复 recursive_paths。")
    normalized_forbidden = tuple(item.lower() for item in forbidden_suffixes if isinstance(item, str) and item)
    if len(normalized_forbidden) != len(forbidden_suffixes):
        raise ValueError("公开归档 manifest forbidden_suffixes 无效。")
    return {
        "root_files": frozenset(normalized_root_files),
        "recursive_paths": normalized_recursive,
        "forbidden_suffixes": normalized_forbidden,
    }


def public_source_files(root: Path) -> list[Path]:
    """Return all public sources, rejecting unknown files below managed directories."""
    policy = load_manifest()
    sources: list[Path] = []
    for relative in sorted(policy["root_files"]):
        candidate = root / relative
        if candidate.exists():
            sources.append(_validated_source(candidate, root))
    for directory, suffixes in policy["recursive_paths"].items():
        base = root / directory
        if not base.exists():
            continue
        if base.is_symlink():
            raise ValueError(f"公开归档拒绝符号链接：{directory}")
        for candidate in base.rglob("*"):
            if candidate.name == ".gitkeep" and candidate.is_file():
                continue
            if candidate.is_symlink():
                raise ValueError(f"公开归档拒绝符号链接：{candidate.relative_to(root).as_posix()}")
            if candidate.is_dir():
                continue
            relative = _relative_path(candidate.relative_to(root).as_posix())
            if not candidate.is_file() or not is_allowed_path(relative) or candidate.suffix.lower() not in suffixes:
                raise ValueError(f"公开归档拒绝未知文件：{relative}")
            sources.append(_validated_source(candidate, root))
    return sorted(sources)


def expected_paths(sources: Iterable[Path], root: Path) -> set[str]:
    return {validated_relative_path(source.relative_to(root.resolve())) for source in sources}


def is_allowed_path(path: str | PurePosixPath) -> bool:
    try:
        relative = _relative_path(str(path))
    except ValueError:
        return False
    policy = load_manifest()
    lowered = relative.lower()
    if lowered.endswith(tuple(policy["forbidden_suffixes"])):
        return False
    if relative in policy["root_files"]:
        return True
    parts = PurePosixPath(relative).parts
    for directory, suffixes in policy["recursive_paths"].items():
        prefix = PurePosixPath(directory).parts
        if len(parts) > len(prefix) and parts[: len(prefix)] == prefix:
            return PurePosixPath(relative).suffix.lower() in suffixes
    return False


def validate_tree_paths(paths: Iterable[str]) -> set[str]:
    normalized = {validated_relative_path(path) for path in paths}
    unexpected = sorted(path for path in normalized if not is_allowed_path(path))
    if unexpected:
        raise ValueError(f"公开归档拒绝未知路径：{', '.join(unexpected)}")
    return normalized


def validated_relative_path(path: str | Path) -> str:
    return _relative_path(Path(path).as_posix())


def _validated_source(source: Path, root: Path) -> Path:
    if source.is_symlink():
        raise ValueError(f"公开归档拒绝符号链接：{source.relative_to(root).as_posix()}")
    resolved = source.resolve(strict=True)
    try:
        relative = resolved.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError("公开归档拒绝工作区外文件。") from error
    validated_relative_path(relative)
    return resolved


def _relative_path(path: object) -> str:
    if not isinstance(path, str) or not path:
        raise ValueError("公开归档 manifest 路径无效。")
    normalized = PurePosixPath(path.replace("\\", "/"))
    if (
        normalized.is_absolute()
        or not normalized.parts
        or normalized.parts[0].endswith(":")
        or any(part in {"", ".", ".."} for part in normalized.parts)
    ):
        raise ValueError("公开归档拒绝绝对路径或路径穿越。")
    return normalized.as_posix()
