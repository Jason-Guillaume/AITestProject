/**
 * AITesta：无头登录（可选图形验证码 + 后端 ddddocr 识别接口）
 *
 * 环境变量：
 * - UI_BASE_URL：前端基址（与 playwright.config 一致）
 * - API_BASE_URL：后端 API 根，如 http://127.0.0.1:8000/api
 * - E2E_USERNAME / E2E_PASSWORD：已存在账号
 * - CAPTCHA_OCR_SECRET：须与 Django CAPTCHA_OCR_SECRET 一致，且已 pip install ddddocr
 *
 * 流程：拉取验证码 → POST /user/captcha/recognize/ → 带 captcha 字段登录
 */
import { test, expect } from '@playwright/test'

const apiBase = (process.env.API_BASE_URL || 'http://127.0.0.1:8000/api').replace(/\/$/, '')
const ocrSecret = process.env.CAPTCHA_OCR_SECRET || ''
const username = process.env.E2E_USERNAME || ''
const password = process.env.E2E_PASSWORD || ''

test('headless login with captcha via backend ddddocr', async ({ request }) => {
  test.skip(!username || !password, '请设置 E2E_USERNAME / E2E_PASSWORD')
  test.skip(!ocrSecret, '请设置 CAPTCHA_OCR_SECRET 与后端一致并安装 ddddocr')

  const cap = await request.get(`${apiBase}/user/captcha/`)
  expect(cap.ok()).toBeTruthy()
  const capJson = await cap.json()
  expect(capJson.code).toBe(200)
  const uuid = capJson.data?.uuid as string
  const image = capJson.data?.image as string
  expect(uuid).toBeTruthy()
  expect(image).toContain('base64')

  const ocrRes = await request.post(`${apiBase}/user/captcha/recognize/`, {
    headers: { 'X-Captcha-Ocr-Secret': ocrSecret },
    json: { image },
  })
  expect(ocrRes.ok(), await ocrRes.text()).toBeTruthy()
  const ocrJson = await ocrRes.json()
  expect(ocrJson.code).toBe(200)
  const captchaText = String(ocrJson.data?.text || '').trim()
  expect(captchaText.length).toBeGreaterThanOrEqual(3)

  const loginRes = await request.post(`${apiBase}/user/login/`, {
    json: {
      username,
      password,
      captcha_code: captchaText,
      captcha_uuid: uuid,
    },
  })
  expect(loginRes.ok(), await loginRes.text()).toBeTruthy()
  const loginJson = await loginRes.json()
  expect(loginJson.code).toBe(200)
  expect(loginJson.data?.token).toBeTruthy()
})
