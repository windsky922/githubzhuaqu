import { useQuery } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { recommendations } from "../lib/api";
import { ProjectCard } from "../components/ProjectCard";

export function RecommendationsPage() {
  const { data = [], isLoading, error } = useQuery({ queryKey: ["recommendations"], queryFn: recommendations });
  return <main className="page"><header className="page-heading"><div><p className="eyebrow">研究排序</p><h1>继续跟踪推荐</h1><p className="page-copy">结合现有研究档案、质量信号与项目趋势的候选列表。</p></div><span className="badge"><Sparkles size={13} />{data.length} 个候选</span></header>{isLoading ? <div className="empty-state">正在排序推荐项目…</div> : error ? <div className="error-state">推荐数据加载失败。</div> : <section className="project-grid">{data.map((project) => <ProjectCard key={project.full_name} project={project} />)}</section>}</main>;
}
