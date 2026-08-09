import { expect, test, type Page } from "@playwright/test";

type SseEvent = { event: string; data: Record<string, unknown> };

function parseSse(text: string): SseEvent[] {
  return text
    .split(/\r?\n\r?\n/)
    .map((block) => block.trim())
    .filter(Boolean)
    .map((block) => {
      const lines = block.split(/\r?\n/);
      const event = lines.find((line) => line.startsWith("event:"))?.slice(6).trim() || "message";
      const payload = lines
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trimStart())
        .join("\n");
      return { event, data: JSON.parse(payload) as Record<string, unknown> };
    });
}

async function submit(page: Page, question: string) {
  await page.getByLabel("输入项目需求").fill(question);
  await page.getByRole("button", { name: "发送需求" }).click();
}

async function postJson(page: Page, body: Record<string, unknown>) {
  return page.evaluate(async (payload) => {
    const response = await fetch("/v1/rag/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`POST ask failed: ${response.status}`);
    return response.json();
  }, body);
}

async function postSse(page: Page, body: Record<string, unknown>) {
  const text = await page.evaluate(async (payload) => {
    const response = await fetch("/v1/rag/ask/stream", {
      method: "POST",
      headers: { Accept: "text/event-stream", "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`POST stream failed: ${response.status}`);
    return response.text();
  }, body);
  return parseSse(text);
}

test.beforeEach(async ({ page, context }) => {
  await context.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if ((url.protocol === "http:" || url.protocol === "https:") && url.hostname !== "127.0.0.1") {
      await route.abort("blockedbyclient");
      return;
    }
    await route.continue();
  });
  await page.addInitScript(() => window.localStorage.clear());
  await page.goto("/app/#/agent?api=1");
});

test("真实 FastAPI 同源提供静态应用、SQLite 和流式 RAG", async ({ page }) => {
  const health = await page.evaluate(async () => (await fetch("/api/health")).json());
  expect(health.status).toBe("ok");
  expect(health.sqlite_exists).toBe(true);
  expect(health.docs_exists).toBe(true);
  expect(String(health.root)).toContain("github-weekly-real-e2e-");
  expect(String(health.root)).not.toContain("New project 3");

  const events = await postSse(page, {
    q: "找 Python 多 Agent 编排项目",
    mode: "hybrid",
    model: "local-hash-v1",
    limit: 3,
    auto_build: true,
  });
  expect(events[0]?.event).toBe("meta");
  expect(events.at(-1)?.event).toBe("final");
  const final = events.at(-1)?.data || {};
  expect(events.map((event) => event.event)).toEqual(["meta", "final"]);
  expect(final.answer_mode).toBe("fallback_rule");
  expect((final.recommendations as Array<{ full_name: string }>)[0]?.full_name).toBe("eval/agent-orchestrator");
  expect((final.citations as unknown[]).length).toBeGreaterThan(0);
  expect((final.evidence as unknown[]).length).toBeGreaterThan(0);
});

test("普通 POST 与 SSE final 的决策和证据等值", async ({ page }) => {
  const body = {
    q: "找本地知识库 RAG 项目",
    mode: "hybrid",
    model: "local-hash-v1",
    limit: 3,
    auto_build: true,
  };
  const normal = await postJson(page, body);
  const stream = await postSse(page, body);
  const final = stream.at(-1)?.data;
  expect(final).toBeDefined();
  for (const key of [
    "resolved_query",
    "clarification_required",
    "input_route",
    "recommendations",
    "answer_quality",
    "citations",
    "evidence",
    "confidence",
    "evidence_coverage",
    "match_confidence",
  ]) {
    expect(final?.[key]).toEqual(normal[key]);
  }
});

test("无上下文短追问直接澄清且页面不展示项目卡", async ({ page }) => {
  const result = await postJson(page, { q: "继续", mode: "hybrid", model: "local-hash-v1", auto_build: true });
  expect(result.answer_mode).toBe("clarification");
  expect(result.input_route.retrieval_performed).toBe(false);
  for (const key of ["contexts", "citations", "evidence", "recommendations"]) expect(result[key]).toEqual([]);

  await submit(page, "继续");
  await expect(page.locator(".answer-status", { hasText: "需要补充需求" })).toBeVisible();
  await expect(page.locator(".project-card")).toHaveCount(0);
  await expect(page.getByText("质量校验未通过")).toHaveCount(0);
});

test("AI Agent 学习、候选追问与显式重置完成真实三轮对话", async ({ page }) => {
  const bodies: Array<Record<string, unknown>> = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname !== "/v1/assistant/turn/stream") return;
    const body = request.postDataJSON();
    if (body && typeof body === "object") bodies.push(body as Record<string, unknown>);
  });

  const firstPromise = page.waitForResponse((response) => new URL(response.url()).pathname === "/v1/assistant/turn/stream");
  await submit(page, "我想学习 AI Agent 开发方向的知识。");
  const first = parseSse(await (await firstPromise).text()).at(-1)?.data || {};
  expect(first.assistant_mode).toBe("knowledge");
  expect(first.knowledge_basis).toBe("mixed");
  expect(String(first.answer)).toContain("学习路线");
  expect((first.citations as unknown[]).length).toBeGreaterThan(0);
  const firstIds = (first.assistant_state as { candidate_repository_ids: string[] }).candidate_repository_ids;
  expect(firstIds.length).toBeGreaterThan(0);
  await expect(page.getByText("模式：教学", { exact: true })).toBeVisible();
  await expect(page.getByText("来源：通用知识 + 项目证据", { exact: true })).toBeVisible();

  const secondPromise = page.waitForResponse((response) => response.request().postData()?.includes("在刚才推荐的项目里") === true);
  await submit(page, "在刚才推荐的项目里，我应该先学哪个，为什么？");
  const second = parseSse(await (await secondPromise).text()).at(-1)?.data || {};
  expect(second.assistant_mode).toBe("project_follow_up");
  expect((second.input_route as { candidate_scope: string; retrieval_performed: boolean }).candidate_scope).toBe("previous_candidates");
  expect((second.input_route as { retrieval_performed: boolean }).retrieval_performed).toBe(true);
  const secondIds = (second.assistant_state as { candidate_repository_ids: string[] }).candidate_repository_ids;
  expect(secondIds.length).toBeGreaterThan(0);
  expect(secondIds.every((id) => firstIds.includes(id))).toBe(true);

  const secondBody = bodies[1] || {};
  expect(Object.keys(secondBody).sort()).toEqual(["limit", "mode", "q", "state"]);
  expect((secondBody.state as { candidate_repository_ids: string[] }).candidate_repository_ids).toEqual(firstIds);
  const serialized = JSON.stringify(secondBody);
  for (const forbidden of ["citations", "evidence", "prompt_context", "contexts", "answer"]) expect(serialized).not.toContain(`\"${forbidden}\"`);

  const thirdPromise = page.waitForResponse((response) => response.request().postData()?.includes("重新搜索适合 Python 的项目") === true);
  await submit(page, "重新搜索适合 Python 的项目");
  const third = parseSse(await (await thirdPromise).text()).at(-1)?.data || {};
  expect(third.assistant_mode).toBe("project_search");
  expect((third.input_route as { candidate_scope: string }).candidate_scope).toBe("archive");
  expect((third.input_route as { retrieval_performed: boolean }).retrieval_performed).toBe(true);
  expect((third.input_route as { requirements: Array<{ field: string; value: string }> }).requirements).toContainEqual(
    expect.objectContaining({ field: "language", value: "Python" }),
  );
});

test("正交能力冲突不能成为 eligible 或首选", async ({ page }) => {
  const result = await postJson(page, {
    q: "必须不依赖外部模型 API",
    context: {
      previous_user_goal: "找 Python 多 Agent 编排项目",
      candidate_repository_ids: ["eval/agent-orchestrator"],
      primary_repository_id: "eval/agent-orchestrator",
      mode: "hybrid",
      resumable: true,
    },
    mode: "hybrid",
    model: "local-hash-v1",
    limit: 3,
    auto_build: true,
  });
  expect(result.answer_mode).toBe("no_match");
  expect(result.recommendations).toHaveLength(1);
  expect(result.recommendations[0].eligibility).toBe("rejected");
  expect(result.recommendations.some((item: { eligibility: string }) => item.eligibility === "eligible")).toBe(false);
  expect(result.recommendations[0].requirement_evaluations[0].status).toBe("unmet");
});
