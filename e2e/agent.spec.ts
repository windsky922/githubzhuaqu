import { expect, test, type Page } from "@playwright/test";

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
  await expect(page.getByText("草稿生成中，等待证据质量校验")).toBeVisible();
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
  await expect(page.getByText("许可证=MIT", { exact: true })).toBeVisible();
  await expect(page.getByText("当前归档内最匹配候选")).toHaveCount(0);
});

test("拒答和模型降级使用独立状态", async ({ page }) => {
  await submit(page, "证据不足");
  await expect(page.getByText("当前归档没有足够证据")).toBeVisible();
  await page.reload();
  await submit(page, "模型降级");
  await expect(page.getByText("已切换为证据约束结论")).toBeVisible();
  await expect(page.getByText("已采用保守结论")).toBeVisible();
});
