<template>
  <div
    class="report-depth report-depth--cyber"
    :class="{ 'report-depth--low-perf': lowPerfMode }"
  >
    <header class="report-depth__bar glass-panel">
      <span class="report-depth__id">Execution · {{ reportIdDisplay }}</span>
      <span class="report-depth__badge">
        {{ headerBadge }}
      </span>
      <span
        v-if="lowPerfMode"
        class="report-depth__perf-hint"
      >性能模式</span>
    </header>

    <div
      v-if="showBlockingLoader"
      class="report-depth__loader-wrap glass-panel"
    >
      <div
        class="cyber-loader cyber-loader--lite"
        :class="{ 'cyber-loader--static-core': lowPerfMode }"
        aria-hidden="true"
      >
        <span class="cyber-loader__ring cyber-loader__ring--a" />
        <span class="cyber-loader__core" />
      </div>
      <p class="report-depth__loader-text">
        {{ blockingLoaderText }}
      </p>
    </div>

    <div
      v-else
      class="report-depth__tri"
    >
      <aside class="report-depth__col report-depth__col--steps report-depth__step-flow step-flow">
        <h2 class="report-depth__h">
          StepFlow
        </h2>
        <p
          v-if="steps.length > 8"
          class="step-flow__hint"
        >
          虚拟列表 · 仅渲染可视区
        </p>
        <el-empty
          v-if="steps.length === 0"
          description="暂无步骤"
          :image-size="48"
        />
        <div
          v-else
          ref="stepScrollRef"
          class="step-flow-virtual"
          @scroll.passive="onStepsScroll"
        >
          <div
            class="step-flow-virtual__sizer"
            :style="{ height: `${virtualTotalHeight}px` }"
          >
            <div
              class="step-flow-virtual__window"
              :style="{ transform: `translateY(${virtualOffsetY}px)` }"
            >
              <div
                v-for="v in virtualItems"
                :key="v.step.id + '-' + v.index"
                class="step-flow-virtual__row"
              >
                <span class="step-flow-virtual__idx">Step {{ v.step.order }}</span>
                <button
                  type="button"
                  class="step-select-btn"
                  :class="{ 'is-active': selectedStepIndex === v.index }"
                  @click="selectStep(v.index)"
                >
                  <span class="step-label">{{ v.step.title }}</span>
                  <span
                    v-if="v.step.subtitle"
                    class="step-sub"
                  >{{ v.step.subtitle }}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </aside>

      <section class="report-depth__col report-depth__col--media report-depth__evidence-viewer evidence-viewer">
        <div class="report-depth__media-head">
          <h2 class="report-depth__h">
            EvidenceViewer
          </h2>
          <el-radio-group
            v-model="mediaMode"
            size="small"
          >
            <el-radio-button value="image">
              Image
            </el-radio-button>
            <el-radio-button value="video">
              Video
            </el-radio-button>
          </el-radio-group>
        </div>
        <div class="report-depth__media-body">
          <template v-if="mediaMode === 'image'">
            <div
              v-if="evidenceImageLoading"
              class="media-state media-state--loading"
            >
              <div
                class="cyber-loader cyber-loader--sm cyber-loader--lite"
                aria-hidden="true"
              >
                <span class="cyber-loader__ring cyber-loader__ring--a" />
              </div>
              <span>加载截图…</span>
            </div>
            <div
              v-else-if="evidenceImageError"
              class="media-state media-state--error"
            >
              {{ evidenceImageError }}
            </div>
            <img
              v-else-if="evidenceObjectUrl"
              class="evidence-img"
              :src="evidenceObjectUrl"
              alt="step evidence"
            >
            <div
              v-else
              class="media-state"
            >
              当前步骤无截图（可查看 Telemetry 文本或右侧堆栈）
            </div>
          </template>
          <template v-else>
            <div
              v-if="videoUrl"
              class="media-state"
            >
              <video
                class="evidence-video"
                controls
                :src="videoUrl"
              />
            </div>
            <div
              v-else
              class="media-state"
            >
              暂无录像证据
            </div>
          </template>
        </div>
      </section>

      <aside class="report-depth__col report-depth__col--ai report-depth__diagnostic-panel diagnostic-panel">
        <h2 class="report-depth__h">
          DiagnosticPanel
        </h2>
        <section class="diag-block">
          <h3 class="diag-block__h">
            Stack / stderr
          </h3>
          <pre class="diag-block__pre">{{ stackTraceDisplay }}</pre>
        </section>
        <section class="diag-block">
          <h3 class="diag-block__h">
            AI 修复建议
          </h3>
          <p
            v-if="aiLoading"
            class="diag-block__ai diag-block__ai--muted"
          >
            正在请求模型诊断…
          </p>
          <p
            v-else-if="aiError"
            class="diag-block__ai diag-block__ai--warn"
          >
            {{ aiError }}
          </p>
          <p
            v-else
            class="diag-block__ai"
          >
            {{ aiSuggestion || '（无失败信息时跳过 AI 诊断）' }}
          </p>
        </section>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  getAnalysisLabReportDetailsApi,
  postUiExecutionDiagnoseApi,
} from '@/api/analysisLab'

