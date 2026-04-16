import { expect, test } from "@playwright/test";

function mustEnv(name: string): string {
  const v = (process.env[name] || "").trim();
  if (!v) throw new Error(`Missing env ${name}. Please set it before running UI smoke tests.`);
  return v;
}

test("ui smoke: login and open key pages", async ({ page, baseURL }) => {
  const username = mustEnv("TEST_API_USERNAME");
  const password = mustEnv("TEST_API_PASSWORD");

  await page.goto("/login", { waitUntil: "domcontentloaded" });

  await page.getByPlaceholder("用户名").fill(username);
  await page.getByPlaceholder("密码").fill(password);
  await page.getByRole("button", { name: "登录" }).click();

  await expect(page).toHaveURL(/\/dashboard(\b|\/|\?|#)/);
  await expect(page.getByText("测试执行情况")).toBeVisible();

  const routes = ["/projects", "/test-plan", "/test-case/api"];
  for (const r of routes) {
    await page.goto(r, { waitUntil: "domcontentloaded" });
    await expect(page).not.toHaveURL(/\/login(\b|\/|\?|#)/);
    await expect(page).toHaveURL(new RegExp(`${escapeRegExp(baseURL || "")}.*${escapeRegExp(r)}`));
  }
});

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

