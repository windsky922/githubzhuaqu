import { useQuery } from "@tanstack/react-query";
import { ExternalLink, GitCompareArrows } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { projectDetail } from "../lib/api";

export function ProjectPage() {
  const { owner = "", repo = "" } = useParams();
  const { data: project, isLoading, error } = useQuery({ queryKey: ["project", owner, repo], queryFn: () => projectDetail(owner, repo) });
  if (isLoading) return <main className="page"><div className="empty-state">正在加载项目详情…</div></main>;
  if (error || !project) return <main className="page"><div className="error-state">未找到此项目的归档数据。</div></main>;
  return <main className="page"><header className="page-heading"><div><p className="eyebrow">项目档案</p><h1>{project.full_name}</h1><p className="page-copy">{project.description || project.recommendation_reason || "当前归档未提供项目描述。"}</p></div><div className="flex gap-2">{project.html_url ? <a className="button" href={project.html_url} target="_blank" rel="noreferrer"><ExternalLink size={15} />GitHub</a> : null}<Link className="button" to={`/compare?repos=${encodeURIComponent(project.full_name)}`}><GitCompareArrows size={15} />对比</Link></div></header><div className="detail-layout"><section className="panel"><h2>研究结论</h2><p>{project.recommendation_reason || project.rag_reason || "暂无额外研究结论。"}</p><h2>风险与质量</h2><p>{project.risk_summary || "当前没有归档风险提示。"}</p></section><aside className="panel"><h2>项目指标</h2><div className="key-value"><span>主要语言</span><b>{project.language || "未标注"}</b></div><div className="key-value"><span>方向</span><b>{project.category || "未标注"}</b></div><div className="key-value"><span>新增 Star</span><b>+{Number(project.stars_added || 0).toLocaleString()}</b></div><div className="key-value"><span>入选日期</span><b>{project.run_date || "未标注"}</b></div></aside></div></main>;
}