const route = useRoute()
const mediaMode = ref<'image' | 'video'>('image')

/** 虚拟列表行高（与 .step-flow-virtual__row 样式一致） */
const STEP_ROW_HEIGHT = 80

const reportIdDisplay = computed(() => {
  const id = route.params.id
  return id != null && String(id) !== '' ? String(id) : '—'
})

interface ReportStep {
  id: string
  order: number
  title: string
  status?: string
  subtitle?: string
  screenshot_url?: string | null
  relpath?: string | null
}

interface ReportExecution {
  id?: number
  status?: string
  script_name?: string
  return_code?: number | null
}

const loadError = ref('')
const detailLoading = ref(true)
const reportStatus = ref<'generating' | 'ready' | ''>('')
const steps = ref<ReportStep[]>([])
const stackTrace = ref('')
const executionMeta = ref<ReportExecution | null>(null)
const videoUrl = ref<string | null>(null)

const selectedStepIndex = ref(0)
const evidenceObjectUrl = ref<string | null>(null)
const evidenceImageLoading = ref(false)
const evidenceImageError = ref('')

const aiSuggestion = ref('')
const aiLoading = ref(false)
const aiError = ref('')

const lowPerfMode = ref(false)
const stepScrollRef = ref<HTMLElement | null>(null)
const stepsScrollTop = ref(0)

let pollTimer: ReturnType<typeof setInterval> | null = null
let detailAbortController: AbortController | null = null
let diagnoseAbortController: AbortController | null = null
let evidenceFetchController: AbortController | null = null
let memCheckTimer: ReturnType<typeof setInterval> | null = null

const POLL_MS_NORMAL = 2200
const POLL_MS_LOW = 4000

function checkMemoryPressure(): boolean {
  try {
    const m = (performance as unknown as { memory?: { usedJSHeapSize: number; jsHeapSizeLimit: number } }).memory
    if (m && m.jsHeapSizeLimit > 0) {
      return m.usedJSHeapSize / m.jsHeapSizeLimit >= 0.8
    }
  } catch {
    /* Chromium 以外常无 memory */
  }
  const dm = (navigator as unknown as { deviceMemory?: number }).deviceMemory
  if (dm != null && dm <= 4) return true
  return false
}

function refreshLowPerf() {
  lowPerfMode.value =
    checkMemoryPressure() ||
    steps.value.length > 40 ||
    (stackTrace.value?.length ?? 0) > 6000
}

const showBlockingLoader = computed(() => {
  if (detailLoading.value) return true
  if (reportStatus.value === 'generating') return true
  return false
})

const blockingLoaderText = computed(() => {
  if (detailLoading.value) return '正在连接 Telemetry 归档…'
  if (reportStatus.value === 'generating') return '报告生成中 · 等待 Runner 落盘…'
  return ''
})

const headerBadge = computed(() => {
  if (loadError.value) return '加载失败'
  if (reportStatus.value === 'generating') return '状态：生成中'
  const st = executionMeta.value?.status
  if (st) return `状态：${st}`
  return 'Telemetry → Artifacts 深度视图'
})

const stackTraceDisplay = computed(() => {
  if (loadError.value) return loadError.value
  let t = stackTrace.value || '—'
  const max = lowPerfMode.value ? 4000 : 10000
  if (t.length > max) {
    t = `${t.slice(0, max)}\n…(已截断以降低内存占用)`
  }
  return t
})

const virtualTotalHeight = computed(() => Math.max(0, steps.value.length * STEP_ROW_HEIGHT))

const virtualItems = computed(() => {
  const list = steps.value
  const el = stepScrollRef.value
  const viewH = el?.clientHeight ?? 360
  const st = stepsScrollTop.value
  const overscan = 3
  const start = Math.max(0, Math.floor(st / STEP_ROW_HEIGHT) - overscan)
  const visibleCount = Math.ceil(viewH / STEP_ROW_HEIGHT) + overscan * 2
  const end = Math.min(list.length, start + visibleCount)
  const slice = list.slice(start, end)
  return slice.map((step, i) => ({ index: start + i, step }))
})

