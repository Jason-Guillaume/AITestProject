import { ref, computed, watch, type Ref } from 'vue'
import Prism from 'prismjs'
import 'prismjs/components/prism-json'
import 'prismjs/components/prism-markup'
import 'prismjs/components/prism-markup-templating'
import 'prismjs/components/prism-php'
import { runApiCaseApi, aiFillTestDataApi, previewRunApiCaseApi } from '@/api/testcase'
import { useCurrentEnvironment } from '@/composables/useCurrentEnvironment'
import {
  relativizeApiUrlIfUnderBase,
  resolveApiUrlWithBase,
} from '@/utils/resolveApiUrlWithBase'
import { getPlansApi, createReportApi, updateReportApi } from '@/api/execution'
import type { TestCaseRow } from '@/types/testcase'
import type { ApiVariableExtractRule } from '@/types/testcase'

export interface ExecutionLogLike {
  id?: number
  trace_id?: string | null
  request_url?: string
  request_method?: string
  request_headers?: Record<string, string>
  request_body?: string
  request_body_text?: string
  /** 执行时真实请求快照 method/url/headers/body */
  request_payload?: Record<string, unknown> | null
  response_status_code?: number | null
  response_body?: string
  response_body_text?: string
  /** 服务端返回摘要 status_code/headers/body_raw/body_json 等 */
  response_payload?: Record<string, unknown> | null
  duration_ms?: number | null
  response_time_ms?: number | null
  assertion_results?: Array<{ name?: string; passed?: boolean; detail?: string }>
  is_passed?: boolean
  execution_status?: string
  error_message?: string
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms))
}

function splitCurlArgs(raw: string): string[] {
  const s = String(raw || '').trim()
  const out: string[] = []
  let cur = ''
  let quote: '"' | "'" | '' = ''
  let escaped = false
  for (let i = 0; i < s.length; i += 1) {
    const ch = s[i]
    if (escaped) {
      cur += ch
      escaped = false
      continue
    }
    if (ch === '\\') {
      escaped = true
      continue
    }
    if (quote) {
      if (ch === quote) {
        quote = ''
      } else {
        cur += ch
      }
      continue
    }
    if (ch === '"' || ch === "'") {
      quote = ch as '"' | "'"
      continue
    }
    if (/\s/.test(ch)) {
      if (cur) {
        out.push(cur)
        cur = ''
      }
      continue
    }
    cur += ch
  }
  if (cur) out.push(cur)
  return out
}

function parseCurlCommand(raw: string): {
  method: string
  url: string
  headers: Record<string, string>
  body: unknown
} {
  const args = splitCurlArgs(raw)
  if (!args.length || String(args[0]).toLowerCase() !== 'curl') {
    throw new Error('请输入有效 cURL 命令（以 curl 开头）')
  }
  const headers: Record<string, string> = {}
  let url = ''
  let method = ''
  let bodyRaw = ''
  for (let i = 1; i < args.length; i += 1) {
    const t = args[i]
    const n = args[i + 1]
    if ((t === '-X' || t === '--request') && n) {
      method = String(n).toUpperCase()
      i += 1
      continue
    }
    if ((t === '-H' || t === '--header') && n) {
      const p = String(n)
      const idx = p.indexOf(':')
      if (idx > 0) {
        const k = p.slice(0, idx).trim()
        const v = p.slice(idx + 1).trim()
        if (k) headers[k] = v
      }
      i += 1
      continue
    }
    if ((t === '-d' || t === '--data' || t === '--data-raw' || t === '--data-binary') && n) {
      bodyRaw = String(n)
      i += 1
      continue
    }
    if (!t.startsWith('-') && /^https?:\/\//i.test(t)) {
      url = t
      continue
    }
  }
  if (!url) {
    throw new Error('cURL 中未识别到 URL')
  }
  if (!method) method = bodyRaw ? 'POST' : 'GET'
  let body: unknown = {}
  if (bodyRaw) {
    const trimmed = bodyRaw.trim()
    try {
      body = JSON.parse(trimmed)
    } catch {
      body = { _raw: trimmed }
    }
  }
  return { method, url, headers, body }
}

