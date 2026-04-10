<template>
  <div v-if="caseRow" class="drawer-api-panel">
    <el-tabs v-model="activeTab" class="drawer-api-tabs">
      <el-tab-pane label="Request Config" name="request">
        <el-form label-position="top" class="drawer-api-form" @submit.prevent>
          <el-row :gutter="10">
            <el-col :span="8">
              <el-form-item label="Method">
                <el-select v-model="requestMethod" class="drawer-api-full" filterable>
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
                <el-input v-model="requestUrl" placeholder="https://..." clearable />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="期望状态码">
            <el-input-number
              v-model="expectedStatus"
              :min="100"
              :max="599"
              controls-position="right"
              class="drawer-api-status"
            />
          </el-form-item>
          <el-form-item>
            <template #label>
              <span class="drawer-api-label-row">
                <span>Headers（JSON）</span>
                <el-button size="small" text type="primary" :loading="aiFilling" @click="onAiHeaders">
                  <el-icon><MagicStick /></el-icon>
                  AI 自动填值
                </el-button>
              </span>
            </template>
            <el-input
              v-model="headersText"
              type="textarea"
              :rows="5"
              class="drawer-api-code"
              spellcheck="false"
            />
          </el-form-item>
          <el-form-item>
            <template #label>
              <span class="drawer-api-label-row">
                <span>Body（JSON）</span>
                <el-button size="small" type="primary" plain :loading="aiFilling" @click="onAiBody">
                  <el-icon><MagicStick /></el-icon>
                  AI 自动填值
                </el-button>
              </span>
            </template>
            <el-input
              v-model="bodyText"
              type="textarea"
              :rows="8"
              class="drawer-api-code"
              spellcheck="false"
            />
          </el-form-item>
          <el-button
            type="warning"
            class="drawer-api-run-now"
            :loading="running"
            :disabled="saving"
            @click="onRunNow"
          >
            ⚡ 立即执行（不保存草稿）
          </el-button>
        </el-form>
      </el-tab-pane>
      <el-tab-pane label="Variable Extraction" name="variable-extraction">
        <div class="drawer-api-extract-head">
          <div class="drawer-api-extract-head__tip">
            已提取规则 {{ extractionRules.length }} 条
          </div>
          <el-button type="primary" plain @click="openAiAssistant">
            <el-icon><MagicStick /></el-icon>
            打开 AI 提取助手
          </el-button>
        </div>

        <div class="drawer-api-extract-table-wrap">
          <el-table :data="extractionRules" size="small" border class="drawer-api-extract-table">
            <el-table-column label="变量名" min-width="150">
              <template #default="{ row }">
                <el-input v-model="row.variableName" placeholder="例如 token" />
              </template>
            </el-table-column>
            <el-table-column label="来源" width="120">
              <template #default="{ row }">
                <el-select v-model="row.source" class="drawer-api-full">
                  <el-option label="Body" value="Body" />
                  <el-option label="Header" value="Header" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="提取表达式" min-width="240">
              <template #default="{ row }">
                <el-input
                  v-model="row.expression"
                  placeholder="Body: $.data.token / Header: authorization"
                />
              </template>
            </el-table-column>
            <el-table-column label="当前值预览" min-width="160">
              <template #default="{ row }">
                <el-input :model-value="previewValue(row)" readonly />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ $index }">
                <TableActionGroup :row="{ index: $index }" :actions="ruleTableActions" @action="handleRuleTableAction" />
              </template>
            </el-table-column>
          </el-table>
          <el-button class="drawer-api-add-rule" plain type="primary" @click="addEmptyRule">+ 新增规则</el-button>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-drawer
      v-model="aiAssistantVisible"
      direction="rtl"
      size="420px"
      class="drawer-api-ai-assistant cyber-drawer-dark"
      title="✨ AI 建议提取"
      append-to-body
    >
      <div class="drawer-api-ai-suggest">
        <div class="drawer-api-ai-suggest__head">
          <span class="drawer-api-ai-suggest__head-left">
            <el-icon><MagicStick /></el-icon>
            <span>可一键应用建议字段</span>
          </span>
          <span v-if="freshSuggestionCount > 0" class="drawer-api-ai-suggest__fresh-tip">
            发现 {{ freshSuggestionCount }} 条新建议
          </span>
        </div>
        <div class="drawer-api-ai-suggest__toolbar">
          <el-button
            size="small"
            type="primary"
            plain
            :disabled="addableSuggestionCount === 0"
            @click="applyAllSuggestions"
          >
            一键全部添加（{{ addableSuggestionCount }}）
          </el-button>
        </div>
        <div v-if="aiSuggestions.length" class="drawer-api-ai-suggest__chips">
          <el-tag
            v-for="(item, index) in aiSuggestions"
            :key="`${item.variableName}-${item.expression}-${index}`"
            type="info"
            effect="dark"
            :class="['drawer-api-ai-suggest__chip', { 'is-fresh': isSuggestionFresh(item, index) }]"
            @click="applySuggestion(item)"
          >
            [+ {{ item.variableName }}]
          </el-tag>
        </div>
        <p v-else class="drawer-api-ai-suggest__empty">先运行一次接口，助手会自动给出可提取字段建议。</p>
      </div>
    </el-drawer>

    <div class="drawer-api-term-title">执行日志（终端）</div>
    <div ref="terminalRef" class="drawer-api-terminal">
      <div v-if="!consoleLines.length" class="drawer-api-terminal__ph">> 等待执行…</div>
      <div v-for="(line, i) in consoleLines" :key="i" class="drawer-api-terminal__line">
        {{ line }}
      </div>
    </div>
    <p v-if="executionLog?.trace_id" class="drawer-api-trace">
      trace_id: {{ executionLog.trace_id }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete, MagicStick } from '@element-plus/icons-vue'
