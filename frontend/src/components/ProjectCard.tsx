import { ExternalLink, FileText, GitCompareArrows } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import type { Project, RagRecommendation } from "../lib/types";
import { useCompareSelection } from "../lib/compareSelection";

function ownerAvatar(fullName: string) { const owner = fullName.split("/")[0]; return owner ? `https://github.com/${encodeURIComponent(owner)}.png?size=64` : ""; }
function fallback(fullName: string) { return fullName.split("/").at(-1)?.slice(0, 1).toUpperCase() || "G"; }

export function projectReason(project: Project) { return project.recommendation_reason || project.rag_reason || project.description || "基于本轮召回证据进入候选。"; }
export function eligibilityLabel(value?: RagRecommendation["eligibility"]) {
  if (value === "eligible") return "符合已验证约束";
  if (value === "rejected") return "违反显式约束";
  return "约束尚无法验证";
}

export function ProjectCard({ project, primary = false, evidenceCount = 0 }: { project: Project; primary?: boolean; evidenceCount?: number }) {
  const [owner = "", repo = project.full_name] = project.full_name.split("/");
  const [avatarFailed, setAvatarFailed] = useState(false);
  const compare = useCompareSelection();
  const selected = compare.isSelected(project.full_name);
  const relativeScore = typeof project.match_score === "number" ? Math.round(project.match_score * 100) : null;
  return <article className={`project-card${primary ? " primary-project" : " candidate-project"}${project.eligibility ? ` eligibility-${project.eligibility}` : ""}`}>
    <div className="project-card-head"><span className="avatar-wrap">{owner && !avatarFailed ? <img className="avatar" src={ownerAvatar(project.full_name)} alt="" onError={() => setAvatarFailed(true)} /> : <span className="avatar avatar-fallback" aria-hidden="true">{fallback(project.full_name)}</span>}</span><div className="project-heading"><strong className="project-name" title={project.full_name}>{project.full_name}</strong><span>{project.description || (project.eligibility ? "当前归档候选" : "未提供项目描述")}</span></div></div>
    <div className="project-meta">{project.eligibility ? <span className={`badge eligibility-badge ${project.eligibility}`}>{eligibilityLabel(project.eligibility)}</span> : null}{relativeScore !== null ? <span className="badge">相对匹配分 {relativeScore}/100</span> : null}{evidenceCount ? <span className="badge">{evidenceCount} 条证据</span> : null}</div>
    <p className="project-reason">{projectReason(project)}</p>
    {project.matched_requirements?.length ? <div className="requirement-list matched"><strong>满足</strong><span>{project.matched_requirements.join("、")}</span></div> : null}
    {project.unmet_requirements?.length ? <div className="requirement-list unmet"><strong>未满足</strong><span>{project.unmet_requirements.join("、")}</span></div> : null}
    <div className="project-actions"><Link className="small-link" to={`/projects/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}`}><FileText size={13} />详情</Link>{project.html_url ? <a className="small-link" href={project.html_url} target="_blank" rel="noreferrer"><ExternalLink size={13} />GitHub</a> : null}<button className="small-link compare-action" type="button" disabled={!selected && !compare.canAdd} onClick={() => selected ? compare.remove(project.full_name) : compare.add(project.full_name)}><GitCompareArrows size={13} />{selected ? "移出对比" : "加入对比"}</button></div>
  </article>;
}

export function PrimaryProjectCard({ project, evidenceCount }: { project: Project; evidenceCount: number }) { return <ProjectCard project={project} primary evidenceCount={evidenceCount} />; }
export function CandidateProjectCard({ project, evidenceCount }: { project: Project; evidenceCount: number }) { return <ProjectCard project={project} evidenceCount={evidenceCount} />; }
