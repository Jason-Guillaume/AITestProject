<template>
  <div class="action-builder">
    <header class="ab-header">
      <div class="ab-header__left">
        <span class="ab-header__tag">KEYWORD-DRIVEN</span>
        <el-select
          v-model="currentCaseId"
          placeholder="选择用例"
          size="small"
          filterable
          clearable
          class="ab-case-select"
          @change="onCaseChange"
        >
          <el-option
            v-for="tc in testCases"
            :key="tc.id"
            :label="tc.name"
            :value="tc.id"
          >
            <span class="ab-case-option__name">{{ tc.name }}</span>
            <span class="ab-case-option__status">{{ tc.status_display }}</span>
          </el-option>
        </el-select>
        <el-button
          size="small"
          class="ab-btn--new-case"
          @click="showNewCaseDialog = true"
        >
          + 新建
        </el-button>
        <span class="ab-header__count">{{ steps.length }} 步</span>
        <span
          v-if="executionStatus"
          class="ab-header__status"
          :class="`ab-header__status--${executionStatus}`"
        >
          {{ statusLabel }}
        </span>
      </div>
      <div class="ab-header__right">
        <el-button
          size="small"
          class="ab-btn--cyan"
          :icon="Plus"
          :disabled="!currentCaseId"
          @click="addStep"
        >
          添加步骤
        </el-button>
        <el-button
          size="small"
          class="ab-btn--save"
          :icon="Check"
          :loading="saveLoading"
          :disabled="!currentCaseId"
          @click="saveAll"
        >
          保存
        </el-button>
        <el-button
          size="small"
          class="ab-btn--exec"
          :icon="VideoPlay"
          :loading="executing"
          :disabled="!currentCaseId || steps.length === 0"
          @click="onExecute"
        >
          执行
        </el-button>
        <el-button
          v-if="executing"
          size="small"
          class="ab-btn--stop"
          :icon="VideoPause"
          @click="onStop"
        >
          停止
        </el-button>
        <el-button
          size="small"
          class="ab-btn--violet"
          :icon="Download"
          @click="exportJson"
        >
          导出 JSON
        </el-button>
      </div>
    </header>

    <div
      ref="stepListRef"
      class="ab-step-list"
    >
      <TransitionGroup name="ab-step">
        <div
          v-for="(step, idx) in steps"
          :key="step._uid"
          class="ab-step-card"
          :class="{
            'ab-step-card--active': activeStepUid === step._uid,
            'ab-step-card--disabled': !step.enabled,
            'ab-step-card--passed': step._result === 'passed',
            'ab-step-card--failed': step._result === 'failed',
            'ab-step-card--skipped': step._result === 'skipped',
            'ab-step-card--running': step._result === 'running',
          }"
          @click="activeStepUid = step._uid"
        >
          <div class="ab-step-card__grip">
            <el-icon :size="14">
              <Rank />
            </el-icon>
          </div>
          <div class="ab-step-card__order">
            <template v-if="step._result === 'passed'">
              ✅
            </template>
            <template v-else-if="step._result === 'failed'">
              ❌
            </template>
            <template v-else-if="step._result === 'skipped'">
              ⏭️
            </template>
            <template v-else-if="step._result === 'running'">
              ⏳
            </template>
            <template v-else>
              {{ step.step_order }}
            </template>
          </div>

          <div class="ab-step-card__field ab-step-card__field--action">
            <el-select
              v-model="step.action_type"
              placeholder="操作类型"
              size="small"
              class="ab-select--cyber"
              @change="onActionTypeChange(step)"
            >
              <el-option
                v-for="a in ACTION_TYPES"
                :key="a.value"
                :label="a.label"
                :value="a.value"
              >
                <span class="ab-option__icon">{{ a.icon }}</span>
                <span>{{ a.label }}</span>
              </el-option>
            </el-select>
          </div>

          <div
            v-if="requiresElement(step.action_type)"
            class="ab-step-card__field ab-step-card__field--locator"
          >
            <el-select
              v-model="step.element"
              placeholder="选择元素"
              size="small"
              filterable
              clearable
              class="ab-select--cyber"
            >
              <el-option
                v-for="loc in locators"
                :key="loc.id"
                :label="loc.name"
                :value="loc.id"
              >
                <div class="ab-locator-option">
                  <span class="ab-locator-option__type">{{ loc.locator_type_display || loc.locator_type }}</span>
                  <span class="ab-locator-option__name">{{ loc.name }}</span>
                  <span
                    class="ab-locator-option__expr"
                    :title="loc.locator_expression"
                  >
                    {{ truncate(loc.locator_expression, 28) }}
                  </span>
                </div>
              </el-option>
            </el-select>
          </div>

          <div
            v-if="requiresValue(step.action_type)"
            class="ab-step-card__field ab-step-card__field--value"
          >
            <el-input
              v-model="step.action_value"
              :placeholder="valuePlaceholder(step.action_type)"
              size="small"
              class="ab-input--cyber"
            />
          </div>

          <template v-if="step.action_type === 'assert'">
            <div class="ab-step-card__field ab-step-card__field--assert-type">
              <el-select
                v-model="step.assert_type"
                placeholder="断言类型"
                size="small"
                class="ab-select--cyber"
              >
                <el-option
                  v-for="at in ASSERT_TYPES"
                  :key="at.value"
                  :label="at.label"
                  :value="at.value"
                />
              </el-select>
            </div>
            <div class="ab-step-card__field ab-step-card__field--assert-expected">
              <el-input
                v-model="step.assert_expected"
                placeholder="期望值"
                size="small"
                class="ab-input--cyber"
              />
            </div>
          </template>

          <div class="ab-step-card__field ab-step-card__field--desc">
            <el-input
              v-model="step.description"
              placeholder="备注"
              size="small"
              class="ab-input--cyber"
            />
          </div>

          <div
            v-if="step._duration"
            class="ab-step-card__duration"
          >
            {{ step._duration }}ms
          </div>

          <div
            v-if="step._error"
            class="ab-step-card__error"
            :title="step._error"
          >
            ⚠ {{ truncate(step._error, 30) }}
          </div>

          <div class="ab-step-card__actions">
            <el-switch
              v-model="step.enabled"
              size="small"
              inline-prompt
              active-text="ON"
              inactive-text="OFF"
              class="ab-switch--cyber"
            />
            <el-button
              :icon="Top"
              size="small"
              text
              class="ab-step-card__btn"
              :disabled="idx === 0"
              @click.stop="moveStep(idx, -1)"
            />
            <el-button
              :icon="Bottom"
              size="small"
              text
              class="ab-step-card__btn"
              :disabled="idx === steps.length - 1"
              @click.stop="moveStep(idx, 1)"
            />
            <el-button
              :icon="Delete"
              size="small"
              text
              type="danger"
              class="ab-step-card__btn"
              @click.stop="removeStep(idx)"
            />
          </div>
        </div>
      </TransitionGroup>

      <div
        v-if="steps.length === 0"
        class="ab-empty"
      >
        <div class="ab-empty__icon">
          ⚡
        </div>
        <p class="ab-empty__text">
          点击「添加步骤」构建关键字驱动用例
        </p>
        <p class="ab-empty__hint">
          选择操作类型 → 关联元素 → 填入数据，无需手写代码
        </p>
      </div>
    </div>

    <div
      v-if="showJsonPreview"
      class="ab-json-preview"
    >
      <div class="ab-json-preview__head">
        <span class="ab-json-preview__label">JSON 输出</span>
        <el-button
          size="small"
          text
          class="ab-btn--cyan"
          @click="copyJson"
        >
          复制
        </el-button>
      </div>
      <pre class="ab-json-preview__code">{{ jsonOutput }}</pre>
    </div>

    <el-dialog
      v-model="showNewCaseDialog"
      title="新建关键字用例"
      width="420px"
      :close-on-click-modal="false"
      class="ab-new-case-dialog"
    >
      <el-form
        label-width="80px"
        label-position="top"
      >
        <el-form-item label="用例名称">
          <el-input
            v-model="newCaseForm.name"
            placeholder="输入用例名称"
          />
        </el-form-item>
        <el-form-item label="基础 URL">
          <el-input
            v-model="newCaseForm.base_url"
            placeholder="https://example.com"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="newCaseForm.description"
            type="textarea"
            :rows="2"
            placeholder="可选"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showNewCaseDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="newCaseLoading"
          @click="createNewCase"
        >
          创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Delete, Download, Top, Bottom, Rank, Check, VideoPlay, VideoPause } from '@element-plus/icons-vue'
