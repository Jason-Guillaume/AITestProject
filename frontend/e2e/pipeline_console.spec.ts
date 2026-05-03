/**
 * 流水线控制台：无头打开前端路由，校验 Cyberpunk 控制台容器存在。
 * 完整「验证码 + ddddocr 后端」登录见 aitea_login.spec.ts。
 */
import { test, expect } from '@playwright/test'

test('pipeline console shell renders', async ({ page }) => {
  const pipelineId = process.env.E2E_PIPELINE_ID || '1'
  await page.goto(`/pipelines/${pipelineId}`)

  const box = page.locator('.pipeline-console')
  await expect(box).toBeVisible({ timeout: 30_000 })
  await expect(box.locator('.pc-panel')).toBeVisible()
})