const virtualOffsetY = computed(() => {
  const start = virtualItems.value[0]?.index ?? 0
  return start * STEP_ROW_HEIGHT
})

function onStepsScroll(ev: Event) {
  const t = ev.target as HTMLElement
  stepsScrollTop.value = t.scrollTop
}

function abortDetail() {
  detailAbortController?.abort()
  detailAbortController = null
}

function abortDiagnose() {
  diagnoseAbortController?.abort()
  diagnoseAbortController = null
}

function abortEvidence() {
  evidenceFetchController?.abort()
  evidenceFetchController = null
}

function selectStep(idx: number) {
  selectedStepIndex.value = idx
}

function revokeEvidenceUrl() {
  if (evidenceObjectUrl.value) {
    try {
      URL.revokeObjectURL(evidenceObjectUrl.value)
    } catch {
      /* ignore */
    }
    evidenceObjectUrl.value = null
  }
}

function sameOriginEvidenceUrl(raw: string): string {
  try {
    const u = new URL(raw, window.location.origin)
    if (u.origin !== window.location.origin) {
      return `${u.pathname}${u.search}`
    }
    return u.href
  } catch {
    return raw
  }
}

async function loadEvidenceForStep(step: ReportStep | undefined) {
  abortEvidence()
  revokeEvidenceUrl()
  evidenceImageError.value = ''
  if (!step?.screenshot_url) {
    evidenceImageLoading.value = false
    return
  }
  evidenceFetchController = new AbortController()
  const sig = evidenceFetchController.signal
  evidenceImageLoading.value = true
  try {
    const token = localStorage.getItem('token')
    const res = await fetch(sameOriginEvidenceUrl(step.screenshot_url), {
      signal: sig,
      headers: token ? { Authorization: `Token ${token}` } : {},
    })
    if (sig.aborted) return
    if (!res.ok) {
      evidenceImageError.value = `截图加载失败（HTTP ${res.status}）`
      return
    }
    const blob = await res.blob()
    if (sig.aborted) return
    evidenceObjectUrl.value = URL.createObjectURL(blob)
  } catch (e: unknown) {
    if (e instanceof DOMException && e.name === 'AbortError') return
    evidenceImageError.value = '截图加载异常'
  } finally {
    if (!sig.aborted) evidenceImageLoading.value = false
  }
}

function clearPoll() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function startPoll() {
  clearPoll()
  const ms = lowPerfMode.value ? POLL_MS_LOW : POLL_MS_NORMAL
  pollTimer = setInterval(async () => {
    try {
      await fetchDetailsOnce()
      if (reportStatus.value !== 'generating') clearPoll()
    } catch {
      /* 保留轮询 */
    }
  }, ms)
}

async function fetchDetailsOnce() {
  const id = route.params.id
  if (id == null || String(id) === '') {
    loadError.value = '缺少报告 ID'
    detailLoading.value = false
    return
  }

  abortDetail()
  detailAbortController = new AbortController()
  const signal = detailAbortController.signal

  const wasGenerating = reportStatus.value === 'generating'
  try {
    const { data } = await getAnalysisLabReportDetailsApi(String(id), { signal })
    reportStatus.value = data.status === 'generating' ? 'generating' : 'ready'
    steps.value = Array.isArray(data.steps) ? data.steps : []
    stackTrace.value = String(data.stack_trace || '')
    executionMeta.value = data.execution || null
    videoUrl.value = data.video_url || null

    refreshLowPerf()

    if (selectedStepIndex.value >= steps.value.length) {
      selectedStepIndex.value = 0
    }
    stepsScrollTop.value = 0
    await nextTick()
    if (stepScrollRef.value) stepScrollRef.value.scrollTop = 0

    await loadEvidenceForStep(steps.value[selectedStepIndex.value])

    if (wasGenerating && data.status !== 'generating' && !aiSuggestion.value) {
      void maybeRunAiDiagnose()
    }
  } catch (e: unknown) {
    if (axios.isCancel(e)) return
    const err = e as { response?: { status?: number; data?: { detail?: string } }; message?: string }
    const msg =
      err.response?.data?.detail ||
      err.message ||
      '加载报告详情失败'
    loadError.value = String(msg)
    reportStatus.value = ''
    steps.value = []
  }
}