import {
  getKWLocators,
  getKWTestCases,
  createKWTestCase,
  getKWActionSteps,
  createKWActionStep,
  updateKWActionStep,
  deleteKWActionStep,
  executeKWTestCase,
  cancelKWExecution,
  getKWExecutionStatus,
  getKWExecutionLogs,
  getKWExecutionSteps,
} from '@/api/kwKeyword'

const ACTION_TYPES = [
  { value: 'click', label: '点击', icon: '👆', needs_element: true, needs_value: false },
  { value: 'input', label: '输入', icon: '⌨️', needs_element: true, needs_value: true },
  { value: 'assert', label: '断言', icon: '✅', needs_element: false, needs_value: false },
  { value: 'hover', label: '悬停', icon: '🖱️', needs_element: true, needs_value: false },
  { value: 'select', label: '选择', icon: '📋', needs_element: true, needs_value: true },
  { value: 'wait', label: '等待元素', icon: '⏳', needs_element: true, needs_value: false },
  { value: 'sleep', label: '休眠', icon: '💤', needs_element: false, needs_value: true },
  { value: 'navigate', label: '导航', icon: '🌐', needs_element: false, needs_value: true },
  { value: 'switch_window', label: '切换窗口', icon: '🪟', needs_element: false, needs_value: true },
  { value: 'switch_frame', label: '切换Frame', icon: '📐', needs_element: false, needs_value: true },
  { value: 'scroll', label: '滚动', icon: '📜', needs_element: true, needs_value: false },
  { value: 'execute_js', label: '执行JS', icon: '⚡', needs_element: false, needs_value: true },
] as const