import TableActionGroup from '@/components/common/TableActionGroup.vue'
import type { ApiVariableExtractRule, TestCaseRow } from '@/types/testcase'
import { useApiExecuteConsole } from '@/composables/useApiExecuteConsole'
import { updateCaseApi } from '@/api/testcase'

const props = defineProps<{
  caseRow: TestCaseRow | null
  moduleId: number | null
}>()

const emit = defineEmits<{
  (e: 'after-execute'): void
}>()

const caseRowRef = computed(() => props.caseRow)

const {
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
  resetFromRow,
  runAiFill,
  runExecute,
  buildApiCasePatch,
} = useApiExecuteConsole(caseRowRef)

const saving = ref(false)
const terminalRef = ref<HTMLElement | null>(null)
const activeTab = ref('request')
const aiAssistantVisible = ref(false)
const ruleTableActions = [{ key: 'delete', tooltip: '删除规则', icon: Delete, type: 'danger' }]

function handleRuleTableAction(action: string, row: { index: number }) {
  if (action === 'delete') removeRule(row.index)
}
const freshSuggestionKeys = ref<Record<string, boolean>>({})
const previousSuggestionKeys = ref<string[]>([])
const suggestionFlashTimers = new Map<string, ReturnType<typeof setTimeout>>()

const aiSuggestions = computed<ApiVariableExtractRule[]>(() => {
  const fromRow = (props.caseRow as TestCaseRow & { ai_extract_suggestions?: unknown })?.ai_extract_suggestions
  if (Array.isArray(fromRow) && fromRow.length) {
    return fromRow
      .map((item) => {
        if (!item || typeof item !== 'object') return null
        const row = item as Record<string, unknown>
        const source = String(row.source ?? 'Body') === 'Header' ? 'Header' : 'Body'
        return {
          variableName: String(row.variableName ?? ''),
          source,
          expression: String(row.expression ?? ''),
          currentValue: '',
        } as ApiVariableExtractRule
      })
      .filter(
        (item): item is ApiVariableExtractRule => !!item && !!item.variableName && !!item.expression,
      )
  }
  const payload = executionLog.value?.response_payload as Record<string, unknown> | null | undefined
  const jsonBody = payload?.body_json as Record<string, unknown> | undefined
  const headers = payload?.headers as Record<string, unknown> | undefined
  const local: ApiVariableExtractRule[] = []
  const candidateNames = ['token', 'access_token', 'refresh_token', 'session_id']
  for (const name of candidateNames) {
    if (jsonBody && jsonBody[name] != null) {
      local.push({
        variableName: name,
        source: 'Body',
        expression: `$.${name}`,
        currentValue: String(jsonBody[name] ?? ''),
      })
    }
    if (jsonBody && typeof jsonBody.data === 'object' && jsonBody.data && (jsonBody.data as Record<string, unknown>)[name] != null) {
      local.push({
        variableName: name,
        source: 'Body',
        expression: `$.data.${name}`,
        currentValue: String((jsonBody.data as Record<string, unknown>)[name] ?? ''),
      })
    }
    if (headers && headers[name] != null) {
      local.push({
        variableName: name,
        source: 'Header',
        expression: name,
        currentValue: String(headers[name] ?? ''),
      })
    }
  }
  return local
})