export const HTTP_STATUS_PHRASE: Record<number, string> = {
  200: 'OK',
  201: 'Created',
  204: 'No Content',
  400: 'Bad Request',
  401: 'Unauthorized',
  403: 'Forbidden',
  404: 'Not Found',
  422: 'Unprocessable Entity',
  500: 'Internal Server Error',
  502: 'Bad Gateway',
  503: 'Service Unavailable',
}

/** 日志行中展示的 path（含 query），便于对齐「/api/login」类示例 */
export function requestPathForConsoleLog(url: string): string {
  const u = (url || '').trim()
  if (!u) return '/'
  try {
    if (/^https?:\/\//i.test(u)) {
      const parsed = new URL(u)
      const p = `${parsed.pathname || '/'}${parsed.search || ''}`
      return p || '/'
    }
  } catch {
    /* ignore */
  }
  return u
}

/** 从 Body JSON 推断 AI 填充所需的字段描述 */
export function inferFieldsFromJsonText(jsonText: string) {
  const t = (jsonText || '').trim()
  if (!t) {
    return [
      { name: 'sample', type: 'string', description: '示例字符串字段' },
    ]
  }
  try {
    const o = JSON.parse(t)
    if (o && typeof o === 'object' && !Array.isArray(o)) {
      return Object.keys(o).map((name) => {
        const v = (o as Record<string, unknown>)[name]
        const type =
          typeof v === 'number'
            ? 'number'
            : typeof v === 'boolean'
              ? 'boolean'
              : 'string'
        return { name, type, description: `与 ${name} 相关的测试数据` }
      })
    }
    if (Array.isArray(o) && o.length && typeof o[0] === 'object' && o[0]) {
      return inferFieldsFromJsonText(JSON.stringify(o[0]))
    }
  } catch {
    /* ignore */
  }
  return [{ name: 'payload', type: 'string', description: '请求体主字段' }]
}

export function highlightJson(code: string): string {
  const raw = (code || '').trim() || '{}'
  try {
    const formatted = JSON.stringify(JSON.parse(raw), null, 2)
    return Prism.highlight(formatted, Prism.languages.json, 'json')
  } catch {
    return Prism.highlight(raw, Prism.languages.json, 'json')
  }
}