const ASSERT_TYPES = [
  { value: 'visible', label: '元素可见' },
  { value: 'not_visible', label: '元素不可见' },
  { value: 'text_equals', label: '文本相等' },
  { value: 'text_contains', label: '文本包含' },
  { value: 'attribute_equals', label: '属性相等' },
  { value: 'url_contains', label: 'URL包含' },
  { value: 'title_contains', label: '标题包含' },
  { value: 'element_count', label: '元素数量' },
]

function requiresElement(actionType: string): boolean {
  return ACTION_TYPES.find(a => a.value === actionType)?.needs_element ?? false
}

function requiresValue(actionType: string): boolean {
  return ACTION_TYPES.find(a => a.value === actionType)?.needs_value ?? false
}

function valuePlaceholder(actionType: string): string {
  const map: Record<string, string> = {
    input: '输入内容，如 ${username}',
    select: '选项值',
    sleep: '秒数，如 3',
    navigate: 'URL，如 /login',
    switch_window: '窗口句柄或索引',
    switch_frame: 'Frame ID 或索引',
    execute_js: 'JavaScript 代码',
  }
  return map[actionType] || '操作值'
}

function truncate(str: string, max: number): string {
  if (!str) return ''
  return str.length > max ? str.slice(0, max) + '…' : str
}

interface StepRow {
  _uid: number
  _id?: number
  step_order: number
  action_type: string
  element: number | null
  action_value: string
  assert_type: string
  assert_expected: string
  description: string
  enabled: boolean
  _result?: 'passed' | 'failed' | 'skipped' | 'running' | ''
  _duration?: number
  _error?: string
}

let uidCounter = 0

const props = defineProps<{
  caseId?: number
  caseName?: string
  projectId?: number
  browserType?: string
  headless?: boolean
}>()

const emit = defineEmits<{
  'update:json': [payload: object[]]
  'execution-log': [entry: { timestamp: string; type: string; message: string }]
  'execution-status': [status: string]
  'case-created': [testCase: { id: number; name: string }]
  'case-selected': [caseId: number | null]
}>()

const steps = ref<StepRow[]>([])
const activeStepUid = ref<number | null>(null)
const showJsonPreview = ref(false)
const saveLoading = ref(false)
const executing = ref(false)
const executionId = ref<string | null>(null)
const executionStatus = ref<string>('')

const currentCaseId = ref<number | undefined>(props.caseId)
const testCases = ref<{ id: number; name: string; status_display: string }[]>([])
const showNewCaseDialog = ref(false)
const newCaseLoading = ref(false)
const newCaseForm = ref({ name: '', base_url: '', description: '' })

const statusLabel = computed(() => {
  const map: Record<string, string> = {
    running: '执行中',
    success: '通过',
    failed: '失败',
  }
  return map[executionStatus.value] || executionStatus.value
})

interface LocatorOption {
  id: number
  name: string
  locator_type: string
  locator_type_display: string
  locator_expression: string
}