const freshSuggestionCount = computed(() =>
  Object.values(freshSuggestionKeys.value).filter(Boolean).length,
)

const addableSuggestionCount = computed(
  () => aiSuggestions.value.filter((item) => !hasRule(item)).length,
)

function suggestionKey(item: ApiVariableExtractRule, index: number): string {
  return `${item.source}::${item.variableName}::${item.expression}::${index}`
}

function isSuggestionFresh(item: ApiVariableExtractRule, index: number): boolean {
  return !!freshSuggestionKeys.value[suggestionKey(item, index)]
}

watch(
  () => props.caseRow?.id,
  () => {
    nextTick(() => resetFromRow())
  },
)

watch(
  consoleLines,
  async () => {
    await nextTick()
    const el = terminalRef.value
    if (el) el.scrollTop = el.scrollHeight
  },
  { deep: true },
)

watch(
  extractionRules,
  (rows) => {
    if (!props.caseRow) return
    ;(props.caseRow as TestCaseRow).api_extract_rules = rows
  },
  { deep: true },
)

watch(
  aiSuggestions,
  (rows) => {
    const nextKeys = rows.map((item, index) => suggestionKey(item, index))
    const prevSet = new Set(previousSuggestionKeys.value)
    for (const key of nextKeys) {
      if (!prevSet.has(key)) {
        freshSuggestionKeys.value = { ...freshSuggestionKeys.value, [key]: true }
        const oldTimer = suggestionFlashTimers.get(key)
        if (oldTimer) clearTimeout(oldTimer)
        const timer = setTimeout(() => {
          const clone = { ...freshSuggestionKeys.value }
          delete clone[key]
          freshSuggestionKeys.value = clone
          suggestionFlashTimers.delete(key)
        }, 2500)
        suggestionFlashTimers.set(key, timer)
      }
    }
    previousSuggestionKeys.value = nextKeys
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  for (const timer of suggestionFlashTimers.values()) clearTimeout(timer)
  suggestionFlashTimers.clear()
})

async function onAiHeaders() {
  try {
    await runAiFill('headers')
    ElMessage.success('已尝试填充 Headers')
  } catch (e) {
    ElMessage.error((e as Error)?.message || 'AI 填充失败')
  }
}

async function onAiBody() {
  try {
    await runAiFill('body')
    ElMessage.success('已尝试填充 Body')
  } catch (e) {
    ElMessage.error((e as Error)?.message || 'AI 填充失败')
  }
}

async function onRunNow() {
  try {
    await runExecute()
    activeTab.value = 'variable-extraction'
    aiAssistantVisible.value = true
    emit('after-execute')
  } catch (e) {
    const msg =
      (e as { response?: { data?: { msg?: string } } })?.response?.data?.msg ||
      (e as Error)?.message ||
      '执行失败'
    ElMessage.error(typeof msg === 'string' ? msg : '执行失败')
  }
}

function openAiAssistant() {
  aiAssistantVisible.value = true
}

function normalizeHeaderMap(raw: unknown): Record<string, unknown> {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {}
  const src = raw as Record<string, unknown>
  const out: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(src)) out[String(k).toLowerCase()] = v
  return out
}

function tokenizeJsonPath(path: string): string[] {
  const normalized = path
    .trim()
    .replace(/^\$\./, '')
    .replace(/^\$/, '')
    .replace(/\[(\d+)\]/g, '.$1')
  return normalized.split('.').map((s) => s.trim()).filter(Boolean)
}

