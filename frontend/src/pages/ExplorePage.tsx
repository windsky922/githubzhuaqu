import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { projectPage } from "../lib/api";
import { useCompareSelection } from "../lib/compareSelection";

const PAGE_SIZE = 50;

function value(params: URLSearchParams, name: string) { return params.get(name) || ""; }

export function ExplorePage() {
  const [params, setParams] = useSearchParams();
  const compare = useCompareSelection();
  const page = Math.max(Number(value(params, "page")) || 1, 1);
  const filters = { query: value(params, "query"), language: value(params, "language"), category: value(params, "category"), source: value(params, "source"), limit: String(PAGE_SIZE), offset: String((page - 1) * PAGE_SIZE), sort: value(params, "sort") || "recent" };
  const { data, isLoading, error } = useQuery({ queryKey: ["project-page", filters], queryFn: () => projectPage(filters) });
  const totalPages = Math.max(Math.ceil((data?.total || 0) / PAGE_SIZE), 1);
  const update = (name: string, next: string) => { const updated = new URLSearchParams(params); if (next) updated.set(name, next); else updated.delete(name); updated.set("page", "1"); setParams(updated, { replace: true }); };
  const movePage = (next: number) => { const updated = new URLSearchParams(params); updated.set("page", String(Math.min(Math.max(next, 1), totalPages))); setParams(updated); };
  const rangeStart = data?.total ? (data.offset + 1) : 0;
  const rangeEnd = data ? data.offset + data.projects.length : 0;

  return <main className="page"><header className="page-heading"><div><p className="eyebrow">项目语料</p><h1>筛选项目</h1><p className="page-copy">从完整历史归档中按技术方向与来源筛选候选项目。</p></div></header><section className="content-grid"><div className="toolbar explore-toolbar"><label className="field">关键词<input value={filters.query} onChange={(event) => update("query", event.target.value)} placeholder="仓库、方向或描述" /></label><label className="field">语言<input value={filters.language} onChange={(event) => update("language", event.target.value)} placeholder="例如 Python" /></label><label className="field">分类<input value={filters.category} onChange={(event) => update("category", event.target.value)} placeholder="例如 AI Agent" /></label><label className="field">来源<input value={filters.source} onChange={(event) => update("source", event.target.value)} placeholder="例如 github_trending" /></label><label className="field">排序<select value={filters.sort} onChange={(event) => update("sort", event.target.value)}><option value="recent">最近入选</option><option value="star-growth">Star 增长</option><option value="quality">质量</option><option value="trending">Trending</option></select></label><span className="badge"><Search size={12} />{data?.total ?? "…"} 个项目</span></div>{isLoading ? <div className="empty-state">正在加载项目归档…</div> : error ? <div className="error-state">项目数据加载失败。</div> : !data?.projects.length ? <div className="empty-state">没有匹配项目，尝试减少筛选条件。</div> : <><div className="table-card">{data.projects.map((project) => { const [owner, repo] = project.full_name.split("/"); const selected = compare.isSelected(project.full_name); return <div className="table-row explore-row" key={project.full_name}><div><Link to={`/projects/${encodeURIComponent(owner || "")}/${encodeURIComponent(repo || "")}`}><strong>{project.full_name}</strong></Link><br /><span>{project.description || project.recommendation_reason || "无描述"}</span></div><span>{project.language || "未标注"}</span><span>{project.category || project.source || "历史归档"}</span><span className="metric">+{Number(project.stars_added || 0).toLocaleString()}</span><button className="button compact" type="button" disabled={!selected && !compare.canAdd} onClick={() => selected ? compare.remove(project.full_name) : compare.add(project.full_name)}>{selected ? "已加入" : "加入对比"}</button></div>; })}</div><nav className="pagination" aria-label="项目分页"><span>{rangeStart}-{rangeEnd} / {data.total}</span><button className="icon-button" type="button" aria-label="上一页" disabled={page <= 1} onClick={() => movePage(page - 1)}><ChevronLeft size={16} /></button><span>第 {page} / {totalPages} 页</span><button className="icon-button" type="button" aria-label="下一页" disabled={!data.has_more} onClick={() => movePage(page + 1)}><ChevronRight size={16} /></button></nav></>}</section></main>;
}
