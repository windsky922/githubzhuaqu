from __future__ import annotations

import json
import html
import re
import sqlite3
import sys
from datetime import UTC, datetime
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models import Repository
from src.quality import apply_quality_signals


def build_pages(root: Path = ROOT) -> list[Path]:
    reports = _report_files(root)
    weekly_dir = root / "docs" / "weekly"
    weekly_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for report in reports:
        target = weekly_dir / report.name
        markdown_text = report.read_text(encoding="utf-8")
        target.write_text(markdown_text, encoding="utf-8")
        written.append(target)
        html_target = weekly_dir / _page_name(report)
        html_target.write_text(_weekly_html_content(markdown_text, report.stem), encoding="utf-8")
        written.append(html_target)

    index = root / "docs" / "index.md"
    index.write_text(_index_content(root, reports), encoding="utf-8")
    written.append(index)
    projects = root / "docs" / "projects.md"
    projects.write_text(_projects_content(root), encoding="utf-8")
    written.append(projects)
    admin_page = root / "docs" / "admin.html"
    admin_page.write_text(_admin_dashboard_content(), encoding="utf-8")
    written.append(admin_page)
    explorer = root / "docs" / "explorer.html"
    explorer.write_text(_explorer_content(), encoding="utf-8")
    written.append(explorer)
    recommendations = root / "docs" / "recommendations.html"
    recommendations.write_text(_recommendations_content(), encoding="utf-8")
    written.append(recommendations)
    subscriptions = root / "docs" / "subscriptions.html"
    subscriptions.write_text(_subscriptions_content(), encoding="utf-8")
    written.append(subscriptions)
    compare = root / "docs" / "compare.html"
    compare.write_text(_compare_content(), encoding="utf-8")
    written.append(compare)
    project_page = root / "docs" / "project.html"
    project_page.write_text(_project_detail_content(), encoding="utf-8")
    written.append(project_page)
    runs_page = root / "docs" / "runs.html"
    runs_page.write_text(_runs_dashboard_content(), encoding="utf-8")
    written.append(runs_page)
    jobs_page = root / "docs" / "jobs.html"
    jobs_page.write_text(_jobs_dashboard_content(), encoding="utf-8")
    written.append(jobs_page)
    job_page = root / "docs" / "job.html"
    job_page.write_text(_job_detail_content(), encoding="utf-8")
    written.append(job_page)
    projects_json = root / "docs" / "projects.json"
    projects_json.write_text(_json_text(_public_projects(root)), encoding="utf-8")
    written.append(projects_json)
    runs_json = root / "docs" / "runs.json"
    runs_json.write_text(_json_text(_public_runs(root, reports)), encoding="utf-8")
    written.append(runs_json)
    jobs_json = root / "docs" / "jobs.json"
    jobs_json.write_text(_json_text(_public_jobs(root, reports)), encoding="utf-8")
    written.append(jobs_json)
    profiles_json = root / "docs" / "profiles.json"
    profiles_json.write_text(_json_text(_public_profiles(root)), encoding="utf-8")
    written.append(profiles_json)
    profiles_page = root / "docs" / "profiles.html"
    profiles_page.write_text(_profiles_page_content(), encoding="utf-8")
    written.append(profiles_page)
    feed = root / "docs" / "feed.xml"
    feed.write_text(_feed_content(root, reports), encoding="utf-8")
    written.append(feed)
    return written


def _report_files(root: Path) -> list[Path]:
    reports_dir = root / "reports"
    if not reports_dir.exists():
        return []
    return sorted(
        [path for path in reports_dir.glob("*.md") if path.name != ".gitkeep"],
        key=lambda path: path.stem,
        reverse=True,
    )


def _index_content(root: Path, reports: list[Path]) -> str:
    lines = [
        "# GitHub 每周热点项目周报归档",
        "",
        "这里归档 GitHub Weekly Agent 自动生成的中文周报。",
        "",
        "## 最新周报",
        "",
    ]
    if reports:
        latest = reports[0]
        lines.append(f"- [{latest.stem}](weekly/{_page_name(latest)})")
        lines.extend(_latest_summary_lines(root, latest.stem))
    else:
        lines.append("- 暂无周报。")

    lines.extend(["", "## 全部周报", ""])
    if reports:
        lines.extend(_report_line(root, report) for report in reports)
    else:
        lines.append("- 暂无周报。")

    lines.extend(
        [
            "",
            "## 项目文档",
            "",
            "- [本地管理首页](admin.html)",
            "- [项目筛选页](explorer.html)",
            "- [项目详情页](project.html)",
            "- [项目对比页](compare.html)",
            "- [运行状态面板](runs.html)",
            "- [任务状态面板](jobs.html)",
            "- [任务详情页](job.html)",
            "- [历史项目索引](projects.html)",
            "- [公共项目 JSON](projects.json)",
            "- [公共运行 JSON](runs.json)",
            "- [公共任务 JSON](jobs.json)",
            "- [个性化方向页](profiles.html)",
            "- [个性化方向 JSON](profiles.json)",
            "- [RSS 订阅](feed.xml)",
            "- [后端 API 说明](api.html)",
            "- [历史归档查询说明](archive-query.html)",
            "- [数据契约说明](data-contracts.html)",
            "- [架构说明](architecture.html)",
            "- [配置说明](setup.html)",
            "- [开发路线图](roadmap.html)",
            "- [未来更新规划](future-plan.html)",
            "- [操作日志](operation-log.html)",
            "",
        ]
    )
    if "- [个性化推荐页](recommendations.html)" not in lines:
        lines.insert(-1, "- [个性化推荐页](recommendations.html)")
    if "- [订阅配置页](subscriptions.html)" not in lines:
        lines.insert(-1, "- [订阅配置页](subscriptions.html)")
    return "\n".join(lines)


def _report_line(root: Path, report: Path) -> str:
    summary = _run_summary(root, report.stem)
    trends = _trend_summary(root, report.stem)
    if not summary:
        return f"- [{report.stem}](weekly/{_page_name(report)})"
    selected_count = summary.get("selected_count", 0)
    kimi = "Kimi" if summary.get("kimi_used") else "降级模板"
    telegram = "已推送" if summary.get("telegram_sent") else "未推送"
    trend_text = _report_trend_text(trends)
    suffix = f"，{trend_text}" if trend_text else ""
    return f"- [{report.stem}](weekly/{_page_name(report)})：{selected_count} 个项目，{kimi}，Telegram {telegram}{suffix}"


def _page_name(markdown_path: Path) -> str:
    return markdown_path.with_suffix(".html").name


