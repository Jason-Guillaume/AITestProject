/**
 * Web UI 工作台（/script-hub/webui）模块级 E2E：登录后校验布局、脚本中心入口、工作台关键控件。
 *
 * 前置：前端可访问（playwright.config 默认 UI_BASE_URL=http://127.0.0.1:4173，需先 `npm run build && npm run preview`）。
 * 凭据：TEST_API_USERNAME / TEST_API_PASSWORD；未设置时本 describe 内用例全部 skip。
 */
import { expect, test } from "@playwright/test";

const hasCreds =
  Boolean((process.env.TEST_API_USERNAME || "").trim()) && Boolean((process.env.TEST_API_PASSWORD || "").trim());

test.describe("WebUI 工作台模块", () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!hasCreds, "需要 TEST_API_USERNAME 与 TEST_API_PASSWORD");
    const username = (process.env.TEST_API_USERNAME || "").trim();
    const password = (process.env.TEST_API_PASSWORD || "").trim();
    await page.goto("/login", { waitUntil: "domcontentloaded" });
    await page.getByPlaceholder("用户名").fill(username);
    await page.getByPlaceholder("密码").fill(password);
    await page.getByRole("button", { name: "登录" }).click();
    await expect(page).toHaveURL(/\/dashboard(\b|\/|\?|#)/, { timeout: 30_000 });
  });

  test("脚本执行中心页可访问", async ({ page }) => {
    await page.goto("/script-hub", { waitUntil: "domcontentloaded" });
    await expect(page).not.toHaveURL(/\/login(\b|\/|\?|#)/);
    await expect(page.locator(".script-hub-container")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "脚本执行中心" })).toBeVisible();
  });

  test("Web UI 工作台：面包屑、侧栏、导入与执行控制台", async ({ page }) => {
    await page.goto("/script-hub/webui", { waitUntil: "domcontentloaded" });
    await expect(page).not.toHaveURL(/\/login(\b|\/|\?|#)/);

    await expect(page.locator(".webui-workbench")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("Web UI 工作台")).toBeVisible();
    await expect(page.getByRole("button", { name: "导入脚本" })).toBeVisible();
    await expect(page.getByRole("radio", { name: "我的脚本" })).toBeVisible();
    await expect(page.getByRole("radio", { name: /回收站/ })).toBeVisible();

    await expect(page.locator("main.wb-main")).toBeVisible();
    await expect(page.getByText("执行控制台")).toBeVisible();
    await expect(page.getByRole("button", { name: "开始执行" })).toBeVisible();
  });
});
