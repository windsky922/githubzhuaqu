import { expect, test } from "@playwright/test";

const legacyKey = "github_weekly_admin_token";
const testCredential = "e2e-admin-memory-only-credential";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(([key, credential]) => {
    window.localStorage.setItem(key, credential);
    window.sessionStorage.setItem(key, credential);
  }, [legacyKey, testCredential]);
});

test("管理口令只保留在当前页面内存并通过请求头发送", async ({ page }) => {
  const consoleMessages: string[] = [];
  page.on("console", message => consoleMessages.push(message.text()));

  await page.goto(`/admin.html?api=0&admin_token=${encodeURIComponent(testCredential)}&view=security`);

  await expect(page).toHaveURL(/admin\.html\?api=0&view=security$/);
  const input = page.locator("[data-admin-auth-input]");
  await expect(input).toBeVisible();
  await expect(input).toHaveAttribute("type", "password");
  await expect(input).toHaveValue("");
  await expect(page.locator("[data-admin-auth-status]")).toContainText("旧链接中的管理口令已忽略");
  await expect(page.locator("[data-admin-auth-status]")).toContainText("可能已进入访问日志");
  await expect(page.locator("[data-admin-auth-status]")).toContainText("立即轮换 ADMIN_API_TOKEN");
  await expect.poll(() => page.evaluate(key => ({
    local: window.localStorage.getItem(key),
    session: window.sessionStorage.getItem(key),
  }), legacyKey)).toEqual({ local: null, session: null });

  let probeRequests = 0;
  let probeUrl = "";
  let probeHeader = "";
  await page.route("**/__admin-auth-probe", async route => {
    probeRequests += 1;
    probeUrl = route.request().url();
    probeHeader = (await route.request().allHeaders())["x-admin-token"] || "";
    await route.fulfill({ status: 204, body: "" });
  });

  const missing = await page.evaluate(async () => {
    try {
      await fetch("/__admin-auth-probe", {
        method: "POST",
        headers: window.GitHubWeeklyAdminAuth.writeHeaders(),
        body: "{}",
      });
      return { code: "", message: "" };
    } catch (error) {
      const value = error as Error & { code?: string };
      return { code: value.code || "", message: value.message };
    }
  });
  expect(missing.code).toBe("admin_token_required");
  expect(missing.message).not.toContain(testCredential);
  expect(probeRequests).toBe(0);

  await input.fill(testCredential);
  await page.evaluate(async () => {
    await fetch("/__admin-auth-probe", {
      method: "POST",
      headers: window.GitHubWeeklyAdminAuth.writeHeaders(),
      body: "{}",
    });
  });
  expect(probeRequests).toBe(1);
  expect(probeHeader).toBe(testCredential);
  expect(probeUrl).not.toContain("admin_token");
  expect(probeUrl).not.toContain(testCredential);
  expect(await page.evaluate(key => ({
    local: window.localStorage.getItem(key),
    session: window.sessionStorage.getItem(key),
  }), legacyKey)).toEqual({ local: null, session: null });

  await page.evaluate(() => window.GitHubWeeklyAdminAuth.handleResponse({ status: 401 }));
  await expect(input).toHaveValue("");
  await expect(page.locator("[data-admin-auth-status]")).toContainText("管理口令无效");

  await input.fill(testCredential);
  await page.reload();
  await expect(page.locator("[data-admin-auth-input]")).toHaveValue("");
  expect(consoleMessages.join("\n")).not.toContain(testCredential);
});

declare global {
  interface Window {
    GitHubWeeklyAdminAuth: {
      handleResponse(response: { status: number }): void;
      writeHeaders(): Record<string, string>;
    };
  }
}
