from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

INCLUDED_SUFFIXES = {".py", ".yml", ".yaml", ".md", ".json", ".example", ".txt"}
EXCLUDED_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", "data", "reports"}

SECRET_PATTERNS = {
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    "telegram_bot_token": re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{30,}\b"),
    "generic_secret_assignment": re.compile(
        r"(?i)\b(api[_-]?key|token|secret|password|chat[_-]?id)\b\s*[:=]\s*['\"]?[A-Za-z0-9_./:+-]{12,}"
    ),
}

ALLOWLIST_MARKERS = (
    "${{ secrets.",
    "os.getenv(",
    "ENV:",
    "GH_SEARCH_TOKEN=",
    "KIMI_API_KEY=",
    "KIMI_MODEL=",
    "TELEGRAM_BOT_TOKEN=",
    "TELEGRAM_CHAT_ID=",
)


def scan_repository(root: Path = ROOT) -> list[str]:
    findings: list[str] = []
    for path in _iter_text_files(root):
        for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            for name, pattern in SECRET_PATTERNS.items():
                if _is_allowlisted(line, name):
                    continue
                if pattern.search(line):
                    relative = path.relative_to(root).as_posix()
                    findings.append(f"{relative}:{line_number}: {name}")
    return findings


def _iter_text_files(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        if path.suffix in INCLUDED_SUFFIXES or path.name == ".env.example":
            files.append(path)
    return files


def _is_allowlisted(line: str, pattern_name: str) -> bool:
    if pattern_name in {"github_token", "telegram_bot_token"}:
        return False
    return any(marker in line for marker in ALLOWLIST_MARKERS)


def main() -> int:
    findings = scan_repository()
    if findings:
        print("发现疑似密钥或敏感配置：", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return 1
    print("安全检查通过：未发现疑似硬编码密钥。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
