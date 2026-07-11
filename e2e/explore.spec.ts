import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.clear());
});

test("项目筛选分页并限制最多三个对比项目", async ({ page }) => {
  await page.goto("/app/#/explore?api=1");
  await expect(page.getByText("1-50 / 55")).toBeVisible();
  await page.getByRole("button", { name: "下一页" }).click();
  await expect(page.getByText("第 2 / 2 页")).toBeVisible();
  await expect(page.getByText("fixture/project-51", { exact: true })).toBeVisible();

  const addButtons = page.getByRole("button", { name: "加入对比" });
  await expect(addButtons).toHaveCount(5);
  for (let index = 0; index < 3; index += 1) await addButtons.nth(index).click();
  await expect(page.getByRole("link", { name: "对比 3/3" })).toBeVisible();
  await expect(page.getByRole("button", { name: "加入对比" })).toHaveCount(2);
  for (const button of await page.getByRole("button", { name: "加入对比" }).all()) await expect(button).toBeDisabled();

  await page.getByRole("link", { name: "对比 3/3" }).click();
  await expect(page.getByRole("heading", { name: "项目对比" })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "fixture/project-51" })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "fixture/project-53" })).toBeVisible();
  await expect(page.getByText("固定对比数据仅用于浏览器回归。")).toBeVisible();
});
