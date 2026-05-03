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
    explorer = root / "docs" / "explorer.html"
    explorer.write_text(_explorer_content(), encoding="utf-8")
    written.append(explorer)
    projects_json = root / "docs" / "projects.json"
    projects_json.write_text(_json_text(_public_projects(root)), encoding="utf-8")
    written.append(projects_json)
    runs_json = root / "docs" / "runs.json"
    runs_json.write_text(_json_text(_public_runs(root, reports)), encoding="utf-8")
    written.append(runs_json)
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
            "- [项目筛选页](explorer.html)",
            "- [历史项目索引](projects.html)",
            "- [公共项目 JSON](projects.json)",
            "- [公共运行 JSON](runs.json)",
            "- [数据契约说明](data-contracts.html)",
            "- [架构说明](architecture.html)",
            "- [配置说明](setup.html)",
            "- [开发路线图](roadmap.html)",
            "- [未来更新规划](future-plan.html)",
            "- [操作日志](operation-log.html)",
            "",
        ]
    )
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
      grid-template-columns: minmax(220px, 2fr) repeat(5, minmax(130px, 1fr));
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
    .meta {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      color: var(--muted);
      margin: 8px 0 12px;
      min-height: 24px;
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
    }
    @media (max-width: 560px) {
      .wrap {
        width: min(100% - 20px, 1180px);
      }
      .filters {
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
      </nav>
    </div>
  </header>
  <main class="wrap">
    <section class="filters" aria-label="筛选条件">
      <label>关键词
        <input id="query" type="search" autocomplete="off">
      </label>
      <label>语言
        <select id="language"></select>
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
      <label>排序
        <select id="sort">
          <option value="run_date">最新入选</option>
          <option value="star_growth">新增 Star</option>
          <option value="trending_rank">Trending 排名</option>
          <option value="score">综合分</option>
          <option value="stars">累计 Star</option>
        </select>
      </label>
      <button id="reset" type="button">重置</button>
    </section>
    <div class="meta">
      <span id="count">0 个项目</span>
      <span id="updated"></span>
    </div>
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
            <th>风险</th>
            <th>周报</th>
          </tr>
        </thead>
        <tbody id="rows">
          <tr><td class="empty" colspan="9">加载中</td></tr>
        </tbody>
      </table>
    </div>
  </main>
  <script>
    const state = { projects: [] };
    const controls = {
      query: document.getElementById("query"),
      language: document.getElementById("language"),
      category: document.getElementById("category"),
      source: document.getElementById("source"),
      risk: document.getElementById("risk"),
      sort: document.getElementById("sort")
    };
    const rows = document.getElementById("rows");
    const count = document.getElementById("count");
    const updated = document.getElementById("updated");

    fetch("projects.json", { cache: "no-store" })
      .then(response => response.json())
      .then(data => {
        state.projects = Array.isArray(data.projects) ? data.projects : [];
        hydrateOptions();
        render();
      })
      .catch(() => {
        rows.innerHTML = '<tr><td class="empty" colspan="9">无法读取 projects.json</td></tr>';
      });

    Object.values(controls).forEach(control => control.addEventListener("input", render));
    document.getElementById("reset").addEventListener("click", () => {
      controls.query.value = "";
      controls.language.value = "";
      controls.category.value = "";
      controls.source.value = "";
      controls.risk.value = "";
      controls.sort.value = "run_date";
      render();
    });

    function hydrateOptions() {
      fillSelect(controls.language, values("language"));
      fillSelect(controls.category, values("category"));
      const dates = state.projects.map(project => project.run_date).filter(Boolean).sort().reverse();
      updated.textContent = dates.length ? `最新数据：${dates[0]}` : "";
    }

    function values(key) {
      return [...new Set(state.projects.map(project => project[key]).filter(Boolean))].sort((a, b) => a.localeCompare(b));
    }

    function fillSelect(select, values) {
      select.innerHTML = '<option value="">全部</option>' + values.map(value => `<option value="${escapeAttribute(value)}">${escapeHtml(value)}</option>`).join("");
    }

    function render() {
      const query = controls.query.value.trim().toLowerCase();
      let filtered = state.projects.filter(project => {
        const text = [project.full_name, project.description, project.language, project.category, ...(project.selection_reasons || [])].join(" ").toLowerCase();
        const riskCount = (project.security_flags || []).length;
        return (!query || text.includes(query))
          && (!controls.language.value || project.language === controls.language.value)
          && (!controls.category.value || project.category === controls.category.value)
          && (!controls.source.value || (project.sources || []).includes(controls.source.value))
          && (!controls.risk.value || (controls.risk.value === "has" ? riskCount > 0 : riskCount === 0));
      });
      filtered = filtered.sort(compareProjects);
      count.textContent = `${filtered.length} 个项目`;
      rows.innerHTML = filtered.length ? filtered.map(rowHtml).join("") : '<tr><td class="empty" colspan="9">没有匹配项目</td></tr>';
    }

    function compareProjects(a, b) {
      const sort = controls.sort.value;
      if (sort === "star_growth") return number(b.star_growth) - number(a.star_growth);
      if (sort === "trending_rank") return rank(a.trending_rank) - rank(b.trending_rank);
      if (sort === "score") return number(b.score) - number(a.score);
      if (sort === "stars") return number(b.stargazers_count) - number(a.stargazers_count);
      return String(b.run_date || "").localeCompare(String(a.run_date || ""));
    }

    function rowHtml(project) {
      const risks = project.security_flags || [];
      const sourceTags = (project.sources || []).map(source => `<span class="tag source">${escapeHtml(sourceLabel(source))}</span>`).join("");
      const riskText = risks.length ? risks.map(flag => `<span class="tag risk">${escapeHtml(flag)}</span>`).join("") : "0";
      return `<tr>
        <td class="repo"><a href="${escapeAttribute(project.html_url)}" target="_blank" rel="noreferrer">${escapeHtml(project.full_name)}</a><div class="desc">${escapeHtml(project.description || "")}</div></td>
        <td>${escapeHtml(project.run_date || "")}</td>
        <td>${escapeHtml(project.language || "Unknown")}</td>
        <td>${escapeHtml(project.category || "Other")}</td>
        <td>${sourceTags || "-"}</td>
        <td class="num">${project.trending_rank ? project.trending_rank : "-"}</td>
        <td class="num">${number(project.star_growth)}</td>
        <td>${riskText}</td>
        <td><a href="${escapeAttribute(project.report_url || "#")}">查看</a></td>
      </tr>`;
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
        projects.append(
            {
                "run_date": row.get("run_date", ""),
                "full_name": row.get("full_name", ""),
                "html_url": row.get("html_url", ""),
                "description": row.get("description", ""),
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
                "report_url": f"weekly/{row.get('run_date', '')}.html" if row.get("run_date") else "",
            }
        )
    return {
        "schema_version": 1,
        "count": len(projects),
        "projects": projects,
    }


def _public_runs(root: Path, reports: list[Path]) -> dict:
    runs = []
    for report in reports:
        summary = _run_summary(root, report.stem)
        trends = _trend_summary(root, report.stem)
        if not summary:
            continue
        runs.append(
            {
                "run_date": report.stem,
                "status": summary.get("status", ""),
                "report_url": f"weekly/{_page_name(report)}",
                "selected_count": _int_value(summary.get("selected_count")),
                "collected_count": _int_value(summary.get("collected_count")),
                "previously_sent_selected_count": _int_value(summary.get("previously_sent_selected_count")),
                "readme_fetched_count": _int_value(summary.get("readme_fetched_count")),
                "star_history_updated_count": _int_value(summary.get("star_history_updated_count")),
                "kimi_used": bool(summary.get("kimi_used")),
                "fallback_used": bool(summary.get("fallback_used")),
                "telegram_sent": bool(summary.get("telegram_sent")),
                "telegram_report_url": summary.get("telegram_report_url", ""),
                "collector_error_count": len(summary.get("collector_errors") or []),
                "top_languages": trends.get("top_languages") or [],
                "top_categories": trends.get("top_categories") or [],
                "total_star_growth": _int_value(trends.get("total_star_growth")),
                "trending_project_count": _int_value(trends.get("trending_project_count")),
                "summary_points": [str(point) for point in trends.get("summary_points") or [] if point],
            }
        )
    return {
        "schema_version": 1,
        "count": len(runs),
        "runs": runs,
    }


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


def _json_text(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _int_value(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _float_value(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


if __name__ == "__main__":
    for path in build_pages():
        print(path.relative_to(ROOT).as_posix())
