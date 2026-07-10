import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { projects } from "../lib/api";

export function ExplorePage() {
  const [query, setQuery] = useState("");
  const [language, setLanguage] = useState("");
  const { data = [], isLoading, error } = useQuery({ queryKey: ["projects"], queryFn: () => projects() });
  const visible = useMemo(() => data.filter((project) => {
    const haystack = `${project.full_name} ${project.description || ""} ${project.category || ""}`.toLowerCase();
    return (!query || haystack.includes(query.toLowerCase())) && (!language || project.language === language);
  }), [data, language, query]);
  const languages = [...new Set(data.map((project) => project.language).filter(Boolean))] as string[];

  return <main className="page"><header className="page-heading"><div><p className="eyebrow">项目语料</p><h1>筛选项目</h1><p className="page-copy">从历史周报与研究归档中快速缩小候选范围。</p></div></header><section className="content-grid"><div className="toolbar"><label className="field">关键词<input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="仓库、方向或描述" /></label><label className="field">语言<select value={language} onChange={(event) => setLanguage(event.target.value)}><option value="">全部语言</option>{languages.map((item) => <option key={item}>{item}</option>)}</select></label><span className="badge"><Search size={12} />{visible.length} 个结果</span></div>{isLoading ? <div className="empty-state">正在加载项目归档…</div> : error ? <div className="error-state">项目数据加载失败。</div> : <div className="table-card">{visible.map((project) => { const [owner, repo] = project.full_name.split("/"); return <div className="table-row" key={project.full_name}><div><Link to={`/projects/${encodeURIComponent(owner || "")}/${encodeURIComponent(repo || "")}`}><strong>{project.full_name}</strong></Link><br /><span>{project.description || project.recommendation_reason || "无描述"}</span></div><span>{project.language || "未标注"}</span><span>{project.category || project.source || "历史归档"}</span><span className="metric">+{Number(project.stars_added || 0).toLocaleString()}</span></div>; })}</div>}</section></main>;
}
