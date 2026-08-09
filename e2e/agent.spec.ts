import { expect, test, type Page } from "@playwright/test";

type SseEvent = { event: string; data: Record<string, unknown> };

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
