import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { projects } from "../lib/api";
import { ProjectCard } from "../components/ProjectCard";

export function ComparePage() {
  const [params] = useSearchParams();
  const selected = params.get("repos")?.split(",").filter(Boolean) || [];
  const { data = [], isLoading } = useQuery({ queryKey: ["projects", "compare"], queryFn: () => projects() });
  const matches = useMemo(() => selected.length ? data.filter((project) => selected.includes(project.full_name)) : data.slice(0, 3), [data, selected]);
  return <main className="page"><header className="page-heading"><div><p className="eyebrow">横向判断</p><h1>项目对比</h1><p className="page-copy">比较候选项目的技术方向、热度与归档研究信息。</p></div></header>{isLoading ? <div className="empty-state">正在加载对比候选…</div> : <section className="project-grid">{matches.map((project) => <ProjectCard key={project.full_name} project={project} />)}</section>}</main>;
}