function extractByJsonPath(source: unknown, path: string): unknown {
  const parts = tokenizeJsonPath(path)
  if (!parts.length) return source
  let cursor: unknown = source
  for (const seg of parts) {
    if (cursor == null) return ''
    if (Array.isArray(cursor)) {
      const idx = Number(seg)
      if (!Number.isInteger(idx) || idx < 0 || idx >= cursor.length) return ''
      cursor = cursor[idx]
      continue
    }
    if (typeof cursor !== 'object') return ''
    cursor = (cursor as Record<string, unknown>)[seg]
  }
  return cursor
}

function stringifyPreview(v: unknown): string {
  if (v == null) return ''
  if (typeof v === 'string') return v
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  try {
    return JSON.stringify(v)
  } catch {
    return String(v)
  }
}

function previewValue(row: ApiVariableExtractRule): string {
  const payload = executionLog.value?.response_payload as Record<string, unknown> | null | undefined
  if (!payload) return row.currentValue || ''
  const source = row.source === 'Header' ? 'Header' : 'Body'
  if (source === 'Header') {
    const headers = normalizeHeaderMap(payload.headers)
    const key = (row.expression || '').trim().toLowerCase()
    if (!key) return row.currentValue || ''
    return stringifyPreview(headers[key] ?? '')
  }
  const bodyJson = payload.body_json
  if (bodyJson != null) {
    return stringifyPreview(extractByJsonPath(bodyJson, row.expression || '$'))
  }
  const bodyRaw = payload.body_raw
  if (typeof bodyRaw === 'string' && bodyRaw.trim()) {
    try {
      const parsed = JSON.parse(bodyRaw)
      return stringifyPreview(extractByJsonPath(parsed, row.expression || '$'))
    } catch {
      return row.currentValue || ''
    }
  }
  return row.currentValue || ''
}

function addEmptyRule() {
  extractionRules.value.push({
    variableName: '',
    source: 'Body',
    expression: '',
    currentValue: '',
  })
}

function removeRule(index: number) {
  extractionRules.value.splice(index, 1)
}

function applySuggestion(item: ApiVariableExtractRule) {
  const exists = hasRule(item)
  if (exists) {
    ElMessage.info('该建议已在规则表中')
    return
  }
  extractionRules.value.push({
    variableName: item.variableName,
    source: item.source,
    expression: item.expression,
    currentValue: item.currentValue || '',
  })
}

function hasRule(item: ApiVariableExtractRule): boolean {
  return extractionRules.value.some(
    (row) =>
      row.variableName === item.variableName &&
      row.expression === item.expression &&
      row.source === item.source,
  )
}

function applyAllSuggestions() {
  const toAdd = aiSuggestions.value.filter((item) => !hasRule(item))
  if (!toAdd.length) {
    ElMessage.info('当前无可新增建议')
    return
  }
  extractionRules.value.push(
    ...toAdd.map((item) => ({
      variableName: item.variableName,
      source: item.source,
      expression: item.expression,
      currentValue: item.currentValue || '',
    })),
  )
  ElMessage.success(`已添加 ${toAdd.length} 条建议`)
}

async function saveAndExecute() {
  const row = props.caseRow
  if (!row?.id) {
    ElMessage.warning('用例未加载完成')
    return
  }
  saving.value = true
  try {
    const patch = buildApiCasePatch(row, props.moduleId)
    await updateCaseApi(row.id, patch)
    ElMessage.success('已保存接口配置')
    Object.assign(row, patch)
    await runExecute()
    activeTab.value = 'variable-extraction'
    aiAssistantVisible.value = true
    emit('after-execute')
  } catch (e: unknown) {
    const msg =
      (e as { response?: { data?: { msg?: string } } })?.response?.data?.msg ||
      (e as Error)?.message ||
      '保存或执行失败'
    ElMessage.error(typeof msg === 'string' ? msg : '保存或执行失败')
    throw e
  } finally {
    saving.value = false
  }
}

defineExpose({
  saveAndExecute,
  saving,
})
</script>

<style scoped lang="scss">
.drawer-api-panel {
  margin-top: 8px;
}

.drawer-api-tabs :deep(.el-tabs__item) {
  color: rgba(148, 163, 184, 0.92);
}

.drawer-api-tabs :deep(.el-tabs__item.is-active) {
  color: #67e8f9;
}