const locators = ref<LocatorOption[]>([])

async function loadTestCases() {
  if (!props.projectId) return
  try {
    const { data } = await getKWTestCases(props.projectId)
    const list = Array.isArray(data) ? data : (data.results || [])
    testCases.value = list.map((tc: any) => ({
      id: tc.id,
      name: tc.name,
      status_display: tc.status_display || tc.status || '',
    }))
  } catch {
    testCases.value = []
  }
}

async function createNewCase() {
  if (!newCaseForm.value.name.trim()) {
    ElMessage.warning('请输入用例名称')
    return
  }
  if (!props.projectId) {
    ElMessage.warning('请先选择项目')
    return
  }
  newCaseLoading.value = true
  try {
    const { data } = await createKWTestCase({
      project: props.projectId,
      name: newCaseForm.value.name.trim(),
      base_url: newCaseForm.value.base_url.trim(),
      description: newCaseForm.value.description.trim(),
      status: 'draft',
    })
    currentCaseId.value = data.id
    showNewCaseDialog.value = false
    newCaseForm.value = { name: '', base_url: '', description: '' }
    await loadTestCases()
    await loadSteps()
    emit('case-created', { id: data.id, name: data.name })
    ElMessage.success(`用例「${data.name}」已创建`)
  } catch (e: any) {
    const msg = e?.response?.data?.name?.[0] || e?.response?.data?.detail || e?.message || '创建失败'
    ElMessage.error(String(msg))
  } finally {
    newCaseLoading.value = false
  }
}

function onCaseChange(val: number | '') {
  const id = val || undefined
  currentCaseId.value = id
  if (id) {
    loadSteps()
  } else {
    steps.value = []
  }
  emit('case-selected', id ?? null)
}

async function onStop() {
  if (!executionId.value) return
  try {
    await cancelKWExecution(executionId.value)
    ElMessage.info('已发送停止请求')
    emit('execution-log', {
      timestamp: new Date().toISOString(),
      type: 'system',
      message: '用户请求停止执行…',
    })
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '停止失败'
    ElMessage.error(String(msg))
  }
}

async function loadLocators() {
  if (!props.projectId) return
  try {
    const { data } = await getKWLocators(props.projectId)
    const list = Array.isArray(data) ? data : (data.results || [])
    locators.value = list.map((el: any) => ({
      id: el.id,
      name: el.name,
      locator_type: el.locator_type,
      locator_type_display: el.locator_type_display || el.locator_type,
      locator_expression: el.locator_expression || '',
    }))
  } catch {
    locators.value = []
  }
}

async function loadSteps() {
  if (!props.caseId) return
  try {
    const { data } = await getKWActionSteps(props.caseId)
    const list = Array.isArray(data) ? data : (data.results || [])
    steps.value = list.map((s: any) => ({
      _uid: ++uidCounter,
      _id: s.id,
      step_order: s.step_order,
      action_type: s.action_type,
      element: s.element,
      action_value: s.action_value || '',
      assert_type: s.assert_type || '',
      assert_expected: s.assert_expected || '',
      description: s.description || '',
      enabled: s.enabled !== false,
      _result: '',
      _duration: undefined,
      _error: undefined,
    }))
  } catch {
    steps.value = []
  }
}

function createEmptyStep(order: number): StepRow {
  return {
    _uid: ++uidCounter,
    step_order: order,
    action_type: '',
    element: null,
    action_value: '',
    assert_type: '',
    assert_expected: '',
    description: '',
    enabled: true,
    _result: '',
    _duration: undefined,
    _error: undefined,
  }
}

function addStep() {
  const nextOrder = steps.value.length > 0
    ? Math.max(...steps.value.map(s => s.step_order)) + 1
    : 1
  const step = createEmptyStep(nextOrder)
  steps.value.push(step)
  activeStepUid.value = step._uid
}

function removeStep(idx: number) {
  const removed = steps.value.splice(idx, 1)[0]
  if (activeStepUid.value === removed._uid) {
    activeStepUid.value = null
  }
  if (removed._id) {
    deleteKWActionStep(removed._id).catch(() => {})
  }
  reindexSteps()
}

function moveStep(idx: number, direction: -1 | 1) {
  const targetIdx = idx + direction
  if (targetIdx < 0 || targetIdx >= steps.value.length) return
  const temp = steps.value[idx]
  steps.value[idx] = steps.value[targetIdx]
  steps.value[targetIdx] = temp
  reindexSteps()
}

