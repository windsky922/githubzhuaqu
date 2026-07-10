import { ExternalLink, FileText } from "lucide-react";
import { Link } from "react-router-dom";
import type { Project } from "../lib/types";

function ownerAvatar(fullName: string) {
  const owner = fullName.split("/")[0];
  return owner ? `https://github.com/${encodeURIComponent(owner)}.png?size=64` : "";
}

export function ProjectCard({ project }: { project: Project }) {
  const [owner = "", repo = project.full_name] = project.full_name.split("/");
  const reason = project.recommendation_reason || project.rag_reason || project.description || "基于本轮召回证据进入候选。";
  return (
    <article className="project-card">
      <div className="project-card-head">
        {owner ? <img className="avatar" src={ownerAvatar(project.full_name)} alt="" onError={(event) => { event.currentTarget.style.display = "none"; }} /> : <span className="avatar avatar-fallback">{repo.slice(0, 1).toUpperCase()}</span>}
        <div className="project-name" title={project.full_name}>{project.full_name}</div>
      </div>
      <div className="answer-meta">
        {project.language ? <span className="badge">{project.language}</span> : null}
        {project.category ? <span className="badge">{project.category}</span> : null}
      </div>
      <p>{reason}</p>
      <div className="project-actions">
        <Link className="small-link" to={`/projects/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}`}><FileText size={12} />详情</Link>
        {project.html_url ? <a className="small-link" href={project.html_url} target="_blank" rel="noreferrer"><ExternalLink size={12} />GitHub</a> : null}
      </div>
    </article>
  );
}
