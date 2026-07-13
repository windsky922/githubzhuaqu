import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, join, resolve, sep } from "node:path";

const port = Number(process.env.PORT || 4173);
const docsRoot = resolve("docs");
const projects = Array.from({ length: 55 }, (_, index) => ({
  full_name: `fixture/project-${String(index + 1).padStart(2, "0")}`,
  html_url: `https://github.com/fixture/project-${String(index + 1).padStart(2, "0")}`,
  description: `固定项目 ${index + 1}`,
  language: index % 2 ? "TypeScript" : "Python",
  category: "AI Agent",
  source: "e2e_fixture",
  stars_added: 100 - index,
}));

const mimeTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};

function json(response, body) {
  response.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
  response.end(JSON.stringify(body));
}

function recommendation(eligibility = "eligible") {
  return {
    full_name: eligibility === "rejected" ? "fixture/rejected" : "fixture/agent-platform",
    rank: 1,
    match_score: eligibility === "rejected" ? 0.7 : 1,
    matched_requirements: eligibility === "eligible" ? ["语言=Python"] : [],
    unmet_requirements: eligibility === "rejected" ? ["许可证=MIT"] : [],
    unknown_requirements: [],
    reasons: [eligibility === "rejected" ? "违反显式约束：许可证=MIT" : "满足显式筛选：语言=Python"],
    citation_indexes: [1],
    evidence_chunk_ids: ["fixture:chunk:1"],
    eligibility,
  };
}

function answerPayload(mode) {
  const clarification = mode === "clarification";
  const noMatch = mode === "no_match";
  const refusal = mode === "refusal";
  const fallback = mode === "fallback_rule";
  const recommendations = clarification || refusal ? [] : [recommendation(noMatch ? "rejected" : "eligible")];
  const answer = clarification
    ? "请补充你希望继续分析的具体项目或完整需求。"
    : noMatch
      ? "当前候选全部违反许可证硬约束，请放宽条件或重新搜索。"
      : refusal
        ? "当前归档没有可引用证据，无法形成项目结论。"
        : fallback
          ? "模型不可用，已依据当前证据返回保守的规则结论。[1]"
          : `${"这是用于验证长流式输出布局的固定证据结论。".repeat(35)}[1]`;
  return {
    schema_version: 1,
    query: mode,
    resolved_query: mode,
    answer,
    answer_model: fallback ? "rule:rag-ask-v1" : "fixture:e2e",
    answer_mode: mode,
    fallback_reason: fallback ? "Kimi API 未配置" : refusal ? "no_evidence" : noMatch ? "hard_constraint_no_match" : "",
    confidence: recommendations.length ? "medium" : "low",
    evidence_coverage: recommendations.length ? "medium" : "low",
    match_confidence: "unknown",
    count: recommendations.length,
    retrieval: { mode: "hybrid" },
    citations: recommendations.length ? [{ index: 1, full_name: recommendations[0].full_name, chunk_id: "fixture:chunk:1" }] : [],
    evidence: recommendations.length ? [{ index: 1, full_name: recommendations[0].full_name, chunk_id: "fixture:chunk:1", quote: "固定可引用证据" }] : [],
    recommendations,
    prompt_context: "",
    contexts: [],
    clarification_required: clarification,
    clarification_question: clarification ? answer : "",
    input_route: {
      route: clarification ? "clarify" : "new_search",
      parser: "rule:follow-up-v1",
      retrieval_performed: !clarification,
      candidate_scope: clarification ? "none" : "archive",
      requirements: noMatch ? [{ field: "license", operator: "eq", value: "MIT", hard: true }] : [],
    },
    model_status: { configured: !fallback, attempted: false, used: false },
    answer_quality: {
      applicable: !clarification && !noMatch,
      passed: true,
      issues: [],
      citation_validity: recommendations.length ? true : "not_applicable",
      evidence_relevance: "not_evaluated",
      claim_support: "not_evaluated",
      data_freshness: "unknown",
    },
  };
}