function reindexSteps() {
  steps.value.forEach((s, i) => {
    s.step_order = i + 1
  })
}

function onActionTypeChange(step: StepRow) {
  if (!requiresElement(step.action_type)) {
    step.element = null
  }
  if (!requiresValue(step.action_type)) {
    step.action_value = ''
  }
  if (step.action_type !== 'assert') {
    step.assert_type = ''
    step.assert_expected = ''
  }
}

const jsonOutput = computed(() => {
  return JSON.stringify(exportSteps(), null, 2)
})

function exportSteps(): object[] {
  return steps.value
    .filter(s => s.action_type)
    .map(s => {
      const row: Record<string, unknown> = {
        step: s.step_order,
        action: s.action_type,
        element_id: s.element,
        value: s.action_value,
        enabled: s.enabled,
      }
      if (s.action_type === 'assert') {
        row.assert_type = s.assert_type
        row.expected = s.assert_expected
      }
      if (s.description) {
        row.description = s.description
      }
      return row
    })
}

function exportJson() {
  const payload = exportSteps()
  if (payload.length === 0) {
    ElMessage.warning('无可导出的步骤，请先添加操作')
    return
  }
  emit('update:json', payload)
  showJsonPreview.value = !showJsonPreview.value
}

async function copyJson() {
  try {
    await navigator.clipboard.writeText(jsonOutput.value)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败')
  }
}

async function saveAll() {
  if (!currentCaseId.value) {
    ElMessage.warning('请先创建关键字用例')
    return
  }
  saveLoading.value = true
  try {
    const toCreate = steps.value.filter(s => !s._id && s.action_type)
    const toUpdate = steps.value.filter(s => s._id && s.action_type)

    for (const step of toCreate) {
      const { data } = await createKWActionStep({
        test_case: currentCaseId.value,
        step_order: step.step_order,
        action_type: step.action_type,
        element: step.element || undefined,
        action_value: step.action_value,
        assert_type: step.assert_type || undefined,
        assert_expected: step.assert_expected || undefined,
        description: step.description,
        enabled: step.enabled,
      })
      step._id = data.id
    }

    for (const step of toUpdate) {
      await updateKWActionStep(step._id!, {
        step_order: step.step_order,
        action_type: step.action_type,
        element: step.element || undefined,
        action_value: step.action_value,
        assert_type: step.assert_type || undefined,
        assert_expected: step.assert_expected || undefined,
        description: step.description,
        enabled: step.enabled,
      })
    }

    ElMessage.success(`已保存 ${toCreate.length + toUpdate.length} 个步骤`)
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.response?.data?.element?.[0] || e?.message || '保存失败'
    ElMessage.error(String(msg))
  } finally {
    saveLoading.value = false
  }
}

async function onExecute() {
  if (!currentCaseId.value) {
    ElMessage.warning('请先创建并保存关键字用例')
    return
  }
  if (steps.value.length === 0) {
    ElMessage.warning('请先添加步骤')
    return
  }

  const unsaved = steps.value.filter(s => !s._id && s.action_type)
  if (unsaved.length > 0) {
    await saveAll()
  }

  clearResults()
  executing.value = true
  executionStatus.value = 'running'
  emit('execution-status', 'running')

  steps.value.forEach(s => {
    if (s.action_type) s._result = 'running'
  })

  try {
    const { data } = await executeKWTestCase(currentCaseId.value, {
      browser: props.browserType || 'chrome',
      headless: props.headless !== undefined ? props.headless : true,
    })
    executionId.value = data.execution_id
    startPolling()
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '执行请求失败'
    ElMessage.error(String(msg))
    executing.value = false
    executionStatus.value = 'failed'
    emit('execution-status', 'failed')
    steps.value.forEach(s => {
      if (s._result === 'running') s._result = ''
    })
  }
}

function clearResults() {
  steps.value.forEach(s => {
    s._result = ''
    s._duration = undefined
    s._error = undefined
  })
  executionId.value = null
  executionStatus.value = ''
}

let pollTimer: ReturnType<typeof setTimeout> | null = null
let pollInFlight = false
let lastLogIndex = 0

function startPolling() {
  lastLogIndex = 0
  pollInFlight = false
  pollTick()
}

function stopPolling() {
  if (pollTimer != null) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
  pollInFlight = false
}

