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
    current_eligible: eligibility === "eligible",
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
      evidence_relevance: "not_applicable",
      claim_support: "not_applicable",
      data_freshness: "fresh",
      source_latest_date: "2026-07-17",
      corpus_latest_date: "2026-07-17",
      embedding_latest_date: "2026-07-17",
      stale_days: 1,
      as_of: "2026-07-18",
      reasons: [],
    },
  };
}

function assistantPayload(query, state, base) {
  const previousIds = Array.isArray(state?.candidate_repository_ids) ? state.candidate_repository_ids : [];
  const previousKnowledge = state?.knowledge_context && typeof state.knowledge_context === "object"
    ? state.knowledge_context : { topic: "", outline: [], focus_id: "" };
  const previousOutline = Array.isArray(previousKnowledge.outline) ? previousKnowledge.outline : [];
  const reset = query.includes("重新搜索") || query.includes("换一批");
  const followUp = previousIds.length > 0 && (query.includes("刚才") || query.includes("这些项目") || query.includes("其中"));
  const knowledgeFollowUp = previousOutline.length > 0 && ["展开", "继续", "举例", "换种说法", "回到"].some((marker) => query.includes(marker));
  const knowledge = query.includes("学习 AI Agent") || query.includes("AI Agent 开发方向") || knowledgeFollowUp;
  let recommendations = base.recommendations;
  let answer = base.answer;
  let assistantMode = "project_search";
  let knowledgeBasis = recommendations.length ? "project_evidence" : "none";
  let candidateScope = base.input_route.candidate_scope;

  if (knowledge) {
    assistantMode = "knowledge";
    knowledgeBasis = "mixed";
    answer = knowledgeFollowUp
      ? `继续讲解 ${query.includes("回到第一点") ? "模型与推理" : "记忆与反馈"}，并保持上一轮教学提纲。`
      : "结论：先学习 Agent 循环、工具调用和状态管理。学习路线：1. 模型与推理 2. 工具与行动 3. 记忆与反馈。最小实践：完成一个只读项目研究助手。[1]";
  } else if (followUp) {
    assistantMode = query.includes("区别") || query.includes("比较") ? "project_compare" : "project_follow_up";
    const selected = { ...recommendation(), full_name: previousIds[0] };
    recommendations = [selected];
    answer = `在上一轮候选中，建议先学习 ${previousIds[0]}，因为它最适合先验证单 Agent 到编排的最小闭环。[1]`;
    candidateScope = "previous_candidates";
  } else if (reset) {
    const selected = { ...recommendation(), full_name: "fixture/python-agent-new" };
    recommendations = [selected];
    answer = "已脱离上一轮候选并重新搜索 Python 项目，当前优先关注 fixture/python-agent-new。[1]";
    candidateScope = "archive";
  }

  const citations = recommendations.map((item, index) => ({ index: index + 1, full_name: item.full_name, chunk_id: `fixture:chunk:${index + 1}` }));
  const evidence = recommendations.map((item, index) => ({ index: index + 1, full_name: item.full_name, chunk_id: `fixture:chunk:${index + 1}`, quote: "固定可引用证据" }));
  const candidateIds = recommendations.filter((item) => item.eligibility === "eligible" && item.current_eligible === true).map((item) => item.full_name);
  const revision = Number.isInteger(state?.revision) ? state.revision + 1 : 1;
  const defaultOutline = [
    { id: "k1", title: "模型与推理" },
    { id: "k2", title: "工具与行动" },
    { id: "k3", title: "记忆与反馈" },
  ];
  const knowledgeContext = knowledge ? {
    topic: previousKnowledge.topic || "Agent 核心组成",
    outline: previousOutline.length ? previousOutline : defaultOutline,
    focus_id: query.includes("第三点") ? "k3" : query.includes("回到第一点") ? "k1" : previousKnowledge.focus_id || "",
  } : previousKnowledge;
  return {
    ...base,
    query,
    resolved_query: query,
    answer,
    assistant_mode: assistantMode,
    knowledge_basis: knowledgeBasis,
    sections: [
      ...(knowledge ? [{ kind: "guidance", title: "AI Agent 学习建议", content: "先学习 Agent 循环、工具调用和状态管理，再完成可评估的最小实践。", citation_indexes: [] }] : []),
      ...(recommendations.length ? [{ kind: "project_evidence", title: "证据支持的项目建议", content: answer, citation_indexes: citations.map((item) => item.index) }] : []),
    ],
    citations,
    evidence,
    recommendations,
    count: recommendations.length,
    input_route: {
      ...base.input_route,
      route: followUp ? "resume" : "new_search",
      candidate_scope: candidateScope,
      selected_repository_ids: followUp ? candidateIds : [],
    },
    assistant_state: {
      schema_version: 2,
      revision,
      goal: query,
      knowledge_context: knowledgeContext,
      constraints: reset ? [{ field: "language", operator: "eq", value: "Python", hard: false }] : [],
      candidate_repository_ids: candidateIds,
      primary_repository_id: candidateIds[0] || "",
      last_intent: assistantMode,
      pending_question: "",
      source_identity: { kind: "fixture", source_id: "fixture-current", run_date: "2026-08-09", as_of: "2026-08-09" },
      mode: "hybrid",
      resumable: candidateIds.length > 0,
    },
    model_status: { provider: "fixture", configured: knowledge, used: knowledge, model: knowledge ? "fixture-knowledge-v1" : "" },
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
  const final = assistantPayload(query, body.state, answerPayload(mode));
  response.writeHead(200, {
    "Cache-Control": "no-cache",
    "Content-Type": "text/event-stream; charset=utf-8",
    Connection: "keep-alive",
  });
  sseEvent(response, "meta", { query, retrieval: { mode: "hybrid" }, citations: final.citations, evidence: final.evidence, freshness: final.answer_quality });
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
    if (request.method === "POST" && ["/v1/rag/ask/stream", "/v1/assistant/turn/stream"].includes(url.pathname)) return await handleAsk(request, response);
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