.drawer-api-tabs :deep(.el-tabs__active-bar) {
  background: #22d3ee;
}

.drawer-api-form :deep(.el-form-item__label) {
  color: rgba(203, 213, 225, 0.88);
  font-size: 12px;
}

.drawer-api-full {
  width: 100%;
}

.drawer-api-status {
  width: 140px;
}

.drawer-api-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.drawer-api-code :deep(textarea) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  background: rgba(15, 23, 42, 0.65) !important;
  color: #e2e8f0 !important;
}

.drawer-api-run-now {
  width: 100%;
  margin-bottom: 12px;
}

.drawer-api-extract-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding: 10px 12px;
  border: 1px solid rgba(71, 85, 105, 0.5);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.45);
}

.drawer-api-extract-head__tip {
  font-size: 12px;
  color: rgba(148, 163, 184, 0.95);
}

.drawer-api-ai-suggest {
  padding: 12px 14px;
  margin-bottom: 14px;
  border: 1px solid rgba(125, 211, 252, 0.52);
  background: linear-gradient(90deg, rgba(30, 64, 175, 0.26), rgba(15, 23, 42, 0.48));
  border-radius: 10px;
  box-shadow: 0 0 0 1px rgba(125, 211, 252, 0.12) inset;
}

.drawer-api-ai-suggest__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
  color: rgba(186, 230, 253, 0.96);
  font-size: 13px;
  font-weight: 600;
}

.drawer-api-ai-suggest__head-left {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.drawer-api-ai-suggest__fresh-tip {
  font-size: 12px;
  color: #fde68a;
  background: rgba(250, 204, 21, 0.18);
  border: 1px solid rgba(250, 204, 21, 0.45);
  border-radius: 999px;
  padding: 2px 8px;
  white-space: nowrap;
}

.drawer-api-ai-suggest__toolbar {
  margin-bottom: 10px;
}

.drawer-api-ai-suggest__chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.drawer-api-ai-suggest__chip {
  cursor: pointer;
  border-color: rgba(125, 211, 252, 0.65);
  color: #e0f2fe;
  background: rgba(2, 132, 199, 0.22) !important;
}

.drawer-api-ai-suggest__chip.is-fresh {
  border-color: rgba(250, 204, 21, 0.95);
  color: #fef08a;
  background: rgba(250, 204, 21, 0.24) !important;
  box-shadow: 0 0 0 1px rgba(250, 204, 21, 0.35), 0 0 14px rgba(250, 204, 21, 0.22);
  animation: drawer-ai-chip-pulse 1.1s ease-in-out 2;
}

@keyframes drawer-ai-chip-pulse {
  0%,
  100% {
    transform: translateY(0);
    filter: brightness(1);
  }
  50% {
    transform: translateY(-1px);
    filter: brightness(1.15);
  }
}

.drawer-api-ai-suggest__empty {
  margin: 0;
  font-size: 12px;
  color: rgba(186, 230, 253, 0.72);
}

.drawer-api-ai-assistant :deep(.el-drawer__header) {
  margin-bottom: 0;
  color: rgba(186, 230, 253, 0.96);
}

.drawer-api-extract-table-wrap {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.drawer-api-add-rule {
  align-self: flex-start;
}

.drawer-api-term-title {
  font-size: 12px;
  font-weight: 600;
  color: rgba(148, 163, 184, 0.95);
  margin-bottom: 6px;
}

.drawer-api-terminal {
  min-height: 140px;
  max-height: 200px;
  overflow: auto;
  padding: 10px 12px;
  border-radius: 8px;
  background: #0c0c0c;
  border: 1px solid #1e5128;
  font-family: ui-monospace, monospace;
  font-size: 12px;
  line-height: 1.55;
  color: #3cff7a;
  text-shadow: 0 0 6px rgba(60, 255, 122, 0.25);
}

.drawer-api-terminal__ph {
  color: #3d5c45;
}

.drawer-api-terminal__line {
  white-space: pre-wrap;
  word-break: break-all;
}

.drawer-api-trace {
  font-size: 11px;
  color: rgba(148, 163, 184, 0.75);
  margin: 8px 0 0;
  word-break: break-all;
}
</style>
