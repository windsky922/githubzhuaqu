from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def build_pages(root: Path = ROOT) -> list[Path]:
    reports = _report_files(root)
    weekly_dir = root / "docs" / "weekly"
    weekly_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for report in reports:
        target = weekly_dir / report.name
        target.write_text(report.read_text(encoding="utf-8"), encoding="utf-8")
        written.append(target)

    index = root / "docs" / "index.md"
    index.write_text(_index_content(root, reports), encoding="utf-8")
    written.append(index)
    projects = root / "docs" / "projects.md"
    projects.write_text(_projects_content(root), encoding="utf-8")
    written.append(projects)
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
        lines.append(f"- [{latest.stem}](weekly/{latest.name})")
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
            "- [历史项目索引](projects.md)",
            "- [架构说明](architecture.md)",
            "- [配置说明](setup.md)",
            "- [开发路线图](roadmap.md)",
            "- [未来更新规划](future-plan.md)",
            "- [操作日志](operation-log.md)",
            "",
        ]
    )
    return "\n".join(lines)


def _report_line(root: Path, report: Path) -> str:
    summary = _run_summary(root, report.stem)
    trends = _trend_summary(root, report.stem)
    if not summary:
        return f"- [{report.stem}](weekly/{report.name})"
    selected_count = summary.get("selected_count", 0)
    kimi = "Kimi" if summary.get("kimi_used") else "降级模板"
    telegram = "已推送" if summary.get("telegram_sent") else "未推送"
    trend_text = _report_trend_text(trends)
    suffix = f"，{trend_text}" if trend_text else ""
    return f"- [{report.stem}](weekly/{report.name})：{selected_count} 个项目，{kimi}，Telegram {telegram}{suffix}"


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
        lines.append("| - | 暂无项目 | - | - | 0 | 0 | 0 | - |")
    lines.extend(["", "## 返回", "", "- [周报归档首页](index.md)", ""])
    return "\n".join(lines)


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


def _source_text(sources: list[str]) -> str:
    labels = {
        "github_trending": "GitHub Trending",
        "github_search": "GitHub Search",
    }
    values = [labels.get(source, source) for source in sources if source]
    return " + ".join(values) if values else "-"


if __name__ == "__main__":
    for path in build_pages():
        print(path.relative_to(ROOT).as_posix())
