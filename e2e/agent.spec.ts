import { expect, test, type Page } from "@playwright/test";

type SseEvent = { event: string; data: Record<string, unknown> };

function readinessFixture({
  status,
  knowledge,
  project,
  current,
  code,
  recovery,
}: {
  status: "ready" | "degraded" | "unavailable";
  knowledge: boolean;
  project: boolean;
  current: boolean;
  code: string;
  recovery: string;
}) {
  const component = (componentStatus: "ready" | "degraded" | "unavailable", componentCode: string) => ({
    status: componentStatus,
    code: componentCode,
    message: `${componentCode} fixture`,
    recovery: componentStatus === "ready" ? "" : recovery,
  });
  return {
    schema_version: 1,
    status,
    summary: `${code} readiness fixture.`,
    capabilities: {
      can_chat: knowledge || project,
      knowledge_available: knowledge,
      project_available: project,
      current_project_available: current,
    },
    components: {
      api: component("ready", "api_process_ready"),
      model: component(knowledge ? "ready" : "unavailable", knowledge ? "model_configured" : "model_not_configured"),
      snapshot: component(current ? "ready" : project ? "degraded" : "unavailable", current ? "snapshot_fresh" : code),
      rag: component(project ? "ready" : "unavailable", project ? "rag_read_only_ready" : "rag_source_unavailable"),
      access: component("ready", "assistant_read_only"),
    },
    issues: status === "ready" ? [] : [{ component: knowledge ? "snapshot" : "model", code, message: `${code} fixture`, recovery }],
  };
}

async function useReadiness(page: Page, getPayload: () => Record<string, unknown>) {
  await page.route("**/v1/assistant/readiness", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(getPayload()) });
  });
  await page.reload();
}

function parseSse(text: string): SseEvent[] {
  return text.split(/\r?\n\r?\n/).map((block) => block.trim()).filter(Boolean).map((block) => {
    const lines = block.split(/\r?\n/);
    const event = lines.find((line) => line.startsWith("event:"))?.slice(6).trim() || "message";
    const payload = lines.filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trimStart()).join("\n");
    return { event, data: JSON.parse(payload) as Record<string, unknown> };
  });
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.clear());
  await page.goto("/app/#/agent?api=1");
});

async function submit(page: Page, question: string) {
  await page.getByLabel("输入项目需求").fill(question);
  await page.getByRole("button", { name: "发送需求" }).click();
}

test("长流式输出完成后输入区仍固定可用", async ({ page }) => {
  await submit(page, "长流式回答");
  await expect(page.getByText("证据已校验", { exact: true })).toBeVisible();
  await expect(page.getByText("当前归档内最匹配候选")).toBeVisible();
  await expect(page.getByText("fixture/agent-platform", { exact: true })).toBeVisible();
  const composer = page.locator(".composer-wrap");
  await expect(composer).toBeVisible();
  const box = await composer.boundingBox();
  const viewport = page.viewportSize();
  expect(box).not.toBeNull();
  expect(viewport).not.toBeNull();
  expect((box?.y || 0) + (box?.height || 0)).toBeLessThanOrEqual((viewport?.height || 0) + 2);
  expect(box?.y || 0).toBeGreaterThan((viewport?.height || 0) * 0.5);
});

test("澄清轮不显示项目卡或质量失败", async ({ page }) => {
  await submit(page, "需要澄清");
  await expect(page.locator(".answer-status", { hasText: "需要补充需求" })).toBeVisible();
  await expect(page.getByText("请补充你希望继续分析的具体项目或完整需求。")).toBeVisible();
  await expect(page.locator(".project-card")).toHaveCount(0);
  await expect(page.getByText("质量校验未通过")).toHaveCount(0);
});

test("无匹配轮展示拒绝候选和硬约束原因", async ({ page }) => {
  await submit(page, "没有匹配");
  await expect(page.getByText("硬约束下无匹配")).toBeVisible();
  await expect(page.getByText("fixture/rejected", { exact: true })).toBeVisible();
  await expect(page.locator(".project-card").getByText("许可证=MIT", { exact: true })).toBeVisible();
  await expect(page.getByText("当前归档内最匹配候选")).toHaveCount(0);
});

test("可将硬约束一键放宽后沿用该轮上下文重试", async ({ page }) => {
  await submit(page, "没有匹配");
  const editor = page.getByLabel("检索条件编辑器");
  await expect(editor.getByText("许可证=MIT", { exact: true })).toBeVisible();
  await editor.getByRole("button", { name: "一键放宽并重试" }).click();
  await expect(page.getByText("使用这些条件重新搜索：偏好许可证=MIT", { exact: true })).toBeVisible();
  await expect(page.getByText("当前归档内最匹配候选")).toBeVisible();
});

test("拒答和模型降级使用独立状态", async ({ page }) => {
  await submit(page, "证据不足");
  await expect(page.getByText("当前归档没有足够证据")).toBeVisible();
  await page.reload();
  await submit(page, "模型降级");
  await expect(page.getByText("已切换为证据约束结论")).toBeVisible();
  await expect(page.getByText("已采用保守结论")).toBeVisible();
});