async function pollTick() {
  if (!executing.value || !executionId.value) {
    stopPolling()
    return
  }
  if (pollInFlight) return
  pollInFlight = true

  try {
    const [logsRes, statusRes, stepsRes] = await Promise.all([
      getKWExecutionLogs(executionId.value, lastLogIndex, -1),
      getKWExecutionStatus(executionId.value),
      getKWExecutionSteps(executionId.value),
    ])

    const logs = logsRes.data?.logs || []
    for (const entry of logs) {
      emit('execution-log', entry)
    }
    lastLogIndex += logs.length

    const stepResults = stepsRes.data?.steps || []
    for (const sr of stepResults) {
      const step = steps.value.find(s => s.step_order === sr.step)
      if (step) {
        step._result = sr.status
        step._duration = sr.duration_ms
        step._error = sr.error || undefined
      }
    }

    const st = statusRes.data?.status || ''
    if (['success', 'failed', 'cancelled'].includes(st)) {
      stopPolling()
      executing.value = false
      executionStatus.value = st === 'cancelled' ? 'failed' : st
      emit('execution-status', st)

      steps.value.forEach(s => {
        if (s._result === 'running') s._result = ''
      })

      if (st === 'success') {
        ElMessage.success('用例执行通过')
      } else if (st === 'cancelled') {
        ElMessage.info('执行已取消')
      } else {
        ElMessage.error('用例执行失败')
      }
      return
    }

    pollTimer = setTimeout(() => {
      pollInFlight = false
      pollTick()
    }, 500)
  } catch {
    pollTimer = setTimeout(() => {
      pollInFlight = false
      pollTick()
    }, 1000)
  }
}

watch(() => props.caseId, (newId) => {
  currentCaseId.value = newId
  if (newId) {
    loadSteps()
  } else {
    steps.value = []
  }
})

watch(() => props.projectId, () => {
  loadLocators()
  loadTestCases()
})

onMounted(() => {
  loadLocators()
  loadTestCases()
  if (props.caseId) {
    currentCaseId.value = props.caseId
    loadSteps()
  }
})

onBeforeUnmount(() => {
  stopPolling()
})

defineExpose({
  exportSteps,
  steps,
  saveAll,
  onExecute,
  onStop,
  clearResults,
  currentCaseId,
})
</script>

<style scoped>
.action-builder {
  --ab-bg: #0b0d12;
  --ab-surface: rgba(18, 23, 34, 0.75);
  --ab-surface2: #181f2e;
  --ab-border: rgba(148, 163, 184, 0.1);
  --ab-text: #e2e8f0;
  --ab-muted: #94a3b8;
  --ab-cyan: rgba(0, 240, 255, 0.8);
  --ab-cyan-dim: rgba(0, 240, 255, 0.08);
  --ab-cyan-border: rgba(0, 240, 255, 0.18);
  --ab-violet: rgba(167, 139, 250, 0.85);
  --ab-violet-dim: rgba(167, 139, 250, 0.08);
  --ab-violet-border: rgba(167, 139, 250, 0.22);
  --ab-danger: #f87171;
  --ab-success: #4ade80;
  --ab-warning: #fbbf24;
  --ab-radius: 10px;

  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  flex: 1;
}

.ab-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-radius: var(--ab-radius);
  border: 1px solid var(--ab-cyan-border);
  background: var(--ab-surface);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.ab-header__left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.ab-header__tag {
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ab-cyan);
  border: 1px solid var(--ab-cyan-border);
  background: var(--ab-cyan-dim);
  white-space: nowrap;
}

.ab-header__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--ab-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ab-header__count {
  font-size: 12px;
  color: var(--ab-muted);
  white-space: nowrap;
}

.ab-header__status {
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  white-space: nowrap;
}

.ab-header__status--running {
  color: var(--ab-warning);
  background: rgba(251, 191, 36, 0.1);
  border: 1px solid rgba(251, 191, 36, 0.25);
}

.ab-header__status--success {
  color: var(--ab-success);
  background: rgba(74, 222, 128, 0.1);
  border: 1px solid rgba(74, 222, 128, 0.25);
}

.ab-header__status--failed {
  color: var(--ab-danger);
  background: rgba(248, 113, 113, 0.1);
  border: 1px solid rgba(248, 113, 113, 0.25);
}

