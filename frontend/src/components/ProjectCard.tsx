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
function sourceLabel(project: Project) {
  if (project.source_kind === "verified_snapshot") return `最新快照${project.source_date ? ` · ${project.source_date}` : ""}`;
  if (project.source_kind === "local_archive_sqlite") return `历史归档 SQLite${project.source_date ? ` · ${project.source_date}` : ""}`;
  if (project.source_kind === "local_archive_json") return `历史归档 JSON${project.source_date ? ` · ${project.source_date}` : ""}`;
  return "待核实来源";
}
function preferenceLabel(preference: NonNullable<Project["preferences"]>[number]) {
  const labels: Record<string, string> = { language: "语言", hosting_mode: "本地部署", multi_agent: "多 Agent", offline_capable: "离线能力", cost: "成本", external_api_required: "外部模型 API" };
  const value = preference.value === true ? "是" : preference.value === false ? "否" : String(preference.value);
  return `${labels[preference.field] || preference.field}：${value}`;
}

export function ProjectCard({ project, primary = false, evidenceCount = 0 }: { project: Project; primary?: boolean; evidenceCount?: number }) {
  const [owner = "", repo = project.full_name] = project.full_name.split("/");
  const [avatarFailed, setAvatarFailed] = useState(false);
  const compare = useCompareSelection();
  const selected = compare.isSelected(project.full_name);
  const relativeScore = typeof project.match_score === "number" ? Math.round(project.match_score * 100) : null;
  return <article className={`project-card${primary ? " primary-project" : " candidate-project"}${project.eligibility ? ` eligibility-${project.eligibility}` : ""}`}>
    <div className="project-card-head"><span className="avatar-wrap">{owner && !avatarFailed ? <img className="avatar" src={ownerAvatar(project.full_name)} alt="" onError={() => setAvatarFailed(true)} /> : <span className="avatar avatar-fallback" aria-hidden="true">{fallback(project.full_name)}</span>}</span><div className="project-heading"><strong className="project-name" title={project.full_name}>{project.full_name}</strong><span>{project.description || (project.eligibility ? "当前归档候选" : "未提供项目描述")}</span></div></div>
    <div className="project-meta">{project.eligibility ? <span className={`badge eligibility-badge ${project.eligibility}`}>{eligibilityLabel(project.eligibility)}</span> : null}{project.source_kind ? <span className={`badge source-badge ${project.current_eligible ? "current" : "history"}`}>{sourceLabel(project)}</span> : null}{relativeScore !== null ? <span className="badge">相对匹配分 {relativeScore}/100</span> : null}{evidenceCount ? <span className="badge">{evidenceCount} 条证据</span> : null}</div>
    {project.source_notice ? <p className="project-source-note">{project.source_notice}</p> : null}
    <p className="project-reason">{projectReason(project)}</p>
    {project.matched_requirements?.length ? <div className="requirement-list matched"><strong>满足</strong><span>{project.matched_requirements.join("、")}</span></div> : null}
    {project.unmet_requirements?.length ? <div className="requirement-list unmet"><strong>未满足</strong><span>{project.unmet_requirements.join("、")}</span></div> : null}
    {project.unknown_requirements?.length ? <div className="requirement-list unknown"><strong>无法验证</strong><span>{project.unknown_requirements.join("、")}</span></div> : null}
    {project.preferences?.length ? <div className="preference-list"><strong>偏好匹配</strong>{project.preferences.map((preference, index) => <span className={`preference ${preference.status}`} key={`${preference.field}-${index}`}>{preferenceLabel(preference)} · {preference.status === "matched" ? "已满足" : preference.status === "unmet" ? "未满足" : "待核实"}</span>)}</div> : null}
    {project.optional_requirements?.length ? <div className="preference-list"><strong>可选条件（不参与筛选）</strong>{project.optional_requirements.map((requirement, index) => <span className="preference" key={`${requirement.field}-optional-${index}`}>{preferenceLabel(requirement)}</span>)}</div> : null}
    <div className="project-actions"><Link className="small-link" to={`/projects/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}`}><FileText size={13} />详情</Link>{project.html_url ? <a className="small-link" href={project.html_url} target="_blank" rel="noreferrer"><ExternalLink size={13} />GitHub</a> : null}<button className="small-link compare-action" type="button" disabled={!selected && !compare.canAdd} onClick={() => selected ? compare.remove(project.full_name) : compare.add(project.full_name)}><GitCompareArrows size={13} />{selected ? "移出对比" : "加入对比"}</button></div>
  </article>;
}

export function PrimaryProjectCard({ project, evidenceCount }: { project: Project; evidenceCount: number }) { return <ProjectCard project={project} primary evidenceCount={evidenceCount} />; }
export function CandidateProjectCard({ project, evidenceCount }: { project: Project; evidenceCount: number }) { return <ProjectCard project={project} evidenceCount={evidenceCount} />; }