test("AI Agent 学习、候选追问和显式重置保持作用域", async ({ page }) => {
  const requestBodies: Array<Record<string, unknown>> = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname !== "/v1/assistant/turn/stream") return;
    const body = request.postDataJSON();
    if (body && typeof body === "object") requestBodies.push(body as Record<string, unknown>);
  });

  await expect(page.locator(".connection-status")).toHaveText("本机依赖已就绪");

  const firstResponse = page.waitForResponse((response) => new URL(response.url()).pathname === "/v1/assistant/turn/stream");
  await submit(page, "我想学习 AI Agent 开发方向的知识。");
  const firstFinal = parseSse(await (await firstResponse).text()).at(-1)?.data || {};
  expect(firstFinal.assistant_mode).toBe("knowledge");
  expect(firstFinal.knowledge_basis).toBe("mixed");
  expect(String(firstFinal.answer)).toContain("学习路线");
  const firstIds = (firstFinal.assistant_state as { candidate_repository_ids: string[] }).candidate_repository_ids;
  expect(firstIds.length).toBeGreaterThan(0);

  const secondResponse = page.waitForResponse((response) => response.request().postData()?.includes("在刚才推荐的项目里") === true);
  await submit(page, "在刚才推荐的项目里，我应该先学哪个，为什么？");
  const secondFinal = parseSse(await (await secondResponse).text()).at(-1)?.data || {};
  expect(secondFinal.assistant_mode).toBe("project_follow_up");
  expect((secondFinal.input_route as { candidate_scope: string; retrieval_performed: boolean }).candidate_scope).toBe("previous_candidates");
  expect((secondFinal.input_route as { retrieval_performed: boolean }).retrieval_performed).toBe(true);
  const secondIds = (secondFinal.assistant_state as { candidate_repository_ids: string[] }).candidate_repository_ids;
  expect(secondIds.length).toBeGreaterThan(0);
  expect(secondIds.every((id) => firstIds.includes(id))).toBe(true);

  const secondBody = requestBodies[1];
  expect(Object.keys(secondBody).sort()).toEqual(["limit", "mode", "q", "state"]);
  expect((secondBody.state as { candidate_repository_ids: string[] }).candidate_repository_ids).toEqual(firstIds);
  for (const forbidden of ["citations", "evidence", "prompt_context", "contexts", "answer"]) {
    expect(JSON.stringify(secondBody)).not.toContain(`\"${forbidden}\"`);
  }

  const thirdResponse = page.waitForResponse((response) => response.request().postData()?.includes("重新搜索适合 Python 的项目") === true);
  await submit(page, "重新搜索适合 Python 的项目");
  const thirdFinal = parseSse(await (await thirdResponse).text()).at(-1)?.data || {};
  expect(thirdFinal.assistant_mode).toBe("project_search");
  expect((thirdFinal.input_route as { candidate_scope: string }).candidate_scope).toBe("archive");
  const thirdIds = (thirdFinal.assistant_state as { candidate_repository_ids: string[] }).candidate_repository_ids;
  expect(thirdIds.some((id) => !secondIds.includes(id))).toBe(true);
});

test("无模型时只开放项目证据入口", async ({ page }) => {
  const payload = readinessFixture({
    status: "degraded", knowledge: false, project: true, current: true,
    code: "model_not_configured", recovery: "配置 KIMI_API_KEY 与 KIMI_MODEL 后重新检查。",
  });
  await useReadiness(page, () => payload);

  await expect(page.locator(".readiness-notice")).toContainText("通用教学不可用");
  await expect(page.getByRole("button", { name: "我想学习 AI Agent 开发方向的知识。" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "推荐适合入门和实践的 AI Agent 项目" })).toBeEnabled();
  await expect(page.getByLabel("输入项目需求")).toBeEnabled();
});

test("无 snapshot 时只开放通用教学入口", async ({ page }) => {
  const payload = readinessFixture({
    status: "degraded", knowledge: true, project: false, current: false,
    code: "missing_verified_weekly_snapshot", recovery: "配置 verified weekly snapshot。",
  });
  await useReadiness(page, () => payload);

  await expect(page.locator(".readiness-notice")).toContainText("项目证据不可用");
  await expect(page.getByRole("button", { name: "我想学习 AI Agent 开发方向的知识。" })).toBeEnabled();
  await expect(page.getByRole("button", { name: "推荐适合入门和实践的 AI Agent 项目" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "重新搜索适合 Python 的项目" })).toBeDisabled();
  await expect(page.getByLabel("输入项目需求")).toBeEnabled();
});

