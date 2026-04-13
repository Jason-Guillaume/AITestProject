<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="min(1240px, 96vw)"
    top="4vh"
    destroy-on-close
    class="api-exec-console-dialog"
    append-to-body
  >
    <div v-if="caseRow" class="api-exec-dialog-body">
      <div class="api-exec-status-ribbon" role="status" aria-live="polite">
        <div class="api-exec-status-badge" :class="statusBadgeClass">{{ statusBadgeLabel }}</div>
        <span v-if="executionMetaChips.length" class="api-exec-status-chips">
          <span v-for="(t, i) in executionMetaChips" :key="i" class="api-exec-status-chip">{{ t }}</span>
        </span>
      </div>

      <div class="api-exec-layout">
      <!-- 左侧：表单可调 Headers / Body 等（约 30%） -->
      <section class="api-exec-pane api-exec-pane--request">
        <div class="api-exec-pane__title">请求配置</div>
        <el-form label-position="top" class="api-exec-el-form" @submit.prevent>
          <el-row :gutter="12">
            <el-col :span="8">
              <el-form-item label="请求方法">
                <el-select v-model="requestMethod" class="api-exec-method-full" filterable>
                  <el-option label="GET" value="GET" />
                  <el-option label="POST" value="POST" />
                  <el-option label="PUT" value="PUT" />
                  <el-option label="PATCH" value="PATCH" />
                  <el-option label="DELETE" value="DELETE" />
                  <el-option label="HEAD" value="HEAD" />
                  <el-option label="OPTIONS" value="OPTIONS" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="16">
              <el-form-item label="URL">
                <el-input v-model="requestUrl" placeholder="https://api.example.com/path" clearable />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="期望状态码">
            <el-input-number
              v-model="expectedStatus"
              :min="100"
              :max="599"
              controls-position="right"
              class="api-exec-status-num"
            />
          </el-form-item>
          <el-form-item label="cURL（可选，一键填充请求）">
            <el-input
              v-model="curlText"
              type="textarea"
              :rows="4"
              class="api-exec-code-input"
              spellcheck="false"
              placeholder="curl -X POST 'https://api.example.com/login' -H 'Content-Type: application/json' -d '{&quot;username&quot;:&quot;test&quot;}'"
            />
            <div style="margin-top:8px">
              <el-button size="small" plain @click="onApplyCurl">从 cURL 填充</el-button>
            </div>
          </el-form-item>

          <el-form-item>
            <template #label>
              <span class="api-exec-form-label-row">
                <span>Headers（JSON）</span>
                <el-button
                  size="small"
                  class="api-exec-ai-btn"
                  :loading="aiFilling"
                  @click="onAiFillHeaders"
                >
                  <el-icon class="api-exec-ai-icon"><MagicStick /></el-icon>
                  AI 填充
                </el-button>
              </span>
            </template>
            <el-input
              v-model="headersText"
              type="textarea"
              :rows="6"
              class="api-exec-code-input"
              spellcheck="false"
              placeholder='{"Content-Type":"application/json"}'
            />
          </el-form-item>

          <el-form-item>
            <template #label>
              <span class="api-exec-form-label-row">
                <span>Body（JSON）</span>
                <el-button
                  size="small"
                  type="primary"
                  plain
                  class="api-exec-ai-btn"
                  :loading="aiFilling"
                  @click="onAiFillBody"
                >
                  <el-icon class="api-exec-ai-icon"><MagicStick /></el-icon>
                  AI 填充
                </el-button>
              </span>
            </template>
            <el-input
              v-model="bodyText"
              type="textarea"
              :rows="10"
              class="api-exec-code-input"
              spellcheck="false"
              placeholder="{}"
            />
          </el-form-item>

          <el-divider content-position="left">报告（执行成功后生成）</el-divider>
          <el-form-item label="关联测试计划">
            <el-select
              v-model="reportForm.plan"
              placeholder="请选择测试计划"
              filterable
              class="api-exec-field-full"
            >
              <el-option v-for="p in plans" :key="p.id" :label="p.plan_name" :value="p.id" />
            </el-select>
          </el-form-item>
          <el-row :gutter="12">
            <el-col :span="16">
              <el-form-item label="报告名称">
                <el-input v-model="reportForm.report_name" placeholder="报告名称" clearable />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="环境">
                <el-select v-model="reportForm.environment" class="api-exec-field-full">
                  <el-option label="TEST" value="TEST" />
                  <el-option label="PROD" value="PROD" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>

          <div class="api-exec-run-actions">
            <el-button
              size="large"
              plain
              class="api-exec-run-btn-half"
              :disabled="activeRunMode !== 'idle'"
              @click="onPreviewResolved"
            >
              预览替换
            </el-button>
            <el-button
              size="large"
              plain
              class="api-exec-run-btn-half"
              title="仅调用 run-api 写入执行日志，不生成测试报告"
              :disabled="activeRunMode !== 'idle'"
              :loading="activeRunMode === 'only'"
              @click="onRunOnly"
            >
              仅执行
            </el-button>
            <el-button
              type="primary"
              size="large"
              class="api-exec-run-btn-half"
              :disabled="activeRunMode !== 'idle'"
              :loading="activeRunMode === 'withReport'"
              @click="onRunAndSaveReport"
            >
              执行并保存报告
            </el-button>
          </div>
          <p v-if="executionLog" class="api-exec-log-hint">
            执行记录已写入日志表 ExecutionLog（#{{ executionLog.id ?? '—' }}）
            <template v-if="executionLog.trace_id">
              · trace_id: {{ executionLog.trace_id }}
            </template>
          </p>
        </el-form>
      </section>

      <!-- 右侧：执行日志 + 响应 + 断言明细（约 70%） -->
      <section class="api-exec-pane api-exec-pane--console">
        <div class="api-exec-pane__title">执行日志</div>
        <div ref="terminalRef" class="api-exec-terminal" tabindex="-1">
          <div v-if="!consoleLines.length" class="api-exec-terminal__placeholder">
            > 等待执行…
          </div>
          <div v-for="(line, i) in consoleLines" :key="i" class="api-exec-terminal__line">
            {{ line }}
          </div>
        </div>
        <div class="api-exec-subhead api-exec-subhead--dim">
          响应体
          <span class="api-exec-lang-pill">{{ responseBodyLangLabel }}</span>
        </div>
        <pre class="api-exec-prism api-exec-prism--response"><code
          :class="responseBodyCodeClass"
          v-html="responseBodyPrism.html"
        /></pre>

        <div v-if="executionLog && assertionTableData.length" class="api-exec-assertions-inline">
          <div class="api-exec-subhead">断言明细</div>
          <el-table
            :data="assertionTableData"
            size="small"
            border
            class="api-exec-assert-table"
            empty-text="无断言明细"
          >
            <el-table-column prop="name" label="名称" width="120" />
            <el-table-column prop="passed" label="通过" width="72" align="center">
              <template #default="{ row }">
                <el-tag :type="row.passed ? 'success' : 'danger'" size="small">
                  {{ row.passed ? '是' : '否' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="detail" label="说明" min-width="160" show-overflow-tooltip />
          </el-table>
        </div>
      </section>
      </div>
    </div>
    <div v-else class="api-exec-empty">未选择用例</div>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, toRef, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { MagicStick } from '@element-plus/icons-vue'
import type { TestCaseRow } from '@/types/testcase'
import { formatCaseDisplayId } from '@/composables/useTestCaseTypeColumns'
import { useApiExecuteConsole, HTTP_STATUS_PHRASE } from '@/composables/useApiExecuteConsole'
import { updateCaseApi } from '@/api/testcase'
import 'prismjs/themes/prism-tomorrow.min.css'

const visible = defineModel<boolean>({ default: false })

const props = defineProps<{
  caseRow: TestCaseRow | null
}>()

const caseRowRef = toRef(props, 'caseRow')
const terminalRef = ref<HTMLElement | null>(null)
const router = useRouter()

const dialogTitle = computed(() => {
  const row = props.caseRow
  if (!row) return '接口调试'
  const num =
    row.case_number != null && !Number.isNaN(Number(row.case_number))
      ? String(row.case_number)
      : formatCaseDisplayId(row)
  return `接口调试 - ${num}`
})

const {
  requestUrl,
  requestMethod,
  headersText,
  bodyText,
  expectedStatus,
  consoleLines,
  executionLog,
  aiFilling,
  plans,
  reportForm,
  responseBodyPrism,
  lastErrorHttpStatus,
  running,
  runAiFill,
  applyCurlCommand,
  runPreviewResolved,
  runExecute,
  runExecuteAndSaveReport,
  buildApiCasePatch,
  loadPlans,
  initReportFormName,
  resetFromRow,
} = useApiExecuteConsole(caseRowRef)

const effectiveStatusCode = computed(() => {
  const log = executionLog.value
  if (log?.response_status_code != null && !Number.isNaN(Number(log.response_status_code))) {
    return Number(log.response_status_code)
  }
  const e = lastErrorHttpStatus.value
  if (e != null && !Number.isNaN(e)) return e
  return null
})

const statusBadgeLabel = computed(() => {
  if (running.value) return '执行中…'
  const c = effectiveStatusCode.value
  if (c == null) {
    if (!executionLog.value && consoleLines.value.length > 0) return '请求失败'
    return '待执行'
  }
  const phrase = HTTP_STATUS_PHRASE[c] || ''
  return `${c}${phrase ? ` ${phrase}` : ''}`
})

const statusBadgeClass = computed(() => {
  if (running.value) return 'api-exec-status-badge--running'
  const c = effectiveStatusCode.value
  if (c == null) {
    if (!executionLog.value && consoleLines.value.length > 0) return 'api-exec-status-badge--error'
    return 'api-exec-status-badge--idle'
  }
  if (c === 200) return 'api-exec-status-badge--ok'
  if (c === 404 || c === 500) return 'api-exec-status-badge--error'
  if (c >= 200 && c < 300) return 'api-exec-status-badge--ok'
  if (c >= 400) return 'api-exec-status-badge--error'
  return 'api-exec-status-badge--warn'
})

const executionMetaChips = computed(() => {
  const log = executionLog.value
  const chips: string[] = []
  if (log?.trace_id) chips.push(`trace ${log.trace_id}`)
  const ms = log?.duration_ms ?? log?.response_time_ms
  if (ms != null) chips.push(`${ms} ms`)
  if (log?.is_passed != null) chips.push(log.is_passed ? '断言通过' : '断言未通过')
  return chips
})

const responseBodyCodeClass = computed(() => `language-${responseBodyPrism.value.lang}`)

const responseBodyLangLabel = computed(() => {
  const m: Record<string, string> = {
    json: 'JSON',
    php: 'PHP',
    markup: 'HTML',
  }
  return m[responseBodyPrism.value.lang] || responseBodyPrism.value.lang.toUpperCase()
})

/** idle | only | withReport — 避免两个执行按钮 loading 状态串台 */
const activeRunMode = ref<'idle' | 'only' | 'withReport'>('idle')
const curlText = ref('')

function scrollTerminalToBottom() {
  const el = terminalRef.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}

watch(
  consoleLines,
  async () => {
    await nextTick()
    requestAnimationFrame(() => {
      scrollTerminalToBottom()
    })
  },
  { deep: true, flush: 'post' },
)

const assertionTableData = computed(() => {
  const ar = executionLog.value?.assertion_results
  if (!Array.isArray(ar)) return []
  return ar.map((a) => ({
    name: a?.name ?? '—',
    passed: !!a?.passed,
    detail: a?.detail ?? '',
  }))
})

/** 与抽屉面板一致：依赖 visible + 用例 id，避免仅 @opened 时未触发或关开竞态导致仍显示上一用例/空表 */
watch(
  () => [visible.value, props.caseRow?.id ?? null] as const,
  async ([open, id]) => {
    if (!open || id == null || !props.caseRow) return
    activeRunMode.value = 'idle'
    consoleLines.value = []
    executionLog.value = null
    lastErrorHttpStatus.value = null
    await resetFromRow()
    curlText.value = String((props.caseRow as TestCaseRow)?.api_source_curl || '').trim()
    initReportFormName()
    await loadPlans()
    await nextTick()
    requestAnimationFrame(scrollTerminalToBottom)
  },
  { flush: 'post' },
)

function onApplyCurl() {
  applyCurlAndPersist().catch((e) => {
    ElMessage.error((e as Error)?.message || 'cURL 解析失败')
  })
}

async function applyCurlAndPersist() {
  try {
    if (!props.caseRow?.id) throw new Error('当前用例不存在，无法保存')
    const parsed = applyCurlCommand(curlText.value || '')
    const moduleId =
      typeof props.caseRow.module === 'number'
        ? props.caseRow.module
        : Number(props.caseRow.module || 0) || null
    const patch = buildApiCasePatch(props.caseRow, moduleId, curlText.value?.trim() ?? '')
    await updateCaseApi(props.caseRow.id, patch)
    Object.assign(props.caseRow, patch)
    ElMessage.success(`已从 cURL 填充并保存：${parsed.method} ${parsed.url}`)
  } catch (e) {
    throw e
  }
}

async function onPreviewResolved() {
  try {
    const data = await runPreviewResolved()
    const req = (data as { request?: Record<string, unknown> })?.request || {}
    const pretty = JSON.stringify(req, null, 2)
    const lines = [
      '> 预览执行前最终请求（未发送）',
      ...String(pretty).split('\n').map((x) => `  ${x}`),
    ]
    consoleLines.value = [...consoleLines.value, ...lines]
    ElMessage.success('已输出预览到执行日志')
  } catch (e) {
    ElMessage.error((e as Error)?.message || '预览失败')
  }
}

async function onAiFillBody() {
  try {
    await runAiFill('body')
    ElMessage.success('已根据 AI 填充 Body')
  } catch (e) {
    ElMessage.error((e as Error)?.message || 'AI 填充失败')
  }
}

async function onAiFillHeaders() {
  try {
    await runAiFill('headers')
    ElMessage.success('已根据 AI 填充 Headers')
  } catch (e) {
    ElMessage.error((e as Error)?.message || 'AI 填充失败')
  }
}

async function onRunOnly() {
  if (activeRunMode.value !== 'idle') return
  activeRunMode.value = 'only'
  try {
    await runExecute()
    ElMessage.success('已执行，日志已落库（未生成报告）')
  } catch (e) {
    const msg =
      (e as { response?: { data?: { msg?: string } } })?.response?.data?.msg ||
      (e as Error)?.message ||
      '执行失败'
    ElMessage.error(typeof msg === 'string' ? msg : '执行失败')
  } finally {
    activeRunMode.value = 'idle'
  }
}

async function onRunAndSaveReport() {
  if (activeRunMode.value !== 'idle') return
  activeRunMode.value = 'withReport'
  try {
    await runExecuteAndSaveReport()
    ElMessage.success('已执行请求，日志已落库并生成测试报告')
    visible.value = false
    router.push('/test-report')
  } catch (e) {
    const msg =
      (e as { response?: { data?: { msg?: string } } })?.response?.data?.msg ||
      (e as Error)?.message ||
      '执行或保存失败'
    ElMessage.error(typeof msg === 'string' ? msg : '执行或保存失败')
  } finally {
    activeRunMode.value = 'idle'
  }
}
</script>

<style scoped lang="scss">
.api-exec-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 0;
  min-height: 0;
}

.api-exec-status-ribbon {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 12px 16px;
  margin: -6px -16px 14px;
  padding: 12px 16px;
  background: linear-gradient(180deg, rgba(22, 27, 34, 0.98) 0%, rgba(13, 17, 23, 0.92) 100%);
  border-bottom: 1px solid #30363d;
}

.api-exec-status-badge {
  font-size: 15px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 10px 22px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow:
    0 0 0 1px rgba(0, 0, 0, 0.35),
    0 8px 24px rgba(0, 0, 0, 0.35);
  line-height: 1.25;
}

.api-exec-status-badge--idle {
  color: #8b949e;
  background: rgba(48, 54, 61, 0.65);
  border-color: rgba(139, 148, 158, 0.35);
}

.api-exec-status-badge--running {
  color: #79c0ff;
  background: rgba(56, 139, 253, 0.2);
  border-color: rgba(121, 192, 255, 0.45);
  animation: api-exec-badge-pulse 1.2s ease-in-out infinite;
}

.api-exec-status-badge--ok {
  color: #0f2418;
  background: linear-gradient(180deg, #3efa9a 0%, #2ba84a 100%);
  border-color: rgba(46, 160, 67, 0.85);
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.25);
}

.api-exec-status-badge--error {
  color: #fff5f5;
  background: linear-gradient(180deg, #f85149 0%, #da3633 100%);
  border-color: rgba(248, 81, 73, 0.75);
  box-shadow:
    0 0 24px rgba(248, 81, 73, 0.35),
    0 0 0 1px rgba(0, 0, 0, 0.35);
}

.api-exec-status-badge--warn {
  color: #1c1410;
  background: linear-gradient(180deg, #e3b341 0%, #d29922 100%);
  border-color: rgba(210, 153, 34, 0.8);
}

@keyframes api-exec-badge-pulse {
  0%,
  100% {
    opacity: 1;
    filter: brightness(1);
  }
  50% {
    opacity: 0.92;
    filter: brightness(1.08);
  }
}

.api-exec-status-chips {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.api-exec-status-chip {
  font-size: 11px;
  color: #8b949e;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(110, 118, 129, 0.18);
  border: 1px solid rgba(48, 54, 61, 0.9);
}

.api-exec-layout {
  display: grid;
  grid-template-columns: minmax(0, 3fr) minmax(0, 7fr);
  gap: 16px;
  min-height: 440px;
  align-items: stretch;
}

.api-exec-pane {
  border-radius: 10px;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: linear-gradient(165deg, #161b22 0%, #0d1117 100%);
}

.api-exec-pane__title {
  font-size: 13px;
  font-weight: 600;
  color: #8b949e;
  margin-bottom: 10px;
  letter-spacing: 0.04em;
}

.api-exec-pane--console {
  background: #0d1117;
  border-color: #30363d;
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
}

.api-exec-pane--request {
  min-width: 0;
  max-height: min(74vh, 760px);
  overflow-y: auto;
}

.api-exec-el-form {
  :deep(.el-form-item__label) {
    color: #c9d1d9;
    font-size: 12px;
  }
}

.api-exec-form-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding-right: 4px;
}

.api-exec-method-full {
  width: 100%;
}

.api-exec-status-num {
  width: 160px;
}

.api-exec-field-full {
  width: 100%;
}

.api-exec-ai-btn {
  font-size: 12px;
}

.api-exec-ai-icon {
  margin-right: 4px;
  vertical-align: middle;
}

:deep(.api-exec-code-input textarea) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    'Courier New', monospace;
  font-size: 12px;
  line-height: 1.45;
  background: #0d1117 !important;
  color: #e6edf3 !important;
  border-color: #30363d !important;
}

.api-exec-run-actions {
  display: flex;
  gap: 10px;
  margin-top: 8px;
}

.api-exec-run-btn-half {
  flex: 1;
}

.api-exec-log-hint {
  font-size: 12px;
  color: #8b949e;
  margin: 10px 0 0;
}

.api-exec-terminal {
  flex: 1 1 220px;
  min-height: 220px;
  max-height: min(40vh, 400px);
  overflow: auto;
  padding: 12px 14px;
  border-radius: 8px;
  background: #1e1e1e;
  border: 1px solid #2d2d2d;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
  color: #d4d4d4;
  box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.35);
}

.api-exec-terminal__placeholder {
  color: #6e6e6e;
}

.api-exec-terminal__line {
  white-space: pre-wrap;
  word-break: break-all;
}

.api-exec-subhead {
  font-size: 12px;
  color: #c9d1d9;
  margin: 12px 0 8px;
}

.api-exec-subhead--dim {
  color: #8b949e;
  margin-top: 14px;
}

.api-exec-lang-pill {
  margin-left: 8px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: #58a6ff;
  padding: 2px 8px;
  border-radius: 6px;
  border: 1px solid rgba(88, 166, 255, 0.35);
  background: rgba(88, 166, 255, 0.12);
  vertical-align: middle;
}

.api-exec-prism {
  margin: 0;
  padding: 10px 12px;
  border-radius: 8px;
  overflow: auto;
  max-height: 200px;
  font-size: 12px;
  line-height: 1.45;
  background: #0d1117 !important;
  border: 1px solid #30363d;
}

.api-exec-prism--response {
  flex-shrink: 0;
  max-height: min(28vh, 320px);
}

.api-exec-prism code {
  font-family: inherit;
}

.api-exec-pane--console .api-exec-assertions-inline {
  flex-shrink: 0;
  max-height: 200px;
  overflow: auto;
}

.api-exec-assertions-inline {
  margin-top: 8px;
}

.api-exec-assert-table {
  width: 100%;
}

.api-exec-empty {
  padding: 24px;
  text-align: center;
  color: #8b949e;
}

@media (max-width: 900px) {
  .api-exec-layout {
    grid-template-columns: 1fr;
  }

  .api-exec-pane--request {
    max-height: none;
  }
}
</style>

<style lang="scss">
.api-exec-console-dialog.el-dialog {
  background: #161b22;
  border: 1px solid #30363d;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.45);
}

.api-exec-console-dialog .el-dialog__header {
  border-bottom: 1px solid #30363d;
  margin-right: 0;
  padding: 14px 16px 12px;
}

.api-exec-console-dialog .el-dialog__title {
  color: #e6edf3;
  font-weight: 600;
}

.api-exec-console-dialog .el-dialog__headerbtn .el-dialog__close {
  color: #8b949e;
}

.api-exec-console-dialog .el-dialog__body {
  padding: 16px;
  background: #0d1117;
}

.api-exec-console-dialog .el-dialog__footer {
  padding: 12px 16px 16px;
  background: #161b22;
  border-top: 1px solid #30363d;
}
</style>
