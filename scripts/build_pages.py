from __future__ import annotations

import json
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
    profiles_json = root / "docs" / "profiles.json"
    profiles_json.write_text(_json_text(_public_profiles(root)), encoding="utf-8")
    written.append(profiles_json)
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
            "- [项目筛选页](explorer.html)",
            "- [历史项目索引](projects.html)",
            "- [公共项目 JSON](projects.json)",
            "- [公共运行 JSON](runs.json)",
            "- [个性化方向 JSON](profiles.json)",
            "- [RSS 订阅](feed.xml)",
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
    const state = { projects: [], profiles: [] };
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
      fetch("projects.json", { cache: "no-store" }).then(response => response.json()),
      fetch("profiles.json", { cache: "no-store" }).then(response => response.json()).catch(() => ({ profiles: [] }))
    ])
      .then(([projectsData, profilesData]) => {
        state.projects = Array.isArray(projectsData.projects) ? projectsData.projects : [];
        state.profiles = Array.isArray(profilesData.profiles) ? profilesData.profiles : [];
        hydrateOptions();
        restoreFiltersFromUrl();
        render();
      })
      .catch(() => {
        rows.innerHTML = '<tr><td class="empty" colspan="10">无法读取 projects.json</td></tr>';
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
      updated.textContent = runDates.length ? `最新数据：${runDates[0]}` : "";
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
        <td class="repo"><a href="${escapeAttribute(project.html_url)}" target="_blank" rel="noreferrer">${escapeHtml(project.full_name)}</a><div class="desc">${escapeHtml(project.description || "")}</div></td>
        <td>${escapeHtml(project.run_date || "")}</td>
        <td>${escapeHtml(project.language || "Unknown")}</td>
        <td>${escapeHtml(project.category || "Other")}</td>
        <td>${sourceTags || "-"}</td>
        <td class="num">${project.trending_rank ? project.trending_rank : "-"}</td>
        <td class="num">${number(project.star_growth)}</td>
        <td>${quality}</td>
        <td>${riskText}</td>
        <td><a href="${escapeAttribute(project.report_url || "#")}">查看</a><button class="detail-toggle" type="button" data-detail="${escapeAttribute(detailId)}">详情</button></td>
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
          <div class="detail-block"><h3>完整链接</h3><p><a class="detail-link" href="${escapeAttribute(project.html_url)}" target="_blank" rel="noreferrer">${escapeHtml(project.html_url)}</a></p></div>
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
        return `<li><a href="${escapeAttribute(match.html_url)}" target="_blank" rel="noreferrer">${escapeHtml(match.full_name)}</a><span>${escapeHtml(meta)}</span>${description}</li>`;
      }).join("")}</ul>`;
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
      button.textContent = open ? "收起" : "详情";
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
    for report in reports:
        summary = _run_summary(root, report.stem)
        trends = _trend_summary(root, report.stem)
        if not summary:
            continue
        selected_count = _int_value(summary.get("selected_count"))
        collector_stats = summary.get("collector_stats") if isinstance(summary.get("collector_stats"), list) else []
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
                "delivery_results": _public_delivery_results(summary.get("delivery_results")),
                "collector_error_count": len(summary.get("collector_errors") or []),
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
            f"    <lastBuildDate>{_xml(format_datetime(datetime.now(UTC)))}</lastBuildDate>",
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