/** 响应体高亮：优先 JSON，其次 PHP / HTML，最后用 JSON 词法兜底（避免整段纯文本无样式） */
export function highlightResponseBody(code: string): { html: string; lang: string } {
  const raw = (code || '').trim()
  if (!raw) {
    return {
      html: Prism.highlight('{}', Prism.languages.json, 'json'),
      lang: 'json',
    }
  }

  try {
    const formatted = JSON.stringify(JSON.parse(raw), null, 2)
    return {
      html: Prism.highlight(formatted, Prism.languages.json, 'json'),
      lang: 'json',
    }
  } catch {
    /* 非 JSON：走下方语言探测 */
  }

  if (/^\s*<\?php/i.test(raw) || /^\s*<\?=/i.test(raw)) {
    return {
      html: Prism.highlight(raw, Prism.languages.php, 'php'),
      lang: 'php',
    }
  }

  if (/^\s*</.test(raw)) {
    return {
      html: Prism.highlight(raw, Prism.languages.markup, 'markup'),
      lang: 'markup',
    }
  }

  if (
    /\$[a-zA-Z_]\w*/.test(raw) ||
    /\b(function|echo|array)\s*\(/i.test(raw) ||
    /\bnamespace\s+/i.test(raw)
  ) {
    return {
      html: Prism.highlight(raw, Prism.languages.php, 'php'),
      lang: 'php',
    }
  }

  return {
    html: Prism.highlight(raw, Prism.languages.json, 'json'),
    lang: 'json',
  }
}

export function useApiExecuteConsole(caseRow: Ref<TestCaseRow | null | undefined>) {
  const { environmentId, baseUrl, loadEnvironments } = useCurrentEnvironment()
  const requestUrl = ref('')
  const requestMethod = ref('GET')
  const headersText = ref('{}')
  const bodyText = ref('{}')
  const expectedStatus = ref<number | null>(null)
  const extractionRules = ref<ApiVariableExtractRule[]>([])
  function normalizeExtractionRules(raw: unknown): ApiVariableExtractRule[] {
    if (!Array.isArray(raw)) return []
    return raw
      .map((item) => {
        if (!item || typeof item !== 'object') return null
        const row = item as Record<string, unknown>
        const sourceRaw = String(row.source ?? 'Body')
        return {
          variableName: String(row.variableName ?? '').trim(),
          source: sourceRaw === 'Header' ? 'Header' : 'Body',
          expression: String(row.expression ?? '').trim(),
          currentValue: String(row.currentValue ?? ''),
        } as ApiVariableExtractRule
      })
      .filter((item): item is ApiVariableExtractRule => !!item && !!item.variableName && !!item.expression)
  }


  const consoleLines = ref<string[]>([])
  const executionLog = ref<ExecutionLogLike | null>(null)
  /** run-api 未返回 ExecutionLog 时（如 axios 异常）记录 HTTP 状态，供弹窗徽章展示 */
  const lastErrorHttpStatus = ref<number | null>(null)
  const running = ref(false)
  const aiFilling = ref(false)
  const savingReport = ref(false)

  const plans = ref<Array<{ id: number; plan_name: string }>>([])
  const reportForm = ref({
    plan: null as number | null,
    report_name: '',
    environment: 'TEST',
  })

  const highlightedRequestPreview = computed(() => {
    try {
      const h = JSON.parse(headersText.value || '{}')
      const b = JSON.parse(bodyText.value || '{}')
      return highlightJson(JSON.stringify({ headers: h, body: b }))
    } catch {
      return highlightJson(
        JSON.stringify({
          headers: headersText.value,
          body: bodyText.value,
        }),
      )
    }
  })

  /** 丢弃过期的 reset（快速关开/切换用例时多个 await loadEnvironments 交错） */
  let resetFromRowSeq = 0

  const responseBodyPrism = computed(() => {
    const log = executionLog.value
    if (!log) {
      return { html: Prism.highlight('{}', Prism.languages.json, 'json'), lang: 'json' as const }
    }
    const text =
      log.response_body_text ??
      log.response_body ??
      (log.error_message || '')
    const s = typeof text === 'string' ? text.trim() : ''
    return highlightResponseBody(s || '{"empty":true}')
  })

  /** 先拉取环境列表再拼接 Base URL，避免弹窗早于顶栏环境选择器完成加载时出现「只有相对路径」 */
  async function resetFromRow() {
    const seq = ++resetFromRowSeq
    await loadEnvironments()
    if (seq !== resetFromRowSeq) return
    const row = caseRow.value
    if (!row) return
    const sc = String((row as TestCaseRow & { api_source_curl?: string }).api_source_curl || '').trim()
    if (sc) {
      try {
        applyCurlCommand(sc)
        expectedStatus.value =
          row.api_expected_status != null ? Number(row.api_expected_status) : null
        extractionRules.value = normalizeExtractionRules((row as TestCaseRow).api_extract_rules)
        const reconciled = String(requestUrl.value || '').trim()
        requestUrl.value = resolveApiUrlWithBase(
          baseUrl.value,
          relativizeApiUrlIfUnderBase(baseUrl.value, reconciled) || reconciled,
        )
        return
      } catch {
        /* cURL 无效时回退为库中 api_* */
      }
    }
    requestUrl.value = resolveApiUrlWithBase(
      baseUrl.value,
      String(row.api_url || '').trim(),
    )
    requestMethod.value = String(row.api_method || 'GET').toUpperCase() || 'GET'
    expectedStatus.value =
      row.api_expected_status != null ? Number(row.api_expected_status) : null
    const h = row.api_headers
    headersText.value = JSON.stringify(
      h && typeof h === 'object' ? { ...h } : {},
      null,
      2,
    )
    const b = row.api_body
    if (b && typeof b === 'object') {
      bodyText.value = JSON.stringify(b, null, 2)
    } else {
      const s = String(b ?? '').trim()
      if (!s) bodyText.value = '{}'
      else {
        try {
          bodyText.value = JSON.stringify(JSON.parse(s), null, 2)
        } catch {
          bodyText.value = JSON.stringify({ _legacy_text: s }, null, 2)
        }
      }
    }
    extractionRules.value = normalizeExtractionRules((row as TestCaseRow).api_extract_rules)
  }

  /** 挂载 / 切换用例 / 详情刷新后同步表单，避免沿用上一用例的空 {} 覆盖库内请求体 */
  watch(
    () => [caseRow.value?.id, caseRow.value?.update_time] as const,
    () => {
      if (caseRow.value?.id != null) void resetFromRow()
    },
    { immediate: true, flush: 'post' },
  )

  /** 切换执行环境时，用例里存的是相对路径则同步刷新展示 URL */
  watch(baseUrl, () => {
    const row = caseRow.value
    if (!row) return
    const raw = String(row.api_url || '').trim()
    if (!raw || /^https?:\/\//i.test(raw)) return
    requestUrl.value = resolveApiUrlWithBase(baseUrl.value, raw)
  })

  async function appendStreamLines(lines: string[]) {
    for (const line of lines) {
      await sleep(220 + Math.random() * 180)
      consoleLines.value = [...consoleLines.value, line]
    }
  }

  function parseHeaders(): Record<string, string> {
    const t = (headersText.value || '').trim()
    if (!t) return {}
    const o = JSON.parse(t) as Record<string, unknown>
    if (!o || typeof o !== 'object' || Array.isArray(o)) {
      throw new Error('Headers 须为 JSON 对象')
    }
    const out: Record<string, string> = {}
    for (const [k, v] of Object.entries(o)) {
      out[String(k)] = v == null ? '' : String(v)
    }
    return out
  }

  function parseBody(): unknown {
    const t = (bodyText.value || '').trim()
    if (!t) return {}
    return JSON.parse(t)
  }

  function applyCurlCommand(rawCurl: string) {
    const parsed = parseCurlCommand(rawCurl)
    requestMethod.value = parsed.method
    requestUrl.value = parsed.url
    headersText.value = JSON.stringify(parsed.headers || {}, null, 2)
    bodyText.value = JSON.stringify(parsed.body ?? {}, null, 2)
    return parsed
  }

  async function runAiFill(target: 'body' | 'headers' = 'body') {
    aiFilling.value = true
    try {
      const fields =
        target === 'body'
          ? inferFieldsFromJsonText(bodyText.value)
          : inferFieldsFromJsonText(headersText.value)
      const payload: Record<string, unknown> = { fields }
      const { data } = await aiFillTestDataApi(payload)
      const filled = (data as { data?: Record<string, unknown> })?.data
      if (!filled || typeof filled !== 'object') {
        throw new Error('AI 未返回有效数据')
      }
      if (target === 'body') {
        let base: Record<string, unknown> = {}
        try {
          base =
            (JSON.parse(bodyText.value || '{}') as Record<string, unknown>) || {}
        } catch {
          base = {}
        }
        bodyText.value = JSON.stringify({ ...base, ...filled }, null, 2)
      } else {
        let base: Record<string, unknown> = {}
        try {
          base =
            (JSON.parse(headersText.value || '{}') as Record<string, unknown>) ||
            {}
        } catch {
          base = {}
        }
        headersText.value = JSON.stringify({ ...base, ...filled }, null, 2)
      }
    } catch (e: unknown) {
      const rsp = (e as { response?: { status?: number; data?: { msg?: string } } })?.response
      const rawMsg =
        rsp?.data?.msg ||
        (e as Error)?.message ||
        'AI 填充失败'
      if (rsp?.status === 401) {
        throw new Error('登录已过期，请重新登录后再试 AI 填充')
      }
      throw new Error(typeof rawMsg === 'string' ? rawMsg : 'AI 填充失败')
    } finally {
      aiFilling.value = false
    }
  }

  async function runExecute() {
    const id = caseRow.value?.id
    if (!id) return
    let headersObj: Record<string, string>
    let bodyObj: unknown
    try {
      headersObj = parseHeaders()
    } catch {
      throw new Error('请求头 JSON 格式不正确')
    }
    try {
      bodyObj = parseBody()
    } catch {
      throw new Error('请求体 JSON 格式不正确')
    }

    running.value = true
    consoleLines.value = []
    executionLog.value = null
    lastErrorHttpStatus.value = null

    const pathLine = requestPathForConsoleLog(requestUrl.value)
    await appendStreamLines([`> 发送请求 [${requestMethod.value}] ${pathLine}...`])

    try {
      const payload: Record<string, unknown> = {
        api_url: requestUrl.value,
        api_method: requestMethod.value,
        api_expected_status: expectedStatus.value,
      }
      if (Object.keys(headersObj).length > 0) {
        payload.api_headers = headersObj
      }
      const bodyEmptyPlainObject =
        bodyObj &&
        typeof bodyObj === 'object' &&
        !Array.isArray(bodyObj) &&
        Object.keys(bodyObj as Record<string, unknown>).length === 0
      if (!bodyEmptyPlainObject) {
        payload.api_body = bodyObj
      }
      const eid = environmentId.value
      if (eid != null) {
        payload.environment_id = eid
      }
      const { data } = await runApiCaseApi(id, payload)
      const log = (data as { execution_log?: ExecutionLogLike })?.execution_log
      executionLog.value = log ?? null
      const ms = log?.duration_ms ?? log?.response_time_ms ?? null
      const code = log?.response_status_code
      const phrase =
        code != null ? HTTP_STATUS_PHRASE[code] || '' : ''
      const inner =
        code != null
          ? `[${code}${phrase ? ` ${phrase}` : ''}]`
          : '[—]'
      await appendStreamLines([
        `> 接收响应 ${inner}${ms != null ? ` 耗时 ${ms}ms` : ''}`,
        `> 断言结果: [${log?.is_passed ? 'PASS' : 'FAIL'}]`,
      ])
      return data
    } catch (e: unknown) {
      const ax = e as { response?: { status?: number; data?: { msg?: string } } }
      const st = ax?.response?.status
      if (typeof st === 'number' && !Number.isNaN(st)) {
        lastErrorHttpStatus.value = st
      }
      const msg =
        ax?.response?.data?.msg ||
        (e as Error)?.message ||
        '请求失败'
      await appendStreamLines([
        '> 接收响应 [失败]',
        '> 断言结果: [FAIL]',
        `> ${msg}`,
      ])
      throw e
    } finally {
      running.value = false
    }
  }

  async function runPreviewResolved() {
    const id = caseRow.value?.id
    if (!id) throw new Error('缺少用例 ID')
    let headersObj: Record<string, string>
    let bodyObj: unknown
    try {
      headersObj = parseHeaders()
    } catch {
      throw new Error('请求头 JSON 格式不正确')
    }
    try {
      bodyObj = parseBody()
    } catch {
      throw new Error('请求体 JSON 格式不正确')
    }
    const payload: Record<string, unknown> = {
      api_url: requestUrl.value,
      api_method: requestMethod.value,
      api_expected_status: expectedStatus.value,
    }
    if (Object.keys(headersObj).length > 0) {
      payload.api_headers = headersObj
    }
    const bodyEmptyPlainObject =
      bodyObj &&
      typeof bodyObj === 'object' &&
      !Array.isArray(bodyObj) &&
      Object.keys(bodyObj as Record<string, unknown>).length === 0
    if (!bodyEmptyPlainObject) {
      payload.api_body = bodyObj
    }
    const eid = environmentId.value
    if (eid != null) payload.environment_id = eid
    const { data } = await previewRunApiCaseApi(id, payload)
    return data
  }

  /** 先 run-api（落库 ExecutionLog），再生成测试报告 */
  async function runExecuteAndSaveReport() {
    await runExecute()
    await saveReport()
  }

  /** 将当前表单合并为 PATCH 用例载荷（与列表编辑弹窗字段对齐） */
  function buildApiCasePatch(
    base: import('@/types/testcase').TestCaseRow,
    moduleId: number | null,
    sourceCurl?: string | null,
  ): Record<string, unknown> {
    if (!base?.id) throw new Error('缺少用例 ID')
    const headersObj = parseHeaders()
    const bodyObj = parseBody()
    const patch: Record<string, unknown> = {
      case_name: base.case_name,
      level: base.level,
      module: moduleId,
      test_type: String(base.test_type || 'api'),
      api_url: relativizeApiUrlIfUnderBase(baseUrl.value, requestUrl.value.trim()),
      api_method: requestMethod.value,
      api_headers: headersObj,
      api_body: bodyObj,
      api_expected_status: expectedStatus.value,
      api_extract_rules: normalizeExtractionRules(extractionRules.value),
    }
    if (sourceCurl !== undefined) {
      patch.api_source_curl = String(sourceCurl ?? '').trim()
    }
    return patch
  }

  async function loadPlans() {
    try {
      const { data } = await getPlansApi({ page_size: 500 })
      const rows = Array.isArray(data)
        ? data
        : data?.results && Array.isArray(data.results)
          ? data.results
          : []
      plans.value = rows.map((p: { id: number; plan_name: string }) => ({
        id: p.id,
        plan_name: p.plan_name,
      }))
    } catch {
      plans.value = []
    }
  }

  async function saveReport() {
    const log = executionLog.value
    if (!log) throw new Error('请先执行请求')
    if (!reportForm.value.plan) throw new Error('请选择关联测试计划')
    const name = (reportForm.value.report_name || '').trim()
    if (!name) throw new Error('请填写报告名称')

    savingReport.value = true
    try {
      const now = new Date().toISOString()
      const passed = !!log.is_passed
      const { data: created } = await createReportApi({
        plan: reportForm.value.plan,
        report_name: name,
        environment: reportForm.value.environment || 'TEST',
        create_method: 1,
        start_time: now,
        end_time: now,
        req_count: 0,
        case_count: 1,
        coverage_rate: passed ? '100.00' : '0.00',
        pass_rate: passed ? '100.00' : '0.00',
        defect_count: passed ? 0 : 1,
      })
      const reportId = (created as { id?: number })?.id
      if (reportId == null) {
        throw new Error('创建报告成功但未返回报告 ID，无法回填执行数据')
      }
      // 数据闭环：将本次执行的 trace、请求/响应快照写入报告，便于报表与审计
      await updateReportApi(reportId, {
        trace_id: (log.trace_id as string) || '',
        execution_log_id: log.id ?? null,
        request_payload: log.request_payload ?? null,
        response_payload: log.response_payload ?? null,
        pass_rate: passed ? '100.00' : '0.00',
        defect_count: passed ? 0 : 1,
        coverage_rate: passed ? '100.00' : '0.00',
        case_count: 1,
        end_time: now,
      })
    } finally {
      savingReport.value = false
    }
  }

  function initReportFormName() {
    const cn = caseRow.value?.case_name || 'API'
    reportForm.value.report_name = `接口执行 — ${cn} — ${new Date().toLocaleString()}`
  }

  return {
    requestUrl,
    requestMethod,
    headersText,
    bodyText,
    expectedStatus,
    extractionRules,
    consoleLines,
    executionLog,
    running,
    aiFilling,
    savingReport,
    plans,
    reportForm,
    highlightedRequestPreview,
    responseBodyPrism,
    lastErrorHttpStatus,
    resetFromRow,
    runAiFill,
    applyCurlCommand,
    runPreviewResolved,
    runExecute,
    runExecuteAndSaveReport,
    buildApiCasePatch,
    loadPlans,
    saveReport,
    initReportFormName,
  }
}