test("stale snapshot 保留历史项目检索但禁用当前项目推荐", async ({ page }) => {
  const payload = readinessFixture({
    status: "degraded", knowledge: true, project: true, current: false,
    code: "snapshot_stale", recovery: "刷新三层 freshness attestation。",
  });
  await useReadiness(page, () => payload);

  await expect(page.locator(".readiness-notice")).toContainText("当前项目事实不可用");
  await expect(page.getByRole("button", { name: "推荐适合入门和实践的 AI Agent 项目" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "重新搜索适合 Python 的项目" })).toBeEnabled();
  await expect(page.getByLabel("输入项目需求")).toBeEnabled();
});

test("两条回答链均不可用时禁用输入并支持重新检查", async ({ page }) => {
  let payload = readinessFixture({
    status: "unavailable", knowledge: false, project: false, current: false,
    code: "dependencies_unavailable", recovery: "恢复模型或项目证据链。",
  });
  await useReadiness(page, () => payload);

  await expect(page.locator(".readiness-notice")).toContainText("助手不可用");
  await expect(page.getByLabel("输入项目需求")).toBeDisabled();

  payload = readinessFixture({
    status: "ready", knowledge: true, project: true, current: true,
    code: "ready", recovery: "",
  });
  await page.getByRole("button", { name: "重新检查" }).click();
  await expect(page.locator(".connection-status")).toHaveText("本机依赖已就绪");
  await expect(page.getByLabel("输入项目需求")).toBeEnabled();
});

test("五轮教学通过 schema-v2 提纲连续解析指代", async ({ page }) => {
  const requestBodies: Array<Record<string, unknown>> = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname !== "/v1/assistant/turn/stream") return;
    const body = request.postDataJSON();
    if (body && typeof body === "object") requestBodies.push(body as Record<string, unknown>);
  });
  const runTurn = async (question: string) => {
    const responsePromise = page.waitForResponse((response) =>
      new URL(response.url()).pathname === "/v1/assistant/turn/stream"
      && response.request().postData()?.includes(question) === true);
    await submit(page, question);
    const final = parseSse(await (await responsePromise).text()).at(-1)?.data || {};
    await expect(page.getByLabel("输入项目需求")).toBeEnabled();
    return final;
  };

  const first = await runTurn("我想学习 AI Agent 的核心组成");
  const second = await runTurn("把第三点展开");
  const third = await runTurn("继续，并举例");
  const fourth = await runTurn("换种说法");
  const fifth = await runTurn("回到第一点");
  const contexts = [first, second, third, fourth, fifth].map((result) =>
    (result.assistant_state as { knowledge_context: { outline: Array<{ id: string }>; focus_id: string } }).knowledge_context);

  expect([first, second, third, fourth, fifth].every((result) => result.assistant_mode === "knowledge")).toBe(true);
  expect(contexts[0].outline.map((item) => item.id)).toEqual(["k1", "k2", "k3"]);
  expect(contexts.map((context) => context.focus_id)).toEqual(["", "k3", "k3", "k3", "k1"]);
  expect(requestBodies).toHaveLength(5);
  for (const body of requestBodies.slice(1)) {
    expect(Object.keys(body).sort()).toEqual(["limit", "mode", "q", "state"]);
    const serialized = JSON.stringify(body);
    for (const forbidden of ["citations", "evidence", "prompt_context", "contexts", "sections", "answer"]) {
      expect(serialized).not.toContain(`\"${forbidden}\"`);
    }
  }
  expect((requestBodies[1].state as { schema_version: number }).schema_version).toBe(2);
  expect((requestBodies[4].state as { knowledge_context: { focus_id: string } }).knowledge_context.focus_id).toBe("k3");
});

test("本机历史默认关闭，开启后只保存最小展示字段，关闭即删除", async ({ page }) => {
  const storageKey = "github_weekly_agent_assistant_conversations_v2";
  expect(await page.evaluate((key) => window.localStorage.getItem(key), storageKey)).toBeNull();
  const historyMenu = page.getByRole("button", { name: "打开对话历史" });
  if (await historyMenu.isVisible()) await historyMenu.click();
  const visibleHistoryToggle = page.locator("label.history-toggle:visible input[type=checkbox]");
  await visibleHistoryToggle.check();
  const closeHistory = page.getByRole("button", { name: "关闭对话历史" });
  if (await closeHistory.isVisible()) await closeHistory.click();
  await submit(page, "长流式回答");
  await expect(page.locator(".answer-status")).toHaveCount(1);
  const stored = await page.evaluate((key) => window.localStorage.getItem(key), storageKey);
  expect(stored).not.toBeNull();
  for (const forbidden of ["citations", "evidence", "prompt_context", "contexts", "model_status", "error"]) {
    expect(stored).not.toContain(`\"${forbidden}\"`);
  }
  expect(stored).not.toContain("fixture:chunk:1");
  expect(stored).not.toContain("固定可引用证据");
  expect(stored).toContain("用于验证长流式输出布局");
  if (await historyMenu.isVisible()) await historyMenu.click();
  await visibleHistoryToggle.uncheck();
  expect(await page.evaluate((key) => window.localStorage.getItem(key), storageKey)).toBeNull();
});