async function loadDetail() {
  abortDetail()
  abortDiagnose()
  clearPoll()

  loadError.value = ''
  detailLoading.value = true
  aiSuggestion.value = ''
  aiError.value = ''
  stackTrace.value = ''
  steps.value = []
  executionMeta.value = null

  try {
    await fetchDetailsOnce()
  } finally {
    detailLoading.value = false
  }

  if (reportStatus.value === 'generating') {
    startPoll()
  }

  void maybeRunAiDiagnose()
}

function shouldRunAiDiagnose(): boolean {
  const st = String(executionMeta.value?.status || '')
  if (['failed', 'timeout'].includes(st)) return true
  const t = stackTrace.value.trim()
  if (t.length < 24) return false
  if (t.includes('暂无错误堆栈')) return false
  return true
}

async function maybeRunAiDiagnose() {
  if (!shouldRunAiDiagnose()) return
  abortDiagnose()
  diagnoseAbortController = new AbortController()
  const signal = diagnoseAbortController.signal

  aiLoading.value = true
  aiError.value = ''
  try {
    const { data } = await postUiExecutionDiagnoseApi(
      {
        stack_trace: stackTrace.value.slice(0, lowPerfMode.value ? 6000 : 12000),
        script_name: executionMeta.value?.script_name || '',
      },
      { signal },
    )
    if (signal.aborted) return
    if (data.success && data.suggestion) {
      aiSuggestion.value = String(data.suggestion)
    } else {
      aiError.value = String(data.message || '诊断未返回内容')
    }
  } catch (e: unknown) {
    if (axios.isCancel(e)) return
    const err = e as { response?: { data?: { message?: string } }; message?: string }
    aiError.value = String(err.response?.data?.message || err.message || 'AI 诊断请求失败')
  } finally {
    if (!signal.aborted) aiLoading.value = false
  }
}

watch(
  () => route.params.id,
  () => {
    void loadDetail()
  },
)

watch(selectedStepIndex, (idx) => {
  void loadEvidenceForStep(steps.value[idx])
})

watch(lowPerfMode, () => {
  if (pollTimer && reportStatus.value === 'generating') {
    startPoll()
  }
})

onMounted(() => {
  refreshLowPerf()
  memCheckTimer = window.setInterval(() => {
    refreshLowPerf()
  }, 8000)
  void loadDetail()
})

function purgeLargeState() {
  stackTrace.value = ''
  steps.value = []
  executionMeta.value = null
  videoUrl.value = null
  aiSuggestion.value = ''
  aiError.value = ''
  loadError.value = ''
}

onBeforeUnmount(() => {
  abortDetail()
  abortDiagnose()
  abortEvidence()
  clearPoll()
  if (memCheckTimer) {
    clearInterval(memCheckTimer)
    memCheckTimer = null
  }
  revokeEvidenceUrl()
  purgeLargeState()
  try {
    const w = window as unknown as { gc?: () => void }
    if (typeof w.gc === 'function') w.gc()
  } catch {
    /* ignore */
  }
})
</script>

<style scoped>
.report-depth--cyber {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px 20px 24px;
  min-height: 0;
  color: rgba(255, 255, 255, 0.9);
}

.report-depth--low-perf .glass-panel,
.report-depth--low-perf .report-depth__col {
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
}

.report-depth--low-perf .report-depth__loader-text {
  text-shadow: none;
}

.glass-panel {
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(12, 18, 32, 0.45);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.report-depth__bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
}

.report-depth__perf-hint {
  margin-left: auto;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: rgba(251, 191, 36, 0.9);
  border: 1px solid rgba(251, 191, 36, 0.35);
  padding: 4px 8px;
  border-radius: 6px;
}

.report-depth__id {
  font-family: ui-monospace, 'JetBrains Mono', Consolas, monospace;
  font-size: 13px;
  color: #00f0ff;
}

.report-depth__badge {
  font-size: 11px;
  letter-spacing: 0.08em;
  color: rgba(167, 139, 250, 0.95);
}

.report-depth__loader-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  min-height: 420px;
  padding: 40px 24px;
}

.report-depth__loader-text {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0.1em;
  color: rgba(0, 240, 255, 0.75);
}

.cyber-loader {
  position: relative;
  width: 72px;
  height: 72px;
}

.cyber-loader--lite .cyber-loader__ring {
  box-shadow: none;
}

.cyber-loader--sm {
  width: 40px;
  height: 40px;
}

.cyber-loader__ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid transparent;
  animation: cyber-spin 2.8s linear infinite;
}

.cyber-loader--lite .cyber-loader__ring {
  animation-duration: 3.2s;
}