def _weekly_html_content(markdown_text: str, title: str) -> str:
    body = _weekly_html_body(markdown_text)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GitHub 周报 {html.escape(title)}</title>
  <style>
    body {{ margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.7; }}
    main {{ max-width: 960px; margin: 0 auto; padding: 32px 20px 56px; }}
    article {{ background: #fff; border: 1px solid #d8dee8; padding: 28px; }}
    h1, h2, h3, h4 {{ line-height: 1.3; }}
    a {{ color: #0969da; }}
    code {{ background: #eef2f7; padding: 2px 5px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 18px 0; display: block; overflow-x: auto; }}
    th, td {{ border: 1px solid #d8dee8; padding: 8px 10px; text-align: left; vertical-align: top; }}
    th {{ background: #f1f4f8; }}
    hr {{ border: 0; border-top: 1px solid #d8dee8; margin: 24px 0; }}
  </style>
</head>
<body>
  <main>
    <article>
{body}
    </article>
  </main>
</body>
</html>
"""


def _markdown_line_to_html(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""
    if stripped == "---":
        return "      <hr>"
    heading_match = re.match(r"^(#{1,4})\s+(.+)$", stripped)
    if heading_match:
        level = len(heading_match.group(1))
        return f"      <h{level}>{_inline_markdown_to_html(heading_match.group(2))}</h{level}>"
    if stripped.startswith("- "):
        return f"      <p>• {_inline_markdown_to_html(stripped[2:])}</p>"
    return f"      <p>{_inline_markdown_to_html(stripped)}</p>"


def _inline_markdown_to_html(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<(?:img|source)\b[^>]*(?:>|$)", "", text, flags=re.IGNORECASE)
    text = re.sub(
        r'<a\s+[^>]*href=["\'](https?://[^"\']+)["\'][^>]*>(.*?)</a>',
        lambda match: f"[{re.sub(r'<[^>]+>', '', match.group(2))}]({match.group(1)})",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"<a\b[^>]*(?:>|$)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(
        r"(https?://[^\s<]+)",
        lambda match: f'<a href="{match.group(1)}">{match.group(1)}</a>',
        escaped,
    )
    return escaped


def _weekly_html_body(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    blocks = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if _is_markdown_table_row(line):
            table_lines = []
            while index < len(lines) and _is_markdown_table_row(lines[index]):
                table_lines.append(lines[index])
                index += 1
            blocks.append(_markdown_table_to_html(table_lines))
            continue
        blocks.append(_markdown_line_to_html(line))
        index += 1
    return "\n".join(block for block in blocks if block)


def _markdown_line_to_html(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""
    if stripped == "---":
        return "      <hr>"
    heading_match = re.match(r"^(#{1,4})\s+(.+)$", stripped)
    if heading_match:
        level = len(heading_match.group(1))
        return f"      <h{level}>{_inline_markdown_to_html(heading_match.group(2))}</h{level}>"
    if stripped.startswith("- "):
        return f"      <p>• {_inline_markdown_to_html(stripped[2:])}</p>"
    return f"      <p>{_inline_markdown_to_html(stripped)}</p>"


def _is_markdown_table_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def _is_markdown_table_separator(line: str) -> bool:
    return bool(re.fullmatch(r"[\s|:\-]+", line.strip()))


def _markdown_table_to_html(lines: list[str]) -> str:
    rows = [_markdown_table_cells(line) for line in lines if not _is_markdown_table_separator(line)]
    if not rows:
        return ""
    header, body_rows = rows[0], rows[1:]
    header_html = "".join(f"<th>{_inline_markdown_to_html(cell)}</th>" for cell in header)
    body_html = "\n".join(
        "        <tr>" + "".join(f"<td>{_inline_markdown_to_html(cell)}</td>" for cell in row) + "</tr>"
        for row in body_rows
    )
    return f"""      <table>
        <thead><tr>{header_html}</tr></thead>
        <tbody>
{body_html}
        </tbody>
      </table>"""


def _markdown_table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _inline_markdown_to_html(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", escaped)
    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda match: (
            f'<a href="{html.escape(match.group(2), quote=True)}">{match.group(1)}</a>'
            if match.group(2).startswith(("http://", "https://"))
            else match.group(1)
        ),
        escaped,
    )
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(
        r'(?<!href=")(?<!">)(?<!&quot;)(https?://[^\s<)&"]+)',
        lambda match: f'<a href="{match.group(1)}">{match.group(1)}</a>',
        escaped,
    )
    escaped = re.sub(r"!\[([^\]]*)\]\([^)]*(?:\)|$)", r"\1", escaped)
    escaped = re.sub(r'\[(<a href="[^"]+">[^<]+</a>)', r"\1", escaped)
    return escaped


def _markdown_line_to_html(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""
    if stripped == "---":
        return "      <hr>"
    heading_match = re.match(r"^(#{1,4})\s+(.+)$", stripped)
    if heading_match:
        level = len(heading_match.group(1))
        return f"      <h{level}>{_inline_markdown_to_html(heading_match.group(2))}</h{level}>"
    if stripped.startswith("- "):
        return f"      <p>• {_inline_markdown_to_html(stripped[2:])}</p>"
    return f"      <p>{_inline_markdown_to_html(stripped)}</p>"


def _inline_markdown_to_html(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<(?:img|source)\b[^>]*(?:>|$)", "", text, flags=re.IGNORECASE)
    text = re.sub(
        r'<a\s+[^>]*href=["\'](https?://[^"\']+)["\'][^>]*>(.*?)</a>',
        lambda match: f"[{re.sub(r'<[^>]+>', '', match.group(2))}]({match.group(1)})",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"<a\b[^>]*(?:>|$)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    escaped = html.escape(text)
    escaped = re.sub(r"!\[([^\]]*)\]\([^)]*(?:\)|$)", r"\1", escaped)
    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda match: (
            f'<a href="{html.escape(match.group(2), quote=True)}">{match.group(1)}</a>'
            if match.group(2).startswith(("http://", "https://"))
            else match.group(1)
        ),
        escaped,
    )
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(
        r'(?<!href=")(?<!">)(?<!&quot;)(https?://[^\s<)&"]+)',
        lambda match: f'<a href="{match.group(1)}">{match.group(1)}</a>',
        escaped,
    )
    escaped = re.sub(r'\[\]\((<a href="[^"]+">[^<]+</a>)\)', r"\1", escaped)
    escaped = re.sub(r'\[(<a href="[^"]+">[^<]+</a>)', r"\1", escaped)
    return escaped


def _markdown_line_to_html(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""
    if stripped == "---":
        return "      <hr>"
    heading_match = re.match(r"^(#{1,4})\s+(.+)$", stripped)
    if heading_match:
        level = len(heading_match.group(1))
        return f"      <h{level}>{_inline_markdown_to_html(heading_match.group(2))}</h{level}>"
    if stripped.startswith("- "):
        return f"      <p>• {_inline_markdown_to_html(stripped[2:])}</p>"
    return f"      <p>{_inline_markdown_to_html(stripped)}</p>"


def _run_summary(root: Path, run_date: str) -> dict:
    path = root / "data" / "runs" / f"{run_date}.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _trend_summary(root: Path, run_date: str) -> dict:
    path = root / "data" / "trends" / f"{run_date}.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _latest_summary_lines(root: Path, run_date: str) -> list[str]:
    summary = _run_summary(root, run_date)
    trends = _trend_summary(root, run_date)
    if not summary and not trends:
        return []

    lines = ["", "## 最新运行摘要", ""]
    if summary:
        kimi = "Kimi" if summary.get("kimi_used") else "降级模板"
        telegram = "已推送" if summary.get("telegram_sent") else "未推送"
        collector_errors = len(summary.get("collector_errors") or [])
        lines.extend(
            [
                f"- 入选项目：{summary.get('selected_count', 0)} 个",
                f"- 采集候选：{summary.get('collected_count', 0)} 个",
                f"- 生成方式：{kimi}",
                f"- Telegram：{telegram}",
                f"- 采集错误：{collector_errors} 条",
            ]
        )
    points = trends.get("summary_points") or []
    if points:
        lines.extend(["", "## 最新趋势要点", ""])
        lines.extend(f"- {point}" for point in points[:5])
    return lines


def _report_trend_text(trends: dict) -> str:
    if not trends:
        return ""
    parts = []
    top_languages = trends.get("top_languages") or []
    top_categories = trends.get("top_categories") or []
    if top_languages:
        parts.append(f"主语言 {top_languages[0].get('name')}")
    if top_categories:
        parts.append(f"主方向 {top_categories[0].get('name')}")
    if trends.get("total_star_growth") is not None:
        parts.append(f"新增 Star {trends.get('total_star_growth')}")
    if trends.get("trending_project_count") is not None:
        parts.append(f"Trending 项目 {trends.get('trending_project_count')}")
    return "，".join(part for part in parts if part)


def _projects_content(root: Path) -> str:
    rows = _selected_project_rows(root)
    lines = [
        "# 历史项目索引",
        "",
        "这里汇总历次周报入选项目，便于按日期、语言和方向回看。",
        "",
        "| 日期 | 项目 | 来源 | Trending 排名 | 方向 | 语言 | Star | 新增 Star | 风险提示 | 链接 |",
        "|---|---|---|---:|---|---|---:|---:|---:|---|",
    ]
    if rows:
        lines.extend(_project_table_row(row) for row in rows)
    else:
        lines.append("| - | 暂无项目 | - | - | - | - | 0 | 0 | 0 | - |")
    lines.extend(["", "## 返回", "", "- [周报归档首页](index.html)", ""])
    return "\n".join(lines)


def _admin_dashboard_content() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GitHub 周报本地管理首页</title>
  <style>
    :root {
      --bg: #f6f8fb;
      --panel: #ffffff;
      --text: #172033;
      --muted: #667085;
      --line: #d8dee8;
      --accent: #2563eb;
      --ok: #15803d;
      --bad: #b42318;
      --warn: #a16207;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.55;
    }
    header {
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }
    .wrap {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
    }
    .topbar {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
      padding: 18px 0;
    }
    h1 {
      margin: 0;
      font-size: 24px;
      line-height: 1.2;
    }
    main { padding: 24px 0 40px; }
    .grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }
    .panel,
    .card {
      border: 1px solid var(--line);
      background: var(--panel);
      padding: 16px;
    }
    .panel { margin-bottom: 14px; }
    .card {
      min-height: 140px;
      display: grid;
      gap: 8px;
      align-content: start;
    }
    .overview {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-top: 12px;
    }
    .metric {
      border: 1px solid var(--line);
      background: #f9fafb;
      padding: 10px;
    }
    .metric span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }
    .metric strong {
      display: block;
      margin-top: 4px;
      font-size: 20px;
      overflow-wrap: anywhere;
    }
    .result-panel {
      margin-top: 12px;
      border: 1px solid var(--line);
      background: #f9fafb;
      padding: 12px;
      display: grid;
      gap: 8px;
    }
    .result-panel h3 {
      margin: 0;
      font-size: 16px;
    }
    .result-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
    }
    .result-item {
      border: 1px solid var(--line);
      background: var(--panel);
      padding: 8px;
      overflow-wrap: anywhere;
    }
    .result-item span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }
    .result-item strong {
      display: block;
      margin-top: 4px;
    }
    .split {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 12px;
      margin-top: 12px;
    }
    .facet-list,
    .search-results {
      display: grid;
      gap: 8px;
    }
    .facet-row,
    .search-row {
      border: 1px solid var(--line);
      background: #f9fafb;
      padding: 10px;
      overflow-wrap: anywhere;
    }
    .facet-row strong,
    .search-row strong {
      display: block;
    }
    .facet-row span,
    .search-row span {
      color: var(--muted);
      font-size: 12px;
    }
    .search-form {
      display: grid;
      grid-template-columns: minmax(180px, 1fr) minmax(120px, .45fr) minmax(120px, .45fr) 96px;
      gap: 8px;
      margin-top: 12px;
      align-items: end;
    }
    .workflow-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }
    .workflow-card {
      border: 1px solid var(--line);
      background: #f9fafb;
      padding: 12px;
      display: grid;
      gap: 8px;
      min-height: 128px;
    }
    .workflow-card h3 {
      margin: 0;
      font-size: 15px;
    }
    .workflow-card p {
      font-size: 13px;
    }
    .task-form {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      align-items: end;
    }
    label {
      display: grid;
      gap: 5px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
    }
    input,
    select,
    textarea,
    button {
      height: 38px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel);
      color: var(--text);
      font: inherit;
      padding: 0 10px;
    }
    textarea {
      min-height: 120px;
      padding: 10px;
      resize: vertical;
    }
    button {
      cursor: pointer;
      border-color: var(--accent);
      background: var(--accent);
      color: #fff;
      font-weight: 700;
    }
    button:disabled {
      cursor: not-allowed;
      border-color: var(--line);
      background: #e5e7eb;
      color: var(--muted);
    }
    .check-label {
      grid-template-columns: 18px 1fr;
      align-items: center;
      gap: 8px;
      min-height: 38px;
    }
    .check-label input {
      width: 16px;
      height: 16px;
      padding: 0;
    }
    .task-status {
      margin-top: 10px;
      color: var(--muted);
      font-size: 13px;
      overflow-wrap: anywhere;
    }
    .toolbar {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 10px;
    }
    .filter-button {
      width: fit-content;
      height: 32px;
      border-color: var(--line);
      background: var(--panel);
      color: var(--accent);
      font-size: 13px;
    }
    .filter-button.active {
      border-color: var(--accent);
      background: var(--accent);
      color: #fff;
    }
    .workbench-list {
      display: grid;
      gap: 8px;
    }
    .job-row {
      display: grid;
      grid-template-columns: minmax(0, 1.25fr) 90px minmax(0, .9fr) minmax(0, 1.1fr) minmax(180px, .9fr);
      gap: 10px;
      align-items: start;
      border: 1px solid var(--line);
      padding: 10px;
      background: #f9fafb;
    }
    .job-row span {
      color: var(--muted);
      font-size: 12px;
    }
    .job-row strong {
      overflow-wrap: anywhere;
    }
    .job-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .secondary-button {
      width: fit-content;
      height: 28px;
      padding: 0 8px;
      border-color: var(--line);
      background: var(--panel);
      color: var(--accent);
      font-size: 12px;
    }
    .execute-button {
      border-color: var(--warn);
      color: var(--warn);
    }
    .retry-button {
      border-color: var(--bad);
      color: var(--bad);
    }
    .precheck-result {
      flex-basis: 100%;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
      overflow-wrap: anywhere;
    }
    .precheck-result.ok {
      color: var(--ok);
    }
    .precheck-result.blocked {
      color: var(--bad);
    }
    .card h2,
    .panel h2 {
      margin: 0;
      font-size: 18px;
    }
    p {
      margin: 0;
      color: var(--muted);
    }
    a {
      color: var(--accent);
      font-weight: 700;
      text-decoration: none;
    }
    .links {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .status {
      display: inline-block;
      width: fit-content;
      padding: 2px 8px;
      border: 1px solid var(--line);
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
    }
    .status.ok { color: var(--ok); border-color: #bbf7d0; background: #f0fdf4; }
    .status.bad { color: var(--bad); border-color: #fecaca; background: #fff1f2; }
    .status.warn { color: var(--warn); border-color: #fde68a; background: #fffbeb; }
    .status.succeeded { color: var(--ok); border-color: #bbf7d0; background: #f0fdf4; }
    .status.failed { color: var(--bad); border-color: #fecaca; background: #fff1f2; }
    .status.planned,
    .status.running { color: var(--warn); border-color: #fde68a; background: #fffbeb; }
    .capabilities {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin-top: 10px;
    }
    .capability {
      border: 1px solid var(--line);
      padding: 8px;
      font-size: 13px;
      overflow-wrap: anywhere;
    }
    pre {
      margin: 10px 0 0;
      overflow: auto;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: #0f172a;
      color: #e5e7eb;
      padding: 12px;
      border-radius: 6px;
      font-size: 12px;
    }
    @media (max-width: 860px) {
      .topbar { align-items: flex-start; flex-direction: column; }
      .grid,
      .overview,
      .result-grid,
      .split,
      .search-form,
      .workflow-grid,
      .task-form,
      .capabilities { grid-template-columns: 1fr; }
      .job-row { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <div class="wrap topbar">
      <h1>GitHub 周报本地管理首页</h1>
      <nav class="links">
        <a href="index.html">周报归档</a>
        <a href="explorer.html">项目筛选</a>
        <a href="recommendations.html">个性化推荐</a>
        <a href="subscriptions.html">订阅配置</a>
        <a href="runs.html">运行状态</a>
        <a href="jobs.html">任务状态</a>
      </nav>
    </div>
  </header>
  <main class="wrap">
    <section class="panel">
      <h2>后端连接</h2>
      <p id="apiMode">检测中</p>
      <div id="health"></div>
    </section>
    <section class="panel">
      <h2>数据概览</h2>
      <div id="overview" class="overview"></div>
      <div id="latestLinks" class="links"></div>
      <div id="latestJobResult" class="result-panel"></div>
    </section>
    <section class="panel">
      <h2>数据库与语料</h2>
      <div id="databaseOverview" class="overview"></div>
      <div id="feedbackSummary" class="result-panel"></div>
      <div class="split">
        <div>
          <h3>主要分面</h3>
          <div id="databaseFacets" class="facet-list"></div>
        </div>
        <div>
          <h3>趋势摘要</h3>
          <div id="databaseTrends" class="facet-list"></div>
        </div>
      </div>
      <div class="search-form">
        <label>语料搜索
          <input id="corpusQuery" type="text" placeholder="agent workflow">
        </label>
        <label>语言
          <input id="corpusLanguage" type="text" placeholder="Python">
        </label>
        <label>方向
          <input id="corpusCategory" type="text" placeholder="AI Agent">
        </label>
        <button id="runCorpusSearch" type="button">搜索</button>
      </div>
      <div id="corpusSearchResults" class="search-results"></div>
      <div class="search-form">
        <label>RAG 问题
          <input id="ragQuery" type="text" placeholder="哪些 Agent 项目适合学习工作流？">
        </label>
        <label>检索方式
          <select id="ragMode">
            <option value="ask">RAG 问答</option>
            <option value="retrieve">FTS 证据检索</option>
            <option value="vector">本地向量检索</option>
          </select>
        </label>
        <label>语言
          <input id="ragLanguage" type="text" placeholder="Python">
        </label>
        <button id="runRagSearch" type="button">检索</button>
      </div>
      <div id="ragSearchResults" class="search-results"></div>
      <h3>开发上下文 RAG</h3>
      <div class="search-form">
        <label>开发上下文问题
          <input id="devContextQuery" type="text" placeholder="反馈入口 / 最近测试失败 / RAG 维护">
        </label>
        <label>来源
          <select id="devContextSource">
            <option value="">全部</option>
            <option value="document">文档</option>
            <option value="git_diff">Git diff</option>
            <option value="test_output">测试输出</option>
            <option value="security_check">安全检查</option>
          </select>
        </label>
        <button id="indexDevContext" type="button">索引开发上下文</button>
        <button id="askDevContext" type="button">问答</button>
        <button id="runDevContextSearch" type="button">搜索</button>
      </div>
      <div id="devContextResults" class="search-results"></div>
      <div id="devContextJobs" class="search-results"></div>
      <div id="ragQualitySummary" class="search-results"></div>
      <div id="ragEvaluationTrends" class="search-results"></div>
      <div class="search-form">
        <label>维护数量
          <input id="ragMaintenanceLimit" type="number" min="1" max="100" value="10">
        </label>
        <label>覆盖检查
          <input id="ragMaintenanceCoverageLimit" type="number" min="1" max="500" value="100">
        </label>
        <button id="planRagMaintenance" type="button">生成维护计划</button>
      </div>
      <div id="ragMaintenanceResults" class="search-results"></div>
      <div class="search-form">
        <label>回填数量
          <input id="ragBackfillLimit" type="number" min="1" max="100" value="5">
        </label>
        <button id="previewRagBackfill" type="button">预览回填</button>
        <label>
          <input id="confirmRagBackfill" type="checkbox">
          确认写入 SQLite
        </label>
        <button id="runRagBackfill" type="button">执行回填</button>
      </div>
      <div id="ragBackfillResults" class="search-results"></div>
    </section>
    <section class="panel">
      <h2>核心工作流</h2>
      <div id="workflowBoard" class="workflow-grid"></div>
    </section>
    <section class="panel">
      <h2>创建 planned 周报任务</h2>
      <div class="task-form">
        <label>个性化方向
          <input id="taskProfile" type="text" placeholder="agent_development">
        </label>
        <label>回看天数
          <input id="taskDaysBack" type="number" min="1" max="30" value="7">
        </label>
        <label>来源
          <select id="taskSource">
            <option value="github_trending">GitHub Trending</option>
            <option value="github_search">GitHub Search</option>
            <option value="">默认来源</option>
          </select>
        </label>
        <label class="check-label">
          <input id="taskPreviewMode" name="taskDeliveryMode" type="radio" value="preview" checked>
          预览，不推送
        </label>
        <label class="check-label">
          <input id="taskDeliveryMode" name="taskDeliveryMode" type="radio" value="delivery">
          确认真实推送
        </label>
        <button id="createTask" type="button">创建任务</button>
      </div>
      <p id="createTaskStatus" class="task-status">静态模式只能查看；启动本地后端或添加 api=1 后可创建任务。</p>
    </section>
    <section class="panel">
      <h2>任务工作台</h2>
      <div class="toolbar" aria-label="任务筛选">
        <button class="filter-button active" type="button" data-job-filter="attention">重点</button>
        <button class="filter-button" type="button" data-job-filter="failed">失败</button>
        <button class="filter-button" type="button" data-job-filter="planned">待执行</button>
        <button class="filter-button" type="button" data-job-filter="running">运行中</button>
        <button class="filter-button" type="button" data-job-filter="all">全部</button>
      </div>
      <div id="jobWorkbench" class="workbench-list"></div>
    </section>
    <section class="panel">
      <h2>项目 Agent 任务</h2>
      <div id="projectAgentTaskSummary" class="overview"></div>
      <div id="projectAgentTaskWorkbench" class="workbench-list"></div>
    </section>
    <section class="grid" aria-label="管理入口">
      <article class="card">
        <h2>项目</h2>
        <p>查看热点项目、个性化方向、相似项目和公开 JSON。</p>
        <div class="links">
          <a href="explorer.html">项目筛选</a>
          <a href="projects.json">projects.json</a>
          <a href="profiles.html">个性化方向</a>
        </div>
      </article>
      <article class="card">
        <h2>运行</h2>
        <p>查看每次采集、生成、推送和观测指标。</p>
        <div class="links">
          <a href="runs.html">运行状态</a>
          <a href="runs.json">runs.json</a>
          <a href="feed.xml">RSS</a>
        </div>
      </article>
      <article class="card">
        <h2>任务</h2>
        <p>创建 planned 任务，进入单任务详情页后执行检查、执行和重试。</p>
        <div class="links">
          <a href="jobs.html">任务状态</a>
          <a href="job.html">任务详情</a>
          <a href="jobs.json">jobs.json</a>
        </div>
      </article>
    </section>
  </main>
  <script>
    const apiMode = document.getElementById("apiMode");
    const health = document.getElementById("health");
    const overview = document.getElementById("overview");
    const latestLinks = document.getElementById("latestLinks");
    const latestJobResult = document.getElementById("latestJobResult");
    const workflowBoard = document.getElementById("workflowBoard");
    const jobWorkbench = document.getElementById("jobWorkbench");
    const projectAgentTaskSummary = document.getElementById("projectAgentTaskSummary");
    const projectAgentTaskWorkbench = document.getElementById("projectAgentTaskWorkbench");
    const databaseOverview = document.getElementById("databaseOverview");
    const feedbackSummary = document.getElementById("feedbackSummary");
    const databaseFacets = document.getElementById("databaseFacets");
    const databaseTrends = document.getElementById("databaseTrends");
    const corpusSearchResults = document.getElementById("corpusSearchResults");
    const ragSearchResults = document.getElementById("ragSearchResults");
    const devContextResults = document.getElementById("devContextResults");
    const devContextJobs = document.getElementById("devContextJobs");
    const ragQualitySummary = document.getElementById("ragQualitySummary");
    const ragEvaluationTrends = document.getElementById("ragEvaluationTrends");
    const ragMaintenanceResults = document.getElementById("ragMaintenanceResults");
    const ragBackfillResults = document.getElementById("ragBackfillResults");
    const adminState = { jobs: [], jobFilter: "attention" };
    const createControls = {
      profile: document.getElementById("taskProfile"),
      daysBack: document.getElementById("taskDaysBack"),
      source: document.getElementById("taskSource"),
      previewMode: document.getElementById("taskPreviewMode"),
      deliveryMode: document.getElementById("taskDeliveryMode"),
      button: document.getElementById("createTask"),
      status: document.getElementById("createTaskStatus"),
    };
    const searchControls = {
      query: document.getElementById("corpusQuery"),
      language: document.getElementById("corpusLanguage"),
      category: document.getElementById("corpusCategory"),
      button: document.getElementById("runCorpusSearch"),
    };
    const ragControls = {
      query: document.getElementById("ragQuery"),
      mode: document.getElementById("ragMode"),
      language: document.getElementById("ragLanguage"),
      button: document.getElementById("runRagSearch"),
    };
    const devContextControls = {
      query: document.getElementById("devContextQuery"),
      source: document.getElementById("devContextSource"),
      indexButton: document.getElementById("indexDevContext"),
      askButton: document.getElementById("askDevContext"),
      searchButton: document.getElementById("runDevContextSearch"),
    };
    const ragBackfillControls = {
      limit: document.getElementById("ragBackfillLimit"),
      previewButton: document.getElementById("previewRagBackfill"),
      confirm: document.getElementById("confirmRagBackfill"),
      runButton: document.getElementById("runRagBackfill"),
    };
    const ragMaintenanceControls = {
      limit: document.getElementById("ragMaintenanceLimit"),
      coverageLimit: document.getElementById("ragMaintenanceCoverageLimit"),
      button: document.getElementById("planRagMaintenance"),
    };

    loadHealth();
    loadOverview();
    loadProjectAgentTasks();
    loadDatabaseInsights();
    setupCreateTask();
      setupCorpusSearch();
      setupRagSearch();
      setupDevContext();
      setupRagBackfill();
    setupRagMaintenance();
    bindWorkbenchFilters();
    jobWorkbench.addEventListener("click", handleWorkbenchAction);

    function bindWorkbenchFilters() {
      document.querySelectorAll("[data-job-filter]").forEach(button => {
        button.addEventListener("click", () => {
          adminState.jobFilter = button.dataset.jobFilter || "attention";
          document.querySelectorAll("[data-job-filter]").forEach(item => item.classList.toggle("active", item === button));
          renderJobWorkbench();
        });
      });
    }

    function setupCreateTask() {
      if (!shouldUseApi()) {
        createControls.button.disabled = true;
        return;
      }
      createControls.status.textContent = "API 模式可创建 planned 任务；创建后进入任务详情页执行检查或运行。";
      createControls.button.addEventListener("click", createPlannedTask);
    }

    function setupCorpusSearch() {
      if (!shouldUseApi()) {
        searchControls.button.disabled = true;
        corpusSearchResults.innerHTML = '<p>语料搜索需要本地后端或 api=1 模式。</p>';
        return;
      }
      searchControls.button.addEventListener("click", runCorpusSearch);
      searchControls.query.addEventListener("keydown", event => {
        if (event.key === "Enter") runCorpusSearch();
      });
    }

    function setupRagSearch() {
      if (!shouldUseApi()) {
        ragControls.button.disabled = true;
        ragSearchResults.innerHTML = '<p>RAG 检索需要本地后端或 api=1 模式。</p>';
        return;
      }
      ragControls.button.addEventListener("click", runRagSearch);
      ragControls.query.addEventListener("keydown", event => {
        if (event.key === "Enter") runRagSearch();
      });
    }

    function setupDevContext() {
      if (!shouldUseApi()) {
        devContextControls.indexButton.disabled = true;
        devContextControls.askButton.disabled = true;
        devContextControls.searchButton.disabled = true;
        devContextResults.innerHTML = '<p>开发上下文索引需要本地后端或 api=1 模式。</p>';
        return;
      }
      devContextControls.indexButton.addEventListener("click", indexDevContext);
      devContextControls.askButton.addEventListener("click", askDevContext);
      devContextControls.searchButton.addEventListener("click", runDevContextSearch);
      devContextControls.query.addEventListener("keydown", event => {
        if (event.key === "Enter") askDevContext();
      });
    }

    function setupRagBackfill() {
      if (!shouldUseApi()) {
        ragBackfillControls.previewButton.disabled = true;
        ragBackfillControls.runButton.disabled = true;
        ragBackfillResults.innerHTML = '<p>RAG 回填需要本地后端或 api=1 模式。</p>';
        return;
      }
      ragBackfillResults.innerHTML = '<p>先预览缺少解释历史的项目，再确认是否写入 SQLite。</p>';
      ragBackfillControls.previewButton.addEventListener("click", () => runRagBackfill(true));
      ragBackfillControls.runButton.addEventListener("click", () => runRagBackfill(false));
    }

    function setupRagMaintenance() {
      if (!shouldUseApi()) {
        ragMaintenanceControls.button.disabled = true;
        ragMaintenanceResults.innerHTML = '<p>RAG 维护计划需要本地后端或 api=1 模式。</p>';
        return;
      }
      ragMaintenanceResults.innerHTML = '<p>根据诊断结果生成 planned 维护任务；执行仍需进入任务详情页确认。</p>';
      ragMaintenanceControls.button.addEventListener("click", runRagMaintenancePlan);
    }

    function runCorpusSearch() {
      const query = searchControls.query.value.trim();
      if (!query) {
        corpusSearchResults.innerHTML = '<p>请输入搜索关键词。</p>';
        return;
      }
      const params = new URLSearchParams();
      params.set("q", query);
      params.set("limit", "8");
      if (searchControls.language.value.trim()) params.set("language", searchControls.language.value.trim());
      if (searchControls.category.value.trim()) params.set("category", searchControls.category.value.trim());
      searchControls.button.disabled = true;
      corpusSearchResults.innerHTML = '<p>搜索中...</p>';
      fetch(`/v1/search?${params.toString()}`, { cache: "no-store" })
        .then(jsonOrThrow)
        .then(data => {
          corpusSearchResults.innerHTML = corpusSearchHtml(data);
        })
        .catch(error => {
          corpusSearchResults.innerHTML = `<p>搜索失败：${escapeHtml(error.message || error)}</p>`;
        })
        .finally(() => {
          searchControls.button.disabled = false;
        });
    }

    function runRagSearch() {
      const query = ragControls.query.value.trim();
      if (!query) {
        ragSearchResults.innerHTML = '<p>请输入 RAG 问题或关键词。</p>';
        return;
      }
      const params = new URLSearchParams();
      params.set("q", query);
      params.set("limit", "6");
      if (ragControls.language.value.trim()) params.set("language", ragControls.language.value.trim());
      const mode = ragControls.mode.value || "retrieve";
      if (mode === "vector") params.set("auto_build", "true");
      const endpoint = mode === "ask" ? "/v1/rag/ask" : mode === "vector" ? "/v1/rag/vector-search" : "/v1/rag/retrieve";
      ragControls.button.disabled = true;
      ragSearchResults.innerHTML = '<p>检索中...</p>';
      fetch(`${endpoint}?${params.toString()}`, { cache: "no-store" })
        .then(jsonOrThrow)
        .then(data => {
          ragSearchResults.innerHTML = ragSearchHtml(data);
        })
        .catch(error => {
          ragSearchResults.innerHTML = `<p>RAG 检索失败：${escapeHtml(error.message || error)}</p>`;
        })
        .finally(() => {
          ragControls.button.disabled = false;
        });
    }

    function indexDevContext() {
      if (!shouldUseApi()) return;
      devContextResults.innerHTML = '<p>开发上下文索引中，可能会运行测试和安全检查...</p>';
      fetch("/v1/dev-context/index", {
        method: "POST",
        headers: adminWriteHeaders(),
        body: JSON.stringify({
          run_checks: true,
          requested_by: "admin_page",
          source: "admin_page"
        })
      })
        .then(jsonOrThrow)
        .then(data => {
          devContextResults.innerHTML = devContextIndexHtml(data);
          if (devContextControls.query.value.trim()) runDevContextSearch();
          loadDatabaseInsights();
        })
        .catch(error => {
          devContextResults.innerHTML = `<p>开发上下文索引失败：${escapeHtml(error.message || error)}</p>`;
        });
    }

    function runDevContextSearch() {
      const query = devContextControls.query.value.trim();
      if (!query) {
        devContextResults.innerHTML = '<p>请输入开发上下文问题或关键词。</p>';
        return;
      }
      const params = new URLSearchParams();
      params.set("q", query);
      params.set("limit", "8");
      if (devContextControls.source.value) params.set("source_type", devContextControls.source.value);
      devContextResults.innerHTML = '<p>开发上下文搜索中...</p>';
      fetch(`/v1/dev-context/search?${params.toString()}`, { cache: "no-store" })
        .then(jsonOrThrow)
        .then(data => {
          devContextResults.innerHTML = devContextSearchHtml(data);
        })
        .catch(error => {
          devContextResults.innerHTML = `<p>开发上下文搜索失败：${escapeHtml(error.message || error)}</p>`;
        });
    }

    function askDevContext() {
      const question = devContextControls.query.value.trim();
      if (!question) {
        devContextResults.innerHTML = '<p>请输入开发上下文问题。</p>';
        return;
      }
      const payload = { question, limit: 8 };
      if (devContextControls.source.value) payload.source_type = devContextControls.source.value;
      devContextControls.askButton.disabled = true;
      devContextResults.innerHTML = '<p>开发上下文问答生成中...</p>';
      fetch("/v1/dev-context/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
        .then(jsonOrThrow)
        .then(data => {
          devContextResults.innerHTML = devContextAskHtml(data);
        })
        .catch(error => {
          devContextResults.innerHTML = `<p>开发上下文问答失败：${escapeHtml(error.message || error)}</p>`;
        })
        .finally(() => {
          devContextControls.askButton.disabled = false;
        });
    }

    function runRagBackfill(dryRun) {
      const limit = Math.max(1, Math.min(Number(ragBackfillControls.limit.value || 5), 100));
      if (!dryRun && !ragBackfillControls.confirm.checked) {
        ragBackfillResults.innerHTML = '<p>执行写入前需要勾选“确认写入 SQLite”。</p>';
        return;
      }
      const payload = {
        limit,
        dry_run: dryRun,
        confirm_execution: !dryRun && ragBackfillControls.confirm.checked,
      };
      ragBackfillControls.previewButton.disabled = true;
      ragBackfillControls.runButton.disabled = true;
      ragBackfillResults.innerHTML = dryRun ? '<p>正在预览 RAG 回填...</p>' : '<p>正在写入 RAG 解释历史...</p>';
      fetch("/v1/rag/backfill-explanations", {
        method: "POST",
        headers: adminWriteHeaders(),
        body: JSON.stringify(payload),
      })
        .then(jsonOrThrow)
        .then(data => {
          ragBackfillResults.innerHTML = ragBackfillHtml(data);
          if (!data.dry_run) loadDatabaseInsights();
        })
        .catch(error => {
          ragBackfillResults.innerHTML = `<p>RAG 回填失败：${escapeHtml(error.message || error)}</p>`;
        })
        .finally(() => {
          ragBackfillControls.previewButton.disabled = false;
          ragBackfillControls.runButton.disabled = false;
        });
    }

    function runRagMaintenancePlan() {
      const limit = Math.max(1, Math.min(Number(ragMaintenanceControls.limit.value || 10), 100));
      const coverageLimit = Math.max(1, Math.min(Number(ragMaintenanceControls.coverageLimit.value || 100), 500));
      const payload = {
        limit,
        coverage_limit: coverageLimit,
        min_gap_count: 1,
        dry_run: true,
        requested_by: "local-admin",
        trigger_source: "admin_page",
      };
      ragMaintenanceControls.button.disabled = true;
      ragMaintenanceResults.innerHTML = '<p>正在生成 RAG 维护计划...</p>';
      fetch("/v1/rag/maintenance-plan", {
        method: "POST",
        headers: adminWriteHeaders(),
        body: JSON.stringify(payload),
      })
        .then(jsonOrThrow)
        .then(data => {
          ragMaintenanceResults.innerHTML = ragMaintenancePlanHtml(data);
          return loadOverview();
        })
        .then(() => loadDatabaseInsights())
        .catch(error => {
          ragMaintenanceResults.innerHTML = `<p>RAG 维护计划生成失败：${escapeHtml(error.message || error)}</p>`;
        })
        .finally(() => {
          ragMaintenanceControls.button.disabled = false;
        });
    }

    function createPlannedTask() {
      createControls.button.disabled = true;
      createControls.status.textContent = "正在创建 planned 任务...";
      const source = createControls.source.value.trim();
      const payload = {
        profile: createControls.profile.value.trim(),
        sources: source ? [source] : [],
        dry_run: createControls.previewMode.checked,
        confirm_delivery: createControls.deliveryMode.checked,
        days_back: number(createControls.daysBack.value) || 7,
        trigger_source: "admin_page",
        requested_by: "local-admin",
      };
      fetch("/v1/runs/trigger", {
        method: "POST",
        headers: adminWriteHeaders(),
        body: JSON.stringify(payload),
      })
        .then(jsonOrThrow)
        .then(data => {
          const jobId = data.job_id || "";
          const warnings = (data.safety_warnings || []).join(" ");
          const detailUrl = jobId ? `job.html?job=${encodeURIComponent(jobId)}&api=1` : "jobs.html?api=1";
          createControls.status.innerHTML = `已创建 ${escapeHtml(jobId || "planned 任务")}。${escapeHtml(warnings)} <a href="${escapeAttribute(detailUrl)}">打开任务详情</a>`;
          return loadOverview();
        })
        .catch(error => {
          createControls.status.textContent = `创建失败：${error.message || error}`;
        })
        .finally(() => {
          createControls.button.disabled = false;
        });
    }

    function loadOverview() {
      Promise.all([
        fetch("projects.json", { cache: "no-store" }).then(jsonOrThrow).catch(() => ({ projects: [] })),
        fetch("runs.json", { cache: "no-store" }).then(jsonOrThrow).catch(() => ({ runs: [] })),
        loadAdminJobs(),
      ]).then(([projectsData, runsData, jobsData]) => {
        const projects = Array.isArray(projectsData.projects) ? projectsData.projects : [];
        const runs = Array.isArray(runsData.runs) ? runsData.runs : [];
        const jobs = Array.isArray(jobsData.jobs) ? jobsData.jobs : [];
        adminState.jobs = jobs;
        const latestRun = runs[0] || {};
        const failedJobs = jobs.filter(job => job.status === "failed");
        const plannedJobs = jobs.filter(job => job.status === "planned");
        overview.innerHTML = [
          metric("项目总数", projects.length),
          metric("最新运行", latestRun.run_date || "-"),
          metric("失败任务", failedJobs.length),
          metric("待执行任务", plannedJobs.length),
        ].join("");
        latestLinks.innerHTML = latestLinksHtml(latestRun, failedJobs[0], plannedJobs[0]);
        latestJobResult.innerHTML = latestJobResultHtml(latestJob(jobs));
        devContextJobs.innerHTML = devContextJobsHtml(jobs);
        workflowBoard.innerHTML = workflowBoardHtml(projects, runs, jobs);
        renderJobWorkbench();
      });
    }

    function loadAdminJobs() {
      if (!shouldUseApi()) return loadAdminJobsJson();
      return fetch("/v1/jobs?limit=200", { cache: "no-store" })
        .then(jsonOrThrow)
        .catch(loadAdminJobsJson);
    }

    function loadProjectAgentTasks() {
      if (!shouldUseApi()) {
        projectAgentTaskSummary.innerHTML = metric("模式", "静态");
        projectAgentTaskWorkbench.innerHTML = "<p>启动本地后端或添加 api=1 后查看项目 Agent 任务。</p>";
        return;
      }
      fetch("/v1/agent-tasks?limit=100", { cache: "no-store" })
        .then(jsonOrThrow)
        .then(data => renderProjectAgentTasks(data))
        .catch(error => {
          projectAgentTaskWorkbench.innerHTML = `<p>项目 Agent 任务读取失败：${escapeHtml(error.message || error)}</p>`;
        });
    }

    function renderProjectAgentTasks(data) {
      const summary = data.summary || {};
      const tasks = Array.isArray(data.tasks) ? data.tasks : [];
      projectAgentTaskSummary.innerHTML = [
        metric("任务总数", number(summary.total_count)),
        metric("活跃任务", number(summary.active_count)),
        metric("覆盖项目", number(summary.repository_count)),
      ].join("");
      if (!tasks.length) {
        projectAgentTaskWorkbench.innerHTML = "<p>暂无项目 Agent 任务。</p>";
        return;
      }
      projectAgentTaskWorkbench.innerHTML = tasks.slice(0, 20).map(task => `
        <div class="workbench-item">
          <strong><a href="project.html?repo=${encodeURIComponent(task.full_name || "")}&api=1">${escapeHtml(task.full_name || "未知项目")}</a></strong>
          <span>${escapeHtml(agentProjectTaskTypeLabel(task.task_type))} / ${escapeHtml(agentProjectTaskStatusLabel(task.status))} / 优先级 ${number(task.priority)}</span>
          <p>${escapeHtml(task.reason || "暂无任务原因。")}</p>
          ${task.result_summary ? `<p>执行结果：${escapeHtml(task.result_summary)}</p>` : ""}
        </div>
      `).join("");
    }

    function agentProjectTaskTypeLabel(value) {
      return ({ observe: "观察", review_risk: "风险复查", deep_analysis: "深度分析", notify: "订阅推送", ignore: "忽略", continue_tracking: "继续跟踪" })[value] || value || "观察";
    }

    function agentProjectTaskStatusLabel(value) {
      return ({ planned: "待执行", in_progress: "执行中", completed: "已完成", failed: "失败", cancelled: "已取消" })[value] || value || "未知";
    }

    function loadAdminJobsJson() {
      return fetch("jobs.json", { cache: "no-store" })
        .then(jsonOrThrow)
        .catch(() => ({ jobs: [] }));
    }

    function loadDatabaseInsights() {
      if (!shouldUseApi()) {
        databaseOverview.innerHTML = metric("数据库模式", "静态");
        feedbackSummary.innerHTML = '<p>启动本地后端或添加 api=1 后显示反馈记忆汇总。</p>';
        databaseFacets.innerHTML = '<p>启动本地后端或添加 api=1 后显示数据库分面。</p>';
        databaseTrends.innerHTML = '<p>启动本地后端或添加 api=1 后显示运行趋势。</p>';
        ragQualitySummary.innerHTML = '<p>启动本地后端或添加 api=1 后显示 RAG 诊断和质量概览。</p>';
        ragEvaluationTrends.innerHTML = '<p>启动本地后端或添加 api=1 后显示 RAG 检索评估趋势。</p>';
        return;
      }
      Promise.all([
        fetch("/v1/database/summary", { cache: "no-store" }).then(jsonOrThrow),
        fetch("/v1/database/facets?limit=6", { cache: "no-store" }).then(jsonOrThrow),
        fetch("/v1/database/trends?limit=8", { cache: "no-store" }).then(jsonOrThrow),
        fetch("/v1/rag/diagnostics?limit=5", { cache: "no-store" }).then(jsonOrThrow),
        fetch("/v1/rag/quality-summary?limit=5", { cache: "no-store" }).then(jsonOrThrow),
        fetch("/v1/rag/search-evaluation-trends?limit=8", { cache: "no-store" }).then(jsonOrThrow),
        fetch("/v1/feedback?limit=200", { cache: "no-store" }).then(jsonOrThrow).catch(() => ({ feedback: [], count: 0 })),
        fetch("/v1/recommendations?limit=20", { cache: "no-store" }).then(jsonOrThrow).catch(() => ({ recommendations: [] })),
      ])
        .then(([summary, facets, trends, diagnostics, qualitySummary, evaluationTrends, feedback, recommendations]) => {
          const counts = summary.table_counts || {};
          databaseOverview.innerHTML = [
            metric("仓库记录", counts.repositories || 0),
            metric("入选记录", counts.selections || 0),
            metric("语料记录", counts.project_corpus || 0),
            metric("订阅记录", counts.subscriptions || 0),
          ].join("");
          feedbackSummary.innerHTML = feedbackSummaryHtml(feedback, recommendations);
          databaseFacets.innerHTML = databaseFacetsHtml(facets);
          databaseTrends.innerHTML = databaseTrendsHtml(trends);
          ragQualitySummary.innerHTML = ragDiagnosticsHtml(diagnostics) + ragQualitySummaryHtml(qualitySummary);
          ragEvaluationTrends.innerHTML = ragEvaluationTrendsHtml(evaluationTrends);
        })
        .catch(error => {
          databaseOverview.innerHTML = metric("数据库状态", "读取失败");
          feedbackSummary.innerHTML = "";
          databaseFacets.innerHTML = `<p>数据库分面读取失败：${escapeHtml(error.message || error)}</p>`;
          databaseTrends.innerHTML = "";
          ragQualitySummary.innerHTML = "";
          ragEvaluationTrends.innerHTML = "";
        });
    }

    function renderJobWorkbench() {
      const jobs = filteredWorkbenchJobs().slice(0, 8);
      if (!jobs.length) {
        jobWorkbench.innerHTML = '<p>当前筛选下没有任务。</p>';
        return;
      }
      jobWorkbench.innerHTML = jobs.map(job => {
        const request = job.request || {};
        const jobId = job.job_id || "";
        const targetId = `admin-action-${safeId(jobId)}`;
        const apiEnabled = shouldUseApi();
        const precheckDisabled = apiEnabled ? "" : " disabled";
        const executeEnabled = apiEnabled && job.status === "planned";
        const retryEnabled = apiEnabled && job.status === "failed";
        return `<article class="job-row">
          <strong><a href="${escapeAttribute(jobDetailUrl(jobId))}">${escapeHtml(jobId)}</a><span>${escapeHtml(job.kind || "")}</span></strong>
          <span class="status ${escapeAttribute(statusClass(job.status))}">${escapeHtml(job.status || "")}</span>
          <div><span>方向</span><strong>${escapeHtml(request.profile || "-")}</strong></div>
          <div><span>提交时间</span><strong>${escapeHtml(job.submitted_at || job.run_date || "-")}</strong></div>
          <div class="job-actions">
            <button class="secondary-button" type="button" data-admin-action="precheck" data-job-id="${escapeAttribute(jobId)}" data-target="${escapeAttribute(targetId)}"${precheckDisabled}>执行前检查</button>
            <button class="secondary-button execute-button" type="button" data-admin-action="execute" data-job-id="${escapeAttribute(jobId)}" data-target="${escapeAttribute(targetId)}"${executeEnabled ? "" : " disabled"}>确认执行</button>
            <button class="secondary-button retry-button" type="button" data-admin-action="retry" data-job-id="${escapeAttribute(jobId)}" data-target="${escapeAttribute(targetId)}"${retryEnabled ? "" : " disabled"}>重试</button>
            <div id="${escapeAttribute(targetId)}" class="precheck-result" aria-live="polite"></div>
          </div>
        </article>`;
      }).join("");
    }

    function handleWorkbenchAction(event) {
      const button = event.target.closest("[data-admin-action]");
      if (!button) return;
      if (button.dataset.adminAction === "precheck") {
        runWorkbenchPrecheck(button);
      } else if (button.dataset.adminAction === "execute") {
        runWorkbenchExecution(button);
      } else if (button.dataset.adminAction === "retry") {
        runWorkbenchRetry(button);
      }
    }

    function runWorkbenchPrecheck(button) {
      const jobId = button.dataset.jobId || "";
      const target = document.getElementById(button.dataset.target || "");
      if (!target) return;
      if (!shouldUseApi()) {
        target.className = "precheck-result blocked";
        target.textContent = "执行前检查需要本地后端或 api=1 模式。";
        return;
      }
      button.disabled = true;
      target.className = "precheck-result";
      target.textContent = "检查中...";
      fetch(`/v1/job-execution-check?job_id=${encodeURIComponent(jobId)}`, { cache: "no-store" })
        .then(jsonOrThrow)
        .then(data => {
          target.className = `precheck-result ${data.executable ? "ok" : "blocked"}`;
          target.innerHTML = precheckHtml(data);
        })
        .catch(error => {
          target.className = "precheck-result blocked";
          target.textContent = `检查失败：${error.message || error}`;
        })
        .finally(() => {
          button.disabled = false;
        });
    }

    function runWorkbenchExecution(button) {
      const jobId = button.dataset.jobId || "";
      const target = document.getElementById(button.dataset.target || "");
      if (!target) return;
      if (!shouldUseApi()) {
        target.className = "precheck-result blocked";
        target.textContent = "执行任务需要本地后端或 api=1 模式。";
        return;
      }
      if (!window.confirm(`确认执行任务 ${jobId}？`)) return;
      button.disabled = true;
      target.className = "precheck-result";
      target.textContent = "执行中...";
      fetch(`/v1/jobs/${encodeURIComponent(jobId)}/execute`, {
        method: "POST",
        headers: adminWriteHeaders(),
        body: JSON.stringify({ confirm_execution: true, requested_by: "admin_page" }),
      })
        .then(jsonOrThrow)
        .then(data => {
          target.className = `precheck-result ${data.accepted && data.executed ? "ok" : "blocked"}`;
          target.innerHTML = executionHtml(data);
          return loadOverview();
        })
        .catch(error => {
          target.className = "precheck-result blocked";
          target.textContent = `执行失败：${error.message || error}`;
        })
        .finally(() => {
          button.disabled = false;
        });
    }

    function runWorkbenchRetry(button) {
      const jobId = button.dataset.jobId || "";
      const target = document.getElementById(button.dataset.target || "");
      if (!target) return;
      if (!shouldUseApi()) {
        target.className = "precheck-result blocked";
        target.textContent = "重试任务需要本地后端或 api=1 模式。";
        return;
      }
      if (!window.confirm(`确认为失败任务 ${jobId} 创建重试任务？`)) return;
      button.disabled = true;
      target.className = "precheck-result";
      target.textContent = "重试创建中...";
      fetch(`/v1/jobs/${encodeURIComponent(jobId)}/retry`, {
        method: "POST",
        headers: adminWriteHeaders(),
        body: JSON.stringify({ requested_by: "admin_page" }),
      })
        .then(jsonOrThrow)
        .then(data => {
          target.className = `precheck-result ${data.accepted && data.retry_created ? "ok" : "blocked"}`;
          target.innerHTML = retryHtml(data);
          return loadOverview();
        })
        .catch(error => {
          target.className = "precheck-result blocked";
          target.textContent = `重试失败：${error.message || error}`;
        })
        .finally(() => {
          button.disabled = false;
        });
    }

    function precheckHtml(data) {
      if (!data || !data.found) return "未找到任务。";
      const lines = [
        data.executable ? "可执行" : "不可执行",
        ...(data.blockers || []).map(item => `阻止：${item}`),
        ...(data.warnings || []).map(item => `提示：${item}`),
      ];
      if (data.next_command) lines.push(`命令：${data.next_command}`);
      return lines.map(line => `<div>${escapeHtml(line)}</div>`).join("");
    }

    function executionHtml(data) {
      const lines = [
        data.accepted ? "已接受执行" : "未执行",
        data.status ? `状态：${data.status}` : "",
        ...(data.blockers || []).map(item => `阻止：${item}`),
        ...(data.warnings || []).map(item => `提示：${item}`),
      ].filter(Boolean);
      return lines.map(line => `<div>${escapeHtml(line)}</div>`).join("");
    }

    function retryHtml(data) {
      const lines = [
        data.retry_created ? "已创建重试任务" : data.accepted ? "已命中已有任务" : "未创建重试任务",
        data.job_id ? `任务：${data.job_id}` : "",
        data.status ? `状态：${data.status}` : "",
        data.duplicate_of ? `已有任务：${data.duplicate_of}` : "",
        ...(data.blockers || []).map(item => `阻止：${item}`),
      ].filter(Boolean);
      return lines.map(line => `<div>${escapeHtml(line)}</div>`).join("");
    }

    function filteredWorkbenchJobs() {
      const jobs = [...adminState.jobs];
      if (adminState.jobFilter === "all") return jobs;
      if (adminState.jobFilter === "attention") {
        return jobs.filter(job => ["failed", "planned", "running"].includes(job.status));
      }
      return jobs.filter(job => job.status === adminState.jobFilter);
    }

    function latestJob(jobs) {
      return [...jobs].sort((left, right) => jobTime(right).localeCompare(jobTime(left)))[0] || null;
    }

    function jobTime(job) {
      return String(job.finished_at || job.submitted_at || job.run_date || "");
    }

    function latestJobResultHtml(job) {
      if (!job) {
        return '<h3>最近任务结果</h3><p>当前没有任务记录。</p>';
      }
      const result = job.result || {};
      const report = result.report_url || job.report_url || "";
      const error = job.error || result.error || "";
      const nextAction = jobNextAction(job);
      const detailUrl = jobDetailUrl(job.job_id || "");
      const reportLink = report ? `<a href="${escapeAttribute(report)}">打开周报</a>` : "暂无";
      return `<h3>最近任务结果</h3>
        <div class="result-grid">
          <div class="result-item"><span>任务</span><strong><a href="${escapeAttribute(detailUrl)}">${escapeHtml(job.job_id || "-")}</a></strong></div>
          <div class="result-item"><span>状态</span><strong><span class="status ${escapeAttribute(statusClass(job.status))}">${escapeHtml(job.status || "-")}</span></strong></div>
          <div class="result-item"><span>完成时间</span><strong>${escapeHtml(job.finished_at || job.submitted_at || job.run_date || "-")}</strong></div>
          <div class="result-item"><span>周报</span><strong>${reportLink}</strong></div>
        </div>
        <p><strong>下一步：</strong>${escapeHtml(nextAction)}</p>
        <p><strong>错误：</strong>${escapeHtml(error || "无")}</p>`;
    }

    function databaseFacetsHtml(data) {
      const languages = (data.languages || []).slice(0, 4).map(item => facetRow(item.name, `${item.project_count || item.count || 0} 个项目`, `Star ${item.total_stars || 0}`));
      const categories = (data.categories || []).slice(0, 4).map(item => facetRow(item.name, `${item.selection_count || item.count || 0} 次入选`, `新增 Star ${item.total_star_growth || 0}`));
      const sources = (data.sources || []).slice(0, 3).map(item => facetRow(item.name, `${item.selection_count || 0} 次入选`, `${item.project_count || 0} 个项目`));
      const ready = data.rag_readiness || {};
      return [
        '<h4>语言</h4>',
        ...(languages.length ? languages : [facetRow("无", "-", "-")]),
        '<h4>方向</h4>',
        ...(categories.length ? categories : [facetRow("无", "-", "-")]),
        '<h4>来源</h4>',
        ...(sources.length ? sources : [facetRow("无", "-", "-")]),
        facetRow("文本搜索", ready.ready_for_text_search ? "已准备" : "未准备", "project_corpus"),
      ].join("");
    }

    function feedbackSummaryHtml(data, recommendationsData) {
      const feedback = Array.isArray(data.feedback) ? data.feedback : [];
      const recommendations = Array.isArray(recommendationsData && recommendationsData.recommendations)
        ? recommendationsData.recommendations
        : [];
      const count = Number(data.count || feedback.length || 0);
      const average = feedback.length
        ? feedback.reduce((total, item) => total + Number(item.rating || 0), 0) / feedback.length
        : 0;
      const positive = feedback.filter(item => Number(item.rating || 0) > 0).length;
      const negative = feedback.filter(item => Number(item.rating || 0) < 0).length;
      const latest = feedback.slice(0, 5).map(item => `<article class="search-row">
        <strong>${escapeHtml(item.full_name || "-")}</strong>
        <span>${escapeHtml(item.profile || "default")} · 评分 ${escapeHtml(item.rating || 0)} · ${escapeHtml(item.source || "-")} · ${escapeHtml(item.created_at || "")}</span>
        <p>${escapeHtml(item.note || "")}</p>
      </article>`).join("");
      const impacted = recommendations
        .filter(item => item.ranking_factors && (Number(item.ranking_factors.preference_score || 0) || Number(item.ranking_factors.tracking_score || 0)))
        .slice(0, 5)
        .map(item => `<article class="search-row">
          <strong>${escapeHtml(item.full_name || "-")}</strong>
          <span>推荐分 ${number(item.recommendation_score)} · 反馈 ${signedNumber(item.ranking_factors.preference_score || 0)} · 跟踪 ${signedNumber(item.ranking_factors.tracking_score || 0)}</span>
          <p>${escapeHtml(item.feedback_reason || "")}</p>
        </article>`)
        .join("");
      return [
        "<h3>反馈记忆汇总</h3>",
        `<div class="overview">${[
          metric("反馈记录", count),
          metric("平均评分", average.toFixed(2)),
          metric("正向反馈", positive),
          metric("负向反馈", negative),
        ].join("")}</div>`,
        latest || "<p>暂无项目反馈。可先在项目详情页或推荐页写入有用/不适合/继续跟踪。</p>",
        "<h3>反馈影响推荐</h3>",
        impacted || "<p>暂无受反馈提升或降低的推荐项目。</p>",
      ].join("");
    }

    function databaseTrendsHtml(data) {
      const summary = data.summary || {};
      const latest = (data.points || []).slice(-1)[0] || {};
      return [
        facetRow("最近运行", summary.latest_run_date || "-", summary.latest_status || "-"),
        facetRow("总入选", summary.total_selected_count || 0, `新增 Star ${summary.total_star_growth || 0}`),
        facetRow("Trending 命中率", percent(summary.average_trending_selected_rate), `Top10 ${latest.trending_top10_count || 0}`),
        facetRow("推送成功", summary.telegram_sent_count || 0, `降级 ${summary.fallback_run_count || 0}`),
      ].join("");
    }

    function ragQualitySummaryHtml(data) {
      const levels = data.quality_levels || {};
      const lowItems = data.recent_low_quality || [];
      const recommendations = data.recommendations || [];
      const levelRows = Object.keys(levels).length
        ? Object.entries(levels).map(([name, count]) => facetRow(name, `${count} 条解释`, "质量等级"))
        : [facetRow("暂无质量分布", "-", "-")];
      const recommendationHtml = recommendations.length
        ? recommendations.map(item => `<p>${escapeHtml(item)}</p>`).join("")
        : "<p>暂无质量建议。</p>";
      const lowHtml = lowItems.length
        ? lowItems.slice(0, 3).map(item => `<article class="search-row">
          <strong>${escapeHtml(item.query || "-")}</strong>
          <span>${escapeHtml(item.quality_level || "-")} · ${escapeHtml(item.quality_score || 0)} 分 · ${escapeHtml(item.mode || "-")}</span>
          <p>${escapeHtml(item.answer || "")}</p>
        </article>`).join("")
        : "<p>暂无低质量解释。</p>";
      return [
        "<h3>RAG 质量概览</h3>",
        `<div class="overview">${[
          metric("解释总数", data.total_count || 0),
          metric("平均质量分", data.average_quality_score || 0),
          metric("最高质量分", data.max_quality_score || 0),
          metric("最低质量分", data.min_quality_score || 0),
        ].join("")}</div>`,
        "<h4>质量分布</h4>",
        ...levelRows,
        "<h4>改进建议</h4>",
        recommendationHtml,
        "<h4>最近低质量解释</h4>",
        lowHtml,
      ].join("");
    }

    function ragEvaluationTrendsHtml(data) {
      const aggregate = data.aggregate || {};
      const jobs = Array.isArray(data.jobs) ? data.jobs : [];
      const summary = Array.isArray(data.summary) ? data.summary : [];
      const recommendations = Array.isArray(data.recommendations) ? data.recommendations : [];
      const preferred = aggregate.preferred_mode_counts || {};
      const preferredRows = Object.keys(preferred).length
        ? Object.entries(preferred).map(([name, count]) => facetRow(name, `${count} 次推荐`, "检索模式"))
        : [facetRow("暂无推荐模式", "-", "-")];
      const summaryHtml = summary.length
        ? summary.map(item => `<p>${escapeHtml(item)}</p>`).join("")
        : "<p>暂无 RAG 检索评估历史。每周 workflow 或脚本执行后会写入趋势数据。</p>";
      const recommendationHtml = recommendations.length
        ? recommendations.map(item => `<p>${escapeHtml(item)}</p>`).join("")
        : "<p>暂无趋势建议。</p>";
      const latestRows = jobs.length
        ? jobs.slice(0, 5).map(job => `<article class="search-row">
          <strong><a href="${escapeAttribute(jobDetailUrl(job.job_id || ""))}">${escapeHtml(job.job_id || "-")}</a></strong>
          <span>${escapeHtml(job.finished_at || job.submitted_at || "-")} · 样本 ${escapeHtml(job.sample_count || 0)} · 覆盖 ${escapeHtml(job.repository_count || 0)}</span>
          <p>零命中 ${escapeHtml(job.zero_hit_count || 0)}；推荐 ${escapeHtml(Object.keys(job.preferred_mode_counts || {}).join("、") || "-")}</p>
        </article>`).join("")
        : "<p>暂无评估任务。</p>";
      return [
        "<h3>RAG 检索评估趋势</h3>",
        `<div class="overview">${[
          metric("评估任务", aggregate.job_count || 0),
          metric("平均样本", aggregate.average_sample_count || 0),
          metric("平均零命中", aggregate.average_zero_hit_count || 0),
          metric("最新推荐", aggregate.latest_preferred_mode || "-"),
        ].join("")}</div>`,
        summaryHtml,
        "<h4>推荐模式分布</h4>",
        ...preferredRows,
        "<h4>趋势建议</h4>",
        recommendationHtml,
        "<h4>最近评估任务</h4>",
        latestRows,
      ].join("");
    }

    function ragDiagnosticsHtml(data) {
      const signals = data.signals || {};
      const tables = data.table_counts || {};
      const coverage = data.coverage || {};
      const actions = data.next_actions || [];
      const actionHtml = actions.length
        ? actions.map(item => `<p>${escapeHtml(item)}</p>`).join("")
        : "<p>暂无诊断建议。</p>";
      return [
        "<h3>RAG 诊断</h3>",
        `<div class="overview">${[
          metric("健康等级", data.level || "-"),
          metric("诊断状态", data.status || "-"),
          metric("覆盖率", percent(coverage.coverage_rate || 0)),
          metric("覆盖缺口", coverage.gap_count || 0),
        ].join("")}</div>`,
        facetRow("语料记录", tables.project_corpus || 0, signals.has_corpus ? "已具备" : "缺少"),
        facetRow("证据块", tables.rag_chunks || 0, signals.has_chunks ? "已具备" : "缺少"),
        facetRow("向量索引", tables.rag_embeddings || 0, signals.has_embeddings ? "已具备" : "缺少"),
        facetRow("解释历史", tables.rag_explanations || 0, signals.has_explanations ? "已具备" : "缺少"),
        facetRow("问答能力", signals.ready_for_answering ? "已准备" : "未准备", "RAG ask"),
        "<h4>诊断建议</h4>",
        actionHtml,
      ].join("");
    }

    function ragMaintenancePlanHtml(data) {
      const jobId = data.job_id || "";
      const job = data.job || {};
      const detail = jobId ? `<a href="${escapeAttribute(jobDetailUrl(jobId))}">打开任务详情</a>` : "";
      const warnings = data.safety_warnings || [];
      const diagnostics = data.diagnostics || {};
      const warningHtml = warnings.length
        ? `<p>${warnings.map(item => escapeHtml(item)).join("；")}</p>`
        : "";
      return [
        "<h3>RAG 维护计划</h3>",
        `<div class="overview">${[
          metric("计划状态", data.planned_job_created ? "已创建" : "未创建"),
          metric("维护类型", job.kind || "-"),
          metric("诊断原因", data.reason || "-"),
          metric("覆盖缺口", data.gap_count || 0),
        ].join("")}</div>`,
        jobId ? `<p>任务编号：<code>${escapeHtml(jobId)}</code> ${detail}</p>` : "<p>当前不需要创建维护任务。</p>",
        diagnostics.status ? `<p>诊断状态：${escapeHtml(diagnostics.status || "")}，健康等级：${escapeHtml(diagnostics.level || "")}</p>` : "",
        warningHtml,
      ].filter(Boolean).join("");
    }

    function ragBackfillHtml(data) {
      const warnings = data.safety_warnings || [];
      const processed = data.processed || [];
      const coverage = data.coverage_before || {};
      const warningHtml = warnings.length
        ? warnings.map(item => `<p>${escapeHtml(item)}</p>`).join("")
        : "";
      const rows = processed.length
        ? processed.slice(0, 8).map(item => `<article class="search-row">
          <strong><a href="${escapeAttribute(projectDetailUrl({ full_name: item.full_name }))}">${escapeHtml(item.full_name || "-")}</a></strong>
          <span>${escapeHtml(item.status || "-")} · ${escapeHtml(item.dry_run ? "预览" : "已写入")} · 证据 ${escapeHtml(item.context_count || 0)}</span>
          <p>${escapeHtml((item.previous_gap_reasons || []).join("；") || item.query || "")}</p>
        </article>`).join("")
        : "<p>当前没有需要回填解释历史的项目。</p>";
      return [
        "<h3>RAG 解释回填</h3>",
        `<div class="overview">${[
          metric("执行模式", data.dry_run ? "预览" : "写入"),
          metric("候选项目", data.candidate_count || 0),
          metric("处理项目", data.processed_count || 0),
          metric("回填前缺口", coverage.gap_count || 0),
        ].join("")}</div>`,
        warningHtml,
        rows,
      ].join("");
    }

    function corpusSearchHtml(data) {
      const summary = (data.summary || []).map(item => `<p>${escapeHtml(item)}</p>`).join("");
      const results = data.results || [];
      if (!results.length) return `${summary}<p>没有搜索结果。</p>`;
      return `${summary}${results.map(result => `<article class="search-row">
        <strong><a href="${escapeAttribute(projectDetailUrl({ full_name: result.full_name }))}">${escapeHtml(result.full_name || "-")}</a></strong>
        <span>${escapeHtml(result.language || "-")} · ${escapeHtml(result.category || "-")} · 分数 ${escapeHtml(result.score || 0)}</span>
        <p>${escapeHtml(result.snippet || result.title || "")}</p>
      </article>`).join("")}`;
    }

    function ragSearchHtml(data) {
      const summary = (data.summary || []).map(item => `<p>${escapeHtml(item)}</p>`).join("");
      const contexts = data.contexts || [];
      const citations = data.citations || [];
      const promptContext = data.prompt_context || "";
      const retrieval = data.retrieval || {};
      const answerHtml = data.answer ? `<article class="search-row">
        <strong>RAG 回答</strong>
        <p>${escapeHtml(data.answer)}</p>
        <span>${escapeHtml(data.answer_model || "-")} · ${escapeHtml(data.confidence || "-")} · ${escapeHtml(data.source_explanation_id || "-")}</span>
      </article>` : "";
      const nextActions = (data.next_actions || []).map(item => `<li>${escapeHtml(item)}</li>`).join("");
      const nextActionsHtml = nextActions ? `<article class="search-row"><strong>下一步动作</strong><ul>${nextActions}</ul></article>` : "";
      if (!contexts.length) return `${answerHtml}${summary}${nextActionsHtml}<p>没有召回 RAG 证据块。</p>`;
      const contextHtml = contexts.map((context, index) => {
        const meta = context.metadata || {};
        const citation = citations[index] || {};
        return `<article class="search-row">
          <strong><a href="${escapeAttribute(projectDetailUrl({ full_name: meta.full_name }))}">${escapeHtml(meta.full_name || "-")}</a></strong>
          <span>${escapeHtml(meta.language || "-")} · ${escapeHtml(meta.category || "-")} · ${escapeHtml(retrieval.mode || "-")} · 分数 ${escapeHtml(context.score || 0)}</span>
          <p>${escapeHtml((context.evidence || [context.text || ""])[0] || "")}</p>
          <span>引用：${escapeHtml(citation.chunk_id || context.chunk_id || "-")} · ${escapeHtml(meta.run_date || "-")}</span>
        </article>`;
      }).join("");
      return `${answerHtml}${summary}${nextActionsHtml}${contextHtml}<label>Prompt Context<textarea readonly>${escapeHtml(promptContext)}</textarea></label>`;
    }

    function devContextIndexHtml(data) {
      return `<article class="search-row">
        <strong>开发上下文索引完成</strong>
        <span>${escapeHtml(data.run_id || "-")} · ${escapeHtml(data.status || "-")}</span>
        <p>来源 ${escapeHtml(data.source_count || 0)}，分块 ${escapeHtml(data.chunk_count || 0)}，embedding ${escapeHtml(data.embedding_count || 0)}，命令 ${escapeHtml(data.command_count || 0)}。</p>
      </article>`;
    }

    function devContextSearchHtml(data) {
      const summary = (data.summary || []).map(item => `<p>${escapeHtml(item)}</p>`).join("");
      const results = data.results || [];
      if (!results.length) return `${summary}<p>没有搜索结果。可先点击“索引开发上下文”。</p>`;
      return `${summary}${results.map(result => `<article class="search-row">
        <strong>${escapeHtml(result.title || result.source_path || "-")}</strong>
        <span>${escapeHtml(result.source_type || "-")} · ${escapeHtml(result.source_path || "-")} · ${escapeHtml(result.run_id || "-")}</span>
        <p>${escapeHtml(result.snippet || "")}</p>
      </article>`).join("")}`;
    }

    function devContextAskHtml(data) {
      const retrieval = data.retrieval || {};
      const nextActions = (data.next_actions || []).map(item => `<li>${escapeHtml(item)}</li>`).join("");
      const nextActionsHtml = nextActions ? `<article class="search-row"><strong>下一步动作</strong><ul>${nextActions}</ul></article>` : "";
      const evidence = data.evidence || [];
      const evidenceHtml = evidence.map(item => `<article class="search-row">
        <strong>${escapeHtml(item.index || "-")} · ${escapeHtml(item.title || item.source_path || "-")}</strong>
        <span>${escapeHtml(item.source_type || "-")} · ${escapeHtml(item.source_path || "-")} · ${escapeHtml(item.run_id || "-")}</span>
        <p>${escapeHtml(item.snippet || "")}</p>
      </article>`).join("");
      const emptyEvidence = evidence.length ? "" : "<p>没有召回证据。可先点击“索引开发上下文”，或换一个更具体的问题。</p>";
      return `<article class="search-row">
        <strong>开发上下文回答</strong>
        <span>${escapeHtml(data.question_type || "-")} · ${escapeHtml(data.confidence || "-")} · ${escapeHtml(retrieval.search_engine || "-")} · 证据 ${escapeHtml(retrieval.count || 0)}</span>
        <p>${escapeHtml(data.answer || "")}</p>
      </article>${nextActionsHtml}${emptyEvidence}${evidenceHtml}`;
    }

    function devContextJobsHtml(jobs) {
      const devJobs = (jobs || []).filter(job => job.kind === "dev_context_index").slice(0, 5);
      if (!devJobs.length) return '<p>暂无开发上下文索引任务。</p>';
      return devJobs.map(job => {
        const result = job.result || {};
        const error = job.error || result.error || "";
        const runId = result.run_id || "";
        const runLink = runId && shouldUseApi() ? `<a href="/v1/dev-context/runs/${encodeURIComponent(runId)}">索引详情</a>` : "索引详情";
        return `<article class="search-row">
          <strong><a href="${escapeAttribute(jobDetailUrl(job.job_id || ""))}">${escapeHtml(job.job_id || "-")}</a></strong>
          <span>${escapeHtml(job.status || "-")} · 分块 ${escapeHtml(result.chunk_count || 0)} · embedding ${escapeHtml(result.embedding_count || 0)} · ${escapeHtml(job.finished_at || job.submitted_at || "-")}</span>
          <p>${error ? `错误：${escapeHtml(error)}` : `运行：${runLink}`}</p>
        </article>`;
      }).join("");
    }

    function facetRow(name, value, detail) {
      return `<div class="facet-row"><strong>${escapeHtml(name)}</strong><span>${escapeHtml(value)} · ${escapeHtml(detail)}</span></div>`;
    }

    function percent(value) {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? `${Math.round(parsed * 100)}%` : "0%";
    }

    function jobNextAction(job) {
      if (job.status === "failed") return "建议先查看错误信息，必要时在任务工作台创建重试任务。";
      if (job.status === "planned") return "建议先执行前检查，通过后再确认执行。";
      if (job.status === "running") return "建议等待任务完成，或进入任务详情页查看最新状态。";
      if (job.status === "succeeded") return "任务已成功，可打开周报或继续查看项目筛选结果。";
      return "建议进入任务详情页查看完整记录。";
    }

    function statusClass(status) {
      if (status === "succeeded") return "succeeded";
      if (status === "failed") return "failed";
      if (status === "planned") return "planned";
      if (status === "running") return "running";
      return "";
    }

    function latestLinksHtml(latestRun, firstFailedJob, firstPlannedJob) {
      const links = [];
      if (latestRun.report_url || latestRun.telegram_report_url) {
        links.push(`<a href="${escapeAttribute(latestRun.report_url || latestRun.telegram_report_url)}">最新周报</a>`);
      }
      if (latestRun.telegram_runs_url) {
        links.push(`<a href="${escapeAttribute(latestRun.telegram_runs_url)}">运行面板</a>`);
      } else {
        links.push('<a href="runs.html">运行面板</a>');
      }
      if (firstFailedJob) {
        links.push(`<a href="${escapeAttribute(jobDetailUrl(firstFailedJob.job_id || ""))}">处理失败任务</a>`);
      }
      if (firstPlannedJob) {
        links.push(`<a href="${escapeAttribute(jobDetailUrl(firstPlannedJob.job_id || ""))}">查看待执行任务</a>`);
      }
      return links.join("");
    }

    function workflowBoardHtml(projects, runs, jobs) {
      const latestRun = runs[0] || {};
      const topProject = topProjects(projects)[0] || null;
      const failedJob = jobs.find(job => job.status === "failed") || null;
      const plannedJob = jobs.find(job => job.status === "planned") || null;
      return [
        workflowCard("最近周报", latestRun.run_date || "暂无运行", latestReportText(latestRun), latestRun.report_url || latestRun.telegram_report_url || "runs.html", "打开周报"),
        workflowCard("Top 项目", projectName(topProject), projectSummary(topProject), topProject ? projectDetailUrl(topProject) : "explorer.html", "查看项目"),
        workflowCard("失败任务", failedJob ? failedJob.job_id : "暂无失败", failedJob ? jobNextAction(failedJob) : "当前没有失败任务。", failedJob ? jobDetailUrl(failedJob.job_id || "") : "jobs.html?status=failed", "处理失败"),
        workflowCard("待执行任务", plannedJob ? plannedJob.job_id : "暂无待执行", plannedJob ? jobNextAction(plannedJob) : "当前没有待执行任务。", plannedJob ? jobDetailUrl(plannedJob.job_id || "") : "jobs.html?status=planned", "查看待执行"),
      ].join("");
    }

    function workflowCard(title, headline, body, href, action) {
      return `<article class="workflow-card">
        <h3>${escapeHtml(title)}</h3>
        <p><strong>${escapeHtml(headline || "-")}</strong></p>
        <p>${escapeHtml(body || "-")}</p>
        <div class="links"><a href="${escapeAttribute(href || "#")}">${escapeHtml(action || "打开")}</a></div>
      </article>`;
    }

    function latestReportText(run) {
      if (!run || !run.run_date) return "等待下一次周报生成。";
      const selected = run.selected_count ?? "-";
      const collected = run.collected_count ?? "-";
      return `入选 ${selected} 个项目，候选 ${collected} 个项目。`;
    }

    function topProjects(projects) {
      return [...projects].sort((left, right) => projectScore(right) - projectScore(left)).slice(0, 3);
    }

    function projectScore(project) {
      if (!project) return 0;
      return number(project.total_score ?? project.score ?? project.weekly_stars ?? project.stargazers_count);
    }

    function projectName(project) {
      if (!project) return "暂无项目";
      return project.full_name || project.name || project.repo || "-";
    }

    function projectSummary(project) {
      if (!project) return "等待项目归档数据。";
      const language = project.language || "未知语言";
      const stars = project.weekly_stars ?? project.stargazers_count ?? "-";
      return `${language}，热度 ${stars}。`;
    }

    function projectDetailUrl(project) {
      const repo = projectName(project);
      return repo && repo !== "-" ? `project.html?repo=${encodeURIComponent(repo)}` : "explorer.html";
    }

    function metric(label, value) {
      return `<article class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></article>`;
    }

    function number(value) {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : 0;
    }

    function loadHealth() {
      if (!shouldUseApi()) {
        apiMode.innerHTML = '<span class="status warn">静态模式</span> 当前页面使用 GitHub Pages 静态数据；本地启动后端或添加 api=1 后显示 /v1/health。';
        health.innerHTML = "";
        return;
      }
      apiMode.innerHTML = '<span class="status warn">API 模式</span> 正在读取 /v1/health。';
      fetch("/v1/health", { cache: "no-store" })
        .then(jsonOrThrow)
        .then(data => {
          apiMode.innerHTML = '<span class="status ok">API 已连接</span> 本地后端可用。';
          health.innerHTML = healthHtml(data);
        })
        .catch(error => {
          apiMode.innerHTML = `<span class="status bad">API 不可用</span> ${escapeHtml(error.message || error)}`;
          health.innerHTML = '<p>会继续保留静态页面查看能力。</p>';
        });
    }

    function healthHtml(data) {
      const capabilities = data.capabilities || {};
      const capabilityHtml = Object.entries(capabilities).map(([key, value]) => {
        const state = value ? "ok" : "bad";
        return `<div class="capability"><span class="status ${state}">${value ? "启用" : "关闭"}</span> ${escapeHtml(key)}</div>`;
      }).join("");
      return `<div class="capabilities">${capabilityHtml}</div><pre>${escapeHtml(JSON.stringify(data.archive || {}, null, 2))}</pre>`;
    }

    function shouldUseApi() {
      const params = new URLSearchParams(window.location.search);
      if (params.get("api") === "1") return true;
      if (params.get("api") === "0") return false;
      return ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname);
    }

    function jsonOrThrow(response) {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    }

    function adminWriteHeaders() {
      const token = adminToken();
      const headers = { "Content-Type": "application/json" };
      if (token) headers["X-Admin-Token"] = token;
      return headers;
    }

    function adminToken() {
      const params = new URLSearchParams(window.location.search);
      const token = params.get("admin_token") || window.localStorage.getItem("github_weekly_admin_token") || "";
      if (params.get("admin_token")) window.localStorage.setItem("github_weekly_admin_token", params.get("admin_token"));
      return token.trim();
    }

    function jobDetailUrl(jobId) {
      const params = new URLSearchParams();
      params.set("job", jobId || "");
      const apiMode = new URLSearchParams(window.location.search).get("api");
      if (apiMode === "1" || apiMode === "0") params.set("api", apiMode);
      return `job.html?${params.toString()}`;
    }

    function safeId(value) {
      return String(value || "unknown").replace(/[^a-zA-Z0-9_-]/g, "-") || "unknown";
    }

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;",
      }[char]));
    }

    function escapeAttribute(value) {
      return escapeHtml(value);
    }
  </script>
</body>
</html>
"""


def _subscriptions_content() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GitHub 订阅配置</title>
  <style>
    :root { color-scheme: light; font-family: Inter, "Microsoft YaHei", Arial, sans-serif; background: #f6f8fa; color: #1f2328; }
    body { margin: 0; }
    header { background: #ffffff; border-bottom: 1px solid #d8dee4; }
    .wrap { max-width: 1120px; margin: 0 auto; padding: 22px 18px; }
    nav { display: flex; gap: 14px; flex-wrap: wrap; font-weight: 700; }
    nav a { color: #0969da; text-decoration: none; }
    h1 { margin: 0 0 6px; font-size: 28px; }
    h2 { margin: 0 0 12px; font-size: 18px; }
    .sub { margin: 0; color: #57606a; }
    .panel { background: #ffffff; border: 1px solid #d8dee4; border-radius: 8px; padding: 16px; margin-top: 18px; }
    .grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; align-items: end; }
    label { display: grid; gap: 6px; color: #57606a; font-size: 13px; font-weight: 700; }
    input, select { box-sizing: border-box; width: 100%; border: 1px solid #d0d7de; border-radius: 6px; padding: 9px 10px; font: inherit; background: #ffffff; }
    button, .button { border: 1px solid #0969da; background: #0969da; color: #ffffff; border-radius: 6px; padding: 9px 12px; font: inherit; font-weight: 700; cursor: pointer; text-decoration: none; text-align: center; }
    .ghost { background: #ffffff; color: #0969da; }
    .quick { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }
    .quick button { background: #ffffff; color: #0969da; padding: 7px 10px; }
    .quick button.active { background: #ddf4ff; border-color: #0969da; }
    .list { display: grid; gap: 12px; }
    .item { border: 1px solid #d8dee4; border-radius: 8px; padding: 14px; display: grid; gap: 10px; }
    .title { font-weight: 800; font-size: 16px; }
    .meta { display: flex; gap: 8px; flex-wrap: wrap; }
    .pill { border: 1px solid #d8dee4; border-radius: 999px; padding: 3px 8px; color: #57606a; background: #f6f8fa; font-size: 12px; }
    .enabled { color: #1a7f37; }
    .disabled { color: #cf222e; }
    .preview { border-top: 1px solid #d8dee4; padding-top: 10px; display: grid; gap: 8px; }
    .preview-list { display: grid; gap: 8px; }
    .preview-item { border: 1px solid #d8dee4; border-radius: 6px; padding: 10px; background: #f6f8fa; }
    .preview-item a { color: #0969da; font-weight: 800; text-decoration: none; }
    .summary-list { margin: 0; padding-left: 18px; color: #57606a; line-height: 1.5; }
    .notice { color: #57606a; line-height: 1.6; }
    .error { color: #cf222e; }
    @media (max-width: 900px) { .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
    @media (max-width: 560px) { .grid { grid-template-columns: 1fr; } h1 { font-size: 24px; } }
  </style>
</head>
<body>
  <header>
    <div class="wrap">
      <h1>GitHub 订阅配置</h1>
      <p class="sub">保存 Java、Python、Agent 开发等偏好，作为后续精准推荐和多渠道推送的输入。</p>
      <nav>
        <a href="admin.html">管理首页</a>
        <a href="recommendations.html">个性化推荐</a>
        <a href="explorer.html">项目筛选</a>
        <a href="profiles.html">方向配置</a>
      </nav>
    </div>
  </header>
  <main class="wrap">
    <section class="panel">
      <h2>新增订阅</h2>
      <div class="grid">
        <label>订阅名称<input id="name" placeholder="Agent 开发周报"></label>
        <label>方向 profile<input id="profile" placeholder="agent_development"></label>
        <label>主要语言<input id="language" placeholder="Python / Java"></label>
        <label>项目方向<input id="category" placeholder="AI Agent / Backend"></label>
        <label>关键词<input id="query" placeholder="agent / spring"></label>
        <label>排序<select id="sort"><option value="score">综合分</option><option value="trending">Trending</option><option value="star-growth">新增 Star</option><option value="quality">质量分</option></select></label>
        <label>数量<input id="limit" type="number" min="1" max="50" value="20"></label>
        <label>推送通道<input id="channels" placeholder="telegram,feishu"></label>
      </div>
      <div id="profileButtons" class="quick" aria-label="个性化方向快捷选择"></div>
      <p class="notice">这里只保存通道名称，不保存 Token、Chat ID 或 Webhook。真实密钥仍从环境变量或 GitHub Actions Secrets 读取。</p>
      <button id="save">保存订阅</button>
      <span id="message" class="notice"></span>
    </section>
    <section class="panel">
      <h2>订阅列表</h2>
      <div id="subscriptions" class="list"><p class="notice">加载中</p></div>
    </section>
  </main>
  <script>
    const params = new URLSearchParams(location.search);
    const apiMode = params.get("api") === "1" || (params.get("api") !== "0" && ["localhost", "127.0.0.1", "::1"].includes(location.hostname));
    const fields = {
      name: document.getElementById("name"),
      profile: document.getElementById("profile"),
      language: document.getElementById("language"),
      category: document.getElementById("category"),
      query: document.getElementById("query"),
      sort: document.getElementById("sort"),
      limit: document.getElementById("limit"),
      channels: document.getElementById("channels")
    };

    function adminWriteHeaders() {
      const token = adminToken();
      const headers = { "Content-Type": "application/json" };
      if (token) headers["X-Admin-Token"] = token;
      return headers;
    }

    function adminToken() {
      const token = params.get("admin_token") || window.localStorage.getItem("github_weekly_admin_token") || "";
      if (params.get("admin_token")) window.localStorage.setItem("github_weekly_admin_token", params.get("admin_token"));
      return token.trim();
    }

    function init() {
      fields.profile.value = params.get("profile") || "";
      fields.language.value = params.get("language") || "";
      fields.category.value = params.get("category") || "";
      fields.query.value = params.get("q") || params.get("query") || "";
      document.getElementById("save").addEventListener("click", createSubscription);
      loadProfiles();
      loadSubscriptions();
    }

    function loadProfiles() {
      fetch("profiles.json", { cache: "no-store" })
        .then(response => {
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          return response.json();
        })
        .then(data => renderProfileButtons(Array.isArray(data.profiles) ? data.profiles : []))
        .catch(() => renderProfileButtons(quickProfiles()));
    }

    function renderProfileButtons(profiles) {
      const target = document.getElementById("profileButtons");
      const items = profiles.length ? profiles : quickProfiles();
      target.innerHTML = "";
      items.slice(0, 8).forEach(profile => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = profile.label || profile.profile_label || profile.name || "未命名方向";
        button.dataset.profile = profile.name || "";
        button.classList.toggle("active", button.dataset.profile === fields.profile.value.trim());
        button.addEventListener("click", () => applyProfile(profile));
        target.appendChild(button);
      });
    }

    function applyProfile(profile) {
      const label = profile.label || profile.profile_label || profile.name || "个性化";
      const languages = firstList(profile.search_languages, profile.preferred_languages);
      const topics = firstList(profile.search_topics, profile.preferred_topics);
      if (!fields.name.value.trim()) fields.name.value = `${label}订阅`;
      fields.profile.value = profile.name || "";
      fields.language.value = languages[0] || "";
      fields.query.value = topics.slice(0, 4).join(" ");
      document.querySelectorAll("#profileButtons button").forEach(button => {
        button.classList.toggle("active", button.dataset.profile === fields.profile.value.trim());
      });
      syncProfileParams();
    }

    function firstList(...values) {
      for (const value of values) {
        if (Array.isArray(value) && value.length) return value;
      }
      return [];
    }

    function quickProfiles() {
      return [
        { name: "agent_development", label: "Agent 开发", search_languages: ["Python"], search_topics: ["agent", "llm", "workflow"] },
        { name: "python", label: "Python", search_languages: ["Python"], search_topics: ["python", "automation", "ai"] },
        { name: "java", label: "Java", search_languages: ["Java"], search_topics: ["java", "spring-boot", "backend"] },
        { name: "backend", label: "后端", search_languages: ["Java"], search_topics: ["backend", "api", "database"] },
        { name: "developer_tools", label: "开发者工具", search_languages: [], search_topics: ["cli", "devtools", "automation"] }
      ];
    }

    function syncProfileParams() {
      const next = new URLSearchParams(location.search);
      if (fields.profile.value.trim()) next.set("profile", fields.profile.value.trim());
      else next.delete("profile");
      if (fields.language.value.trim()) next.set("language", fields.language.value.trim());
      else next.delete("language");
      if (fields.query.value.trim()) next.set("q", fields.query.value.trim());
      else next.delete("q");
      history.replaceState(null, "", `subscriptions.html?${next.toString()}`);
    }

    async function loadSubscriptions() {
      const target = document.getElementById("subscriptions");
      if (!apiMode) {
        target.innerHTML = '<p class="notice">当前是静态模式。请用本地后端打开 subscriptions.html?api=1 后保存订阅。</p>';
        return;
      }
      try {
        const response = await fetch("/v1/subscriptions?limit=100", { cache: "no-store" });
        if (!response.ok) throw new Error(`读取失败：${response.status}`);
        const data = await response.json();
        renderSubscriptions(data.subscriptions || []);
      } catch (error) {
        target.innerHTML = `<p class="error">${escapeHtml(error.message || String(error))}</p>`;
      }
    }

    async function createSubscription() {
      if (!apiMode) {
        setMessage("静态模式不能保存订阅，请启动本地后端。", true);
        return;
      }
      const payload = currentPayload();
      try {
        const response = await fetch("/v1/subscriptions", {
          method: "POST",
          headers: adminWriteHeaders(),
          body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error(`保存失败：${response.status}`);
        const data = await response.json();
        setMessage(`已保存：${data.subscription.name || data.subscription.subscription_id}`, false);
        loadSubscriptions();
      } catch (error) {
        setMessage(error.message || String(error), true);
      }
    }

    function currentPayload() {
      return {
        name: fields.name.value.trim(),
        profile: fields.profile.value.trim(),
        language: fields.language.value.trim(),
        category: fields.category.value.trim(),
        query: fields.query.value.trim(),
        sort: fields.sort.value,
        limit: Number(fields.limit.value || 20),
        channels: fields.channels.value.split(",").map(item => item.trim()).filter(Boolean)
      };
    }

    function renderSubscriptions(items) {
      const target = document.getElementById("subscriptions");
      if (!items.length) {
        target.innerHTML = '<p class="notice">暂无订阅。</p>';
        return;
      }
      target.innerHTML = items.map(item => `
        <article class="item">
          <div class="title">${escapeHtml(item.name || item.subscription_id)} <span class="${escapeAttribute(item.status)}">${escapeHtml(item.status)}</span></div>
          <div class="meta">
            ${pill("profile", item.profile)}
            ${pill("语言", item.language)}
            ${pill("方向", item.category)}
            ${pill("关键词", item.query)}
            ${pill("排序", item.sort)}
            ${pill("数量", item.limit)}
            ${pill("通道", (item.channels || []).join(","))}
          </div>
          <div class="meta">
            <a class="button ghost" href="${escapeAttribute(recommendationUrl(item))}">查看推荐</a>
            <button class="ghost" data-preview="${escapeAttribute(item.subscription_id)}" data-target="${escapeAttribute(previewTargetId(item))}">预览推荐</button>
            <button class="ghost" data-trigger="${escapeAttribute(item.subscription_id)}">生成任务</button>
            <button class="ghost" data-toggle="${escapeAttribute(item.subscription_id)}" data-status="${item.status === "enabled" ? "disabled" : "enabled"}">${item.status === "enabled" ? "停用" : "启用"}</button>
          </div>
          <div id="${escapeAttribute(previewTargetId(item))}" class="preview" hidden></div>
        </article>
      `).join("");
      document.querySelectorAll("[data-toggle]").forEach(button => button.addEventListener("click", () => updateStatus(button.dataset.toggle, button.dataset.status)));
      document.querySelectorAll("[data-preview]").forEach(button => button.addEventListener("click", () => loadSubscriptionPreview(button.dataset.preview, button.dataset.target)));
      document.querySelectorAll("[data-trigger]").forEach(button => button.addEventListener("click", () => triggerSubscription(button.dataset.trigger)));
    }

    async function triggerSubscription(id) {
      if (!apiMode) {
        setMessage("静态模式不能生成任务，请启动本地后端。", true);
        return;
      }
      if (!window.confirm("生成一个 dry-run 计划任务？生成后需要在任务详情页确认执行。")) return;
      try {
        const response = await fetch(`/v1/subscriptions/${encodeURIComponent(id)}/trigger`, {
          method: "POST",
          headers: adminWriteHeaders(),
          body: JSON.stringify({ dry_run: true, requested_by: "subscriptions_page" })
        });
        if (!response.ok) throw new Error(`生成任务失败：${response.status}`);
        const data = await response.json();
        if (!data.accepted && data.blockers && data.blockers.length) {
          setMessage(data.blockers.join("；"), true);
          return;
        }
        const jobId = data.job_id || data.duplicate_of || "";
        if (jobId) {
          location.href = `job.html?job=${encodeURIComponent(jobId)}&api=1`;
          return;
        }
        setMessage("任务请求已提交，但没有返回任务编号。", true);
      } catch (error) {
        setMessage(error.message || String(error), true);
      }
    }

    async function updateStatus(id, status) {
      try {
        const response = await fetch(`/v1/subscriptions/${encodeURIComponent(id)}`, {
          method: "PATCH",
          headers: adminWriteHeaders(),
          body: JSON.stringify({ status })
        });
        if (!response.ok) throw new Error(`更新失败：${response.status}`);
        loadSubscriptions();
      } catch (error) {
        setMessage(error.message || String(error), true);
      }
    }

    async function loadSubscriptionPreview(id, targetId) {
      const target = document.getElementById(targetId);
      if (!target) return;
      target.hidden = false;
      target.innerHTML = '<p class="notice">正在读取推荐预览...</p>';
      try {
        const response = await fetch(`/v1/subscriptions/${encodeURIComponent(id)}/recommendations?limit=5`, { cache: "no-store" });
        if (!response.ok) throw new Error(`预览失败：${response.status}`);
        const data = await response.json();
        target.innerHTML = previewHtml(data);
      } catch (error) {
        target.innerHTML = `<p class="error">${escapeHtml(error.message || String(error))}</p>`;
      }
    }

    function previewHtml(data) {
      if (!data.found) {
        return '<p class="notice">订阅不存在，无法生成推荐预览。</p>';
      }
      const summary = (data.selection_summary || []).map(item => `<li>${escapeHtml(item)}</li>`).join("");
      const projects = data.recommendations || [];
      const rows = projects.map(project => `
        <div class="preview-item">
          <a href="${escapeAttribute(projectDetailUrl(project.full_name || ""))}">${escapeHtml(project.full_name || "")}</a>
          <div class="notice">${escapeHtml(project.description || "暂无简介")}</div>
          <div class="meta">
            ${pill("语言", project.language)}
            ${pill("方向", project.category)}
            ${pill("新增 Star", project.star_growth)}
            ${pill("Trending", project.trending_rank ? `#${project.trending_rank}` : "")}
          </div>
        </div>
      `).join("");
      return `
        <ul class="summary-list">${summary}</ul>
        <div class="preview-list">${rows || '<p class="notice">当前订阅没有匹配到推荐项目。</p>'}</div>
      `;
    }

    function recommendationUrl(item) {
      const next = new URLSearchParams();
      ["profile", "language", "category", "sort"].forEach(key => {
        if (item[key]) next.set(key, item[key]);
      });
      if (item.query) next.set("q", item.query);
      if (params.get("api")) next.set("api", params.get("api"));
      return `recommendations.html?${next.toString()}`;
    }

    function previewTargetId(item) {
      return `preview-${safeId(item.subscription_id || item.name || "subscription")}`;
    }

    function projectDetailUrl(fullName) {
      const next = new URLSearchParams();
      next.set("repo", fullName);
      if (params.get("api")) next.set("api", params.get("api"));
      return `project.html?${next.toString()}`;
    }

    function safeId(value) {
      return String(value || "").replace(/[^a-zA-Z0-9_-]/g, "-");
    }

    function pill(label, value) {
      return value ? `<span class="pill">${escapeHtml(label)}：${escapeHtml(value)}</span>` : "";
    }

    function setMessage(text, isError) {
      const message = document.getElementById("message");
      message.textContent = text;
      message.className = isError ? "error" : "notice";
    }

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
    }

    function escapeAttribute(value) {
      return escapeHtml(value);
    }

    init();
  </script>
</body>
</html>
"""


def _recommendations_content() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GitHub 个性化推荐</title>
  <style>
    :root { color-scheme: light; font-family: Inter, "Microsoft YaHei", Arial, sans-serif; background: #f6f8fa; color: #1f2328; }
    body { margin: 0; }
    header { background: #ffffff; border-bottom: 1px solid #d8dee4; }
    .wrap { max-width: 1180px; margin: 0 auto; padding: 22px 18px; }
    nav { display: flex; gap: 14px; flex-wrap: wrap; font-weight: 700; }
    nav a { color: #0969da; text-decoration: none; }
    h1 { margin: 0 0 6px; font-size: 28px; }
    h2 { margin: 0 0 12px; font-size: 18px; }
    .sub { margin: 0; color: #57606a; }
    .panel { background: #ffffff; border: 1px solid #d8dee4; border-radius: 8px; padding: 16px; margin-top: 18px; }
    .filters { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; align-items: end; }
    label { display: grid; gap: 6px; color: #57606a; font-size: 13px; font-weight: 700; }
    input, select { box-sizing: border-box; width: 100%; border: 1px solid #d0d7de; border-radius: 6px; padding: 9px 10px; font: inherit; background: #ffffff; }
    button, .button { border: 1px solid #0969da; background: #0969da; color: #ffffff; border-radius: 6px; padding: 9px 12px; font: inherit; font-weight: 700; cursor: pointer; text-decoration: none; text-align: center; }
    .ghost { background: #ffffff; color: #0969da; }
    .quick { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
    .quick button { background: #f6f8fa; color: #0969da; border-color: #d0d7de; }
    .summary { display: grid; gap: 8px; margin: 0; padding-left: 18px; color: #57606a; }
    .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; margin-top: 14px; }
    .card { background: #ffffff; border: 1px solid #d8dee4; border-radius: 8px; padding: 14px; display: grid; gap: 10px; }
    .repo { font-size: 17px; font-weight: 800; color: #0969da; text-decoration: none; overflow-wrap: anywhere; }
    .desc { color: #57606a; margin: 0; line-height: 1.5; }
    .meta { display: flex; flex-wrap: wrap; gap: 8px; }
    .pill { border: 1px solid #d8dee4; border-radius: 999px; padding: 3px 8px; color: #57606a; background: #f6f8fa; font-size: 12px; }
    .pill.preference { border-color: #bbf7d0; color: #15803d; background: #f0fdf4; }
    .reasons { margin: 0; padding-left: 18px; color: #57606a; line-height: 1.55; }
    .ranking-factors { display: flex; flex-wrap: wrap; gap: 6px; }
    .ranking-factors span { border: 1px solid #d8dee4; border-radius: 6px; padding: 3px 6px; color: #57606a; background: #ffffff; font-size: 12px; }
    .agent-explain { display: grid; gap: 6px; color: #57606a; font-size: 13px; line-height: 1.5; }
    .agent-explain p { margin: 0; }
    .feedback { border-top: 1px solid #d8dee4; padding-top: 10px; display: grid; gap: 8px; }
    .feedback-actions { display: flex; flex-wrap: wrap; gap: 8px; }
    .feedback-actions button { width: auto; background: #ffffff; color: #0969da; border-color: #d0d7de; padding: 7px 10px; }
    .feedback-actions button:disabled { cursor: not-allowed; opacity: .55; }
    .feedback-memory { color: #57606a; font-size: 13px; margin: 0; }
    .feedback-status { min-height: 18px; color: #57606a; font-size: 13px; }
    .feedback-status.error { color: #cf222e; }
    .empty, .error { border: 1px dashed #d0d7de; color: #57606a; padding: 18px; text-align: center; background: #ffffff; }
    .error { color: #cf222e; }
    @media (max-width: 900px) { .filters { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
    @media (max-width: 560px) { .filters { grid-template-columns: 1fr; } h1 { font-size: 24px; } }
  </style>
</head>
<body>
  <header>
    <div class="wrap">
      <h1>GitHub 个性化推荐</h1>
      <p class="sub">按语言、方向和关键词快速查看适合当前需求的热点项目。</p>
      <nav>
        <a href="admin.html">管理首页</a>
        <a href="explorer.html">项目筛选</a>
        <a href="subscriptions.html">订阅配置</a>
        <a href="profiles.html">方向配置</a>
        <a href="projects.json">projects.json</a>
      </nav>
    </div>
  </header>
  <main class="wrap">
    <section class="panel">
      <h2>推荐条件</h2>
      <div class="filters">
        <label>方向 profile
          <input id="profile" placeholder="agent_development">
        </label>
        <label>主要语言
          <input id="language" placeholder="Python / Java / TypeScript">
        </label>
        <label>项目方向
          <input id="category" placeholder="AI Agent / Backend">
        </label>
        <label>关键词
          <input id="query" placeholder="agent / java / workflow">
        </label>
        <label>排序
          <select id="sort">
            <option value="score">综合分</option>
            <option value="trending">Trending 排名</option>
            <option value="star-growth">新增 Star</option>
            <option value="quality">质量分</option>
            <option value="recent">最新入选</option>
          </select>
        </label>
        <button id="apply">生成推荐</button>
      </div>
      <div id="profileButtons" class="quick"></div>
    </section>
    <section class="panel">
      <h2>推荐摘要</h2>
      <ul id="summary" class="summary"><li>加载中</li></ul>
    </section>
    <section id="recommendationRows" class="cards"></section>
  </main>
  <script>
    const params = new URLSearchParams(location.search);
    const apiMode = params.get("api") === "1" || (params.get("api") !== "0" && ["localhost", "127.0.0.1", "::1"].includes(location.hostname));
    const quickProfiles = [
      ["agent_development", "Agent 开发"],
      ["python", "Python"],
      ["java", "Java"],
      ["backend", "后端"],
      ["frontend", "前端"],
      ["ai_tools", "AI 工具"]
    ];
    const controls = {
      profile: document.getElementById("profile"),
      language: document.getElementById("language"),
      category: document.getElementById("category"),
      query: document.getElementById("query"),
      sort: document.getElementById("sort")
    };

    function init() {
      adminToken();
      controls.profile.value = params.get("profile") || "";
      controls.language.value = params.get("language") || "";
      controls.category.value = params.get("category") || "";
      controls.query.value = params.get("q") || params.get("query") || "";
      controls.sort.value = params.get("sort") || "score";
      renderProfileButtons();
      document.getElementById("apply").addEventListener("click", () => loadRecommendations(true));
      Object.values(controls).forEach(control => control.addEventListener("keydown", event => {
        if (event.key === "Enter") loadRecommendations(true);
      }));
      loadRecommendations(false);
    }

    function renderProfileButtons() {
      document.getElementById("profileButtons").innerHTML = quickProfiles.map(([value, label]) =>
        `<button type="button" data-profile="${escapeAttribute(value)}">${escapeHtml(label)}</button>`
      ).join("");
      document.querySelectorAll("[data-profile]").forEach(button => button.addEventListener("click", () => {
        controls.profile.value = button.dataset.profile || "";
        loadRecommendations(true);
      }));
    }

    async function loadRecommendations(updateLocation) {
      const request = currentRequest();
      if (updateLocation) updateUrl(request);
      try {
        const data = apiMode ? await fetchApiRecommendations(request) : await fetchStaticRecommendations(request);
        renderRecommendations(data);
      } catch (error) {
        renderError(error);
      }
    }

    function currentRequest() {
      return {
        profile: controls.profile.value.trim(),
        language: controls.language.value.trim(),
        category: controls.category.value.trim(),
        query: controls.query.value.trim(),
        sort: controls.sort.value,
        limit: "50"
      };
    }

    function updateUrl(request) {
      const next = new URLSearchParams();
      Object.entries(request).forEach(([key, value]) => {
        if (!value || key === "limit") return;
        next.set(key === "query" ? "q" : key, value);
      });
      if (params.get("api")) next.set("api", params.get("api"));
      history.replaceState(null, "", `${location.pathname}?${next.toString()}`);
    }

    async function fetchApiRecommendations(request) {
      const query = new URLSearchParams(request);
      const response = await fetch(`/v1/recommendations?${query.toString()}`);
      if (!response.ok) throw new Error(`API 请求失败：${response.status}`);
      return response.json();
    }

    async function fetchStaticRecommendations(request) {
      const response = await fetch("projects.json");
      if (!response.ok) throw new Error(`静态 projects.json 读取失败：${response.status}`);
      const data = await response.json();
      let projects = Array.isArray(data.projects) ? data.projects.slice() : [];
      projects = projects.filter(project => matchesRequest(project, request));
      projects = dedupeProjects(sortProjects(projects, request.sort)).slice(0, Number(request.limit || 50));
      return {
        schema_version: 1,
        profile: request.profile,
        language: request.language,
        category: request.category,
        query: request.query,
        sort: request.sort,
        count: projects.length,
        selection_summary: staticSummary(projects, request),
        recommendations: projects
      };
    }

    function matchesRequest(project, request) {
      if (request.language && (project.language || "").toLowerCase() !== request.language.toLowerCase()) return false;
      if (request.category && (project.category || "").toLowerCase() !== request.category.toLowerCase()) return false;
      const text = [
        project.full_name, project.description, project.category, project.language,
        ...(project.sources || []), ...(project.selection_reasons || [])
      ].join(" ").toLowerCase();
      if (request.profile && !text.includes(request.profile.toLowerCase().replaceAll("_", " "))) {
        const profileWords = request.profile.toLowerCase().split(/[_\\s-]+/).filter(Boolean);
        if (!profileWords.some(word => text.includes(word))) return false;
      }
      if (request.query && !text.includes(request.query.toLowerCase())) return false;
      return true;
    }

    function sortProjects(projects, sort) {
      const number = value => Number(value || 0);
      return projects.sort((left, right) => {
        if (sort === "trending") return trendingValue(left) - trendingValue(right);
        if (sort === "star-growth") return number(right.star_growth) - number(left.star_growth);
        if (sort === "quality") return number(right.quality_score) - number(left.quality_score);
        if (sort === "recent") return String(right.run_date || "").localeCompare(String(left.run_date || ""));
        return number(right.score) - number(left.score) || number(right.star_growth) - number(left.star_growth);
      });
    }

    function dedupeProjects(projects) {
      const seen = new Set();
      return projects.filter(project => {
        const fullName = String(project.full_name || "").toLowerCase();
        if (!fullName || seen.has(fullName)) return false;
        seen.add(fullName);
        return true;
      });
    }

    function trendingValue(project) {
      const rank = Number(project.trending_rank || 0);
      return rank > 0 ? rank : 999999;
    }

    function staticSummary(projects, request) {
      const filters = [];
      if (request.profile) filters.push(`profile=${request.profile}`);
      if (request.language) filters.push(`language=${request.language}`);
      if (request.category) filters.push(`category=${request.category}`);
      if (request.query) filters.push(`query=${request.query}`);
      const trendingCount = projects.filter(project => Number(project.trending_rank || 0) > 0).length;
      const summary = [
        `当前筛选：${filters.length ? filters.join("、") : "全部项目"}`,
        `返回 ${projects.length} 个候选项目，静态模式按本地 projects.json 计算。`
      ];
      if (trendingCount) summary.push(`其中 ${trendingCount} 个项目进入过 GitHub Trending。`);
      if (projects[0]) summary.push(`当前首选项目是 ${projects[0].full_name || "-"}，新增 Star ${projects[0].star_growth || 0}。`);
      return summary;
    }

    function renderRecommendations(data) {
      const projects = data.recommendations || [];
      document.getElementById("summary").innerHTML = (data.selection_summary || []).map(item => `<li>${escapeHtml(item)}</li>`).join("") || "<li>暂无摘要。</li>";
      const target = document.getElementById("recommendationRows");
      if (!projects.length) {
        target.innerHTML = '<div class="empty">暂无匹配项目，请调整方向、语言或关键词。</div>';
        return;
      }
      target.innerHTML = projects.map(project => `
        <article class="card">
          <a class="repo" href="${escapeAttribute(projectDetailUrl(project))}">${escapeHtml(project.full_name || "-")}</a>
          <p class="desc">${escapeHtml(project.description || "暂无简介")}</p>
          <div class="meta">
            <span class="pill">${escapeHtml(project.language || "Unknown")}</span>
            <span class="pill">${escapeHtml(project.category || "Other")}</span>
            <span class="pill">新增 Star ${number(project.star_growth)}</span>
            <span class="pill">Trending ${project.trending_rank ? "#" + number(project.trending_rank) : "-"}</span>
            <span class="pill">质量 ${number(project.quality_score)}</span>
            <span class="pill">推荐分 ${number(project.recommendation_score)}</span>
            <span class="pill preference">偏好 ${signedNumber(project.preference_score)}</span>
          </div>
          ${rankingFactorsHtml(project.ranking_factors)}
          ${agentExplanationHtml(project)}
          <ul class="reasons">${reasonsHtml(project)}</ul>
          <div class="feedback">
            ${feedbackMemoryHtml(project.feedback_memory)}
            <div class="feedback-actions" data-repo="${escapeAttribute(project.full_name || "")}">
              <button type="button" data-feedback="useful"${apiMode ? "" : " disabled"}>有用</button>
              <button type="button" data-feedback="not_fit"${apiMode ? "" : " disabled"}>不适合</button>
              <button type="button" data-feedback="watch"${apiMode ? "" : " disabled"}>继续跟踪</button>
            </div>
            <div id="feedback-${safeId(project.full_name || "")}" class="feedback-status" aria-live="polite">${apiMode ? "" : "反馈写入需要本地后端或 api=1。"}</div>
          </div>
          <div class="meta">
            <a class="button ghost" href="${escapeAttribute(projectDetailUrl(project))}">项目详情</a>
            <a class="button ghost" href="${escapeAttribute(compareUrl([project.full_name]))}">加入对比</a>
            <a class="button ghost" href="${escapeAttribute(project.html_url || "#")}" target="_blank" rel="noreferrer">GitHub</a>
          </div>
        </article>
      `).join("");
      bindRecommendationFeedback();
    }

    function reasonsHtml(project) {
      const reasons = Array.isArray(project.selection_reasons) && project.selection_reasons.length ? project.selection_reasons.slice(0, 3) : ["综合热度、方向和项目质量进入推荐列表。"];
      return reasons.map(reason => `<li>${escapeHtml(reason)}</li>`).join("");
    }

    function feedbackMemoryHtml(memory) {
      const count = Number(memory && (memory.record_count || memory.count) || 0);
      if (!memory || !count) return '<p class="feedback-memory">暂无反馈记忆。</p>';
      const labels = Array.isArray(memory.labels) ? memory.labels.slice(0, 3).join(", ") : "";
      const note = memory.latest_note ? ` / ${memory.latest_note}` : "";
      return `<p class="feedback-memory">反馈 ${number(count)} 条，均分 ${number(memory.average_rating)}，最近 ${signedNumber(memory.latest_rating)}${labels ? ` / ${escapeHtml(labels)}` : ""}${escapeHtml(note)}</p>`;
    }

    function rankingFactorsHtml(factors) {
      if (!factors || typeof factors !== "object") return "";
      const labels = {
        base_score: "基础",
        quality_score: "质量",
        trend_score: "趋势",
        rag_relevance_score: "RAG",
        preference_score: "反馈",
        tracking_score: "跟踪",
        risk_penalty: "风险"
      };
      return `<div class="ranking-factors">${Object.keys(labels).map(key => `<span>${labels[key]} ${signedNumber(factors[key] || 0)}</span>`).join("")}</div>`;
    }

    function agentExplanationHtml(project) {
      const lines = [project.recommendation_reason, project.rag_reason, project.feedback_reason].filter(Boolean);
      if (!lines.length) return "";
      return `<div class="agent-explain">${lines.map(line => `<p>${escapeHtml(line)}</p>`).join("")}</div>`;
    }

    function bindRecommendationFeedback() {
      document.querySelectorAll("[data-feedback]").forEach(button => {
        button.addEventListener("click", () => submitRecommendationFeedback(button));
      });
    }

    async function submitRecommendationFeedback(button) {
      const row = button.closest("[data-repo]");
      const fullName = row ? row.dataset.repo || "" : "";
      const action = button.dataset.feedback || "";
      const status = document.getElementById(`feedback-${safeId(fullName)}`);
      if (!apiMode || !fullName) return;
      const payload = feedbackPayload(fullName, action, "recommendations_page");
      try {
        setFeedbackStatus(status, "写入中...", false);
        const response = await fetch("/v1/feedback", {
          method: "POST",
          headers: adminWriteHeaders(),
          body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        setFeedbackStatus(status, "反馈已写入，正在刷新推荐排序。", false);
        await loadRecommendations(false);
      } catch (error) {
        setFeedbackStatus(status, `反馈写入失败：${error.message || error}`, true);
      }
    }

    function feedbackPayload(fullName, action, source) {
      const ratings = { useful: 2, not_fit: -2, watch: 1 };
      const notes = { useful: "recommendation useful", not_fit: "recommendation not fit", watch: "continue tracking" };
      return {
        full_name: fullName,
        profile: controls.profile.value.trim(),
        rating: ratings[action] || 0,
        labels: [action],
        note: notes[action] || action,
        source
      };
    }

    function setFeedbackStatus(target, message, isError) {
      if (!target) return;
      target.textContent = message;
      target.classList.toggle("error", Boolean(isError));
    }

    function adminWriteHeaders() {
      const token = adminToken();
      const headers = { "Content-Type": "application/json" };
      if (token) headers["X-Admin-Token"] = token;
      return headers;
    }

    function adminToken() {
      const token = params.get("admin_token") || window.localStorage.getItem("github_weekly_admin_token") || "";
      if (params.get("admin_token")) window.localStorage.setItem("github_weekly_admin_token", params.get("admin_token"));
      return token.trim();
    }

    function renderError(error) {
      document.getElementById("summary").innerHTML = `<li>${escapeHtml(error.message || String(error))}</li>`;
      document.getElementById("recommendationRows").innerHTML = '<div class="error">推荐数据读取失败。</div>';
    }

    function projectDetailUrl(project) {
      const repo = project.full_name || "";
      const next = new URLSearchParams();
      next.set("repo", repo);
      if (controls.profile.value.trim()) next.set("profile", controls.profile.value.trim());
      if (params.get("api")) next.set("api", params.get("api"));
      return `project.html?${next.toString()}`;
    }

    function compareUrl(repos) {
      const names = [...new Set(repos.filter(Boolean))];
      const next = new URLSearchParams();
      next.set("repos", names.join(","));
      if (params.get("api")) next.set("api", params.get("api"));
      return `compare.html?${next.toString()}`;
    }

    function number(value) {
      return Number(value || 0).toLocaleString("zh-CN");
    }

    function signedNumber(value) {
      const numberValue = Number(value || 0);
      return numberValue > 0 ? `+${number(numberValue)}` : number(numberValue);
    }

    function safeId(value) {
      return String(value || "item").replace(/[^a-zA-Z0-9_-]+/g, "-");
    }

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
    }

    function escapeAttribute(value) {
      return escapeHtml(value);
    }

    init();
  </script>
</body>
</html>
"""


def _explorer_content() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GitHub 热点项目筛选</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f8fa;
      --panel: #ffffff;
      --text: #20242a;
      --muted: #5f6b7a;
      --line: #d9dee7;
      --accent: #2563eb;
      --accent-2: #0f766e;
      --risk: #b42318;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 15px;
      line-height: 1.5;
    }
    header {
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }
    .wrap {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
    }
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      min-height: 68px;
    }
    h1 {
      margin: 0;
      font-size: 22px;
      font-weight: 700;
      letter-spacing: 0;
    }
    nav {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
    nav a {
      color: var(--accent);
      text-decoration: none;
      font-weight: 600;
    }
    main {
      padding: 20px 0 32px;
    }
    .filters {
      display: grid;
      grid-template-columns: minmax(220px, 2fr) repeat(7, minmax(120px, 1fr)) minmax(170px, 1.2fr);
      gap: 10px;
      align-items: end;
      margin-bottom: 14px;
    }
    label {
      display: grid;
      gap: 5px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 600;
    }
    input, select, button {
      width: 100%;
      height: 38px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel);
      color: var(--text);
      font: inherit;
      padding: 0 10px;
    }
    button {
      cursor: pointer;
      background: var(--accent);
      border-color: var(--accent);
      color: white;
      font-weight: 700;
    }
    .actions {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    .actions button:last-child {
      background: var(--accent-2);
      border-color: var(--accent-2);
    }
    .meta {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      color: var(--muted);
      margin: 8px 0 12px;
      min-height: 24px;
    }
    .profile-shortcuts {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 0 0 14px;
    }
    .profile-chip {
      width: auto;
      height: 32px;
      padding: 0 12px;
      background: var(--panel);
      border-color: var(--line);
      color: var(--text);
      font-size: 13px;
      font-weight: 700;
    }
    .profile-chip.active {
      background: var(--accent);
      border-color: var(--accent);
      color: white;
    }
    .summary {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }
    .metric {
      min-height: 72px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 6px;
    }
    .metric span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }
    .metric strong {
      display: block;
      margin-top: 6px;
      font-size: 18px;
      line-height: 1.2;
      overflow-wrap: anywhere;
    }
    .table-shell {
      overflow-x: auto;
      border: 1px solid var(--line);
      background: var(--panel);
    }
    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 980px;
    }
    th, td {
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
      text-align: left;
    }
    th {
      position: sticky;
      top: 0;
      background: #eef2f7;
      color: #344054;
      font-size: 13px;
      z-index: 1;
    }
    tbody tr:hover {
      background: #f8fbff;
    }
    .repo a {
      color: var(--accent);
      font-weight: 700;
      text-decoration: none;
    }
    .desc {
      color: var(--muted);
      margin-top: 4px;
      max-width: 420px;
    }
    .tag {
      display: inline-block;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 2px 8px;
      margin: 0 4px 4px 0;
      font-size: 12px;
      white-space: nowrap;
      background: #f9fafb;
    }
    .tag.source {
      border-color: #bfdbfe;
      color: #1d4ed8;
      background: #eff6ff;
    }
    .tag.risk {
      border-color: #fecaca;
      color: var(--risk);
      background: #fff1f2;
    }
    .tag.quality-high {
      border-color: #bbf7d0;
      color: #15803d;
      background: #f0fdf4;
    }
    .tag.quality-medium {
      border-color: #fde68a;
      color: #a16207;
      background: #fffbeb;
    }
    .tag.quality-low,
    .tag.quality-unknown {
      border-color: #fecaca;
      color: var(--risk);
      background: #fff1f2;
    }
    .detail-toggle {
      height: 30px;
      margin-top: 6px;
      padding: 0 8px;
      font-size: 13px;
    }
    .detail-row td {
      background: #fbfcfe;
      padding: 0;
    }
    .detail-panel {
      display: none;
      padding: 14px 16px 16px;
      border-top: 1px solid var(--line);
    }
    .detail-panel.open {
      display: grid;
      gap: 10px;
    }
    .detail-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }
    .detail-block {
      min-width: 0;
    }
    .detail-block h3 {
      margin: 0 0 4px;
      font-size: 13px;
      color: #344054;
    }
    .detail-block p,
    .detail-block ul {
      margin: 0;
      color: var(--muted);
    }
    .detail-block ul {
      padding-left: 18px;
    }
    .detail-link {
      color: var(--accent);
      overflow-wrap: anywhere;
    }
    .similar-block {
      grid-column: 1 / -1;
    }
    .similar-list {
      display: grid;
      gap: 6px;
      padding-left: 0;
      list-style: none;
    }
    .similar-list li {
      display: grid;
      gap: 2px;
    }
    .similar-list a {
      color: var(--accent);
      font-weight: 700;
      text-decoration: none;
      overflow-wrap: anywhere;
    }
    .num {
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }
    .empty {
      padding: 28px 12px;
      color: var(--muted);
      text-align: center;
    }
    @media (max-width: 900px) {
      .topbar {
        align-items: flex-start;
        flex-direction: column;
        padding: 16px 0;
      }
      .filters {
        grid-template-columns: 1fr 1fr;
      }
      .summary {
        grid-template-columns: 1fr 1fr;
      }
      .detail-grid {
        grid-template-columns: 1fr;
      }
    }
    @media (max-width: 560px) {
      .wrap {
        width: min(100% - 20px, 1180px);
      }
      .filters {
        grid-template-columns: 1fr;
      }
      .summary {
        grid-template-columns: 1fr;
      }
      h1 {
        font-size: 20px;
      }
    }
  </style>
</head>
<body>
  <header>
    <div class="wrap topbar">
      <h1>GitHub 热点项目筛选</h1>
      <nav>
        <a href="index.html">周报归档</a>
        <a href="projects.html">项目索引</a>
        <a href="projects.json">projects.json</a>
        <a href="profiles.json">profiles.json</a>
      </nav>
    </div>
  </header>
  <main class="wrap">
    <section class="filters" aria-label="筛选条件">
      <label>关键词
        <input id="query" type="search" autocomplete="off">
      </label>
      <label>日期
        <select id="runDate"></select>
      </label>
      <label>语言
        <select id="language"></select>
      </label>
      <label>个性化方向
        <select id="profile"></select>
      </label>
      <label>方向
        <select id="category"></select>
      </label>
      <label>来源
        <select id="source">
          <option value="">全部</option>
          <option value="github_trending">GitHub Trending</option>
          <option value="github_search">GitHub Search</option>
        </select>
      </label>
      <label>风险
        <select id="risk">
          <option value="">全部</option>
          <option value="none">无风险提示</option>
          <option value="has">有风险提示</option>
        </select>
      </label>
      <label>质量
        <select id="qualityLevel">
          <option value="">全部</option>
          <option value="high">高质量</option>
          <option value="medium">中等质量</option>
          <option value="low">低质量</option>
          <option value="unknown">未知</option>
        </select>
      </label>
      <label>排序
        <select id="sort">
          <option value="run_date">最新入选</option>
          <option value="star_growth">新增 Star</option>
          <option value="trending_rank">Trending 排名</option>
          <option value="score">综合分</option>
          <option value="quality_score">质量分</option>
          <option value="stars">累计 Star</option>
        </select>
      </label>
      <div class="actions">
        <button id="reset" type="button">重置</button>
        <button id="share" type="button">复制链接</button>
      </div>
    </section>
    <div class="meta">
      <span id="count">0 个项目</span>
      <span id="updated"></span>
    </div>
    <section id="profileShortcuts" class="profile-shortcuts" aria-label="个性化方向快捷视图"></section>
    <section id="summary" class="summary" aria-label="筛选结果概览"></section>
    <div class="table-shell">
      <table>
        <thead>
          <tr>
            <th>项目</th>
            <th>日期</th>
            <th>语言</th>
            <th>方向</th>
            <th>来源</th>
            <th>Trending</th>
            <th>新增 Star</th>
            <th>质量</th>
            <th>风险</th>
            <th>周报</th>
          </tr>
        </thead>
        <tbody id="rows">
          <tr><td class="empty" colspan="10">加载中</td></tr>
        </tbody>
      </table>
    </div>
  </main>
  <script>
    const state = { projects: [], profiles: [], dataSource: "json" };
    const controls = {
      query: document.getElementById("query"),
      runDate: document.getElementById("runDate"),
      language: document.getElementById("language"),
      profile: document.getElementById("profile"),
      category: document.getElementById("category"),
      source: document.getElementById("source"),
      risk: document.getElementById("risk"),
      qualityLevel: document.getElementById("qualityLevel"),
      sort: document.getElementById("sort")
    };
    const rows = document.getElementById("rows");
    const count = document.getElementById("count");
    const updated = document.getElementById("updated");
    const summary = document.getElementById("summary");
    const profileShortcuts = document.getElementById("profileShortcuts");
    const share = document.getElementById("share");

    Promise.all([
      loadProjects(),
      loadProfiles()
    ])
      .then(([projectsData, profilesData]) => {
        state.projects = Array.isArray(projectsData.projects) ? projectsData.projects : [];
        state.profiles = Array.isArray(profilesData.profiles) ? profilesData.profiles : [];
        state.dataSource = projectsData.source || "json";
        hydrateOptions();
        restoreFiltersFromUrl();
        render();
      })
      .catch(() => {
        rows.innerHTML = '<tr><td class="empty" colspan="10">无法读取项目数据</td></tr>';
      });

    Object.values(controls).forEach(control => control.addEventListener("input", render));
    rows.addEventListener("click", event => {
      const button = event.target.closest("[data-detail]");
      if (button) toggleDetails(button);
    });
    profileShortcuts.addEventListener("click", event => {
      const button = event.target.closest("[data-profile]");
      if (!button) return;
      controls.profile.value = button.dataset.profile || "";
      render();
    });
    document.getElementById("reset").addEventListener("click", () => {
      controls.query.value = "";
      controls.runDate.value = "";
      controls.language.value = "";
      controls.profile.value = "";
      controls.category.value = "";
      controls.source.value = "";
      controls.risk.value = "";
      controls.qualityLevel.value = "";
      controls.sort.value = "run_date";
      render();
    });
    share.addEventListener("click", () => {
      const link = window.location.href;
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(link).then(() => setShareLabel("已复制"));
      } else {
        setShareLabel("链接已更新");
      }
    });

    function hydrateOptions() {
      fillSelect(controls.runDate, dates());
      fillSelect(controls.language, values("language"));
      fillProfileSelect();
      renderProfileShortcuts();
      fillSelect(controls.category, values("category"));
      const runDates = dates();
      const source = state.dataSource === "api" ? "后端 API" : "静态 JSON";
      updated.textContent = runDates.length ? `最新数据：${runDates[0]}，来源：${source}` : `来源：${source}`;
    }

    function loadProjects() {
      if (!shouldUseApi()) return loadProjectsJson();
      return fetch("/api/projects?limit=200&sort=recent", { cache: "no-store" })
        .then(jsonOrThrow)
        .then(data => ({ ...data, source: "api" }))
        .catch(loadProjectsJson);
    }

    function loadProjectsJson() {
      return fetch("projects.json", { cache: "no-store" })
        .then(jsonOrThrow)
        .then(data => ({ ...data, source: "json" }));
    }

    function loadProfiles() {
      if (!shouldUseApi()) return loadProfilesJson();
      return fetch("/api/profiles", { cache: "no-store" })
        .then(jsonOrThrow)
        .catch(loadProfilesJson);
    }

    function loadProfilesJson() {
      return fetch("profiles.json", { cache: "no-store" })
        .then(jsonOrThrow)
        .catch(() => ({ profiles: [] }));
    }

    function shouldUseApi() {
      const params = new URLSearchParams(window.location.search);
      if (params.get("api") === "1") return true;
      if (params.get("api") === "0") return false;
      return ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname);
    }

    function jsonOrThrow(response) {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    }

    function dates() {
      return [...new Set(state.projects.map(project => project.run_date).filter(Boolean))].sort().reverse();
    }

    function values(key) {
      return [...new Set(state.projects.map(project => project[key]).filter(Boolean))].sort((a, b) => a.localeCompare(b));
    }

    function fillSelect(select, values) {
      select.innerHTML = '<option value="">全部</option>' + values.map(value => `<option value="${escapeAttribute(value)}">${escapeHtml(value)}</option>`).join("");
    }

    function fillProfileSelect() {
      controls.profile.innerHTML = '<option value="">全部</option>' + state.profiles.map(profile => {
        const value = profile.name || "";
        const label = profile.label || value;
        return `<option value="${escapeAttribute(value)}">${escapeHtml(label)}</option>`;
      }).join("");
    }

    function renderProfileShortcuts() {
      const chips = [{ name: "", label: "全部方向" }, ...state.profiles];
      profileShortcuts.innerHTML = chips.map(profile => {
        const value = profile.name || "";
        const active = value === controls.profile.value ? " active" : "";
        return `<button class="profile-chip${active}" type="button" data-profile="${escapeAttribute(value)}">${escapeHtml(profile.label || value)}</button>`;
      }).join("");
    }

    function render() {
      const query = controls.query.value.trim().toLowerCase();
      const selectedProfile = state.profiles.find(profile => profile.name === controls.profile.value);
      let filtered = state.projects.filter(project => {
        const text = [project.full_name, project.description, project.language, project.category, ...(project.selection_reasons || [])].join(" ").toLowerCase();
        const riskCount = (project.security_flags || []).length;
        return (!query || text.includes(query))
          && (!controls.runDate.value || project.run_date === controls.runDate.value)
          && (!controls.language.value || project.language === controls.language.value)
          && (!selectedProfile || matchesProfile(project, selectedProfile))
          && (!controls.category.value || project.category === controls.category.value)
          && (!controls.source.value || (project.sources || []).includes(controls.source.value))
          && (!controls.risk.value || (controls.risk.value === "has" ? riskCount > 0 : riskCount === 0))
          && (!controls.qualityLevel.value || qualityLevel(project) === controls.qualityLevel.value);
      });
      filtered = filtered.sort(compareProjects);
      count.textContent = `${filtered.length} 个项目`;
      renderProfileShortcuts();
      summary.innerHTML = summaryHtml(filtered);
      rows.innerHTML = filtered.length ? filtered.map(rowHtml).join("") : '<tr><td class="empty" colspan="10">没有匹配项目</td></tr>';
      updateUrl();
    }

    function summaryHtml(projects) {
      const starGrowth = projects.reduce((total, project) => total + number(project.star_growth), 0);
      const trendingCount = projects.filter(project => number(project.trending_rank) > 0).length;
      const riskCount = projects.filter(project => (project.security_flags || []).length > 0).length;
      const averageQuality = projects.length ? Math.round(projects.reduce((total, project) => total + number(project.quality_score), 0) / projects.length) : 0;
      const language = topValue(projects, "language");
      const category = topValue(projects, "category");
      return [
        metric("新增 Star", starGrowth),
        metric("Trending 项目", trendingCount),
        metric("平均质量分", averageQuality),
        metric("风险提示", riskCount),
        metric("主语言 / 方向", `${language || "-"} / ${category || "-"}`)
      ].join("");
    }

    function metric(label, value) {
      return `<div class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
    }

    function topValue(projects, key) {
      const counts = new Map();
      projects.forEach(project => {
        const value = project[key];
        if (value) counts.set(value, (counts.get(value) || 0) + 1);
      });
      return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0]?.[0] || "";
    }

    function restoreFiltersFromUrl() {
      const params = new URLSearchParams(window.location.search);
      const keys = { q: "query", date: "runDate", lang: "language", profile: "profile", category: "category", source: "source", risk: "risk", quality: "qualityLevel", sort: "sort" };
      Object.entries(keys).forEach(([param, key]) => {
      if (params.has(param)) controls[key].value = params.get(param) || "";
      });
    }

    function updateUrl() {
      const params = new URLSearchParams();
      const apiMode = new URLSearchParams(window.location.search).get("api");
      if (apiMode === "1" || apiMode === "0") params.set("api", apiMode);
      if (controls.query.value.trim()) params.set("q", controls.query.value.trim());
      if (controls.runDate.value) params.set("date", controls.runDate.value);
      if (controls.language.value) params.set("lang", controls.language.value);
      if (controls.profile.value) params.set("profile", controls.profile.value);
      if (controls.category.value) params.set("category", controls.category.value);
      if (controls.source.value) params.set("source", controls.source.value);
      if (controls.risk.value) params.set("risk", controls.risk.value);
      if (controls.qualityLevel.value) params.set("quality", controls.qualityLevel.value);
      if (controls.sort.value && controls.sort.value !== "run_date") params.set("sort", controls.sort.value);
      const query = params.toString();
      const next = `${window.location.pathname}${query ? "?" + query : ""}`;
      window.history.replaceState(null, "", next);
      setShareLabel("复制链接", false);
    }

    function setShareLabel(text, temporary = true) {
      share.textContent = text;
      if (temporary) {
        window.setTimeout(() => { share.textContent = "复制链接"; }, 1600);
      }
    }

    function compareProjects(a, b) {
      const sort = controls.sort.value;
      if (sort === "star_growth") return number(b.star_growth) - number(a.star_growth);
      if (sort === "trending_rank") return rank(a.trending_rank) - rank(b.trending_rank);
      if (sort === "score") return number(b.score) - number(a.score);
      if (sort === "quality_score") return number(b.quality_score) - number(a.quality_score);
      if (sort === "stars") return number(b.stargazers_count) - number(a.stargazers_count);
      return String(b.run_date || "").localeCompare(String(a.run_date || ""));
    }

    function matchesProfile(project, profile) {
      const languages = profile.preferred_languages || [];
      if (languages.includes(project.language)) return true;
      const keywords = [...(profile.preferred_topics || []), ...(profile.search_topics || [])].map(value => String(value).toLowerCase());
      if (!keywords.length) return false;
      const text = [project.full_name, project.description, project.category, ...(project.selection_reasons || [])].join(" ").toLowerCase();
      return keywords.some(keyword => keyword && text.includes(keyword));
    }

    function rowHtml(project, index) {
      const risks = project.security_flags || [];
      const sourceTags = (project.sources || []).map(source => `<span class="tag source">${escapeHtml(sourceLabel(source))}</span>`).join("");
      const riskText = securityText(project, risks);
      const quality = qualityText(project);
      const detailId = `detail-${index}`;
      return `<tr>
        <td class="repo"><a href="${escapeAttribute(projectDetailUrl(project))}">${escapeHtml(project.full_name)}</a><div class="desc">${escapeHtml(project.description || "")}</div></td>
        <td>${escapeHtml(project.run_date || "")}</td>
        <td>${escapeHtml(project.language || "Unknown")}</td>
        <td>${escapeHtml(project.category || "Other")}</td>
        <td>${sourceTags || "-"}</td>
        <td class="num">${project.trending_rank ? project.trending_rank : "-"}</td>
        <td class="num">${number(project.star_growth)}</td>
        <td>${quality}</td>
        <td>${riskText}</td>
        <td><a href="${escapeAttribute(project.report_url || "#")}">周报</a><a href="${escapeAttribute(projectDetailUrl(project))}">详情页</a><a href="${escapeAttribute(compareUrl([project.full_name]))}">对比</a><button class="detail-toggle" type="button" data-detail="${escapeAttribute(detailId)}">展开</button></td>
      </tr>
      <tr class="detail-row"><td colspan="10">${detailPanel(project, detailId)}</td></tr>`;
    }

    function detailPanel(project, detailId) {
      const reasons = listHtml(project.selection_reasons || [], "暂无推荐理由。");
      const risks = listHtml(project.security_flags || [], "暂无风险提示。");
      const qualityFlags = listHtml(project.quality_flags || [], "暂无质量扣分项。");
      const summary = project.readme_summary || project.description || "暂无 README 摘要。";
      return `<div id="${escapeAttribute(detailId)}" class="detail-panel">
        <div class="detail-grid">
          <div class="detail-block"><h3>README 摘要</h3><p>${escapeHtml(summary)}</p></div>
          <div class="detail-block"><h3>推荐理由</h3>${reasons}</div>
          <div class="detail-block"><h3>质量信号</h3><p>${qualityText(project)}</p>${qualityFlags}</div>
        </div>
        <div class="detail-grid">
          <div class="detail-block"><h3>项目指标</h3><p>综合分 ${escapeHtml(number(project.score).toFixed(3))}；质量分 ${escapeHtml(project.quality_score || 0)}；安全分 ${escapeHtml(project.security_score || 100)}；累计 Star ${escapeHtml(project.stargazers_count || 0)}；Fork ${escapeHtml(project.forks_count || 0)}</p></div>
          <div class="detail-block"><h3>来源</h3><p>${escapeHtml((project.sources || []).map(sourceLabel).join(" + ") || "-")}</p></div>
          <div class="detail-block"><h3>完整链接</h3><p><a class="detail-link" href="${escapeAttribute(project.html_url)}" target="_blank" rel="noreferrer">${escapeHtml(project.html_url)}</a></p><p><a class="detail-link" href="${escapeAttribute(projectDetailUrl(project))}">打开项目详情页</a></p><p><a class="detail-link" href="${escapeAttribute(compareWithSimilarUrl(project))}">与相似项目对比</a></p></div>
        </div>
        <div class="detail-grid">
          <div class="detail-block"><h3>风险提示</h3>${risks}</div>
          <div class="detail-block similar-block"><h3>相似项目</h3>${similarProjectsHtml(project)}</div>
        </div>
      </div>`;
    }

    function similarProjectsHtml(project) {
      const matches = similarProjects(project);
      if (!matches.length) return "<p>暂无相似历史项目。</p>";
      return `<ul class="similar-list">${matches.map(match => {
        const description = match.description ? `<span>${escapeHtml(match.description)}</span>` : "";
        const meta = [match.language || "Unknown", match.category || "Other", `新增 Star ${number(match.star_growth)}`].join(" / ");
        return `<li><a href="${escapeAttribute(projectDetailUrl(match))}">${escapeHtml(match.full_name)}</a><span>${escapeHtml(meta)}</span>${description}<span><a href="${escapeAttribute(compareUrl([project.full_name, match.full_name]))}">与当前项目对比</a> · <a href="${escapeAttribute(match.html_url)}" target="_blank" rel="noreferrer">GitHub</a></span></li>`;
      }).join("")}</ul>`;
    }

    function projectDetailUrl(project) {
      const repo = project.full_name || "";
      const params = new URLSearchParams();
      const apiMode = new URLSearchParams(window.location.search).get("api");
      params.set("repo", repo);
      if (apiMode === "1" || apiMode === "0") params.set("api", apiMode);
      return `project.html?${params.toString()}`;
    }

    function compareUrl(repos) {
      const params = new URLSearchParams();
      const names = [...new Set(repos.filter(Boolean))];
      params.set("repos", names.join(","));
      const apiMode = new URLSearchParams(window.location.search).get("api");
      if (apiMode === "1" || apiMode === "0") params.set("api", apiMode);
      return `compare.html?${params.toString()}`;
    }

    function compareWithSimilarUrl(project) {
      return compareUrl([project.full_name, ...similarProjects(project).map(match => match.full_name)]);
    }

    function similarProjects(project) {
      return state.projects
        .filter(candidate => candidate.full_name !== project.full_name)
        .map(candidate => ({ project: candidate, score: similarityScore(project, candidate) }))
        .filter(item => item.score > 0)
        .sort((a, b) => b.score - a.score || number(b.project.star_growth) - number(a.project.star_growth) || rank(a.project.trending_rank) - rank(b.project.trending_rank))
        .slice(0, 3)
        .map(item => item.project);
    }

    function similarityScore(base, candidate) {
      let score = 0;
      if (base.language && base.language === candidate.language) score += 4;
      if (base.category && base.category === candidate.category) score += 5;
      score += overlapCount(base.sources || [], candidate.sources || []);
      score += Math.min(4, overlapCount(projectKeywords(base), projectKeywords(candidate)));
      return score;
    }

    function projectKeywords(project) {
      return [project.full_name, project.description, project.category, ...(project.selection_reasons || [])]
        .join(" ")
        .toLowerCase()
        .split(/[^a-z0-9\u4e00-\u9fa5]+/)
        .filter(token => token.length >= 2);
    }

    function overlapCount(left, right) {
      const rightSet = new Set(right);
      return [...new Set(left)].filter(value => rightSet.has(value)).length;
    }

    function listHtml(items, emptyText) {
      if (!items.length) return `<p>${escapeHtml(emptyText)}</p>`;
      return `<ul>${items.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
    }

    function toggleDetails(button) {
      const panel = document.getElementById(button.dataset.detail);
      if (!panel) return;
      const open = panel.classList.toggle("open");
      button.textContent = open ? "收起" : "展开";
    }

    function securityText(project, risks) {
      const level = project.security_level || "low";
      const score = Number.isFinite(Number(project.security_score)) ? Number(project.security_score) : 100;
      const label = level === "high" ? "高风险" : level === "medium" ? "中风险" : "低风险";
      const tags = risks.length ? risks.map(flag => `<span class="tag risk">${escapeHtml(flag)}</span>`).join("") : "";
      return `<span class="tag risk">${escapeHtml(label)} ${score}</span>${tags}`;
    }

    function qualityText(project) {
      const level = qualityLevel(project);
      const score = Number.isFinite(Number(project.quality_score)) ? Number(project.quality_score) : 0;
      const label = level === "high" ? "高质量" : level === "medium" ? "中等质量" : level === "low" ? "低质量" : "未知质量";
      return `<span class="tag quality-${escapeAttribute(level)}">${escapeHtml(label)} ${score}</span>`;
    }

    function qualityLevel(project) {
      const level = String(project.quality_level || "unknown").toLowerCase();
      return ["high", "medium", "low"].includes(level) ? level : "unknown";
    }

    function sourceLabel(source) {
      if (source === "github_trending") return "GitHub Trending";
      if (source === "github_search") return "GitHub Search";
      return source;
    }

    function number(value) {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : 0;
    }

    function rank(value) {
      const parsed = number(value);
      return parsed > 0 ? parsed : 9999;
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
    }

    function escapeAttribute(value) {
      return escapeHtml(value).replace(/`/g, "&#96;");
    }
  </script>
</body>
</html>
"""


def _compare_content() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GitHub 项目对比</title>
  <style>
    :root {
      --bg: #f7f8fa;
      --panel: #ffffff;
      --text: #20242a;
      --muted: #5f6b7a;
      --line: #d9dee7;
      --accent: #2563eb;
      --ok: #15803d;
      --warn: #b45309;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 15px;
      line-height: 1.5;
    }
    header {
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }
    .wrap {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
    }
    .topbar {
      min-height: 68px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }
    h1 { margin: 0; font-size: 22px; letter-spacing: 0; }
    h2 { margin: 0 0 10px; font-size: 16px; }
    nav { display: flex; gap: 12px; flex-wrap: wrap; }
    a { color: var(--accent); text-decoration: none; font-weight: 700; overflow-wrap: anywhere; }
    main { padding: 20px 0 32px; }
    .panel {
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 6px;
      padding: 14px;
      margin-bottom: 12px;
    }
    .controls {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      align-items: end;
    }
    label { display: grid; gap: 6px; color: var(--muted); font-size: 13px; font-weight: 700; }
    textarea {
      width: 100%;
      min-height: 76px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      font: inherit;
      color: var(--text);
      background: #fff;
    }
    button {
      min-height: 42px;
      border: 1px solid var(--accent);
      border-radius: 6px;
      padding: 0 14px;
      background: var(--accent);
      color: #fff;
      font-weight: 800;
      cursor: pointer;
    }
    .summary {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 12px;
    }
    .metric {
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 6px;
      padding: 10px 12px;
      min-height: 74px;
    }
    .metric span { display: block; color: var(--muted); font-size: 12px; font-weight: 800; }
    .metric strong { display: block; margin-top: 6px; font-size: 17px; overflow-wrap: anywhere; }
    .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
    .muted { color: var(--muted); }
    .profile-shortcuts {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }
    .profile-shortcuts button {
      min-height: 32px;
      border-color: var(--line);
      background: #fff;
      color: var(--accent);
      font-size: 13px;
    }
    .profile-shortcuts button.active {
      border-color: var(--accent);
      background: #eff6ff;
    }
    .tag {
      display: inline-block;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 2px 8px;
      margin: 0 4px 6px 0;
      font-size: 12px;
      background: #f9fafb;
    }
    .tag.ok { border-color: #bbf7d0; color: var(--ok); background: #f0fdf4; }
    .tag.warn { border-color: #fed7aa; color: var(--warn); background: #fffbeb; }
    .table-shell { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; min-width: 860px; }
    th, td { border-bottom: 1px solid var(--line); padding: 9px 10px; text-align: left; vertical-align: top; }
    th { background: #eef2f7; color: #344054; font-size: 13px; }
    ul { margin: 0; padding-left: 18px; }
    li { margin: 4px 0; }
    .empty {
      padding: 28px 12px;
      color: var(--muted);
      text-align: center;
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 6px;
    }
    @media (max-width: 820px) {
      .topbar, .controls { align-items: stretch; grid-template-columns: 1fr; flex-direction: column; padding: 16px 0; }
      .summary, .grid { grid-template-columns: 1fr; }
      .wrap { width: min(100% - 20px, 1180px); }
    }
  </style>
</head>
<body>
  <header>
    <div class="wrap topbar">
      <h1>GitHub 项目对比</h1>
      <nav>
        <a href="index.html">周报归档</a>
        <a href="explorer.html">项目筛选</a>
        <a href="recommendations.html">个性化推荐</a>
        <a href="project.html">项目详情</a>
      </nav>
    </div>
  </header>
  <main class="wrap">
    <section class="panel">
      <div class="controls">
        <label>
          仓库全名，逗号或换行分隔，最多 8 个
          <textarea id="repos" placeholder="owner/repo, owner/another"></textarea>
        </label>
        <label>方向<input id="profile" placeholder="agent_development / java / python"></label>
        <label>语言<input id="language" placeholder="Python / Java"></label>
        <label>分类<input id="category" placeholder="AI Agent / Backend"></label>
        <label>关键词<input id="query" placeholder="agent / spring / rag"></label>
        <button id="compareButton" type="button">对比</button>
      </div>
      <p class="muted" id="modeText"></p>
      <div class="profile-shortcuts" id="profileButtons"></div>
    </section>
    <section id="content" class="empty">请输入至少 2 个仓库后开始对比。</section>
  </main>
  <script>
    const reposInput = document.getElementById("repos");
    const compareButton = document.getElementById("compareButton");
    const content = document.getElementById("content");
    const modeText = document.getElementById("modeText");
    const profileButtons = document.getElementById("profileButtons");
    const preferenceControls = {
      profile: document.getElementById("profile"),
      language: document.getElementById("language"),
      category: document.getElementById("category"),
      query: document.getElementById("query")
    };

    init();

    function init() {
      const params = new URLSearchParams(window.location.search);
      reposInput.value = params.get("repos") || params.get("repo") || "";
      preferenceControls.profile.value = params.get("profile") || "";
      preferenceControls.language.value = params.get("language") || "";
      preferenceControls.category.value = params.get("category") || "";
      preferenceControls.query.value = params.get("q") || params.get("query") || "";
      modeText.textContent = shouldUseApi()
        ? "当前优先读取本地后端 /v1/projects/compare。"
        : "当前使用静态 projects.json 聚合，GitHub Pages 可直接查看。";
      compareButton.addEventListener("click", runCompare);
      Object.values(preferenceControls).forEach(control => control.addEventListener("keydown", event => {
        if (event.key === "Enter") runCompare();
      }));
      loadProfiles();
      if (normalizeRepos(reposInput.value).length >= 2) runCompare();
    }

    function loadProfiles() {
      fetch("profiles.json", { cache: "no-store" })
        .then(jsonOrThrow)
        .then(data => renderProfileButtons(Array.isArray(data.profiles) ? data.profiles : []))
        .catch(() => renderProfileButtons(quickProfiles()));
    }

    function renderProfileButtons(profiles) {
      const items = profiles.length ? profiles : quickProfiles();
      profileButtons.innerHTML = "";
      items.slice(0, 8).forEach(profile => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = profile.label || profile.profile_label || profile.name || "未命名方向";
        button.dataset.profile = profile.name || "";
        if (button.dataset.profile === preferenceControls.profile.value.trim()) {
          button.classList.add("active");
        }
        button.addEventListener("click", () => applyProfile(profile));
        profileButtons.appendChild(button);
      });
    }

    function applyProfile(profile) {
      const name = profile.name || "";
      const languages = firstList(profile.search_languages, profile.preferred_languages);
      const topics = firstList(profile.search_topics, profile.preferred_topics);
      preferenceControls.profile.value = name;
      preferenceControls.language.value = languages[0] || "";
      preferenceControls.category.value = "";
      preferenceControls.query.value = topics.slice(0, 4).join(" ");
      profileButtons.querySelectorAll("button").forEach(button => {
        button.classList.toggle("active", button.dataset.profile === name);
      });
      if (normalizeRepos(reposInput.value).length >= 2) runCompare();
    }

    function firstList(...values) {
      for (const value of values) {
        if (Array.isArray(value) && value.length) return value;
      }
      return [];
    }

    function quickProfiles() {
      return [
        { name: "agent_development", label: "Agent 开发", search_languages: ["Python"], search_topics: ["agent", "llm", "workflow"] },
        { name: "python", label: "Python", search_languages: ["Python"], search_topics: ["python", "automation", "ai"] },
        { name: "java", label: "Java", search_languages: ["Java"], search_topics: ["java", "spring-boot", "backend"] },
        { name: "backend", label: "后端", search_languages: ["Java"], search_topics: ["backend", "api", "database"] },
        { name: "developer_tools", label: "开发者工具", search_languages: [], search_topics: ["cli", "devtools", "automation"] }
      ];
    }

    function runCompare() {
      const repos = normalizeRepos(reposInput.value);
      const preference = currentPreference();
      if (repos.length < 2) {
        content.className = "empty";
        content.textContent = "请输入至少 2 个 owner/repo。";
        return;
      }
      const params = new URLSearchParams(window.location.search);
      params.set("repos", repos.join(","));
      setOptional(params, "profile", preference.profile);
      setOptional(params, "language", preference.language);
      setOptional(params, "category", preference.category);
      setOptional(params, "q", preference.query);
      if (shouldUseApi()) params.set("api", "1");
      history.replaceState(null, "", `compare.html?${params.toString()}`);
      content.className = "empty";
      content.textContent = "加载中";
      loadCompare(repos, preference)
        .then(renderCompare)
        .catch(error => {
          content.className = "empty";
          content.textContent = `无法生成对比：${error.message}`;
        });
    }

    function loadCompare(repos, preference) {
      if (!shouldUseApi()) return loadStaticCompare(repos, preference);
      return fetch(`/v1/projects/compare?${compareQuery(repos, preference)}`, { cache: "no-store" })
        .then(jsonOrThrow)
        .catch(() => loadStaticCompare(repos, preference));
    }

    function loadStaticCompare(repos, preference) {
      return fetch("projects.json", { cache: "no-store" })
        .then(jsonOrThrow)
        .then(data => buildStaticCompare(repos, Array.isArray(data.projects) ? data.projects : [], preference));
    }

    function buildStaticCompare(repos, projects, preference) {
      const details = repos.map(repo => staticProject(repo, projects));
      const found = details.filter(Boolean);
      const missing = repos.filter(repo => !details.find(project => project && same(project.full_name, repo)));
      return {
        schema_version: 1,
        requested: repos,
        count: found.length,
        missing,
        preference,
        projects: found,
        matrix: comparisonMatrix(found),
        best_by: bestBy(found),
        recommendation: compareRecommendation(found, missing, preference),
        selection_summary: comparisonSummary(found, missing)
      };
    }

    function staticProject(repo, projects) {
      const history = projects
        .filter(project => same(project.full_name, repo))
        .sort((a, b) => String(b.run_date || "").localeCompare(String(a.run_date || "")));
      if (!history.length) return null;
      const latest = history[0];
      return {
        full_name: latest.full_name || repo,
        html_url: latest.html_url || "",
        description: latest.description || "",
        language: latest.language || "",
        category: latest.category || "",
        sources: unique(history.flatMap(project => project.sources || [])),
        latest_run_date: latest.run_date || "",
        first_run_date: history[history.length - 1].run_date || "",
        history_count: history.length,
        total_star_growth: history.reduce((total, project) => total + number(project.star_growth), 0),
        best_trending_rank: bestTrendingRank(history),
        latest_quality_score: number(latest.quality_score),
        latest_quality_level: latest.quality_level || "unknown",
        security_flag_count: unique(history.flatMap(project => project.security_flags || [])).length,
        quality_flag_count: unique(history.flatMap(project => project.quality_flags || [])).length,
        latest_star_growth: number(latest.star_growth),
        latest_trending_rank: number(latest.trending_rank),
        selection_reasons: unique(history.flatMap(project => project.selection_reasons || [])).slice(0, 5),
        trend_summary: []
      };
    }

    function renderCompare(data) {
      if (!data.count) {
        content.className = "empty";
        content.textContent = "没有找到可对比项目。";
        return;
      }
      content.className = "";
      const recommendation = data.recommendation || compareRecommendation(data.projects || [], data.missing || [], data.preference || currentPreference());
      content.innerHTML = `
        <section class="summary">
          ${metric("项目数量", data.count)}
          ${metric("累计 Star 领先", valueLabel(data.best_by && data.best_by.highest_total_star_growth))}
          ${metric("质量分领先", valueLabel(data.best_by && data.best_by.highest_quality_score))}
          ${metric("最好 Trending", valueLabel(data.best_by && data.best_by.best_trending_rank))}
        </section>
        <section class="panel"><h2>推荐结论</h2>${recommendationHtml(recommendation)}</section>
        <section class="panel"><h2>对比摘要</h2>${listHtml(data.selection_summary || [])}</section>
        <section class="panel">
          <h2>对比矩阵</h2>
          <div class="table-shell">${matrixHtml(data.matrix || [], data.projects || [])}</div>
        </section>
        <section class="grid">${(data.projects || []).map(projectCard).join("")}</section>
        ${data.missing && data.missing.length ? `<section class="panel"><h2>未找到项目</h2>${tags(data.missing, "warn")}</section>` : ""}
      `;
    }

    function matrixHtml(matrix, projects) {
      const names = projects.map(project => project.full_name || "");
      return `<table><thead><tr><th>指标</th>${names.map(name => `<th>${escapeHtml(name)}</th>`).join("")}</tr></thead><tbody>${matrix.map(row => `
        <tr><td>${escapeHtml(row.label || row.metric || "")}</td>${names.map(name => `<td>${escapeHtml(formatValue(row.values ? row.values[name] : ""))}</td>`).join("")}</tr>
      `).join("")}</tbody></table>`;
    }

    function projectCard(project) {
      return `<section class="panel">
        <h2><a href="project.html?repo=${encodeURIComponent(project.full_name || "")}${shouldUseApi() ? "&api=1" : ""}">${escapeHtml(project.full_name || "")}</a></h2>
        <p class="muted">${escapeHtml(project.description || "")}</p>
        <p>${tags([project.language || "Unknown", project.category || "Other", ...(project.sources || [])])}</p>
        <ul>
          <li>历史入选：${number(project.history_count)} 次</li>
          <li>累计新增 Star：${number(project.total_star_growth)}</li>
          <li>最好 Trending：${project.best_trending_rank ? "#" + number(project.best_trending_rank) : "-"}</li>
          <li>最新质量分：${number(project.latest_quality_score)} / ${escapeHtml(project.latest_quality_level || "unknown")}</li>
          <li>风险提示：${number(project.security_flag_count)} 条</li>
        </ul>
      </section>`;
    }

    function comparisonMatrix(projects) {
      const metrics = [
        ["language", "主要语言"],
        ["category", "项目方向"],
        ["latest_run_date", "最近入选"],
        ["history_count", "历史入选次数"],
        ["total_star_growth", "累计新增 Star"],
        ["latest_star_growth", "最近新增 Star"],
        ["best_trending_rank", "最好 Trending 排名"],
        ["latest_quality_score", "最新质量分"],
        ["security_flag_count", "风险提示数量"],
        ["quality_flag_count", "质量提示数量"]
      ];
      return metrics.map(([metric, label]) => ({
        metric,
        label,
        values: Object.fromEntries(projects.map(project => [project.full_name || "", project[metric]]))
      }));
    }

    function bestBy(projects) {
      return {
        highest_total_star_growth: bestProject(projects, "total_star_growth"),
        highest_latest_star_growth: bestProject(projects, "latest_star_growth"),
        highest_quality_score: bestProject(projects, "latest_quality_score"),
        best_trending_rank: bestProject(projects, "best_trending_rank", true),
        lowest_risk_flags: bestProject(projects, "security_flag_count", true, true)
      };
    }

    function bestProject(projects, key, lower = false, allowZero = false) {
      let candidates = projects.filter(project => project.full_name);
      if (lower && !allowZero) {
        const positive = candidates.filter(project => number(project[key]) > 0);
        if (positive.length) candidates = positive;
      }
      if (!candidates.length) return "";
      const sorted = [...candidates].sort((a, b) => lower ? number(a[key]) - number(b[key]) : number(b[key]) - number(a[key]));
      return sorted[0].full_name || "";
    }

    function compareRecommendation(projects, missing, preference) {
      preference = preference || currentPreference();
      if (!projects.length) {
        return {
          primary_project: "",
          reasons: ["没有找到可对比项目，无法给出优先推荐。"],
          cautions: missing && missing.length ? [`未找到项目：${missing.join(", ")}。`] : [],
          next_actions: ["请从项目筛选页或项目详情页选择已归档项目进入对比。"],
          scoring_model: preference.active ? "rule:v2-preference" : "rule:v1"
        };
      }
      const ranked = [...projects].sort((a, b) => compareScore(b, preference) - compareScore(a, preference));
      const primary = ranked[0];
      const cautions = [];
      if (number(primary.security_flag_count)) cautions.push(`该项目仍有 ${number(primary.security_flag_count)} 条风险提示，需要人工复核。`);
      if (primary.latest_quality_level && primary.latest_quality_level !== "good") cautions.push(`最新质量等级为 ${primary.latest_quality_level}，建议查看质量提示。`);
      if (missing && missing.length) cautions.push(`未找到项目：${missing.join(", ")}。`);
      return {
        primary_project: primary.full_name || "",
        score: Math.round(compareScore(primary, preference) * 100) / 100,
        reasons: [
          `综合规则评分最高：${Math.round(compareScore(primary, preference) * 100) / 100}。`,
          `累计新增 Star ${number(primary.total_star_growth)}，最近一次新增 Star ${number(primary.latest_star_growth)}。`,
          `历史入选 ${number(primary.history_count)} 次，最新质量分 ${number(primary.latest_quality_score)}。`,
          ...(number(primary.best_trending_rank) ? [`最好 GitHub Trending 排名第 ${number(primary.best_trending_rank)} 位。`] : []),
          ...preferenceReasons(primary, preference)
        ],
        cautions: cautions.length ? cautions : ["暂未发现额外注意事项。"],
        next_actions: [
          `优先打开 ${primary.full_name || ""} 的详情页，确认 README 摘要、风险提示和历史趋势。`,
          "如需进一步细分，请调整方向、语言、分类或关键词后重新对比。"
        ],
        scoring_model: preference.active ? "rule:v2-preference" : "rule:v1"
      };
    }

    function compareScore(project, preference) {
      const trendingRank = number(project.best_trending_rank);
      const trendingBonus = trendingRank ? Math.max(0, 60 - trendingRank) : 0;
      return number(project.total_star_growth) * 2
        + number(project.latest_star_growth) * 2
        + number(project.latest_quality_score) * 1.5
        + number(project.history_count) * 5
        + trendingBonus
        - number(project.security_flag_count) * 8
        + preferenceBonus(project, preference || currentPreference());
    }

    function preferenceBonus(project, preference) {
      if (!preference || !preference.active) return 0;
      let bonus = 0;
      const languages = new Set((preference.preferred_languages || []).map(value => String(value).toLowerCase()));
      const topics = (preference.preferred_topics || []).map(value => String(value).toLowerCase()).filter(Boolean);
      if (languages.has(String(project.language || "").toLowerCase())) bonus += 80;
      const text = projectText(project);
      bonus += Math.min(topics.filter(topic => text.includes(topic)).length, 5) * 20;
      return bonus;
    }

    function preferenceReasons(project, preference) {
      if (!preference || !preference.active) return [];
      const reasons = [];
      const languages = new Set((preference.preferred_languages || []).map(value => String(value).toLowerCase()));
      if (languages.has(String(project.language || "").toLowerCase())) reasons.push(`语言匹配当前偏好：${project.language || ""}。`);
      const text = projectText(project);
      const topics = (preference.preferred_topics || []).filter(topic => topic && text.includes(String(topic).toLowerCase()));
      if (topics.length) reasons.push(`关键词匹配当前偏好：${topics.slice(0, 5).join(", ")}。`);
      return reasons;
    }

    function projectText(project) {
      return [
        project.full_name,
        project.description,
        project.language,
        project.category,
        ...(project.sources || []),
        ...(project.selection_reasons || []),
        ...(project.trend_summary || [])
      ].join(" ").toLowerCase();
    }

    function recommendationHtml(recommendation) {
      const primary = recommendation && recommendation.primary_project ? recommendation.primary_project : "暂无";
      const score = recommendation && recommendation.score !== undefined ? `，规则评分 ${recommendation.score}` : "";
      return `
        <p><strong>优先查看：${escapeHtml(primary)}</strong>${escapeHtml(score)}</p>
        <h3>理由</h3>${listHtml(recommendation && recommendation.reasons || [])}
        <h3>注意事项</h3>${listHtml(recommendation && recommendation.cautions || [])}
        <h3>下一步</h3>${listHtml(recommendation && recommendation.next_actions || [])}
      `;
    }

    function currentPreference() {
      const profile = preferenceControls.profile.value.trim();
      const language = preferenceControls.language.value.trim();
      const category = preferenceControls.category.value.trim();
      const query = preferenceControls.query.value.trim();
      const profileTopics = profile ? profile.split(/[_\\s-]+/).filter(Boolean) : [];
      return {
        profile,
        language,
        category,
        query,
        preferred_languages: language ? [language] : [],
        preferred_topics: [...profileTopics, category, ...queryTerms(query)].filter(Boolean),
        active: Boolean(profile || language || category || query)
      };
    }

    function compareQuery(repos, preference) {
      const params = new URLSearchParams();
      params.set("repos", repos.join(","));
      setOptional(params, "profile", preference.profile);
      setOptional(params, "language", preference.language);
      setOptional(params, "category", preference.category);
      setOptional(params, "query", preference.query);
      return params.toString();
    }

    function setOptional(params, key, value) {
      if (value) params.set(key, value);
      else params.delete(key);
    }

    function queryTerms(value) {
      return String(value || "").replaceAll("，", " ").replaceAll(",", " ").split(/\\s+/).map(item => item.trim()).filter(Boolean);
    }

    function comparisonSummary(projects, missing) {
      if (!projects.length) return ["没有找到可对比的项目。"];
      const summary = [`已找到 ${projects.length} 个可对比项目。`];
      summary.push(`语言分布：${countText(projects.map(project => project.language || "unknown"))}。`);
      summary.push(`方向分布：${countText(projects.map(project => project.category || "Other"))}。`);
      const best = bestBy(projects);
      if (best.highest_total_star_growth) summary.push(`累计新增 Star 最高：${best.highest_total_star_growth}。`);
      if (best.best_trending_rank) summary.push(`最好 Trending 排名：${best.best_trending_rank}。`);
      if (missing.length) summary.push(`未找到 ${missing.length} 个项目：${missing.join("、")}。`);
      return summary;
    }

    function normalizeRepos(value) {
      const seen = new Set();
      return String(value || "")
        .split(/[,\n]/)
        .map(item => item.trim())
        .filter(item => item.includes("/"))
        .filter(item => {
          const key = item.toLowerCase();
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        })
        .slice(0, 8);
    }

    function bestTrendingRank(history) {
      const ranks = history.map(project => number(project.trending_rank)).filter(value => value > 0);
      return ranks.length ? Math.min(...ranks) : 0;
    }

    function countText(values) {
      const counts = {};
      values.forEach(value => { counts[value] = (counts[value] || 0) + 1; });
      return Object.entries(counts).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([name, count]) => `${name}(${count})`).join("、") || "-";
    }

    function listHtml(items) {
      if (!items.length) return "<p class=\"muted\">暂无摘要。</p>";
      return `<ul>${items.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
    }

    function tags(items, className = "") {
      return unique(items).map(item => `<span class="tag ${className}">${escapeHtml(item)}</span>`).join("");
    }

    function metric(label, value) {
      return `<div class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
    }

    function valueLabel(value) {
      return value || "-";
    }

    function formatValue(value) {
      if (Array.isArray(value)) return value.join("、");
      if (value === null || value === undefined || value === "") return "-";
      return String(value);
    }

    function same(left, right) {
      return String(left || "").toLowerCase() === String(right || "").toLowerCase();
    }

    function shouldUseApi() {
      const params = new URLSearchParams(window.location.search);
      if (params.get("api") === "1") return true;
      if (params.get("api") === "0") return false;
      return ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname);
    }

    function jsonOrThrow(response) {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    }

    function unique(items) {
      return [...new Set((items || []).map(item => String(item || "").trim()).filter(Boolean))];
    }

    function number(value) {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : 0;
    }

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
    }
  </script>
</body>
</html>
"""


def _project_detail_content() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GitHub 项目详情</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f8fa;
      --panel: #ffffff;
      --text: #20242a;
      --muted: #5f6b7a;
      --line: #d9dee7;
      --accent: #2563eb;
      --risk: #b42318;
      --ok: #15803d;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 15px;
      line-height: 1.5;
    }
    header {
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }
    .wrap {
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
    }
    .topbar {
      min-height: 68px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }
    h1 {
      margin: 0;
      font-size: 22px;
      letter-spacing: 0;
    }
    nav {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
    a {
      color: var(--accent);
      text-decoration: none;
      font-weight: 700;
      overflow-wrap: anywhere;
    }
    main {
      padding: 20px 0 32px;
    }
    .hero {
      display: grid;
      gap: 8px;
      margin-bottom: 14px;
    }
    .desc {
      color: var(--muted);
      max-width: 860px;
      margin: 0;
    }
    .meta {
      color: var(--muted);
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .summary {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 10px;
      margin: 14px 0;
    }
    .metric,
    .section {
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 6px;
    }
    .metric {
      min-height: 76px;
      padding: 10px 12px;
    }
    .metric span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }
    .metric strong {
      display: block;
      margin-top: 6px;
      font-size: 18px;
      line-height: 1.2;
      overflow-wrap: anywhere;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    .wide {
      grid-column: 1 / -1;
    }
    .section {
      padding: 14px;
      min-width: 0;
    }
    h2 {
      margin: 0 0 10px;
      font-size: 16px;
    }
    ul {
      margin: 0;
      padding-left: 18px;
    }
    li {
      margin: 4px 0;
    }
    .tag {
      display: inline-block;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 2px 8px;
      margin: 0 4px 6px 0;
      font-size: 12px;
      background: #f9fafb;
    }
    .tag.risk {
      border-color: #fecaca;
      color: var(--risk);
      background: #fff1f2;
    }
    .tag.ok {
      border-color: #bbf7d0;
      color: var(--ok);
      background: #f0fdf4;
    }
    .trend-list {
      display: grid;
      gap: 10px;
    }
    .trend-row {
      display: grid;
      grid-template-columns: 96px 1fr 72px 72px;
      gap: 10px;
      align-items: center;
      color: var(--muted);
      font-size: 13px;
    }
    .trend-bars {
      display: grid;
      gap: 4px;
      min-width: 0;
    }
    .bar-track {
      height: 8px;
      border-radius: 999px;
      background: #eef2f7;
      overflow: hidden;
    }
    .bar-fill {
      height: 100%;
      min-width: 2px;
      border-radius: 999px;
      background: var(--accent);
    }
    .bar-fill.quality {
      background: var(--ok);
    }
    .trend-label {
      color: var(--text);
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }
    .evidence-list {
      display: grid;
      gap: 10px;
      margin-top: 10px;
    }
    .evidence-item {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: #f8fafc;
    }
    .evidence-item strong,
    .evidence-item span {
      display: block;
    }
    .evidence-item span {
      color: var(--muted);
      font-size: 12px;
      margin-top: 2px;
    }
    .evidence-item p {
      margin: 8px 0 0;
      line-height: 1.55;
    }
    .prompt-context {
      white-space: pre-wrap;
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: #0f172a;
      color: #e2e8f0;
      font-size: 12px;
      line-height: 1.5;
      margin: 10px 0 0;
    }
    .feedback-panel {
      margin: 12px 0;
      border: 1px solid var(--line);
      background: var(--panel);
      padding: 14px;
      display: grid;
      gap: 10px;
    }
    .feedback-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .feedback-actions button {
      width: auto;
      min-width: 96px;
    }
    .feedback-actions button:disabled {
      cursor: not-allowed;
      opacity: .55;
    }
    .feedback-status {
      min-height: 18px;
      color: var(--muted);
      font-size: 13px;
    }
    .workbench-list { display: grid; gap: 8px; }
    .workbench-item { border-top: 1px solid var(--line); padding: 10px 0; display: grid; gap: 7px; }
    .workbench-item:first-child { border-top: 0; }
    .workbench-item span { color: var(--muted); font-size: 13px; }
    .workbench-item p { margin: 0; }
    .workbench-item .actions { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
    .workbench-item input { min-width: min(320px, 100%); flex: 1 1 240px; }
    .workbench-item button { width: auto; min-width: 80px; }
    .feedback-status.error {
      color: var(--risk);
    }
    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 760px;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      padding: 9px 10px;
      text-align: left;
      vertical-align: top;
    }
    th {
      background: #eef2f7;
      color: #344054;
      font-size: 13px;
    }
    .table-shell {
      overflow-x: auto;
    }
    .empty {
      padding: 28px 12px;
      color: var(--muted);
      text-align: center;
      border: 1px solid var(--line);
      background: var(--panel);
    }
    @media (max-width: 800px) {
      .topbar { align-items: flex-start; flex-direction: column; padding: 16px 0; }
      .summary, .grid { grid-template-columns: 1fr; }
      .wrap { width: min(100% - 20px, 1120px); }
      .trend-row { grid-template-columns: 1fr 1fr; }
      .trend-bars { grid-column: 1 / -1; }
    }
  </style>
</head>
<body>
  <header>
    <div class="wrap topbar">
      <h1 id="title">GitHub 项目详情</h1>
      <nav>
        <a href="index.html">周报归档</a>
        <a href="explorer.html">项目筛选</a>
        <a href="compare.html">项目对比</a>
        <a href="projects.json">projects.json</a>
      </nav>
    </div>
  </header>
  <main class="wrap">
    <section id="content" class="empty">加载中</section>
  </main>
  <script>
    const content = document.getElementById("content");
    const title = document.getElementById("title");

    adminToken();

    Promise.resolve()
      .then(loadDetail)
      .then(render)
      .catch(error => {
        content.className = "empty";
        content.textContent = `无法读取项目详情：${error.message}`;
      });

    function loadDetail() {
      const repo = repoName();
      if (!repo) throw new Error("URL 缺少 repo 参数，请从项目筛选页点击具体项目进入。");
      if (!shouldUseApi()) return loadStaticDetail(repo);
      return fetch(`/api/projects/${encodeURIComponentOwnerRepo(repo)}`, { cache: "no-store" })
        .then(jsonOrThrow)
        .then(data => data && data.found ? enrichApiDetail(repo, { ...data, data_source: "后端 API" }) : loadStaticDetail(repo))
        .catch(() => loadStaticDetail(repo));
    }

    function enrichApiDetail(repo, detail) {
      return Promise.all([
        fetch(`/api/projects/${encodeURIComponentOwnerRepo(repo)}/similar?limit=8`, { cache: "no-store" })
          .then(jsonOrThrow)
          .catch(() => ({})),
        loadProjectRag(repo, detail),
      ])
        .then(([data, rag]) => ({
          ...detail,
          similar_projects: Array.isArray(data.similar_projects) ? data.similar_projects : detail.similar_projects || [],
          similar_summary: Array.isArray(data.selection_summary) ? data.selection_summary : [],
          similar_search_engine: data.search_engine || "",
          rag_contexts: Array.isArray(rag.contexts) ? rag.contexts : [],
          rag_citations: Array.isArray(rag.citations) ? rag.citations : [],
          rag_summary: Array.isArray(rag.summary) ? rag.summary : [],
          rag_prompt_context: rag.prompt_context || "",
          rag_retrieval: rag.retrieval || {},
          rag_explanations: Array.isArray(rag.explanations) ? rag.explanations : [],
          rag_explanation_count: number((rag.explanation_summary || {}).count),
          rag_explanation_summary: rag.explanation_summary || {},
          feedback_memory: rag.feedback_memory || detail.feedback_memory || {},
          project_profile: rag.project_profile || detail.project_profile || {},
          agent_tasks: rag.agent_tasks || { count: 0, tasks: [], summary: {} },
          next_actions: Array.isArray(rag.next_actions) ? rag.next_actions : [],
        }))
        .catch(() => detail);
    }

    function loadStaticDetail(repo) {
      return fetch("projects.json", { cache: "no-store" })
        .then(jsonOrThrow)
        .then(data => buildStaticDetail(repo, Array.isArray(data.projects) ? data.projects : []));
    }

    function buildStaticDetail(repo, projects) {
      const history = projects
        .filter(project => String(project.full_name || "").toLowerCase() === repo.toLowerCase())
        .sort((a, b) => String(b.run_date || "").localeCompare(String(a.run_date || "")));
      if (!history.length) {
        return { schema_version: 1, found: false, full_name: repo, history: [], selection_reasons: [], trend_summary: [], similar_projects: [], rag_contexts: [], rag_citations: [], rag_summary: [], data_source: "静态 JSON" };
      }
      const latest = history[0];
      return {
        schema_version: 1,
        found: true,
        full_name: latest.full_name || repo,
        html_url: latest.html_url || "",
        description: latest.description || "",
        language: latest.language || "",
        category: latest.category || "",
        latest_run_date: latest.run_date || "",
        first_run_date: history[history.length - 1].run_date || "",
        history_count: history.length,
        total_star_growth: history.reduce((total, project) => total + number(project.star_growth), 0),
        best_trending_rank: bestTrendingRank(history),
        sources: unique(history.flatMap(project => project.sources || [])),
        selection_reasons: projectSelectionReasons(history),
        trend_summary: projectTrendSummary(history),
        security_flags: unique(history.flatMap(project => project.security_flags || [])),
        quality_flags: unique(history.flatMap(project => project.quality_flags || [])),
        best_quality_score: Math.max(0, ...history.map(project => number(project.quality_score))),
        latest_quality_score: number(latest.quality_score),
        latest_quality_level: latest.quality_level || "unknown",
        history,
        similar_projects: similarProjects(latest, projects),
        rag_contexts: [],
        rag_citations: [],
        rag_summary: ["RAG 证据需要本地后端或 URL 带 api=1 后读取。"],
        rag_explanations: [],
        rag_explanation_count: 0,
        rag_explanation_summary: {},
        feedback_memory: {},
        project_profile: {},
        agent_tasks: { count: 0, tasks: [], summary: {} },
        next_actions: [],
        data_source: "静态 JSON"
      };
    }

    function render(detail) {
      if (!detail.found) {
        title.textContent = "未找到项目";
        content.className = "empty";
        content.innerHTML = `未找到 ${escapeHtml(detail.full_name || "")} 的历史记录。`;
        return;
      }
      title.textContent = detail.full_name;
      document.title = `${detail.full_name} - GitHub 项目详情`;
      content.className = "";
      content.innerHTML = `
        <section class="hero">
          <h1>${escapeHtml(detail.full_name)}</h1>
          <p class="desc">${escapeHtml(detail.description || "")}</p>
          <div class="meta">
            <span>${escapeHtml(detail.language || "Unknown")}</span>
            <span>${escapeHtml(detail.category || "Other")}</span>
            <span>来源：${escapeHtml(detail.data_source || "静态 JSON")}</span>
            ${detail.html_url ? `<a href="${escapeAttribute(detail.html_url)}" target="_blank" rel="noreferrer">${escapeHtml(detail.html_url)}</a>` : ""}
            <a href="${escapeAttribute(compareUrl([detail.full_name, ...(detail.similar_projects || []).map(project => project.full_name)]))}">与相似项目对比</a>
          </div>
        </section>
        <section class="summary">
          ${metric("历史入选", number(detail.history_count))}
          ${metric("累计新增 Star", number(detail.total_star_growth))}
          ${metric("最好 Trending", detail.best_trending_rank ? "#" + detail.best_trending_rank : "-")}
          ${metric("最近入选", detail.latest_run_date || "-")}
          ${metric("质量分", number(detail.latest_quality_score))}
        </section>
        <section class="feedback-panel">
          <h2>项目反馈</h2>
          ${feedbackMemoryHtml(detail.feedback_memory)}
          <div class="feedback-actions" data-repo="${escapeAttribute(detail.full_name || "")}">
            <button type="button" data-project-feedback="useful"${shouldUseApi() ? "" : " disabled"}>有用</button>
            <button type="button" data-project-feedback="not_fit"${shouldUseApi() ? "" : " disabled"}>不适合</button>
            <button type="button" data-project-feedback="watch"${shouldUseApi() ? "" : " disabled"}>继续跟踪</button>
          </div>
          <div id="projectFeedbackStatus" class="feedback-status" aria-live="polite">${shouldUseApi() ? "" : "反馈写入需要本地后端或 api=1。"}</div>
        </section>
        <section class="section" style="margin-top:12px">
          <h2>Agent 研究摘要</h2>
          ${projectProfileHtml(detail.project_profile)}
        </section>
        <section class="section" style="margin-top:12px">
          <h2>Agent 下一步动作</h2>
          ${agentTasksHtml(detail.agent_tasks, detail.next_actions)}
          <div id="projectAgentTaskStatus" class="feedback-status" aria-live="polite">${shouldUseApi() ? "" : "任务操作需要本地后端或 api=1。"}</div>
        </section>
        <section class="grid">
          <div class="section"><h2>推荐理由</h2>${listHtml(detail.selection_reasons || [], "暂无推荐理由。")}</div>
          <div class="section"><h2>趋势判断</h2>${listHtml(detail.trend_summary || [], "暂无趋势判断。")}</div>
          <div class="section"><h2>风险提示</h2>${tags(detail.security_flags || [], "risk", "暂无风险提示")}</div>
          <div class="section"><h2>质量提示</h2>${tags(detail.quality_flags || [], "ok", "暂无质量扣分项")}</div>
          <div class="section"><h2>历史来源</h2>${tags(detail.sources || [], "", "暂无来源")}</div>
          <div class="section"><h2>相似项目</h2>${similarHtml(detail.full_name, detail.similar_projects || [], detail.similar_summary || [])}</div>
          <div class="section wide"><h2>RAG 证据</h2>${ragEvidenceHtml(detail)}</div>
          <div class="section wide"><h2>RAG 解释历史</h2>${ragExplanationsHtml(detail)}</div>
        </section>
        <section class="section" style="margin-top:12px">
          <h2>历史趋势</h2>
          ${trendHtml(detail.history || [])}
        </section>
        <section class="section" style="margin-top:12px">
          <h2>历史入选记录</h2>
          <div class="table-shell">${historyTable(detail.history || [])}</div>
        </section>
      `;
      bindProjectFeedback(detail);
      bindProjectAgentTasks(detail);
    }

    function historyTable(history) {
      if (!history.length) return '<div class="empty">暂无历史记录</div>';
      return `<table><thead><tr><th>日期</th><th>方向</th><th>来源</th><th>Trending</th><th>新增 Star</th><th>质量</th><th>周报</th></tr></thead><tbody>${history.map(project => `
        <tr>
          <td>${escapeHtml(project.run_date || "")}</td>
          <td>${escapeHtml(project.category || "Other")}</td>
          <td>${escapeHtml((project.sources || []).join(" + ") || "-")}</td>
          <td>${project.trending_rank ? "#" + escapeHtml(project.trending_rank) : "-"}</td>
          <td>${number(project.star_growth)}</td>
          <td>${number(project.quality_score)} / ${escapeHtml(project.quality_level || "unknown")}</td>
          <td>${project.report_url ? `<a href="${escapeAttribute(project.report_url)}">查看</a>` : "-"}</td>
        </tr>`).join("")}</tbody></table>`;
    }

    function trendHtml(history) {
      if (!history.length) return '<div class="empty">暂无趋势数据</div>';
      const ordered = [...history].sort((a, b) => String(a.run_date || "").localeCompare(String(b.run_date || "")));
      const maxGrowth = Math.max(1, ...ordered.map(project => number(project.star_growth)));
      return `<div class="trend-list">${ordered.map(project => {
        const growth = number(project.star_growth);
        const quality = number(project.quality_score);
        const growthWidth = Math.max(2, Math.round((growth / maxGrowth) * 100));
        const qualityWidth = Math.max(2, Math.min(100, quality));
        return `<div class="trend-row">
          <span class="trend-label">${escapeHtml(project.run_date || "")}</span>
          <span class="trend-bars">
            <span class="bar-track"><span class="bar-fill" style="width:${growthWidth}%"></span></span>
            <span class="bar-track"><span class="bar-fill quality" style="width:${qualityWidth}%"></span></span>
          </span>
          <span class="trend-label">Star ${growth}</span>
          <span class="trend-label">质量 ${quality}</span>
        </div>`;
      }).join("")}</div>`;
    }

    function projectSelectionReasons(history) {
      return unique(history.flatMap(project => project.selection_reasons || []));
    }

    function projectTrendSummary(history) {
      if (!history.length) return [];
      const ordered = [...history].sort((a, b) => String(a.run_date || "").localeCompare(String(b.run_date || "")));
      const totalGrowth = ordered.reduce((total, project) => total + number(project.star_growth), 0);
      const bestRank = bestTrendingRank(ordered);
      const latest = ordered[ordered.length - 1] || {};
      const summary = [
        `历史入选 ${ordered.length} 次，累计新增 Star ${totalGrowth}。`,
        `最近一次入选日期为 ${latest.run_date || "unknown"}。`,
      ];
      if (bestRank) summary.push(`最好 GitHub Trending 排名为第 ${bestRank} 位。`);
      if (ordered.length >= 2) {
        const latestGrowth = number(ordered[ordered.length - 1].star_growth);
        const previousGrowth = number(ordered[ordered.length - 2].star_growth);
        if (latestGrowth > previousGrowth) {
          summary.push("最近一次新增 Star 高于上次入选，热度仍在上升。");
        } else if (latestGrowth < previousGrowth) {
          summary.push("最近一次新增 Star 低于上次入选，热度可能回落。");
        } else {
          summary.push("最近两次新增 Star 持平，热度相对稳定。");
        }
      }
      return summary;
    }

    function loadProjectRag(repo, detail) {
      if (!shouldUseApi()) {
        return Promise.resolve({
          contexts: [],
          citations: [],
          summary: ["RAG 证据需要本地后端或 URL 带 api=1 后读取。"],
          prompt_context: "",
          rag_explanations: [],
          rag_explanation_count: 0,
          feedback_memory: {},
          project_profile: {},
        });
      }
      const params = new URLSearchParams();
      params.set("limit", "6");
      params.set("explanation_limit", "5");
      return fetch(`/v1/projects/${encodeURIComponentOwnerRepo(repo)}/rag?${params.toString()}`, { cache: "no-store" })
        .then(jsonOrThrow)
        .catch(() => ({
          contexts: [],
          citations: [],
          summary: ["RAG 聚合包读取失败，请确认本地后端和 SQLite 索引可用。"],
          prompt_context: "",
          explanations: [],
          explanation_summary: { count: 0, recommendations: [] },
          feedback_memory: {},
          project_profile: {},
          agent_tasks: { count: 0, tasks: [], summary: {} },
          next_actions: [],
        }));
    }

    function projectProfileHtml(profile) {
      if (!profile || !Object.keys(profile).length) return "<p>项目研究档案需要本地后端或 api=1 模式读取。</p>";
      return `
        <div class="grid">
          <div><h3>项目定位</h3><p>${escapeHtml(profile.project_positioning || "暂无项目定位。")}</p></div>
          <div><h3>适用场景</h3>${listHtml(profile.use_cases || [], "暂无适用场景。")}</div>
          <div><h3>优势信号</h3>${listHtml(profile.strengths || [], "暂无优势信号。")}</div>
          <div><h3>风险点</h3>${listHtml(profile.risks || [], "暂无风险点。")}</div>
          <div><h3>质量判断</h3><p>${escapeHtml(profile.quality_summary || "暂无质量判断。")}</p></div>
          <div><h3>跟踪理由</h3><p>${escapeHtml(profile.tracking_reason || "暂无跟踪理由。")}</p></div>
          <div class="wide"><h3>RAG 摘要</h3><p>${escapeHtml(profile.rag_summary || "暂无 RAG 摘要。")}</p></div>
          <div class="wide"><h3>Agent 判断</h3><p>${escapeHtml(profile.agent_judgement || "暂无 Agent 判断。")}</p></div>
        </div>
      `;
    }

    function feedbackMemoryHtml(memory) {
      const summary = memory && memory.summary ? memory.summary : memory || {};
      const count = Number(memory && memory.count !== undefined ? memory.count : summary.record_count || 0);
      if (!count) return "<p>暂无反馈记忆。</p>";
      const labels = Array.isArray(summary.labels) ? summary.labels.slice(0, 4).join(", ") : "";
      const latestNote = summary.latest_note ? ` / ${summary.latest_note}` : "";
      return `<p>反馈 ${number(count)} 条，平均评分 ${number(summary.average_rating)}，最近评分 ${signedNumber(summary.latest_rating)}${labels ? ` / ${escapeHtml(labels)}` : ""}${escapeHtml(latestNote)}</p>`;
    }

    function agentTasksHtml(memory, nextActions) {
      const tasks = memory && Array.isArray(memory.tasks) ? memory.tasks : [];
      const suggestions = Array.isArray(nextActions) ? nextActions.filter(item => item && item.status === "suggested") : [];
      const taskRows = tasks.map(task => {
        const actions = [];
        if (task.status === "planned") actions.push(`<button type="button" data-agent-task-update="in_progress" data-agent-task-id="${escapeAttribute(task.task_id || "")}"${shouldUseApi() ? "" : " disabled"}>开始</button>`);
        if (task.status === "in_progress") actions.push(`<input type="text" data-agent-task-result="${escapeAttribute(task.task_id || "")}" maxlength="2000" placeholder="执行结果摘要"><button type="button" data-agent-task-update="completed" data-agent-task-id="${escapeAttribute(task.task_id || "")}"${shouldUseApi() ? "" : " disabled"}>完成</button>`);
        if (task.status === "failed" || task.status === "cancelled") actions.push(`<button type="button" data-agent-task-update="planned" data-agent-task-id="${escapeAttribute(task.task_id || "")}"${shouldUseApi() ? "" : " disabled"}>重新计划</button>`);
        return `<div class="workbench-item"><strong>${escapeHtml(agentTaskTypeLabel(task.task_type))}</strong><span>优先级 ${number(task.priority)} / ${escapeHtml(agentTaskStatusLabel(task.status))}</span><p>${escapeHtml(task.reason || "暂无任务原因。")}</p>${task.result_summary ? `<p>结果：${escapeHtml(task.result_summary)}</p>` : ""}<div class="actions">${actions.join("")}</div></div>`;
      });
      const suggestionRows = suggestions.map((action, index) => `<div class="workbench-item"><strong>${escapeHtml(agentTaskTypeLabel(action.task_type))}</strong><span>建议优先级 ${number(action.priority)}</span><p>${escapeHtml(action.reason || "")}</p><button type="button" data-agent-task-create="${index}"${shouldUseApi() ? "" : " disabled"}>创建任务</button></div>`);
      const rows = [...taskRows, ...suggestionRows];
      return rows.length ? `<div class="workbench-list">${rows.join("")}</div>` : "<p>暂无 Agent 任务。</p>";
    }

    function bindProjectAgentTasks(detail) {
      document.querySelectorAll("[data-agent-task-create]").forEach(button => {
        button.addEventListener("click", () => createProjectAgentTask(button, detail));
      });
      document.querySelectorAll("[data-agent-task-update]").forEach(button => {
        button.addEventListener("click", () => updateProjectAgentTask(button));
      });
    }

    async function createProjectAgentTask(button, detail) {
      if (!shouldUseApi()) return;
      const status = document.getElementById("projectAgentTaskStatus");
      const action = (detail.next_actions || [])[Number(button.dataset.agentTaskCreate)];
      if (!action) return;
      try {
        status.textContent = "创建任务中...";
        const response = await fetch(`/v1/projects/${encodeURIComponentOwnerRepo(detail.full_name || repoName())}/agent-tasks`, {
          method: "POST",
          headers: adminWriteHeaders(),
          body: JSON.stringify({
            task_type: action.task_type,
            priority: action.priority,
            reason: action.reason,
            source: "project_page",
            payload: { subscription_action: action.subscription_action || "watch" }
          })
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        status.textContent = "任务已创建，正在刷新。";
        window.location.reload();
      } catch (error) {
        status.textContent = `任务创建失败：${error.message}`;
      }
    }

    async function updateProjectAgentTask(button) {
      if (!shouldUseApi()) return;
      const status = document.getElementById("projectAgentTaskStatus");
      try {
        status.textContent = "更新任务中...";
        const taskId = button.dataset.agentTaskId || "";
        const resultInput = document.querySelector(`[data-agent-task-result="${taskId}"]`);
        const payload = { status: button.dataset.agentTaskUpdate || "planned" };
        if (payload.status === "completed" && resultInput) payload.result_summary = resultInput.value.trim();
        const response = await fetch(`/v1/agent-tasks/${encodeURIComponent(taskId)}`, {
          method: "PATCH",
          headers: adminWriteHeaders(),
          body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        status.textContent = "任务状态已更新，正在刷新。";
        window.location.reload();
      } catch (error) {
        status.textContent = `任务更新失败：${error.message}`;
      }
    }

    function agentTaskTypeLabel(value) {
      return ({ observe: "观察", review_risk: "风险复查", deep_analysis: "深度分析", notify: "订阅推送", ignore: "忽略", continue_tracking: "继续跟踪" })[value] || value || "观察";
    }

    function agentTaskStatusLabel(value) {
      return ({ planned: "待执行", in_progress: "执行中", completed: "已完成", failed: "失败", cancelled: "已取消", suggested: "建议" })[value] || value || "未知";
    }

    function bindProjectFeedback(detail) {
      document.querySelectorAll("[data-project-feedback]").forEach(button => {
        button.addEventListener("click", () => submitProjectFeedback(button, detail));
      });
    }

    async function submitProjectFeedback(button, detail) {
      if (!shouldUseApi()) return;
      const status = document.getElementById("projectFeedbackStatus");
      const action = button.dataset.projectFeedback || "";
      const payload = projectFeedbackPayload(detail.full_name || repoName(), action);
      try {
        setFeedbackStatus(status, "写入中...", false);
        const response = await fetch("/v1/feedback", {
          method: "POST",
          headers: adminWriteHeaders(),
          body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        setFeedbackStatus(status, "反馈已写入，刷新后会影响推荐排序。", false);
      } catch (error) {
        setFeedbackStatus(status, `反馈写入失败：${error.message || error}`, true);
      }
    }

    function projectFeedbackPayload(fullName, action) {
      const ratings = { useful: 2, not_fit: -2, watch: 1 };
      const notes = { useful: "project useful", not_fit: "project not fit", watch: "continue tracking" };
      const params = new URLSearchParams(window.location.search);
      return {
        full_name: fullName,
        profile: params.get("profile") || "",
        rating: ratings[action] || 0,
        labels: [action],
        note: notes[action] || action,
        source: "project_page"
      };
    }

    function setFeedbackStatus(target, message, isError) {
      if (!target) return;
      target.textContent = message;
      target.classList.toggle("error", Boolean(isError));
    }

    function adminWriteHeaders() {
      const token = adminToken();
      const headers = { "Content-Type": "application/json" };
      if (token) headers["X-Admin-Token"] = token;
      return headers;
    }

    function adminToken() {
      const params = new URLSearchParams(window.location.search);
      const token = params.get("admin_token") || window.localStorage.getItem("github_weekly_admin_token") || "";
      if (params.get("admin_token")) window.localStorage.setItem("github_weekly_admin_token", params.get("admin_token"));
      return token.trim();
    }

    function ragEvidenceHtml(detail) {
      const contexts = Array.isArray(detail.rag_contexts) ? detail.rag_contexts : [];
      const summary = Array.isArray(detail.rag_summary) ? detail.rag_summary : [];
      const summaryHtml = summary.length ? `<p class="desc">${escapeHtml(summary.join(" "))}</p>` : "";
      if (!contexts.length) {
        return `${summaryHtml || "<p>暂无 RAG 证据块。</p>"}`;
      }
      const citations = Array.isArray(detail.rag_citations) ? detail.rag_citations : [];
      const contextHtml = contexts.map((context, index) => {
        const metadata = context.metadata || {};
        const citation = citations[index] || {};
        const title = metadata.full_name || citation.full_name || detail.full_name || "";
        const meta = [
          metadata.language || "",
          metadata.category || "",
          metadata.run_date || "",
          metadata.source || "",
        ].filter(Boolean).join(" / ");
        const chunkLabel = citation.chunk_id ? `引用：${citation.chunk_id}` : `证据块 ${index + 1}`;
        return `<div class="evidence-item">
          <strong>${escapeHtml(title)}</strong>
          <span>${escapeHtml(meta || chunkLabel)}</span>
          <p>${escapeHtml(context.text || "")}</p>
          <span>${escapeHtml(chunkLabel)}</span>
        </div>`;
      }).join("");
      const prompt = detail.rag_prompt_context
        ? `<details><summary>查看 prompt_context</summary><pre class="prompt-context">${escapeHtml(detail.rag_prompt_context)}</pre></details>`
        : "";
      return `${summaryHtml}<div class="evidence-list">${contextHtml}</div>${prompt}`;
    }

    function ragExplanationsHtml(detail) {
      const explanations = Array.isArray(detail.rag_explanations) ? detail.rag_explanations : [];
      if (!shouldUseApi()) {
        return "<p>RAG 解释历史需要本地后端或 URL 带 api=1 后读取。</p>";
      }
      if (!explanations.length) {
        return "<p>暂无该项目的 RAG 解释历史。可先通过 /v1/rag/explain 生成解释。</p>";
      }
      return `<div class="evidence-list">${explanations.map(item => {
        const citationCount = Array.isArray(item.citations) ? item.citations.length : 0;
        const meta = [
          item.mode || "",
          item.quality_level ? `质量 ${item.quality_level}` : "",
          `质量分 ${number(item.quality_score)}`,
          `引用 ${citationCount}`,
          item.created_at || "",
        ].filter(Boolean).join(" / ");
        return `<div class="evidence-item">
          <strong>${escapeHtml(item.query || "-")}</strong>
          <span>${escapeHtml(meta)}</span>
          <p>${escapeHtml(item.answer || "")}</p>
        </div>`;
      }).join("")}</div>`;
    }

    function similarHtml(currentRepo, projects, summary) {
      if (!projects.length) return "<p>暂无相似历史项目。</p>";
      const summaryHtml = Array.isArray(summary) && summary.length ? `<p class="desc">${escapeHtml(summary[0])}</p>` : "";
      return `${summaryHtml}<ul>${projects.map(project => {
        const reasons = Array.isArray(project.similarity_reasons) && project.similarity_reasons.length
          ? `<br><span>${escapeHtml(project.similarity_reasons.join("；"))}</span>`
          : "";
        const score = project.similarity_score ? ` / 相似度 ${number(project.similarity_score)}` : "";
        return `<li><a href="project.html?repo=${encodeURIComponent(project.full_name || "")}${shouldUseApi() ? "&api=1" : ""}">${escapeHtml(project.full_name || "")}</a> <span>${escapeHtml(project.language || "Unknown")} / ${escapeHtml(project.category || "Other")} / 新增 Star ${number(project.star_growth)}${score}</span>${reasons}<br><span><a href="${escapeAttribute(compareUrl([currentRepo, project.full_name]))}">与当前项目对比</a></span></li>`;
      }).join("")}</ul>`;
    }

    function listHtml(items, emptyText) {
      const values = unique(items);
      if (!values.length) return `<p>${escapeHtml(emptyText)}</p>`;
      return `<ul>${values.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
    }

    function tags(items, className, emptyText) {
      const values = unique(items);
      if (!values.length) return `<p>${escapeHtml(emptyText)}</p>`;
      return values.map(value => `<span class="tag ${className}">${escapeHtml(value)}</span>`).join("");
    }

    function metric(label, value) {
      return `<div class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
    }

    function similarProjects(base, projects) {
      return projects
        .filter(project => project.full_name && project.full_name !== base.full_name)
        .map(project => ({ project, score: similarityScore(base, project) }))
        .filter(item => item.score > 0)
        .sort((a, b) => b.score - a.score || number(b.project.star_growth) - number(a.project.star_growth))
        .slice(0, 5)
        .map(item => item.project);
    }

    function similarityScore(base, project) {
      let score = 0;
      if (base.language && base.language === project.language) score += 4;
      if (base.category && base.category === project.category) score += 5;
      score += overlap(base.sources || [], project.sources || []);
      score += Math.min(4, overlap(projectKeywords(base), projectKeywords(project)));
      return score;
    }

    function projectKeywords(project) {
      return String([project.full_name, project.description, project.category, ...(project.selection_reasons || [])].join(" "))
        .toLowerCase()
        .replace(/[\\/\\-_]/g, " ")
        .split(/\\s+/)
        .filter(value => value.length >= 3);
    }

    function overlap(a, b) {
      const right = new Set(b);
      return unique(a).filter(value => right.has(value)).length;
    }

    function bestTrendingRank(history) {
      const ranks = history.map(project => number(project.trending_rank)).filter(value => value > 0);
      return ranks.length ? Math.min(...ranks) : 0;
    }

    function repoName() {
      return new URLSearchParams(window.location.search).get("repo") || "";
    }

    function compareUrl(repos) {
      const params = new URLSearchParams();
      const names = [...new Set(repos.filter(Boolean))];
      params.set("repos", names.join(","));
      const apiMode = new URLSearchParams(window.location.search).get("api");
      if (apiMode === "1" || apiMode === "0") params.set("api", apiMode);
      return `compare.html?${params.toString()}`;
    }

    function shouldUseApi() {
      const params = new URLSearchParams(window.location.search);
      if (params.get("api") === "1") return true;
      if (params.get("api") === "0") return false;
      return ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname);
    }

    function encodeURIComponentOwnerRepo(repo) {
      return repo.split("/").map(part => encodeURIComponent(part)).join("/");
    }

    function jsonOrThrow(response) {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    }

    function unique(items) {
      return [...new Set((items || []).map(value => String(value)).filter(Boolean))];
    }

    function number(value) {
      const parsed = Number(value || 0);
      return Number.isFinite(parsed) ? parsed : 0;
    }

    function signedNumber(value) {
      const numberValue = number(value);
      return numberValue > 0 ? `+${numberValue}` : numberValue;
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
    }

    function escapeAttribute(value) {
      return escapeHtml(value).replace(/`/g, "&#96;");
    }
  </script>
</body>
</html>
"""


def _runs_dashboard_content() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>运行状态面板</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f8fa;
      --panel: #ffffff;
      --text: #20242a;
      --muted: #5f6b7a;
      --line: #d9dee7;
      --accent: #2563eb;
      --ok: #15803d;
      --warn: #a16207;
      --bad: #b42318;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 15px;
      line-height: 1.5;
    }
    header {
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }
    .wrap {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
    }
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      min-height: 68px;
    }
    h1 {
      margin: 0;
      font-size: 22px;
      letter-spacing: 0;
    }
    nav {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      font-size: 14px;
    }
    a {
      color: var(--accent);
      text-decoration: none;
    }
    a:hover { text-decoration: underline; }
    main {
      padding: 20px 0 36px;
    }
    .filters {
      display: grid;
      grid-template-columns: repeat(6, minmax(140px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }
    label {
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 13px;
    }
    input,
    select {
      width: 100%;
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 7px 10px;
      background: var(--panel);
      color: var(--text);
      font: inherit;
    }
    .summary {
      display: grid;
      grid-template-columns: repeat(6, minmax(130px, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }
    .metric {
      min-height: 72px;
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
      padding: 12px;
      display: grid;
      align-content: center;
      gap: 4px;
    }
    .metric span {
      color: var(--muted);
      font-size: 12px;
    }
    .metric strong {
      font-size: 20px;
    }
    .table-shell {
      overflow-x: auto;
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 1120px;
    }
    th,
    td {
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      white-space: nowrap;
    }
    th {
      color: var(--muted);
      font-size: 12px;
      font-weight: 600;
      background: #fbfcfe;
    }
    td.num {
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      border-radius: 999px;
      border: 1px solid var(--line);
      padding: 2px 8px;
      font-size: 12px;
      font-weight: 600;
    }
    .ok {
      color: var(--ok);
      background: #f0fdf4;
      border-color: #bbf7d0;
    }
    .warn {
      color: var(--warn);
      background: #fffbeb;
      border-color: #fde68a;
    }
    .bad {
      color: var(--bad);
      background: #fff1f2;
      border-color: #fecaca;
    }
    .links {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .empty {
      padding: 28px;
      text-align: center;
      color: var(--muted);
    }
    @media (max-width: 900px) {
      .topbar {
        align-items: flex-start;
        flex-direction: column;
        padding: 14px 0;
      }
      .filters,
      .summary {
        grid-template-columns: 1fr 1fr;
      }
    }
    @media (max-width: 560px) {
      .wrap { width: min(100% - 20px, 1180px); }
      .filters,
      .summary {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <header>
    <div class="wrap topbar">
      <h1>运行状态面板</h1>
      <nav>
        <a href="index.html">周报归档</a>
        <a href="explorer.html">项目筛选</a>
        <a href="runs.json">runs.json</a>
      </nav>
    </div>
  </header>
  <main class="wrap">
    <section class="filters" aria-label="筛选条件">
      <label>关键词
        <input id="query" type="search" autocomplete="off">
      </label>
      <label>状态
        <select id="status">
          <option value="">全部</option>
          <option value="success">成功</option>
          <option value="empty">空结果</option>
          <option value="failed">失败</option>
        </select>
      </label>
      <label>生成方式
        <select id="fallback">
          <option value="">全部</option>
          <option value="kimi">Kimi</option>
          <option value="fallback">规则版</option>
        </select>
      </label>
      <label>Telegram
        <select id="telegram">
          <option value="">全部</option>
          <option value="sent">已推送</option>
          <option value="not_sent">未推送</option>
        </select>
      </label>
      <label>采集异常
        <select id="errorKind">
          <option value="">全部</option>
        </select>
      </label>
      <label>排序
        <select id="sort">
          <option value="date">最新运行</option>
          <option value="collector">采集成功率</option>
          <option value="trending">Trending Top10 命中率</option>
          <option value="readme">README 抓取率</option>
          <option value="selected">入选项目数</option>
        </select>
      </label>
    </section>
    <section id="summary" class="summary" aria-label="运行概览"></section>
    <div class="table-shell">
      <table>
        <thead>
          <tr>
            <th>日期</th>
            <th>状态</th>
            <th>入选</th>
            <th>采集</th>
            <th>采集成功率</th>
            <th>Trending Top10</th>
            <th>README</th>
            <th>采集异常</th>
            <th>Kimi</th>
            <th>Telegram</th>
            <th>链接</th>
          </tr>
        </thead>
        <tbody id="rows">
          <tr><td class="empty" colspan="11">正在读取运行数据</td></tr>
        </tbody>
      </table>
    </div>
  </main>
  <script>
    const state = { runs: [] };
    const controls = {
      query: document.getElementById("query"),
      status: document.getElementById("status"),
      fallback: document.getElementById("fallback"),
      telegram: document.getElementById("telegram"),
      errorKind: document.getElementById("errorKind"),
      sort: document.getElementById("sort")
    };
    const rows = document.getElementById("rows");
    const summary = document.getElementById("summary");

    fetch("runs.json", { cache: "no-store" })
      .then(response => response.json())
      .then(data => {
        state.runs = Array.isArray(data.runs) ? data.runs : [];
        hydrateErrorKinds();
        restoreFiltersFromUrl();
        render();
      })
      .catch(() => {
        rows.innerHTML = '<tr><td class="empty" colspan="11">无法读取 runs.json</td></tr>';
      });

    Object.values(controls).forEach(control => control.addEventListener("input", render));

    function render() {
      const query = controls.query.value.trim().toLowerCase();
      let filtered = state.runs.filter(run => {
        const errorKinds = collectorErrorKinds(run);
        const text = [run.run_date, run.status, run.report_url, run.telegram_report_url, run.telegram_explorer_url, ...errorKinds].join(" ").toLowerCase();
        return (!query || text.includes(query))
          && (!controls.status.value || run.status === controls.status.value)
          && (!controls.fallback.value || (controls.fallback.value === "fallback" ? run.fallback_used : run.kimi_used))
          && (!controls.telegram.value || (controls.telegram.value === "sent" ? run.telegram_sent : !run.telegram_sent))
          && (!controls.errorKind.value || errorKinds.includes(controls.errorKind.value));
      });
      filtered = filtered.sort(compareRuns);
      summary.innerHTML = summaryHtml(filtered);
      rows.innerHTML = filtered.length ? filtered.map(rowHtml).join("") : '<tr><td class="empty" colspan="11">没有匹配的运行记录</td></tr>';
      updateUrl();
    }

    function hydrateErrorKinds() {
      const kinds = [...new Set(state.runs.flatMap(collectorErrorKinds).filter(Boolean))].sort();
      controls.errorKind.innerHTML = '<option value="">全部</option>' + kinds.map(kind => `<option value="${escapeAttribute(kind)}">${escapeHtml(errorKindLabel(kind))}</option>`).join("");
    }

    function summaryHtml(runs) {
      const latest = runs.map(run => run.run_date || "").sort().reverse()[0] || "-";
      const telegramCount = runs.filter(run => run.telegram_sent).length;
      const averageCollector = average(runs, "collector_success_rate");
      const averageTrending = average(runs, "trending_top10_fulfillment_rate");
      const errorCount = runs.reduce((total, run) => total + number(run.collector_failed_count), 0);
      return [
        metric("运行次数", runs.length),
        metric("最新日期", latest),
        metric("采集异常", errorCount),
        metric("Telegram 成功", telegramCount),
        metric("平均采集成功率", percent(averageCollector)),
        metric("平均 Trending 命中", percent(averageTrending))
      ].join("");
    }

    function rowHtml(run) {
      const report = run.telegram_report_url || run.report_url || "";
      const explorer = run.telegram_explorer_url || "";
      return `<tr>
        <td>${escapeHtml(run.run_date || "")}</td>
        <td>${statusBadge(run)}</td>
        <td class="num">${number(run.selected_count)}</td>
        <td class="num">${number(run.collected_count)}</td>
        <td>${rateBadge(run.collector_success_rate)}</td>
        <td>${rateBadge(run.trending_top10_fulfillment_rate)} <span>${number(run.trending_top10_selected_count)}/${number(run.trending_top10_available_count)}</span></td>
        <td>${rateBadge(run.readme_fetch_rate)}</td>
        <td>${collectorErrorText(run)}</td>
        <td>${run.kimi_used ? badge("Kimi", "ok") : badge("规则版", run.fallback_used ? "warn" : "bad")}</td>
        <td>${run.telegram_sent ? badge("已推送", "ok") : badge("未推送", "warn")}</td>
        <td><span class="links">${link("周报", report)}${link("筛选", explorer)}</span></td>
      </tr>`;
    }

    function statusBadge(run) {
      if (run.status === "success") return badge("成功", "ok");
      if (run.status === "empty") return badge("空结果", "warn");
      return badge(run.status || "未知", "bad");
    }

    function rateBadge(value) {
      const rate = number(value);
      const level = rate >= 0.9 ? "ok" : rate >= 0.6 ? "warn" : "bad";
      return badge(percent(rate), level);
    }

    function badge(text, level) {
      return `<span class="badge ${level}">${escapeHtml(text)}</span>`;
    }

    function link(label, href) {
      if (!href) return "";
      return `<a href="${escapeAttribute(href)}">${escapeHtml(label)}</a>`;
    }

    function collectorErrorKinds(run) {
      if (Array.isArray(run.collector_error_kinds)) return run.collector_error_kinds.map(value => String(value)).filter(Boolean);
      if (!Array.isArray(run.collector_error_summary)) return [];
      return [...new Set(run.collector_error_summary.map(error => String(error.error_kind || "")).filter(Boolean))];
    }

    function collectorErrorText(run) {
      const errors = Array.isArray(run.collector_error_summary) ? run.collector_error_summary : [];
      if (!errors.length) return badge("无异常", "ok");
      return errors.slice(0, 3).map(error => {
        const kind = String(error.error_kind || "unknown");
        const statusCode = number(error.status_code);
        const label = `${errorKindLabel(kind)}${statusCode ? " " + statusCode : ""}`;
        return badge(label, kind.includes("rate") ? "warn" : "bad");
      }).join("");
    }

    function errorKindLabel(kind) {
      const labels = {
        rate_limited: "主限流",
        secondary_rate_limited: "二级限流",
        authentication_failed: "认证失败",
        not_found: "仓库不存在",
        server_error: "GitHub 服务错误",
        http_error: "HTTP 错误",
        runtime_error: "运行错误",
        unknown: "未知异常"
      };
      return labels[kind] || kind;
    }

    function metric(label, value) {
      return `<div class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
    }

    function compareRuns(a, b) {
      const sort = controls.sort.value;
      if (sort === "collector") return number(b.collector_success_rate) - number(a.collector_success_rate);
      if (sort === "trending") return number(b.trending_top10_fulfillment_rate) - number(a.trending_top10_fulfillment_rate);
      if (sort === "readme") return number(b.readme_fetch_rate) - number(a.readme_fetch_rate);
      if (sort === "selected") return number(b.selected_count) - number(a.selected_count);
      return String(b.run_date || "").localeCompare(String(a.run_date || ""));
    }

    function restoreFiltersFromUrl() {
      const params = new URLSearchParams(window.location.search);
      const keys = { q: "query", status: "status", fallback: "fallback", telegram: "telegram", error: "errorKind", sort: "sort" };
      Object.entries(keys).forEach(([param, key]) => {
        if (params.has(param)) controls[key].value = params.get(param) || "";
      });
    }

    function updateUrl() {
      const params = new URLSearchParams();
      if (controls.query.value.trim()) params.set("q", controls.query.value.trim());
      if (controls.status.value) params.set("status", controls.status.value);
      if (controls.fallback.value) params.set("fallback", controls.fallback.value);
      if (controls.telegram.value) params.set("telegram", controls.telegram.value);
      if (controls.errorKind.value) params.set("error", controls.errorKind.value);
      if (controls.sort.value && controls.sort.value !== "date") params.set("sort", controls.sort.value);
      const query = params.toString();
      const next = `${window.location.pathname}${query ? "?" + query : ""}`;
      window.history.replaceState({}, "", next);
    }

    function average(items, key) {
      return items.length ? items.reduce((total, item) => total + number(item[key]), 0) / items.length : 0;
    }

    function percent(value) {
      return `${Math.round(number(value) * 100)}%`;
    }

    function number(value) {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : 0;
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
    }

    function escapeAttribute(value) {
      return escapeHtml(value).replace(/`/g, "&#96;");
    }
  </script>
</body>
</html>
"""


def _jobs_dashboard_content() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GitHub 周报任务状态</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f8fa;
      --panel: #ffffff;
      --text: #20242a;
      --muted: #5f6b7a;
      --line: #d9dee7;
      --accent: #2563eb;
      --ok: #15803d;
      --warn: #a16207;
      --bad: #b42318;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 15px;
      line-height: 1.5;
    }
    header {
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }
    .wrap {
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
    }
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      min-height: 68px;
    }
    h1 {
      margin: 0;
      font-size: 22px;
      font-weight: 700;
      letter-spacing: 0;
    }
    nav {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
    }
    nav a {
      color: var(--accent);
      font-weight: 700;
      text-decoration: none;
    }
    main {
      padding: 20px 0 32px;
    }
    .filters {
      display: grid;
      grid-template-columns: minmax(160px, 1fr) minmax(160px, 1fr) minmax(180px, 1.2fr) minmax(220px, 2fr);
      gap: 10px;
      margin-bottom: 14px;
    }
    .task-panel {
      margin-bottom: 14px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel);
    }
    .task-panel h2 {
      margin: 0 0 10px;
      font-size: 16px;
      line-height: 1.3;
    }
    .task-form {
      display: grid;
      grid-template-columns: minmax(160px, 1.2fr) minmax(120px, .8fr) minmax(160px, 1fr) minmax(140px, .8fr) minmax(140px, .8fr);
      gap: 10px;
      align-items: end;
    }
    label {
      display: grid;
      gap: 5px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
    }
    input, select, button {
      height: 38px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel);
      color: var(--text);
      font: inherit;
      padding: 0 10px;
    }
    button {
      cursor: pointer;
      border-color: var(--accent);
      background: var(--accent);
      color: #fff;
      font-weight: 700;
    }
    button:disabled {
      cursor: not-allowed;
      border-color: var(--line);
      background: #e5e7eb;
      color: var(--muted);
    }
    .check-label {
      grid-template-columns: 18px 1fr;
      align-items: center;
      gap: 8px;
      min-height: 38px;
    }
    .check-label input {
      width: 16px;
      height: 16px;
      padding: 0;
    }
    .task-status {
      margin: 10px 0 0;
      color: var(--muted);
      font-size: 13px;
    }
    .row-actions {
      display: grid;
      gap: 6px;
      min-width: 150px;
    }
    .secondary-button {
      width: fit-content;
      height: 30px;
      padding: 0 8px;
      border-color: var(--line);
      background: var(--panel);
      color: var(--accent);
      font-size: 12px;
    }
    .precheck-result {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
      overflow-wrap: anywhere;
    }
    .precheck-result.ok {
      color: var(--ok);
    }
    .precheck-result.blocked {
      color: var(--bad);
    }
    .execute-button {
      border-color: var(--warn);
      color: var(--warn);
    }
    .retry-button {
      border-color: var(--bad);
      color: var(--bad);
    }
    .summary {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }
    .metric {
      min-height: 72px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 6px;
    }
    .metric span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }
    .metric strong {
      display: block;
      margin-top: 6px;
      font-size: 18px;
      line-height: 1.2;
    }
    .table-shell {
      overflow-x: auto;
      border: 1px solid var(--line);
      background: var(--panel);
    }
    table {
      width: 100%;
      min-width: 980px;
      border-collapse: collapse;
    }
    th, td {
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
      text-align: left;
    }
    th {
      background: #eef2f7;
      color: #344054;
      font-size: 13px;
    }
    .status {
      display: inline-block;
      min-width: 78px;
      padding: 2px 8px;
      border-radius: 999px;
      text-align: center;
      font-size: 12px;
      font-weight: 700;
      border: 1px solid var(--line);
      background: #f9fafb;
    }
    .status.succeeded { color: var(--ok); border-color: #bbf7d0; background: #f0fdf4; }
    .status.failed { color: var(--bad); border-color: #fecaca; background: #fff1f2; }
    .status.running { color: var(--accent); border-color: #bfdbfe; background: #eff6ff; }
    .status.planned { color: var(--warn); border-color: #fde68a; background: #fffbeb; }
    .muted {
      color: var(--muted);
    }
    .mono {
      font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
      overflow-wrap: anywhere;
    }
    a {
      color: var(--accent);
      font-weight: 700;
      text-decoration: none;
    }
    .empty {
      padding: 28px 12px;
      color: var(--muted);
      text-align: center;
    }
    @media (max-width: 760px) {
      .topbar {
        align-items: flex-start;
        flex-direction: column;
        padding: 16px 0;
      }
      .filters,
      .task-form,
      .summary {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <header>
    <div class="wrap topbar">
      <h1>GitHub 周报任务状态</h1>
      <nav>
        <a href="index.html">周报归档</a>
        <a href="runs.html">运行状态</a>
        <a href="explorer.html">项目筛选</a>
        <a href="jobs.json">jobs.json</a>
      </nav>
    </div>
  </header>
  <main class="wrap">
    <section class="filters" aria-label="任务筛选">
      <label>状态
        <select id="status">
          <option value="">全部</option>
          <option value="planned">planned</option>
          <option value="running">running</option>
          <option value="succeeded">succeeded</option>
          <option value="failed">failed</option>
        </select>
      </label>
      <label>类型
        <select id="kind">
          <option value="">全部</option>
          <option value="weekly_report">weekly_report</option>
          <option value="rag_backfill">rag_backfill</option>
          <option value="rag_corpus_rebuild">rag_corpus_rebuild</option>
          <option value="rag_embedding_build">rag_embedding_build</option>
          <option value="rag_search_evaluation">rag_search_evaluation</option>
          <option value="dev_context_index">dev_context_index</option>
        </select>
      </label>
      <label>Profile
        <input id="profile" type="search" autocomplete="off">
      </label>
      <label>关键词
        <input id="query" type="search" autocomplete="off">
      </label>
    </section>
    <section class="task-panel" aria-label="创建 planned 任务">
      <h2>创建 planned 任务</h2>
      <div class="task-form">
        <label>Profile
          <input id="createProfile" type="search" autocomplete="off" placeholder="agent_development">
        </label>
        <label>回看天数
          <input id="createDaysBack" type="number" min="1" max="30" value="7">
        </label>
        <label>来源
          <select id="createSource">
            <option value="github_trending">github_trending</option>
            <option value="github_search">github_search</option>
            <option value="">不指定</option>
          </select>
        </label>
        <label class="check-label">
          <input id="createPreviewMode" name="createDeliveryMode" type="radio" value="preview" checked>
          <span>预览，不推送</span>
        </label>
        <label class="check-label">
          <input id="createDeliveryMode" name="createDeliveryMode" type="radio" value="delivery">
          <span>确认推送</span>
        </label>
        <button id="createTask" type="button">创建任务</button>
      </div>
      <p id="createTaskStatus" class="task-status">只在本地后端或 api=1 模式下创建 planned 任务。</p>
    </section>
    <section id="summary" class="summary" aria-label="任务概览"></section>
    <div class="table-shell">
      <table>
        <thead>
          <tr>
            <th>任务</th>
            <th>状态</th>
            <th>Profile</th>
            <th>日期</th>
            <th>提交时间</th>
            <th>完成时间</th>
            <th>结果</th>
            <th>错误</th>
          </tr>
        </thead>
        <tbody id="rows">
          <tr><td class="empty" colspan="8">加载中</td></tr>
        </tbody>
      </table>
    </div>
  </main>
  <script>
    const state = { jobs: [] };
    const controls = {
      status: document.getElementById("status"),
      kind: document.getElementById("kind"),
      profile: document.getElementById("profile"),
      query: document.getElementById("query"),
    };
    const createControls = {
      profile: document.getElementById("createProfile"),
      daysBack: document.getElementById("createDaysBack"),
      source: document.getElementById("createSource"),
      previewMode: document.getElementById("createPreviewMode"),
      deliveryMode: document.getElementById("createDeliveryMode"),
      button: document.getElementById("createTask"),
      status: document.getElementById("createTaskStatus"),
    };
    const rows = document.getElementById("rows");
    const summary = document.getElementById("summary");

    restoreFilters();
    bind();
    setupCreateTask();
    loadJobs()
      .then(data => {
        state.jobs = Array.isArray(data.jobs) ? data.jobs : [];
        render();
      })
      .catch(() => {
        rows.innerHTML = '<tr><td class="empty" colspan="8">无法读取 jobs.json</td></tr>';
      });

    function bind() {
      Object.values(controls).forEach(control => control.addEventListener("input", render));
      Object.values(controls).forEach(control => control.addEventListener("change", render));
      rows.addEventListener("click", event => {
        const precheckButton = event.target.closest("[data-precheck]");
        if (precheckButton) {
          runExecutionCheck(precheckButton);
          return;
        }
        const executeButton = event.target.closest("[data-execute]");
        if (executeButton) {
          runJobExecution(executeButton);
          return;
        }
        const retryButton = event.target.closest("[data-retry]");
        if (retryButton) runJobRetry(retryButton);
      });
    }

    function setupCreateTask() {
      if (!shouldUseApi()) {
        createControls.button.disabled = true;
        createControls.status.textContent = "当前使用静态 JSON，只能查看任务；启动本地后端或添加 api=1 后可创建 planned 任务。";
        return;
      }
      createControls.button.addEventListener("click", createPlannedTask);
    }

    function createPlannedTask() {
      createControls.button.disabled = true;
      createControls.status.textContent = "正在创建 planned 任务...";
      const source = createControls.source.value.trim();
      const payload = {
        profile: createControls.profile.value.trim(),
        sources: source ? [source] : [],
        dry_run: createControls.previewMode.checked,
        confirm_delivery: createControls.deliveryMode.checked,
        days_back: number(createControls.daysBack.value) || 7,
        trigger_source: "jobs_page",
        requested_by: "local-ui",
      };
      fetch("/v1/runs/trigger", {
        method: "POST",
        headers: adminWriteHeaders(),
        body: JSON.stringify(payload),
      })
        .then(jsonOrThrow)
        .then(data => {
          const warnings = (data.safety_warnings || []).join(" ");
          createControls.status.textContent = `已创建 ${data.job_id || "planned 任务"}。${warnings}`;
          controls.status.value = "planned";
          return loadJobs();
        })
        .then(data => {
          state.jobs = Array.isArray(data.jobs) ? data.jobs : [];
          render();
        })
        .catch(error => {
          createControls.status.textContent = `创建失败：${error.message || error}`;
        })
        .finally(() => {
          createControls.button.disabled = false;
        });
    }

    function loadJobs() {
      if (!shouldUseApi()) return loadJobsJson();
      return fetch("/v1/jobs?limit=200", { cache: "no-store" })
        .then(jsonOrThrow)
        .catch(loadJobsJson);
    }

    function loadJobsJson() {
      return fetch("jobs.json", { cache: "no-store" })
        .then(jsonOrThrow);
    }

    function runExecutionCheck(button) {
      const jobId = button.dataset.precheck || "";
      const target = document.getElementById(button.dataset.target || "");
      if (!target) return;
      if (!shouldUseApi()) {
        target.className = "precheck-result blocked";
        target.textContent = "执行前检查需要本地后端或 api=1 模式。";
        return;
      }
      button.disabled = true;
      target.className = "precheck-result";
      target.textContent = "检查中...";
      fetch(`/v1/job-execution-check?job_id=${encodeURIComponent(jobId)}`, { cache: "no-store" })
        .then(jsonOrThrow)
        .then(data => {
          target.className = `precheck-result ${data.executable ? "ok" : "blocked"}`;
          target.innerHTML = precheckHtml(data);
        })
        .catch(error => {
          target.className = "precheck-result blocked";
          target.textContent = `检查失败：${error.message || error}`;
        })
        .finally(() => {
          button.disabled = false;
        });
    }

    function precheckHtml(data) {
      if (!data || !data.found) return "未找到任务。";
      const lines = [
        data.executable ? "可执行" : "不可执行",
        ...(data.blockers || []).map(item => `阻止：${item}`),
        ...(data.warnings || []).map(item => `提示：${item}`),
      ];
      if (data.next_command) lines.push(`命令：${data.next_command}`);
      return lines.map(line => `<div>${escapeHtml(line)}</div>`).join("");
    }

    function runJobExecution(button) {
      const jobId = button.dataset.execute || "";
      const target = document.getElementById(button.dataset.target || "");
      if (!target) return;
      if (!shouldUseApi()) {
        target.className = "precheck-result blocked";
        target.textContent = "执行任务需要本地后端或 api=1 模式。";
        return;
      }
      if (!window.confirm(`确认执行任务 ${jobId}？`)) return;
      button.disabled = true;
      target.className = "precheck-result";
      target.textContent = "执行中...";
      fetch(`/v1/jobs/${encodeURIComponent(jobId)}/execute`, {
        method: "POST",
        headers: adminWriteHeaders(),
        body: JSON.stringify({ confirm_execution: true }),
      })
        .then(jsonOrThrow)
        .then(data => {
          target.className = `precheck-result ${data.accepted && data.executed ? "ok" : "blocked"}`;
          target.innerHTML = executionHtml(data);
          return loadJobs();
        })
        .then(data => {
          state.jobs = Array.isArray(data.jobs) ? data.jobs : [];
          render();
        })
        .catch(error => {
          target.className = "precheck-result blocked";
          target.textContent = `执行失败：${error.message || error}`;
        })
        .finally(() => {
          button.disabled = false;
        });
    }

    function executionHtml(data) {
      const lines = [
        data.accepted ? "已接受执行" : "未执行",
        data.status ? `状态：${data.status}` : "",
        ...(data.blockers || []).map(item => `阻止：${item}`),
        ...(data.warnings || []).map(item => `提示：${item}`),
      ].filter(Boolean);
      return lines.map(line => `<div>${escapeHtml(line)}</div>`).join("");
    }

    function runJobRetry(button) {
      const jobId = button.dataset.retry || "";
      const target = document.getElementById(button.dataset.target || "");
      if (!target) return;
      if (!shouldUseApi()) {
        target.className = "precheck-result blocked";
        target.textContent = "重试任务需要本地后端或 api=1 模式。";
        return;
      }
      if (!window.confirm(`确认为失败任务 ${jobId} 创建重试任务？`)) return;
      button.disabled = true;
      target.className = "precheck-result";
      target.textContent = "重试创建中...";
      fetch(`/v1/jobs/${encodeURIComponent(jobId)}/retry`, {
        method: "POST",
        headers: adminWriteHeaders(),
        body: JSON.stringify({ requested_by: "jobs_page" }),
      })
        .then(jsonOrThrow)
        .then(data => {
          target.className = `precheck-result ${data.accepted && data.retry_created ? "ok" : "blocked"}`;
          target.innerHTML = retryHtml(data);
          return loadJobs();
        })
        .then(data => {
          state.jobs = Array.isArray(data.jobs) ? data.jobs : [];
          render();
        })
        .catch(error => {
          target.className = "precheck-result blocked";
          target.textContent = `重试失败：${error.message || error}`;
        })
        .finally(() => {
          button.disabled = false;
        });
    }

    function retryHtml(data) {
      const lines = [
        data.retry_created ? "已创建重试任务" : data.accepted ? "已命中已有任务" : "未创建重试任务",
        data.job_id ? `任务：${data.job_id}` : "",
        data.status ? `状态：${data.status}` : "",
        data.duplicate_of ? `已有任务：${data.duplicate_of}` : "",
        ...(data.blockers || []).map(item => `阻止：${item}`),
      ].filter(Boolean);
      return lines.map(line => `<div>${escapeHtml(line)}</div>`).join("");
    }

    function shouldUseApi() {
      const params = new URLSearchParams(window.location.search);
      if (params.get("api") === "1") return true;
      if (params.get("api") === "0") return false;
      return ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname);
    }

    function jsonOrThrow(response) {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    }

    function adminWriteHeaders() {
      const token = adminToken();
      const headers = { "Content-Type": "application/json" };
      if (token) headers["X-Admin-Token"] = token;
      return headers;
    }

    function adminToken() {
      const params = new URLSearchParams(window.location.search);
      const token = params.get("admin_token") || window.localStorage.getItem("github_weekly_admin_token") || "";
      if (params.get("admin_token")) window.localStorage.setItem("github_weekly_admin_token", params.get("admin_token"));
      return token.trim();
    }

    function render() {
      const filtered = state.jobs.filter(job => {
        if (controls.status.value && job.status !== controls.status.value) return false;
        if (controls.kind.value && job.kind !== controls.kind.value) return false;
        const profile = String((job.request || {}).profile || "").toLowerCase();
        if (controls.profile.value.trim() && profile !== controls.profile.value.trim().toLowerCase()) return false;
        const haystack = [
          job.job_id,
          job.kind,
          job.status,
          job.run_date,
          job.submitted_at,
          ...((job.request || {}).sources || []),
          profile,
          job.error,
          job.report_url,
          (job.result || {}).report_url,
          (job.result || {}).report_path,
        ].join(" ").toLowerCase();
        return !controls.query.value.trim() || haystack.includes(controls.query.value.trim().toLowerCase());
      });
      renderSummary(filtered);
      rows.innerHTML = filtered.length ? filtered.map(rowHtml).join("") : '<tr><td class="empty" colspan="8">没有匹配任务</td></tr>';
      updateUrl();
    }

    function renderSummary(jobs) {
      const succeeded = jobs.filter(job => job.status === "succeeded").length;
      const failed = jobs.filter(job => job.status === "failed").length;
      const planned = jobs.filter(job => job.status === "planned").length;
      const running = jobs.filter(job => job.status === "running").length;
      summary.innerHTML = [
        metric("任务总数", jobs.length),
        metric("成功", succeeded),
        metric("失败", failed),
        metric("待执行 / 执行中", `${planned} / ${running}`),
      ].join("");
    }

    function metric(label, value) {
      return `<article class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></article>`;
    }

    function rowHtml(job) {
      const request = job.request || {};
      const result = job.result || {};
      const report = result.report_url || job.report_url || "";
      const jobId = job.job_id || "";
      const precheckId = `precheck-${safeId(jobId)}`;
      const executeId = `execute-${safeId(jobId)}`;
      const retryId = `retry-${safeId(jobId)}`;
      const precheckDisabled = shouldUseApi() ? "" : " disabled";
      const precheckTitle = shouldUseApi() ? "执行前检查" : "仅本地后端或 api=1 模式可用";
      const executeEnabled = shouldUseApi() && job.status === "planned";
      const executeDisabled = executeEnabled ? "" : " disabled";
      const executeTitle = executeEnabled ? "确认后执行 planned 任务" : "仅 API 模式下的 planned 任务可执行";
      const retryEnabled = shouldUseApi() && job.status === "failed";
      const retryDisabled = retryEnabled ? "" : " disabled";
      const retryTitle = retryEnabled ? "为 failed 任务创建 planned 重试任务" : "仅 API 模式下的 failed 任务可重试";
      const errorText = escapeHtml(shortText(job.error || result.error || ""));
      const resultText = [
        result.selected_count !== undefined ? `入选 ${number(result.selected_count)}` : "",
        result.collected_count !== undefined ? `候选 ${number(result.collected_count)}` : "",
        result.kimi_used ? "Kimi" : "",
        report ? `<a href="${escapeAttribute(report)}">周报</a>` : "",
      ].filter(Boolean).join(" · ") || "-";
      return `<tr>
        <td><div class="mono"><a href="${escapeAttribute(jobDetailUrl(jobId))}">${escapeHtml(job.job_id || "")}</a></div><div class="muted">${escapeHtml(job.kind || "")}</div></td>
        <td><span class="status ${escapeAttribute(job.status || "")}">${escapeHtml(job.status || "")}</span></td>
        <td>${escapeHtml(request.profile || "-")}</td>
        <td>${escapeHtml(job.run_date || "-")}</td>
        <td>${escapeHtml(job.submitted_at || "-")}</td>
        <td>${escapeHtml(job.finished_at || "-")}</td>
        <td>${resultText}</td>
        <td>
          <div class="row-actions">
            <div>${errorText || "-"}</div>
            <button class="secondary-button" type="button" title="${escapeAttribute(precheckTitle)}" data-precheck="${escapeAttribute(jobId)}" data-target="${escapeAttribute(precheckId)}"${precheckDisabled}>执行前检查</button>
            <button class="secondary-button execute-button" type="button" title="${escapeAttribute(executeTitle)}" data-execute="${escapeAttribute(jobId)}" data-target="${escapeAttribute(executeId)}"${executeDisabled}>确认执行</button>
            <button class="secondary-button retry-button" type="button" title="${escapeAttribute(retryTitle)}" data-retry="${escapeAttribute(jobId)}" data-target="${escapeAttribute(retryId)}"${retryDisabled}>重试</button>
            <div id="${escapeAttribute(precheckId)}" class="precheck-result" aria-live="polite"></div>
            <div id="${escapeAttribute(executeId)}" class="precheck-result" aria-live="polite"></div>
            <div id="${escapeAttribute(retryId)}" class="precheck-result" aria-live="polite"></div>
          </div>
        </td>
      </tr>`;
    }

    function restoreFilters() {
      const params = new URLSearchParams(window.location.search);
      for (const [key, control] of Object.entries(controls)) {
        if (params.has(key)) control.value = params.get(key) || "";
      }
      if (params.has("q")) controls.query.value = params.get("q") || "";
    }

    function jobDetailUrl(jobId) {
      const params = new URLSearchParams();
      params.set("job", jobId || "");
      const apiMode = new URLSearchParams(window.location.search).get("api");
      if (apiMode === "1" || apiMode === "0") params.set("api", apiMode);
      return `job.html?${params.toString()}`;
    }

    function updateUrl() {
      const params = new URLSearchParams();
      const apiMode = new URLSearchParams(window.location.search).get("api");
      if (apiMode === "1" || apiMode === "0") params.set("api", apiMode);
      for (const [key, control] of Object.entries(controls)) {
        if (!control.value) continue;
        params.set(key === "query" ? "q" : key, control.value);
      }
      const next = `${window.location.pathname}${params.toString() ? "?" + params.toString() : ""}`;
      window.history.replaceState({}, "", next);
    }

    function number(value) {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : 0;
    }

    function shortText(value) {
      const text = String(value || "");
      return text.length > 160 ? `${text.slice(0, 157)}...` : text;
    }

    function safeId(value) {
      return String(value || "unknown").replace(/[^a-zA-Z0-9_-]/g, "-") || "unknown";
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
    }

    function escapeAttribute(value) {
      return escapeHtml(value).replace(/`/g, "&#96;");
    }
  </script>
</body>
</html>
"""


def _profiles_page_content() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>个性化方向</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f8fa;
      --panel: #ffffff;
      --text: #20242a;
      --muted: #5f6b7a;
      --line: #d9dee7;
      --accent: #2563eb;
      --accent-2: #0f766e;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 15px;
      line-height: 1.5;
    }
    header {
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }
    .wrap {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
    }
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      min-height: 68px;
    }
    h1 {
      margin: 0;
      font-size: 22px;
      letter-spacing: 0;
    }
    nav {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      font-size: 14px;
    }
    a {
      color: var(--accent);
      text-decoration: none;
    }
    a:hover { text-decoration: underline; }
    main {
      padding: 20px 0 36px;
    }
    .toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 16px;
    }
    input {
      width: min(420px, 100%);
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 7px 10px;
      background: var(--panel);
      color: var(--text);
      font: inherit;
    }
    .count {
      color: var(--muted);
      font-size: 14px;
      white-space: nowrap;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 14px;
    }
    .card {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 16px;
      display: grid;
      gap: 12px;
      align-content: start;
    }
    .card h2 {
      margin: 0;
      font-size: 18px;
      letter-spacing: 0;
    }
    .meta {
      display: grid;
      gap: 8px;
    }
    .meta strong {
      display: block;
      margin-bottom: 4px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 600;
    }
    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .chip {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      border-radius: 999px;
      border: 1px solid #c7d2fe;
      padding: 2px 8px;
      background: #eef2ff;
      color: #3730a3;
      font-size: 12px;
      font-weight: 600;
    }
    .chip.topic {
      border-color: #99f6e4;
      background: #f0fdfa;
      color: var(--accent-2);
    }
    .actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      padding-top: 4px;
    }
    .button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 34px;
      border-radius: 6px;
      border: 1px solid var(--accent);
      padding: 6px 10px;
      background: var(--accent);
      color: #ffffff;
      font-weight: 600;
    }
    .button.secondary {
      background: var(--panel);
      color: var(--accent);
    }
    .empty {
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      color: var(--muted);
      text-align: center;
    }
    @media (max-width: 640px) {
      .wrap { width: min(100% - 20px, 1180px); }
      .topbar,
      .toolbar {
        align-items: flex-start;
        flex-direction: column;
      }
      input {
        width: 100%;
      }
    }
  </style>
</head>
<body>
  <header>
    <div class="wrap topbar">
      <h1>个性化方向</h1>
      <nav>
        <a href="index.html">周报归档</a>
        <a href="explorer.html">项目筛选</a>
        <a href="profiles.json">profiles.json</a>
      </nav>
    </div>
  </header>
  <main class="wrap">
    <section class="toolbar" aria-label="方向筛选">
      <input id="query" type="search" autocomplete="off" placeholder="搜索方向、语言、主题">
      <span id="count" class="count">0 个方向</span>
    </section>
    <section id="profiles" class="grid" aria-label="个性化方向列表"></section>
  </main>
  <script>
    const state = { profiles: [] };
    const query = document.getElementById("query");
    const count = document.getElementById("count");
    const profiles = document.getElementById("profiles");

    fetch("profiles.json", { cache: "no-store" })
      .then(response => response.json())
      .then(data => {
        state.profiles = Array.isArray(data.profiles) ? data.profiles : [];
        restoreQuery();
        render();
      })
      .catch(() => {
        profiles.innerHTML = '<div class="empty">无法读取 profiles.json</div>';
      });

    query.addEventListener("input", render);

    function render() {
      const keyword = query.value.trim().toLowerCase();
      const filtered = state.profiles.filter(profile => {
        const text = [
          profile.name,
          profile.label,
          ...(profile.learning_goals || []),
          ...(profile.preferred_languages || []),
          ...(profile.search_languages || []),
          ...(profile.preferred_topics || []),
          ...(profile.search_topics || [])
        ].join(" ").toLowerCase();
        return !keyword || text.includes(keyword);
      });
      count.textContent = `${filtered.length} 个方向`;
      profiles.innerHTML = filtered.length ? filtered.map(profileHtml).join("") : '<div class="empty">没有匹配的个性化方向</div>';
      updateUrl();
    }

    function profileHtml(profile) {
      const name = profile.name || "";
      const label = profile.label || name;
      const languages = unique([...(profile.preferred_languages || []), ...(profile.search_languages || [])]);
      const topics = unique([...(profile.preferred_topics || []), ...(profile.search_topics || [])]);
      const goals = profile.learning_goals || [];
      const explorer = `explorer.html?profile=${encodeURIComponent(name)}`;
      const queryLink = topics[0] ? `explorer.html?profile=${encodeURIComponent(name)}&q=${encodeURIComponent(topics[0])}` : explorer;
      return `<article class="card">
        <h2>${escapeHtml(label)}</h2>
        <div class="meta">
          <div><strong>学习目标</strong>${chips(goals, "暂无目标")}</div>
          <div><strong>语言</strong>${chips(languages, "不限语言")}</div>
          <div><strong>主题</strong>${chips(topics, "暂无主题", "topic")}</div>
        </div>
        <div class="actions">
          <a class="button" href="${escapeAttribute(explorer)}">查看匹配项目</a>
          <a class="button secondary" href="${escapeAttribute(queryLink)}">主题筛选</a>
        </div>
      </article>`;
    }

    function chips(items, emptyText, extraClass = "") {
      const values = unique(items).filter(Boolean);
      if (!values.length) return `<span class="count">${escapeHtml(emptyText)}</span>`;
      return `<div class="chips">${values.map(value => `<span class="chip ${extraClass}">${escapeHtml(value)}</span>`).join("")}</div>`;
    }

    function unique(items) {
      return [...new Set((items || []).map(value => String(value)).filter(Boolean))];
    }

    function restoreQuery() {
      const params = new URLSearchParams(window.location.search);
      if (params.has("q")) query.value = params.get("q") || "";
    }

    function updateUrl() {
      const params = new URLSearchParams();
      if (query.value.trim()) params.set("q", query.value.trim());
      const next = `${window.location.pathname}${params.toString() ? "?" + params.toString() : ""}`;
      window.history.replaceState({}, "", next);
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
    }

    function escapeAttribute(value) {
      return escapeHtml(value).replace(/`/g, "&#96;");
    }
  </script>
</body>
</html>
"""


def _selected_project_rows(root: Path) -> list[dict]:
    selected_dir = root / "data" / "selected"
    if not selected_dir.exists():
        return []
    rows = []
    for path in sorted(selected_dir.glob("*.json"), key=lambda item: item.stem, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(data, list):
            continue
        for item in data:
            if isinstance(item, dict):
                row = dict(item)
                row["run_date"] = path.stem
                rows.append(row)
    return rows


def _public_projects(root: Path) -> dict:
    projects = []
    for row in _selected_project_rows(root):
        quality = _quality_fields(row)
        projects.append(
            {
                "run_date": row.get("run_date", ""),
                "full_name": row.get("full_name", ""),
                "html_url": row.get("html_url", ""),
                "description": row.get("description", ""),
                "readme_summary": row.get("readme_summary") or row.get("readme_excerpt") or "",
                "category": row.get("category", "Other"),
                "language": row.get("language", "Unknown"),
                "stargazers_count": _int_value(row.get("stargazers_count")),
                "forks_count": _int_value(row.get("forks_count")),
                "star_growth": _int_value(row.get("star_growth")),
                "score": _float_value(row.get("score")),
                "sources": [str(source) for source in row.get("sources") or [] if source],
                "trending_rank": _int_value(row.get("trending_rank")),
                "selection_reasons": [str(reason) for reason in row.get("selection_reasons") or [] if reason],
                "security_flags": [str(flag) for flag in row.get("security_flags") or [] if flag],
                "security_score": _int_value(row.get("security_score"), 100),
                "security_level": str(row.get("security_level") or "low"),
                "quality_flags": quality["quality_flags"],
                "quality_score": quality["quality_score"],
                "quality_level": quality["quality_level"],
                "report_url": f"weekly/{row.get('run_date', '')}.html" if row.get("run_date") else "",
            }
        )
    return {
        "schema_version": 1,
        "count": len(projects),
        "projects": projects,
    }


def _quality_fields(row: dict) -> dict:
    if row.get("quality_score") or row.get("quality_level") or row.get("quality_flags"):
        return {
            "quality_flags": [str(flag) for flag in row.get("quality_flags") or [] if flag],
            "quality_score": _int_value(row.get("quality_score")),
            "quality_level": str(row.get("quality_level") or "unknown"),
        }
    repo = Repository(
        full_name=str(row.get("full_name") or ""),
        html_url=str(row.get("html_url") or ""),
        description=str(row.get("description") or ""),
        stargazers_count=_int_value(row.get("stargazers_count")),
        forks_count=_int_value(row.get("forks_count")),
        language=str(row.get("language") or "Unknown"),
        created_at=str(row.get("created_at") or ""),
        updated_at=str(row.get("updated_at") or ""),
        pushed_at=str(row.get("pushed_at") or row.get("updated_at") or ""),
        topics=[str(topic) for topic in row.get("topics") or [] if topic],
        archived=bool(row.get("archived")),
        fork=bool(row.get("fork")),
        open_issues_count=_int_value(row.get("open_issues_count")),
        license_name=str(row.get("license_name") or ""),
        readme_excerpt=str(row.get("readme_excerpt") or ""),
        readme_summary=str(row.get("readme_summary") or ""),
        trending_rank=_int_value(row.get("trending_rank")),
    )
    apply_quality_signals([repo])
    return {
        "quality_flags": repo.quality_flags,
        "quality_score": repo.quality_score,
        "quality_level": repo.quality_level,
    }


def _public_profiles(root: Path) -> dict:
    path = root / "config" / "profiles.json"
    if not path.exists():
        path = root / "config" / "profiles.example.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    profiles = []
    if isinstance(data, dict):
        for name, profile in data.items():
            if not isinstance(profile, dict):
                continue
            profiles.append(
                {
                    "name": str(name),
                    "label": str(profile.get("profile_label") or name),
                    "learning_goals": _string_list(profile.get("learning_goals")),
                    "preferred_languages": _string_list(profile.get("preferred_languages")),
                    "preferred_topics": _string_list(profile.get("preferred_topics")),
                    "search_languages": _string_list(profile.get("search_languages")),
                    "search_topics": _string_list(profile.get("search_topics")),
                }
            )
    return {
        "schema_version": 1,
        "count": len(profiles),
        "profiles": profiles,
    }


def _public_runs(root: Path, reports: list[Path]) -> dict:
    runs = []
    site_base_url = _site_base_url(root, reports)
    for report in reports:
        summary = _run_summary(root, report.stem)
        trends = _trend_summary(root, report.stem)
        if not summary:
            continue
        selected_count = _int_value(summary.get("selected_count"))
        collector_stats = summary.get("collector_stats") if isinstance(summary.get("collector_stats"), list) else []
        collector_errors = _public_collector_errors(collector_stats)
        collector_query_count = _int_value(summary.get("collector_query_count")) or len(collector_stats)
        collector_success_count = _int_value(summary.get("collector_success_count")) or sum(
            1 for item in collector_stats if isinstance(item, dict) and item.get("status") == "success"
        )
        readme_fetched_count = _int_value(summary.get("readme_fetched_count"))
        previously_sent_count = _int_value(summary.get("previously_sent_selected_count"))
        trending_project_count = _int_value(trends.get("trending_project_count"))
        trending_top10_selected_count = _int_value(
            summary.get("trending_top10_selected_count") or trends.get("trending_top10_selected_count")
        )
        runs.append(
            {
                "run_date": report.stem,
                "status": summary.get("status", ""),
                "run_schema_version": _int_value(summary.get("schema_version"), 1),
                "report_url": f"weekly/{_page_name(report)}",
                "selected_count": selected_count,
                "collected_count": _int_value(summary.get("collected_count")),
                "previously_sent_selected_count": previously_sent_count,
                "previously_sent_selected_rate": _metric_rate(
                    summary.get("previously_sent_selected_rate"), previously_sent_count, selected_count
                ),
                "readme_fetched_count": readme_fetched_count,
                "readme_fetch_rate": _metric_rate(summary.get("readme_fetch_rate"), readme_fetched_count, selected_count),
                "star_history_updated_count": _int_value(summary.get("star_history_updated_count")),
                "kimi_used": bool(summary.get("kimi_used")),
                "fallback_used": bool(summary.get("fallback_used")),
                "telegram_sent": bool(summary.get("telegram_sent")),
                "telegram_report_url": summary.get("telegram_report_url", ""),
                "telegram_explorer_url": summary.get("telegram_explorer_url", ""),
                "telegram_runs_url": summary.get("telegram_runs_url") or _absolute_url(site_base_url, "runs.html"),
                "delivery_results": _public_delivery_results(summary.get("delivery_results")),
                "collector_error_count": len(summary.get("collector_errors") or []),
                "collector_failed_count": sum(
                    1 for item in collector_stats if isinstance(item, dict) and item.get("status") in {"failed", "partial"}
                ),
                "collector_error_kinds": sorted(
                    {error["error_kind"] for error in collector_errors if error.get("error_kind")}
                ),
                "collector_error_summary": collector_errors,
                "collector_query_count": collector_query_count,
                "collector_success_count": collector_success_count,
                "collector_success_rate": _metric_rate(summary.get("collector_success_rate"), collector_success_count, collector_query_count),
                "top_languages": trends.get("top_languages") or [],
                "top_categories": trends.get("top_categories") or [],
                "total_star_growth": _int_value(trends.get("total_star_growth")),
                "trending_project_count": trending_project_count,
                "trending_top10_available_count": _int_value(summary.get("trending_top10_available_count")),
                "trending_top10_selected_count": trending_top10_selected_count,
                "trending_top10_fulfillment_rate": _float_value(summary.get("trending_top10_fulfillment_rate")),
                "trending_selected_rate": _metric_rate(trends.get("trending_selected_rate"), trending_project_count, selected_count),
                "summary_points": [str(point) for point in trends.get("summary_points") or [] if point],
            }
        )
    return {
        "schema_version": 1,
        "count": len(runs),
        "runs": runs,
    }


def _job_detail_content() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GitHub 周报任务详情</title>
  <style>
    :root {
      --bg: #f6f8fb;
      --panel: #ffffff;
      --text: #172033;
      --muted: #667085;
      --line: #d8dee8;
      --accent: #2563eb;
      --ok: #15803d;
      --bad: #b42318;
      --warn: #a16207;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.55;
    }
    header {
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }
    .wrap {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
    }
    .topbar {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
      padding: 18px 0;
    }
    h1 {
      margin: 0;
      font-size: 24px;
      line-height: 1.2;
    }
    nav {
      display: flex;
      gap: 14px;
      flex-wrap: wrap;
    }
    a {
      color: var(--accent);
      font-weight: 700;
      text-decoration: none;
    }
    main { padding: 24px 0 40px; }
    .panel {
      margin-bottom: 14px;
      border: 1px solid var(--line);
      background: var(--panel);
      padding: 16px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }
    .field span,
    .event span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }
    .field strong,
    .event strong {
      display: block;
      margin-top: 3px;
      overflow-wrap: anywhere;
    }
    .status {
      display: inline-block;
      padding: 2px 8px;
      border: 1px solid var(--line);
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
    }
    .status.succeeded { color: var(--ok); border-color: #bbf7d0; background: #f0fdf4; }
    .status.failed { color: var(--bad); border-color: #fecaca; background: #fff1f2; }
    .status.running { color: var(--accent); border-color: #bfdbfe; background: #eff6ff; }
    .status.planned { color: var(--warn); border-color: #fde68a; background: #fffbeb; }
    pre {
      margin: 8px 0 0;
      overflow: auto;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: #0f172a;
      color: #e5e7eb;
      padding: 12px;
      border-radius: 6px;
      font-size: 12px;
    }
    .events { display: grid; gap: 10px; }
    .event {
      border-left: 3px solid var(--line);
      padding-left: 12px;
    }
    .event.succeeded,
    .event.planned { border-color: var(--ok); }
    .event.failed,
    .event.blocked { border-color: var(--bad); }
    .muted { color: var(--muted); }
    .summary-list {
      display: grid;
      gap: 8px;
      margin-top: 10px;
    }
    .summary-row {
      display: grid;
      grid-template-columns: minmax(120px, 180px) 1fr;
      gap: 10px;
      padding: 9px 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #f8fafc;
    }
    .summary-row span {
      color: var(--muted);
      font-size: 13px;
    }
    .summary-row strong {
      overflow-wrap: anywhere;
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    button {
      height: 34px;
      padding: 0 10px;
      border: 1px solid var(--accent);
      border-radius: 6px;
      background: var(--accent);
      color: #fff;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }
    button:disabled {
      cursor: not-allowed;
      border-color: var(--line);
      background: #e5e7eb;
      color: var(--muted);
    }
    .secondary-button {
      background: var(--panel);
      color: var(--accent);
    }
    .execute-button {
      border-color: var(--warn);
      color: var(--warn);
    }
    .retry-button {
      border-color: var(--bad);
      color: var(--bad);
    }
    .action-result {
      margin-top: 10px;
      color: var(--muted);
      font-size: 13px;
      overflow-wrap: anywhere;
    }
    .action-result.ok { color: var(--ok); }
    .action-result.blocked { color: var(--bad); }
    .empty {
      color: var(--muted);
      text-align: center;
      padding: 30px 12px;
    }
    @media (max-width: 760px) {
      .topbar { align-items: flex-start; flex-direction: column; }
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <div class="wrap topbar">
      <h1>GitHub 周报任务详情</h1>
      <nav>
        <a href="jobs.html">任务状态</a>
        <a href="runs.html">运行状态</a>
        <a href="index.html">周报归档</a>
      </nav>
    </div>
  </header>
  <main class="wrap">
    <section id="content" class="panel"><div class="empty">加载中</div></section>
  </main>
  <script>
    const content = document.getElementById("content");
    const params = new URLSearchParams(window.location.search);
    const jobId = params.get("job") || "";
    let actionMessage = "";
    let actionMessageClass = "";

    if (!jobId) {
      content.innerHTML = '<div class="empty">URL 缺少 job 参数，请从任务状态页点击任务编号进入。</div>';
    } else {
      refreshDetail();
    }

    function refreshDetail() {
      return Promise.all([loadJob(jobId), loadEvents(jobId)])
        .then(([detail, events]) => render(detail, events))
        .catch(error => {
          content.innerHTML = `<div class="empty">无法读取任务详情：${escapeHtml(error.message || error)}</div>`;
        });
    }

    function loadJob(id) {
      if (shouldUseApi()) {
        return fetch(`/v1/jobs/${encodeURIComponent(id)}`, { cache: "no-store" })
          .then(jsonOrThrow)
          .catch(() => loadJobFromJson(id));
      }
      return loadJobFromJson(id);
    }

    function loadJobFromJson(id) {
      return fetch("jobs.json", { cache: "no-store" })
        .then(jsonOrThrow)
        .then(data => {
          const job = (data.jobs || []).find(item => item.job_id === id);
          return { schema_version: 1, found: Boolean(job), job: job || {}, run_summary: {} };
        });
    }

    function loadEvents(id) {
      if (!shouldUseApi()) return Promise.resolve({ schema_version: 1, count: 0, events: [] });
      return fetch(`/v1/jobs/${encodeURIComponent(id)}/events?limit=200`, { cache: "no-store" })
        .then(jsonOrThrow)
        .catch(() => ({ schema_version: 1, count: 0, events: [] }));
    }

    function render(detail, eventData) {
      if (!detail || !detail.found) {
        content.innerHTML = `<div class="empty">未找到任务：${escapeHtml(jobId)}</div>`;
        return;
      }
      const job = detail.job || {};
      const events = Array.isArray(eventData.events) ? eventData.events : [];
      content.className = "";
      content.innerHTML = `
        <section class="panel">
          <h2>${escapeHtml(job.job_id || jobId)}</h2>
          <div class="grid">
            ${field("状态", `<span class="status ${escapeAttribute(job.status || "")}">${escapeHtml(job.status || "")}</span>`)}
            ${field("类型", escapeHtml(job.kind || "-"))}
            ${field("运行日期", escapeHtml(job.run_date || "-"))}
            ${field("提交时间", escapeHtml(job.submitted_at || "-"))}
            ${field("开始时间", escapeHtml(job.started_at || "-"))}
            ${field("结束时间", escapeHtml(job.finished_at || "-"))}
          </div>
        </section>
        <section class="panel">
          <h2>任务操作</h2>
          ${operationHtml(job)}
          <div id="actionResult" class="action-result ${escapeAttribute(actionMessageClass)}" aria-live="polite">${actionMessage}</div>
        </section>
        <section class="panel">
          <h2>任务请求</h2>
          <pre>${escapeHtml(JSON.stringify(job.request || {}, null, 2))}</pre>
        </section>
        <section class="panel">
          <h2>执行结果</h2>
          ${job.error ? `<p class="muted">错误：${escapeHtml(job.error)}</p>` : ""}
          ${ragResultSummaryHtml(job)}
          <pre>${escapeHtml(JSON.stringify(job.result || {}, null, 2))}</pre>
        </section>
        <section class="panel">
          <h2>审计事件</h2>
          ${eventsHtml(events)}
        </section>`;
      bindOperationControls(job);
    }

    function ragResultSummaryHtml(job) {
      const result = job.result || {};
      const kind = job.kind || "";
      if (!["rag_corpus_rebuild", "rag_embedding_build", "rag_backfill", "dev_context_index"].includes(kind)) return "";
      const rows = [
        ["执行模式", result.dry_run ? "预览，不写库" : "已写入 SQLite"],
        ["任务状态", result.status || "-"],
      ];
      if (kind === "rag_corpus_rebuild") {
        rows.push(
          ["归档入选记录", result.selected_archive_count || 0],
          ["语料记录", countDelta(result, "project_corpus")],
          ["证据块", countDelta(result, "rag_chunks")],
          ["向量索引", countDelta(result, "rag_embeddings")]
        );
      } else if (kind === "rag_embedding_build") {
        rows.push(
          ["模型", result.model || "-"],
          ["维度", result.dimensions || "-"],
          ["证据块", result.chunk_count || countValue(result.before_counts, "rag_chunks")],
          ["向量索引", countDelta(result, "rag_embeddings")]
        );
      } else if (kind === "rag_backfill") {
        rows.push(
          ["候选项目", result.candidate_count || 0],
          ["处理项目", result.processed_count || 0],
          ["回填前覆盖率", percent((result.coverage_before || {}).coverage_rate || 0)],
          ["回填前缺口", (result.coverage_before || {}).gap_count || 0]
        );
      } else if (kind === "dev_context_index") {
        rows.push(
          ["索引运行", result.run_id || "-"],
          ["来源数量", result.source_count || 0],
          ["分块数量", result.chunk_count || 0],
          ["embedding", result.embedding_count || 0],
          ["命令数量", result.command_count || 0],
          ["运行测试", result.run_checks ? "是" : "否"]
        );
      }
      const repositories = Array.isArray(result.processed_repositories) ? result.processed_repositories : [];
      const repoHtml = repositories.length
        ? `<h3>处理仓库</h3><div class="summary-list">${repositories.slice(0, 10).map(item => summaryRow(
            item.full_name || "-",
            `${item.status || "-"} · ${item.dry_run ? "预览" : "已写入"} · 质量 ${item.quality_score || 0} ${item.quality_level || ""}`
          )).join("")}</div>`
        : "";
      return `<div class="summary-list">${rows.map(([label, value]) => summaryRow(label, value)).join("")}</div>${repoHtml}`;
    }

    function countDelta(result, key) {
      const beforeValue = countValue(result.before_counts, key);
      const afterValue = countValue(result.after_counts, key);
      const delta = afterValue - beforeValue;
      return `${beforeValue} -> ${afterValue}${delta ? ` (${delta > 0 ? "+" : ""}${delta})` : ""}`;
    }

    function countValue(source, key) {
      return Number((source || {})[key] || 0);
    }

    function percent(value) {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? `${Math.round(parsed * 100)}%` : "0%";
    }

    function summaryRow(label, value) {
      return `<div class="summary-row"><span>${escapeHtml(label)}</span><strong>${escapeHtml(String(value))}</strong></div>`;
    }

    function operationHtml(job) {
      const apiEnabled = shouldUseApi();
      const status = job.status || "";
      const precheckDisabled = apiEnabled ? "" : " disabled";
      const executeDisabled = apiEnabled && status === "planned" ? "" : " disabled";
      const retryDisabled = apiEnabled && status === "failed" ? "" : " disabled";
      return `<div class="actions">
        <button class="secondary-button" type="button" id="precheckButton"${precheckDisabled}>执行前检查</button>
        <button class="secondary-button execute-button" type="button" id="executeButton"${executeDisabled}>确认执行</button>
        <button class="secondary-button retry-button" type="button" id="retryButton"${retryDisabled}>重试失败任务</button>
      </div>
      <p class="muted">${apiEnabled ? "操作会调用本地后端 /v1 接口。" : "静态 Pages 模式只能查看；启动本地后端或添加 api=1 后可操作。"}</p>`;
    }

    function bindOperationControls(job) {
      const precheckButton = document.getElementById("precheckButton");
      const executeButton = document.getElementById("executeButton");
      const retryButton = document.getElementById("retryButton");
      if (precheckButton) precheckButton.addEventListener("click", () => runDetailPrecheck(precheckButton));
      if (executeButton) executeButton.addEventListener("click", () => runDetailExecution(executeButton));
      if (retryButton) retryButton.addEventListener("click", () => runDetailRetry(retryButton));
    }

    function runDetailPrecheck(button) {
      if (!shouldUseApi()) return setAction("执行前检查需要本地后端或 api=1 模式。", "blocked");
      button.disabled = true;
      setAction("检查中...", "");
      fetch(`/v1/job-execution-check?job_id=${encodeURIComponent(jobId)}`, { cache: "no-store" })
        .then(jsonOrThrow)
        .then(data => {
          setAction(precheckHtml(data), data.executable ? "ok" : "blocked");
        })
        .catch(error => setAction(`检查失败：${escapeHtml(error.message || error)}`, "blocked"))
        .finally(() => {
          button.disabled = false;
        });
    }

    function runDetailExecution(button) {
      if (!shouldUseApi()) return setAction("执行任务需要本地后端或 api=1 模式。", "blocked");
      if (!window.confirm(`确认执行任务 ${jobId}？`)) return;
      button.disabled = true;
      setAction("执行中...", "");
      fetch(`/v1/jobs/${encodeURIComponent(jobId)}/execute`, {
        method: "POST",
        headers: adminWriteHeaders(),
        body: JSON.stringify({ confirm_execution: true, requested_by: "job_detail_page" }),
      })
        .then(jsonOrThrow)
        .then(data => {
          setAction(executionHtml(data), data.accepted && data.executed ? "ok" : "blocked");
          return refreshDetail();
        })
        .catch(error => setAction(`执行失败：${escapeHtml(error.message || error)}`, "blocked"))
        .finally(() => {
          button.disabled = false;
        });
    }

    function runDetailRetry(button) {
      if (!shouldUseApi()) return setAction("重试任务需要本地后端或 api=1 模式。", "blocked");
      if (!window.confirm(`确认为失败任务 ${jobId} 创建重试任务？`)) return;
      button.disabled = true;
      setAction("重试创建中...", "");
      fetch(`/v1/jobs/${encodeURIComponent(jobId)}/retry`, {
        method: "POST",
        headers: adminWriteHeaders(),
        body: JSON.stringify({ requested_by: "job_detail_page" }),
      })
        .then(jsonOrThrow)
        .then(data => {
          setAction(retryHtml(data), data.accepted && data.retry_created ? "ok" : "blocked");
          return refreshDetail();
        })
        .catch(error => setAction(`重试失败：${escapeHtml(error.message || error)}`, "blocked"))
        .finally(() => {
          button.disabled = false;
        });
    }

    function precheckHtml(data) {
      if (!data || !data.found) return "未找到任务。";
      const lines = [
        data.executable ? "可执行" : "不可执行",
        ...(data.blockers || []).map(item => `阻止：${item}`),
        ...(data.warnings || []).map(item => `提示：${item}`),
      ];
      if (data.next_command) lines.push(`命令：${data.next_command}`);
      return lines.map(line => `<div>${escapeHtml(line)}</div>`).join("");
    }

    function executionHtml(data) {
      const lines = [
        data.accepted ? "已接受执行" : "未执行",
        data.status ? `状态：${data.status}` : "",
        ...(data.blockers || []).map(item => `阻止：${item}`),
        ...(data.warnings || []).map(item => `提示：${item}`),
      ].filter(Boolean);
      return lines.map(line => `<div>${escapeHtml(line)}</div>`).join("");
    }

    function retryHtml(data) {
      const lines = [
        data.retry_created ? "已创建重试任务" : data.accepted ? "已命中已有任务" : "未创建重试任务",
        data.job_id ? `任务：${data.job_id}` : "",
        data.status ? `状态：${data.status}` : "",
        data.duplicate_of ? `已有任务：${data.duplicate_of}` : "",
        ...(data.blockers || []).map(item => `阻止：${item}`),
      ].filter(Boolean);
      return lines.map(line => `<div>${escapeHtml(line)}</div>`).join("");
    }

    function setAction(html, className) {
      actionMessage = html;
      actionMessageClass = className || "";
      const target = document.getElementById("actionResult");
      if (target) {
        target.className = `action-result ${actionMessageClass}`;
        target.innerHTML = actionMessage;
      }
    }

    function eventsHtml(events) {
      if (!events.length) return '<p class="muted">静态模式不包含事件；启动本地后端或添加 api=1 后可查看审计事件。</p>';
      return `<div class="events">${events.map(event => `
        <article class="event ${escapeAttribute(event.status || "")}">
          <span>${escapeHtml(event.created_at || "")} · ${escapeHtml(event.actor || "-")}</span>
          <strong>${escapeHtml(event.event_type || "")} / ${escapeHtml(event.status || "")}</strong>
          <p>${escapeHtml(event.message || "")}</p>
          ${event.payload && Object.keys(event.payload).length ? `<pre>${escapeHtml(JSON.stringify(event.payload, null, 2))}</pre>` : ""}
        </article>`).join("")}</div>`;
    }

    function field(label, value) {
      return `<div class="field"><span>${escapeHtml(label)}</span><strong>${value}</strong></div>`;
    }

    function shouldUseApi() {
      const apiMode = params.get("api");
      if (apiMode === "1") return true;
      if (apiMode === "0") return false;
      return ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname);
    }

    function jsonOrThrow(response) {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    }

    function adminWriteHeaders() {
      const token = adminToken();
      const headers = { "Content-Type": "application/json" };
      if (token) headers["X-Admin-Token"] = token;
      return headers;
    }

    function adminToken() {
      const token = params.get("admin_token") || window.localStorage.getItem("github_weekly_admin_token") || "";
      if (params.get("admin_token")) window.localStorage.setItem("github_weekly_admin_token", params.get("admin_token"));
      return token.trim();
    }

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;",
      }[char]));
    }

    function escapeAttribute(value) {
      return escapeHtml(value);
    }
  </script>
</body>
</html>
"""


def _public_jobs(root: Path, reports: list[Path]) -> dict:
    jobs = _sqlite_jobs(root)
    if not jobs:
        jobs = _jobs_from_runs(_public_runs(root, reports).get("runs") or [])
    return {
        "schema_version": 1,
        "count": len(jobs),
        "jobs": jobs,
    }


def _sqlite_jobs(root: Path) -> list[dict]:
    db_path = root / "data" / "github_weekly.sqlite"
    if not db_path.exists():
        return []
    try:
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        try:
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'jobs'"
            ).fetchone()
            if not table:
                return []
            rows = connection.execute(
                """
                SELECT job_id, kind, status, run_date, submitted_at, started_at, finished_at,
                       request_json, result_json, error
                FROM jobs
                ORDER BY COALESCE(NULLIF(submitted_at, ''), run_date) DESC, job_id DESC
                LIMIT 500
                """
            ).fetchall()
        finally:
            connection.close()
    except sqlite3.Error:
        return []
    return [_public_job_from_row(row) for row in rows]


def _public_job_from_row(row: sqlite3.Row) -> dict:
    request = _public_job_request(_json_object(row["request_json"]))
    result = _public_job_result(_json_object(row["result_json"]))
    return {
        "job_id": str(row["job_id"] or ""),
        "kind": str(row["kind"] or ""),
        "status": str(row["status"] or ""),
        "run_date": str(row["run_date"] or ""),
        "submitted_at": str(row["submitted_at"] or ""),
        "started_at": str(row["started_at"] or ""),
        "finished_at": str(row["finished_at"] or ""),
        "request": request,
        "result": result,
        "error": str(row["error"] or "")[:240],
        "report_url": str(result.get("report_url") or ""),
    }


def _jobs_from_runs(runs: list[dict]) -> list[dict]:
    jobs = []
    for run in runs:
        run_date = str(run.get("run_date") or "")
        if not run_date:
            continue
        failed = run.get("status") == "failed"
        jobs.append(
            {
                "job_id": f"run:{run_date}",
                "kind": "weekly_report",
                "status": "failed" if failed else "succeeded",
                "run_date": run_date,
                "submitted_at": run_date,
                "started_at": "",
                "finished_at": run_date,
                "request": _public_job_request({}),
                "result": {
                    "run_date": run_date,
                    "status": str(run.get("status") or ""),
                    "selected_count": _int_value(run.get("selected_count")),
                    "collected_count": _int_value(run.get("collected_count")),
                    "kimi_used": bool(run.get("kimi_used")),
                    "fallback_used": bool(run.get("fallback_used")),
                    "telegram_sent": bool(run.get("telegram_sent")),
                    "telegram_error": "",
                    "report_path": "",
                    "report_url": str(run.get("report_url") or run.get("telegram_report_url") or ""),
                    "sqlite_index_path": "",
                    "sqlite_error": "",
                    "error": "",
                },
                "error": "",
                "report_url": str(run.get("report_url") or run.get("telegram_report_url") or ""),
            }
        )
    return jobs


def _public_job_request(data: dict) -> dict:
    return {
        "profile": str(data.get("profile") or ""),
        "sources": _string_list(data.get("sources")),
        "dry_run": bool(data.get("dry_run")),
        "requested_dry_run": bool(data.get("requested_dry_run", data.get("dry_run"))),
        "confirm_delivery": bool(data.get("confirm_delivery")),
        "delivery_allowed": bool(data.get("delivery_allowed")),
        "days_back": _int_value(data.get("days_back")),
        "trigger_source": str(data.get("trigger_source") or ""),
        "requested_by": str(data.get("requested_by") or ""),
        "safety_warnings": _string_list(data.get("safety_warnings")),
    }


def _public_job_result(data: dict) -> dict:
    return {
        "run_date": str(data.get("run_date") or ""),
        "status": str(data.get("status") or ""),
        "selected_count": _int_value(data.get("selected_count")),
        "collected_count": _int_value(data.get("collected_count")),
        "kimi_used": bool(data.get("kimi_used")),
        "fallback_used": bool(data.get("fallback_used")),
        "telegram_sent": bool(data.get("telegram_sent")),
        "telegram_error": str(data.get("telegram_error") or "")[:240],
        "report_path": str(data.get("report_path") or ""),
        "report_url": str(data.get("report_url") or ""),
        "sqlite_index_path": str(data.get("sqlite_index_path") or ""),
        "sqlite_error": str(data.get("sqlite_error") or "")[:240],
        "error": str(data.get("error") or "")[:240],
    }


def _json_object(text: str) -> dict:
    try:
        data = json.loads(text or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _public_collector_errors(collector_stats: list) -> list[dict]:
    errors = []
    for item in collector_stats:
        if not isinstance(item, dict):
            continue
        if item.get("status") not in {"failed", "partial"} and not item.get("error_kind"):
            continue
        error_kind = str(item.get("error_kind") or "unknown")
        message = str(item.get("error") or "")
        errors.append(
            {
                "source": str(item.get("source") or ""),
                "stage": str(item.get("stage") or ""),
                "status": str(item.get("status") or ""),
                "error_kind": error_kind,
                "status_code": _int_value(item.get("status_code")),
                "retry_after": str(item.get("retry_after") or ""),
                "rate_limit_remaining": str(item.get("rate_limit_remaining") or ""),
                "rate_limit_reset": str(item.get("rate_limit_reset") or ""),
                "message": message[:240],
            }
        )
    return errors[:10]


def _feed_content(root: Path, reports: list[Path]) -> str:
    base_url = _site_base_url(root, reports)
    site_link = _absolute_url(base_url, "index.html")
    items = []
    for report in reports[:20]:
        summary = _run_summary(root, report.stem)
        trends = _trend_summary(root, report.stem)
        report_link = _absolute_url(base_url, f"weekly/{_page_name(report)}")
        title = f"GitHub 每周热点项目周报 - {report.stem}"
        description = _feed_description(summary, trends)
        items.append(
            "\n".join(
                [
                    "    <item>",
                    f"      <title>{_xml(title)}</title>",
                    f"      <link>{_xml(report_link)}</link>",
                    f"      <guid isPermaLink=\"true\">{_xml(report_link)}</guid>",
                    f"      <pubDate>{_xml(_rss_date(report.stem))}</pubDate>",
                    f"      <description>{_xml(description)}</description>",
                    "    </item>",
                ]
            )
        )
    body = "\n".join(items)
    return "\n".join(
        [
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
            "<rss version=\"2.0\">",
            "  <channel>",
            "    <title>GitHub 每周热点项目周报</title>",
            f"    <link>{_xml(site_link)}</link>",
            "    <description>GitHub Weekly Agent 自动生成的中文开源项目情报周报。</description>",
            f"    <lastBuildDate>{_xml(_feed_last_build_date(reports))}</lastBuildDate>",
            "    <language>zh-CN</language>",
            body,
            "  </channel>",
            "</rss>",
            "",
        ]
    )


def _feed_description(summary: dict, trends: dict) -> str:
    parts = []
    if summary:
        parts.append(f"入选项目 {summary.get('selected_count', 0)} 个")
        parts.append(f"采集候选 {summary.get('collected_count', 0)} 个")
        parts.append("生成方式：" + ("Kimi" if summary.get("kimi_used") else "降级模板"))
        parts.append("Telegram：" + ("已推送" if summary.get("telegram_sent") else "未推送"))
    trend_text = _report_trend_text(trends)
    if trend_text:
        parts.append(trend_text)
    points = trends.get("summary_points") or []
    parts.extend(str(point) for point in points[:2])
    return "；".join(parts) if parts else "本期周报已生成。"


def _site_base_url(root: Path, reports: list[Path]) -> str:
    for report in reports:
        url = str(_run_summary(root, report.stem).get("telegram_report_url") or "")
        marker = "/weekly/"
        if marker in url:
            return url.split(marker, 1)[0].rstrip("/") + "/"
    return ""


def _absolute_url(base_url: str, path: str) -> str:
    return f"{base_url}{path}" if base_url else path


def _rss_date(run_date: str) -> str:
    try:
        value = datetime.fromisoformat(run_date).replace(tzinfo=UTC)
    except ValueError:
        value = datetime.now(UTC)
    return format_datetime(value)


def _feed_last_build_date(reports: list[Path]) -> str:
    if reports:
        return _rss_date(reports[0].stem)
    return format_datetime(datetime(1970, 1, 1, tzinfo=UTC))


def _xml(value: object) -> str:
    return xml_escape(str(value), {'"': "&quot;"})


def _project_table_row(row: dict) -> str:
    url = str(row.get("html_url") or "")
    link = f"[{url}]({url})" if url else "-"
    risk_count = len(row.get("security_flags") or [])
    sources = _source_text(row.get("sources") or [])
    trending_rank = row.get("trending_rank") or "-"
    return (
        f"| {row.get('run_date', '')} | {row.get('full_name', '')} | {sources} | {trending_rank} | "
        f"{row.get('category', 'Other')} | {row.get('language', 'Unknown')} | {row.get('stargazers_count', 0)} | "
        f"{row.get('star_growth', 0)} | {risk_count} | {link} |"
    )


def _public_delivery_results(value: object) -> list[dict[str, str | bool]]:
    if not isinstance(value, list):
        return []
    results = []
    for item in value:
        if not isinstance(item, dict):
            continue
        results.append(
            {
                "channel": str(item.get("channel") or ""),
                "sent": bool(item.get("sent")),
                "error": str(item.get("error") or ""),
                "skipped": bool(item.get("skipped")),
            }
        )
    return results


def _source_text(sources: list[str]) -> str:
    labels = {
        "github_trending": "GitHub Trending",
        "github_search": "GitHub Search",
    }
    values = [labels.get(source, source) for source in sources if source]
    return " + ".join(values) if values else "-"


def _json_text(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _int_value(value: object, default: int = 0) -> int:
    try:
        return int(value if value is not None else default)
    except (TypeError, ValueError):
        return default


def _float_value(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _metric_rate(value: object, numerator: int, denominator: int) -> float:
    explicit = _float_value(value)
    if explicit:
        return explicit
    return round(numerator / denominator, 4) if denominator else 0.0


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


if __name__ == "__main__":
    for path in build_pages():
        print(path.relative_to(ROOT).as_posix())
