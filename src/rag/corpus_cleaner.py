from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from html.parser import HTMLParser


CORPUS_VERSION = "project-corpus-v2"
CLEANER_VERSION = "stdlib-markdown-html-v1"

_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HTML_ATTR_RE = re.compile(r"\b(?:href|src|width|height|style|class)\s*=", re.IGNORECASE)
_LINKED_IMAGE_RE = re.compile(r"\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)")
_MARKDOWN_IMAGE_RE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_FENCE_RE = re.compile(r"^\s*```[^`\r\n]*$", re.MULTILINE)
_BADGE_RE = re.compile(r"shields\.io|badge|trendshift|img\.shields", re.IGNORECASE)
_PROMPT_INJECTION_RE = re.compile(
    r"ignore\s+(?:all\s+)?previous\s+instructions|system\s+prompt|忽略(?:以上|之前|所有)指令|你现在是",
    re.IGNORECASE,
)
_TOC_RE = re.compile(r"^(?:table of contents|目录|contents)\s*:?$", re.IGNORECASE)


@dataclass(frozen=True)
class CleanedText:
    text: str
    content_hash: str
    noise: dict[str, int]
    is_untrusted: bool


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "svg"}:
            self.hidden_depth += 1
        elif tag in {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "pre", "code"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "svg"} and self.hidden_depth:
            self.hidden_depth -= 1
        elif tag in {"p", "div", "li", "pre", "code"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            self.parts.append(data)


def clean_external_text(value: str) -> CleanedText:
    raw = str(value or "")
    noise = {
        "raw_chars": len(raw),
        "html_tags": len(_HTML_TAG_RE.findall(raw)),
        "html_attributes": len(_HTML_ATTR_RE.findall(raw)),
        "markdown_images": len(re.findall(r"!\[[^\]]*\]\([^)]*\)", raw)),
        "badge_lines": sum(1 for line in raw.splitlines() if _BADGE_RE.search(line)),
        "duplicate_lines": 0,
        "prompt_injection_lines": 0,
        "cleaned_chars": 0,
    }
    text = _HTML_COMMENT_RE.sub("\n", raw)
    text = _FENCE_RE.sub("\n", text)
    text = _LINKED_IMAGE_RE.sub("", text)
    text = _MARKDOWN_IMAGE_RE.sub(lambda match: "" if match.group(0).startswith("!") else match.group(1), text)
    text = _MARKDOWN_LINK_RE.sub(lambda match: match.group(1), text)
    parser = _VisibleTextParser()
    try:
        parser.feed(text)
        text = "".join(parser.parts)
    except Exception:
        text = _HTML_TAG_RE.sub(" ", text)
    output: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = " ".join(raw_line.replace("|", " ").split()).strip("#>*- ")
        if not line or _TOC_RE.fullmatch(line):
            continue
        if _BADGE_RE.search(line):
            continue
        if _PROMPT_INJECTION_RE.search(line):
            noise["prompt_injection_lines"] += 1
            continue
        key = line.casefold()
        if key in seen:
            noise["duplicate_lines"] += 1
            continue
        seen.add(key)
        output.append(line)
    cleaned = "\n".join(output)
    noise["cleaned_chars"] = len(cleaned)
    return CleanedText(
        text=cleaned,
        content_hash=sha256(cleaned.encode("utf-8")).hexdigest(),
        noise=noise,
        is_untrusted=bool(noise["prompt_injection_lines"]),
    )


def clean_internal_text(value: str) -> str:
    lines = []
    seen = set()
    for raw_line in str(value or "").splitlines():
        line = " ".join(raw_line.split())
        if line and line.casefold() not in seen:
            seen.add(line.casefold())
            lines.append(line)
    return "\n".join(lines)


def content_hash(value: str) -> str:
    return sha256(str(value or "").encode("utf-8")).hexdigest()