.ab-header__right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.ab-btn--cyan {
  border-color: var(--ab-cyan-border) !important;
  color: var(--ab-text) !important;
  background: var(--ab-cyan-dim) !important;
}
.ab-btn--cyan:hover {
  border-color: var(--ab-cyan) !important;
  box-shadow: 0 0 12px rgba(0, 240, 255, 0.15);
}

.ab-btn--save {
  border-color: rgba(74, 222, 128, 0.25) !important;
  color: var(--ab-text) !important;
  background: rgba(74, 222, 128, 0.08) !important;
}
.ab-btn--save:hover {
  border-color: rgba(74, 222, 128, 0.6) !important;
  box-shadow: 0 0 12px rgba(74, 222, 128, 0.15);
}

.ab-btn--exec {
  border-color: rgba(251, 191, 36, 0.25) !important;
  color: var(--ab-text) !important;
  background: rgba(251, 191, 36, 0.08) !important;
}
.ab-btn--exec:hover {
  border-color: rgba(251, 191, 36, 0.6) !important;
  box-shadow: 0 0 12px rgba(251, 191, 36, 0.15);
}

.ab-btn--violet {
  border-color: var(--ab-violet-border) !important;
  color: var(--ab-text) !important;
  background: var(--ab-violet-dim) !important;
}
.ab-btn--violet:hover {
  border-color: var(--ab-violet) !important;
  box-shadow: 0 0 12px rgba(167, 139, 250, 0.2);
}

.ab-btn--new-case {
  border-color: rgba(74, 222, 128, 0.25) !important;
  color: rgba(74, 222, 128, 0.85) !important;
  background: rgba(74, 222, 128, 0.06) !important;
  font-size: 12px;
  font-weight: 600;
}
.ab-btn--new-case:hover {
  border-color: rgba(74, 222, 128, 0.5) !important;
  color: rgba(74, 222, 128, 1) !important;
  box-shadow: 0 0 10px rgba(74, 222, 128, 0.15);
}

.ab-btn--stop {
  border-color: rgba(248, 113, 113, 0.3) !important;
  color: var(--ab-text) !important;
  background: rgba(248, 113, 113, 0.08) !important;
}
.ab-btn--stop:hover {
  border-color: rgba(248, 113, 113, 0.6) !important;
  box-shadow: 0 0 12px rgba(248, 113, 113, 0.2);
}

.ab-case-select {
  width: 180px;
}
.ab-case-select :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.04) !important;
  box-shadow: none !important;
  border-radius: 6px;
}
.ab-case-select :deep(.el-input__inner) {
  color: var(--ab-text);
  font-size: 13px;
  font-weight: 600;
}
.ab-case-select :deep(.el-input__inner::placeholder) {
  color: var(--ab-muted);
  opacity: 0.7;
}

.ab-case-option__name {
  font-size: 13px;
  font-weight: 500;
  color: var(--ab-text);
}

.ab-case-option__status {
  margin-left: 8px;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  color: var(--ab-muted);
  background: rgba(148, 163, 184, 0.08);
  border: 1px solid rgba(148, 163, 184, 0.12);
}

.ab-step-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 2px 0;
}

.ab-step-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: var(--ab-radius);
  border: 1px solid var(--ab-border);
  background: var(--ab-surface);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
}

.ab-step-card:hover {
  border-color: var(--ab-cyan-border);
  background: rgba(0, 240, 255, 0.03);
}

.ab-step-card--active {
  border-color: var(--ab-cyan) !important;
  box-shadow: 0 0 0 1px rgba(0, 240, 255, 0.12), 0 0 16px rgba(0, 240, 255, 0.1);
  background: rgba(0, 240, 255, 0.04);
}

.ab-step-card--disabled {
  opacity: 0.4;
}

.ab-step-card--passed {
  border-color: rgba(74, 222, 128, 0.3) !important;
  background: rgba(74, 222, 128, 0.04);
}

.ab-step-card--failed {
  border-color: rgba(248, 113, 113, 0.4) !important;
  background: rgba(248, 113, 113, 0.04);
}

.ab-step-card--skipped {
  opacity: 0.55;
}

.ab-step-card--running {
  border-color: rgba(251, 191, 36, 0.35) !important;
  background: rgba(251, 191, 36, 0.04);
  animation: ab-pulse 1.5s ease-in-out infinite;
}

@keyframes ab-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(251, 191, 36, 0); }
  50% { box-shadow: 0 0 12px rgba(251, 191, 36, 0.15); }
}

