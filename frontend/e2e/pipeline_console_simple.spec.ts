/**
 * 轻量校验：流水线详情页渲染控制台（依赖 playwright.config 的 baseURL）。
 */
import { test, expect } from '@playwright/test'

test('pipeline console renders', async ({ page }) => {
  const pipelineId = process.env.E2E_PIPELINE_ID || '1'
  await page.goto(`/pipelines/${pipelineId}`)

  await expect(page.locator('.pipeline-console')).toBeVisible({ timeout: 15_000 })
  await expect(page.locator('.pipeline-console .pc-panel')).toBeVisible()
})