.report-depth--low-perf .cyber-loader__ring {
  animation: none;
  border-top-color: rgba(0, 240, 255, 0.65);
  transform: rotate(45deg);
}

.cyber-loader__ring--a {
  border-top-color: rgba(0, 240, 255, 0.85);
  border-right-color: rgba(0, 240, 255, 0.12);
}

.cyber-loader__core {
  position: absolute;
  inset: 24px;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 30%, rgba(0, 240, 255, 0.28), rgba(12, 18, 32, 0.15));
  opacity: 0.9;
}

.cyber-loader--sm .cyber-loader__core {
  display: none;
}

.cyber-loader--static-core .cyber-loader__core {
  animation: none;
}

.report-depth--low-perf .cyber-loader__core {
  opacity: 0.5;
}

@keyframes cyber-spin {
  to {
    transform: rotate(360deg);
  }
}

.report-depth__tri {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr) 400px;
  gap: 14px;
  min-height: 420px;
  flex: 1;
}

.report-depth__col {
  border-radius: 10px;
  border: 1px solid rgba(0, 240, 255, 0.12);
  background: rgba(12, 18, 32, 0.35);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  padding: 12px 14px;
  min-height: 0;
  overflow: auto;
  box-shadow:
    0 0 0 1px rgba(0, 240, 255, 0.06) inset,
    0 8px 28px rgba(0, 0, 0, 0.35);
}

.report-depth__col--steps {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.report-depth__h {
  margin: 0 0 12px;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(0, 240, 255, 0.8);
}

.step-flow__hint {
  margin: -6px 0 8px;
  font-size: 10px;
  color: rgba(148, 163, 184, 0.65);
}

.step-flow-virtual {
  flex: 1;
  min-height: 200px;
  max-height: min(52vh, 480px);
  overflow-y: auto;
  overflow-x: hidden;
  contain: strict;
}

.step-flow-virtual__sizer {
  position: relative;
  width: 100%;
}

.step-flow-virtual__window {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  will-change: transform;
}

.step-flow-virtual__row {
  height: 80px;
  box-sizing: border-box;
  padding: 4px 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.step-flow-virtual__idx {
  font-size: 10px;
  letter-spacing: 0.08em;
  color: rgba(148, 163, 184, 0.7);
}

.step-select-btn {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  width: 100%;
  flex: 1;
  min-height: 0;
  margin: 0;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.2);
  color: inherit;
  cursor: pointer;
  text-align: left;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.step-select-btn:hover {
  border-color: rgba(0, 240, 255, 0.35);
}

.step-select-btn.is-active {
  border-color: rgba(0, 240, 255, 0.55);
  box-shadow: 0 0 14px rgba(0, 240, 255, 0.18);
}

.step-label {
  font-size: 13px;
  color: rgba(226, 232, 240, 0.92);
}

.step-sub {
  font-size: 10px;
  color: rgba(148, 163, 184, 0.75);
  word-break: break-all;
}

.report-depth__media-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.report-depth__media-body {
  min-height: 280px;
  border-radius: 8px;
  border: 1px dashed rgba(255, 255, 255, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.media-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 24px;
  font-size: 13px;
  color: rgba(148, 163, 184, 0.9);
  text-align: center;
}

.media-state--error {
  color: rgba(248, 113, 113, 0.9);
}

.evidence-img {
  max-width: 100%;
  max-height: min(62vh, 520px);
  object-fit: contain;
  display: block;
}

.evidence-video {
  max-width: 100%;
  max-height: min(62vh, 520px);
}

.diag-block {
  margin-bottom: 14px;
}

.diag-block__h {
  margin: 0 0 6px;
  font-size: 12px;
  color: rgba(203, 213, 225, 0.95);
}

.diag-block__pre {
  margin: 0;
  padding: 10px;
  font-size: 11px;
  line-height: 1.45;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.35);
  color: rgba(248, 113, 113, 0.9);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 280px;
  overflow: auto;
  content-visibility: auto;
}

.report-depth--low-perf .diag-block__pre {
  max-height: 200px;
}

.diag-block__ai {
  margin: 0;
  font-size: 12px;
  line-height: 1.55;
  color: rgba(167, 139, 250, 0.95);
}

.diag-block__ai--muted {
  color: rgba(148, 163, 184, 0.85);
}

.diag-block__ai--warn {
  color: rgba(251, 191, 36, 0.95);
}

@media (max-width: 1100px) {
  .report-depth__tri {
    grid-template-columns: 1fr;
  }
}
</style>
