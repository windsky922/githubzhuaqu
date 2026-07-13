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

test("序号追问只提交最小上下文并只检索第二个候选", async ({ page }) => {
  const bodies: Array<Record<string, unknown>> = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname !== "/v1/rag/ask/stream") return;
    const body = request.postDataJSON();
    if (body && typeof body === "object") bodies.push(body as Record<string, unknown>);
  });

  await submit(page, "工作流 自动化");
  await expect(page.locator(".answer-status")).toHaveCount(1);
  const responsePromise = page.waitForResponse((response) => {
    if (new URL(response.url()).pathname !== "/v1/rag/ask/stream") return false;
    return response.request().postData()?.includes("第二个呢") === true;
  });
  await submit(page, "第二个呢");
  const response = await responsePromise;
  const events = parseSse(await response.text());
  await expect(page.locator(".answer-status")).toHaveCount(2);

  const secondBody = bodies.at(-1) || {};
  const context = secondBody.context as Record<string, unknown>;
  expect(Object.keys(context).sort()).toEqual([
    "candidate_repository_ids",
    "mode",
    "previous_user_goal",
    "primary_repository_id",
    "resumable",
  ]);
  const serialized = JSON.stringify(secondBody);
  for (const forbidden of ["assistant", "citations", "evidence", "prompt_context"]) expect(serialized).not.toContain(forbidden);

  const expected = (context.candidate_repository_ids as string[])[1];
  const final = events.at(-1)?.data || {};
  expect((final.input_route as { selected_repository_ids: string[] }).selected_repository_ids).toEqual([expected]);
  expect((final.recommendations as Array<{ full_name: string }>).map((item) => item.full_name)).toEqual([expected]);
  await expect(page.locator(".assistant-message").last().getByText(expected, { exact: true }).first()).toBeVisible();
});

test("正交能力冲突不能成为 eligible 或首选", async ({ page }) => {
  const result = await postJson(page, {
    q: "不要云 API",
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
