import type { AskIntentContext, Comparison, Project, ProjectPage, RagAnswer } from "./types";

type JsonEnvelope<T> = { projects?: T[]; profiles?: unknown[]; recommendations?: T[]; total?: number; offset?: number; limit?: number; has_more?: boolean; count?: number };
export type StreamEvent = { event: "meta" | "delta" | "final" | "error"; data: Record<string, unknown> };

function queryParams() {
  const normal = new URLSearchParams(window.location.search);
  const hash = window.location.hash.split("?")[1];
  return new URLSearchParams(hash || normal.toString());
}

export function shouldUseApi() {
  const params = queryParams();
  if (params.get("api") === "1") return true;
  if (params.get("api") === "0") return false;
  return ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname);
}

function publicUrl(name: string) {
  return new URL(`../${name}`, window.location.href).toString();
}

async function readJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json() as Promise<T>;
}

export async function projects(filters: Record<string, string> = {}) {
  return (await projectPage({ ...filters, limit: filters.limit || "200" })).projects;
}

function archiveFilter(items: Project[], filters: Record<string, string>) {
  const query = (filters.query || "").trim().toLowerCase();
  return items.filter((project) => {
    const text = `${project.full_name} ${project.description || ""} ${project.category || ""} ${project.source || ""}`.toLowerCase();
    return (!query || text.includes(query)) && (!filters.language || project.language === filters.language) && (!filters.category || project.category === filters.category) && (!filters.source || project.source === filters.source);
  });
}

export async function projectPage(filters: Record<string, string> = {}): Promise<ProjectPage> {
  const limit = Math.min(Math.max(Number(filters.limit || 50), 1), 200);
  const offset = Math.max(Number(filters.offset || 0), 0);
  if (shouldUseApi()) {
    try {
      const params = new URLSearchParams(filters);
      const data = await readJson<JsonEnvelope<Project>>(`/api/projects?${params}`);
      const items = data.projects || [];
      return { projects: items, count: data.count ?? items.length, total: data.total ?? items.length, offset: data.offset ?? offset, limit: data.limit ?? limit, has_more: data.has_more ?? false };
    } catch { /* fall through to public archive */ }
  }
  const data = await readJson<JsonEnvelope<Project>>(publicUrl("projects.json"));
  const all = archiveFilter(data.projects || [], filters);
  const items = all.slice(offset, offset + limit);
  return { projects: items, count: items.length, total: all.length, offset, limit, has_more: offset + items.length < all.length, static_fallback: true };
}

export async function compareProjects(repos: string[]): Promise<Comparison> {
  const selected = [...new Set(repos)].filter(Boolean).slice(0, 3);
  if (!selected.length) return { count: 0, missing: [], projects: [], matrix: [], best_by: {}, recommendation: {}, selection_summary: [] };
  if (shouldUseApi()) return readJson<Comparison>(`/api/projects/compare?${new URLSearchParams({ repos: selected.join(",") })}`);
  const all = await projects();
  const items = all.filter((item) => selected.includes(item.full_name));
  return { count: items.length, missing: selected.filter((name) => !items.some((item) => item.full_name === name)), projects: items, matrix: ["language", "category", "source", "run_date", "stars", "stars_added", "recommendation_score"].map((key) => ({ key, label: key, values: Object.fromEntries(items.map((item) => [item.full_name, item[key]])) })), best_by: {}, recommendation: {}, selection_summary: [] };
}

export async function projectDetail(owner: string, repo: string) {
  const fullName = `${owner}/${repo}`;
  if (shouldUseApi()) {
    try {
      return await readJson<Project>(`/api/projects/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}`);
    } catch { /* fall through to public archive */ }
  }
  const all = await projects();
  return all.find((item) => item.full_name === fullName) || null;
}

export async function recommendations() {
  if (shouldUseApi()) {
    try {
      const data = await readJson<JsonEnvelope<Project>>("/v1/recommendations?limit=30");
      return data.recommendations || [];
    } catch { /* fall through to public archive */ }
  }
  return [...(await projects())].sort((left, right) => Number(right.recommendation_score || 0) - Number(left.recommendation_score || 0)).slice(0, 30);
}

export function contextualAskBody(question: string, context?: AskIntentContext) {
  return { q: question, ...(context ? { context } : {}), mode: context?.mode || "hybrid", limit: 3, auto_build: true };
}

export async function streamRagAsk(question: string, context: AskIntentContext | undefined, signal: AbortSignal, onEvent: (event: StreamEvent) => void) {
  const response = await fetch("/v1/rag/ask/stream", {
    method: "POST",
    signal,
    headers: { Accept: "text/event-stream", "Content-Type": "application/json" },
    body: JSON.stringify(contextualAskBody(question, context)),
  });
  if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`);
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "error";

  while (true) {
    const chunk = await reader.read();
    if (chunk.done) break;
    buffer += decoder.decode(chunk.value, { stream: true });
    let boundary = buffer.indexOf("\n\n");
    while (boundary >= 0) {
      const frame = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const dataLine = frame.split("\n").find((line) => line.startsWith("data:"));
      const eventLine = frame.split("\n").find((line) => line.startsWith("event:"));
      currentEvent = eventLine ? eventLine.slice(6).trim() : currentEvent;
      if (dataLine) {
        try {
          const event = currentEvent as StreamEvent["event"];
          onEvent({ event, data: JSON.parse(dataLine.slice(5).trim()) as Record<string, unknown> });
        } catch {
          onEvent({ event: "error", data: { message: "流式响应解析失败" } });
        }
      }
      boundary = buffer.indexOf("\n\n");
    }
  }
}

export function answerFromEvent(data: Record<string, unknown>) {
  return data as unknown as RagAnswer;
}
