import type { Project, RagAnswer } from "./types";

type JsonEnvelope<T> = { projects?: T[]; profiles?: unknown[]; recommendations?: T[] };
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
  if (shouldUseApi()) {
    try {
      const params = new URLSearchParams(filters);
      const data = await readJson<JsonEnvelope<Project>>(`/api/projects?${params}`);
      return data.projects || [];
    } catch { /* fall through to public archive */ }
  }
  const data = await readJson<JsonEnvelope<Project>>(publicUrl("projects.json"));
  return data.projects || [];
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

export async function streamRagAsk(question: string, signal: AbortSignal, onEvent: (event: StreamEvent) => void) {
  const params = new URLSearchParams({ q: question, mode: "hybrid", limit: "3", auto_build: "true" });
  const response = await fetch(`/v1/rag/ask/stream?${params}`, { signal, headers: { Accept: "text/event-stream" } });
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
