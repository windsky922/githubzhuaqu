import { expect, test } from "@playwright/test";

test.use({ trace: "off" });

const testToken = ["p0", "10", "real", "e2e", "admin"].join("-");

test.beforeEach(async ({ context }) => {
  await context.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if ((url.protocol === "http:" || url.protocol === "https:") && url.hostname !== "127.0.0.1") {
      await route.abort("blockedbyclient");
      return;
    }
    await route.continue();
  });
});

test("管理口令只经请求头创建临时 planned 任务", async ({ page }) => {
  const requests: Array<{ url: string; token: string }> = [];
  page.on("request", async (request) => {
    if (new URL(request.url()).pathname !== "/v1/dev-context/index-plan") return;
    requests.push({
      url: request.url(),
      token: (await request.allHeaders())["x-admin-token"] || "",
    });
  });

  await page.goto("/admin.html?api=1&admin_token=ignored-legacy-value");
  await expect(page).not.toHaveURL(/admin_token/);
  await expect(page.getByTestId("admin-token-status")).toContainText("可能已进入访问日志");

  const missing = await page.evaluate(async () => {
    try {
      await fetch("/v1/dev-context/index-plan", {
        method: "POST",
        headers: window.GitHubWeeklyAdminAuth.writeHeaders(),
        body: JSON.stringify({ run_checks: false, requested_by: "real-e2e" }),
      });
      return "sent";
    } catch (error) {
      return String((error as Error & { code?: string }).code || "");
    }
  });
  expect(missing).toBe("admin_token_required");
  expect(requests).toHaveLength(0);

  await page.getByTestId("admin-token-input").fill("wrong-test-token");
  const invalidStatus = await page.evaluate(async () => {
    const response = await fetch("/v1/dev-context/index-plan?admin_token=p0-10-real-e2e-admin", {
      method: "POST",
      headers: window.GitHubWeeklyAdminAuth.writeHeaders(),
      body: JSON.stringify({ run_checks: false, requested_by: "real-e2e" }),
    });
    window.GitHubWeeklyAdminAuth.handleResponse(response);
    return response.status;
  });
  expect(invalidStatus).toBe(401);
  await expect(page.getByTestId("admin-token-input")).toHaveValue("");

  await page.getByTestId("admin-token-input").fill(testToken);
  const accepted = await page.evaluate(async () => {
    const response = await fetch("/v1/dev-context/index-plan", {
      method: "POST",
      headers: window.GitHubWeeklyAdminAuth.writeHeaders(),
      body: JSON.stringify({ run_checks: false, requested_by: "real-e2e", trigger_source: "playwright-real" }),
    });
    window.GitHubWeeklyAdminAuth.handleResponse(response);
    return { status: response.status, body: await response.json() };
  });
  expect(accepted.status).toBe(202);
  expect(accepted.body.planned_job_created).toBe(true);
  expect(accepted.body.status).toBe("planned");
  expect(requests).toHaveLength(2);
  expect(requests[0].url).toContain("admin_token=");
  expect(requests[0].token).toBe("wrong-test-token");
  expect(requests[1].url).not.toContain("admin_token");
  expect(requests[1].token).toBe(testToken);
  expect(await page.evaluate(() => localStorage.getItem("github_weekly_admin_token"))).toBeNull();
  expect(await page.evaluate(() => sessionStorage.getItem("github_weekly_admin_token"))).toBeNull();
});

declare global {
  interface Window {
    GitHubWeeklyAdminAuth: {
      handleResponse(response: Response): Response;
      writeHeaders(): Record<string, string>;
    };
  }
}