.ab-step-card__grip {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  color: var(--ab-muted);
  cursor: grab;
  transition: color 0.15s, background 0.15s;
}
.ab-step-card__grip:hover {
  color: var(--ab-cyan);
  background: var(--ab-cyan-dim);
}
.ab-step-card__grip:active {
  cursor: grabbing;
}

.ab-step-card__order {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: var(--ab-cyan);
  background: var(--ab-cyan-dim);
  border: 1px solid var(--ab-cyan-border);
}

.ab-step-card__field {
  flex-shrink: 0;
  min-width: 0;
}
.ab-step-card__field--action { width: 120px; }
.ab-step-card__field--locator { width: 170px; }
.ab-step-card__field--value { width: 140px; }
.ab-step-card__field--assert-type { width: 120px; }
.ab-step-card__field--assert-expected { width: 120px; }
.ab-step-card__field--desc { flex: 1; min-width: 60px; }

.ab-step-card__duration {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 600;
  color: var(--ab-muted);
  font-family: ui-monospace, Consolas, monospace;
}

.ab-step-card__error {
  flex-shrink: 1;
  min-width: 0;
  max-width: 180px;
  font-size: 10px;
  color: var(--ab-danger);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ab-step-card__actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 2px;
  margin-left: auto;
}

.ab-step-card__btn {
  color: var(--ab-muted) !important;
}
.ab-step-card__btn:hover {
  color: var(--ab-text) !important;
}

.ab-select--cyber :deep(.el-input__wrapper),
.ab-input--cyber :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.04) !important;
  box-shadow: none !important;
  border-radius: 6px;
}

.ab-select--cyber :deep(.el-input__inner),
.ab-input--cyber :deep(.el-input__inner) {
  color: var(--ab-text);
  font-size: 12px;
}

.ab-select--cyber :deep(.el-input__inner::placeholder),
.ab-input--cyber :deep(.el-input__inner::placeholder) {
  color: var(--ab-muted);
  opacity: 0.7;
}

.ab-switch--cyber :deep(.el-switch.is-checked .el-switch__core) {
  background-color: var(--ab-cyan);
  border-color: var(--ab-cyan);
}

.ab-locator-option {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.ab-locator-option__type {
  flex-shrink: 0;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--ab-cyan);
  background: var(--ab-cyan-dim);
  border: 1px solid var(--ab-cyan-border);
}

.ab-locator-option__name {
  font-size: 13px;
  font-weight: 500;
  color: var(--ab-text);
}

.ab-locator-option__expr {
  font-size: 11px;
  color: var(--ab-muted);
  font-family: ui-monospace, Consolas, monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 160px;
}

.ab-option__icon {
  margin-right: 6px;
}

.ab-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  gap: 8px;
}

.ab-empty__icon {
  font-size: 40px;
  filter: drop-shadow(0 0 12px rgba(0, 240, 255, 0.4));
}

.ab-empty__text {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--ab-text);
}

.ab-empty__hint {
  margin: 0;
  font-size: 12px;
  color: var(--ab-muted);
  text-align: center;
  max-width: 320px;
  line-height: 1.55;
}

.ab-json-preview {
  border-radius: var(--ab-radius);
  border: 1px solid var(--ab-violet-border);
  background: rgba(167, 139, 250, 0.04);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  padding: 10px 14px;
}

.ab-json-preview__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.ab-json-preview__label {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ab-violet);
}

.ab-json-preview__code {
  margin: 0;
  padding: 10px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.3);
  color: rgba(167, 243, 208, 0.9);
  font-family: ui-monospace, 'JetBrains Mono', Consolas, monospace;
  font-size: 12px;
  line-height: 1.55;
  overflow-x: auto;
  max-height: 200px;
  overflow-y: auto;
}

.ab-step-enter-active { transition: all 0.25s ease; }
.ab-step-leave-active { transition: all 0.2s ease; }
.ab-step-enter-from { opacity: 0; transform: translateY(-12px); }
.ab-step-leave-to { opacity: 0; transform: translateX(20px); }
.ab-step-move { transition: transform 0.25s ease; }

.ab-step-list::-webkit-scrollbar,
.ab-json-preview__code::-webkit-scrollbar {
  width: 5px;
}
.ab-step-list::-webkit-scrollbar-thumb,
.ab-json-preview__code::-webkit-scrollbar-thumb {
  background: rgba(0, 240, 255, 0.25);
  border-radius: 4px;
}
</style>