function sseEvent(response, event, data) {
  response.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
}

function delay(milliseconds) {
  return new Promise((resolveDelay) => setTimeout(resolveDelay, milliseconds));
}

async function handleAsk(request, response) {
  let raw = "";
  for await (const chunk of request) raw += chunk;
  const body = JSON.parse(raw || "{}");
  const query = String(body.q || "");
  const mode = query.includes("需要澄清")
    ? "clarification"
    : query.includes("没有匹配")
      ? "no_match"
      : query.includes("证据不足")
        ? "refusal"
        : query.includes("模型降级")
          ? "fallback_rule"
          : "llm";
  const final = answerPayload(mode);
  response.writeHead(200, {
    "Cache-Control": "no-cache",
    "Content-Type": "text/event-stream; charset=utf-8",
    Connection: "keep-alive",
  });
  sseEvent(response, "meta", { query, retrieval: { mode: "hybrid" }, citations: final.citations, evidence: final.evidence });
  if (mode === "clarification") {
    sseEvent(response, "final", final);
    response.end();
    return;
  }
  await delay(80);
  sseEvent(response, "delta", { text: "正在根据固定证据生成草稿。" });
  await delay(query.includes("长流式") ? 1_200 : 80);
  sseEvent(response, "final", final);
  response.end();
}

function handleProjects(url, response) {
  const offset = Math.max(0, Number(url.searchParams.get("offset") || 0));
  const limit = Math.min(50, Math.max(1, Number(url.searchParams.get("limit") || 50)));
  const items = projects.slice(offset, offset + limit);
  json(response, {
    projects: items,
    count: items.length,
    total: projects.length,
    offset,
    limit,
    has_more: offset + items.length < projects.length,
  });
}

function handleComparison(url, response) {
  const names = String(url.searchParams.get("repos") || "").split(",").filter(Boolean).slice(0, 3);
  const selected = projects.filter((project) => names.includes(project.full_name));
  json(response, {
    count: selected.length,
    missing: names.filter((name) => !selected.some((project) => project.full_name === name)),
    projects: selected,
    matrix: [{ key: "language", label: "语言", values: Object.fromEntries(selected.map((project) => [project.full_name, project.language])) }],
    best_by: {},
    recommendation: {},
    selection_summary: ["固定对比数据仅用于浏览器回归。"],
  });
}

async function handleStatic(url, response) {
  const requestPath = url.pathname === "/" ? "/app/" : decodeURIComponent(url.pathname);
  let filePath = resolve(join(docsRoot, requestPath.replace(/^\/+/, "")));
  if (filePath !== docsRoot && !filePath.startsWith(`${docsRoot}${sep}`)) {
    response.writeHead(403);
    response.end("Forbidden");
    return;
  }
  try {
    if ((await stat(filePath)).isDirectory()) filePath = join(filePath, "index.html");
    await stat(filePath);
  } catch {
    response.writeHead(404);
    response.end("Not found");
    return;
  }
  response.writeHead(200, { "Content-Type": mimeTypes[extname(filePath)] || "application/octet-stream" });
  createReadStream(filePath).pipe(response);
}

createServer(async (request, response) => {
  try {
    const url = new URL(request.url || "/", `http://127.0.0.1:${port}`);
    if (request.method === "POST" && url.pathname === "/v1/rag/ask/stream") return await handleAsk(request, response);
    if (request.method === "GET" && url.pathname === "/api/projects/compare") return handleComparison(url, response);
    if (request.method === "GET" && url.pathname === "/api/projects") return handleProjects(url, response);
    return await handleStatic(url, response);
  } catch (error) {
    response.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
    response.end(error instanceof Error ? error.message : "mock server error");
  }
}).listen(port, "127.0.0.1", () => {
  console.log(`E2E mock server listening on http://127.0.0.1:${port}`);
});
