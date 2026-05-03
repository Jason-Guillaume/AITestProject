<template>
  <div class="pipeline-console">
    <header class="pc-header">
      <span class="pc-title">PIPELINE // LOG STREAM</span>
      <span v-if="pipelineId" class="pc-meta">
        ID {{ pipelineId }} · {{ statusLabel }} · {{ modeLabel }}
      </span>
    </header>
    <div class="pc-panel" ref="logPanelRef" role="log" aria-live="polite">
      <div v-for="(line, idx) in lines" :key="idx" class="pc-line">{{ line }}</div>
      <div v-if="!lines.length" class="pc-empty">等待日志输出…</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, computed, nextTick } from 'vue'
import request from '@/utils/request'

const props = withDefaults(
  defineProps<{
    pipelineId: number
    /** 使用 HTTP 轮询（适合无 WebSocket 的 2C2G 部署） */
    usePolling?: boolean
    pollIntervalMs?: number
    /** 递增后清空本地日志并从开头轮询（如：清空服务端日志后再次构建） */
    resetNonce?: number
  }>(),
  {
    usePolling: true,
    pollIntervalMs: 1500,
    resetNonce: 0,
  }
)

const lines = ref<string[]>([])
const logPanelRef = ref<HTMLElement | null>(null)
const pipelineStatus = ref<number | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null
let lastLogId = 0

const statusLabel = computed(() => {
  const m: Record<number, string> = {
    0: 'Pending',
    1: 'Running',
    2: 'Success',
    3: 'Fail',
  }
  if (pipelineStatus.value == null) return '—'
  return m[pipelineStatus.value] ?? String(pipelineStatus.value)
})

const modeLabel = computed(() => (props.usePolling ? 'POLL' : 'WS'))

function scrollToBottom() {
  nextTick(() => {
    const el = logPanelRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

async function fetchLogs() {
  if (!props.pipelineId) return
  try {
    const { data } = await request.get(`/project/pipelines/${props.pipelineId}/logs/`, {
      params: { after_id: lastLogId, limit: 500 },
    })
    pipelineStatus.value =
      typeof data?.pipeline_status === 'number' ? data.pipeline_status : null
    const items = Array.isArray(data?.items) ? data.items : []
    for (const row of items) {
      const text = row?.log_text ?? ''
      if (text) lines.value.push(String(text))
    }
    if (typeof data?.last_log_id === 'number' && data.last_log_id > lastLogId) {
      lastLogId = data.last_log_id
    }
    if (lines.value.length > 8000) {
      lines.value.splice(0, lines.value.length - 8000)
    }
    scrollToBottom()
  } catch {
    /* 轮询失败时静默，避免刷屏 */
  }
}

function startPolling() {
  stopPolling()
  if (!props.usePolling || !props.pipelineId) return
  lastLogId = 0
  lines.value = []
  void fetchLogs()
  pollTimer = setInterval(fetchLogs, props.pollIntervalMs)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

watch(
  () => [props.pipelineId, props.usePolling, props.pollIntervalMs] as const,
  () => {
    lastLogId = 0
    lines.value = []
    if (props.usePolling) startPolling()
    else stopPolling()
  }
)

watch(
  () => props.resetNonce,
  () => {
    lastLogId = 0
    lines.value = []
    if (props.usePolling) startPolling()
  }
)

onMounted(() => {
  if (props.usePolling) startPolling()
})

onBeforeUnmount(() => {
  stopPolling()
})

watch(
  () => lines.value.length,
  () => scrollToBottom()
)
</script>

<style scoped>
.pipeline-console {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 280px;
  background: #0a1628;
  border: 1px solid rgba(0, 240, 255, 0.55);
  box-shadow:
    0 0 0 1px rgba(0, 240, 255, 0.12),
    0 0 24px rgba(0, 240, 255, 0.08);
  border-radius: 10px;
  color: #e0f7ff;
  font-family: ui-monospace, 'Cascadia Code', 'Source Code Pro', Menlo, monospace;
}

.pc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid rgba(0, 240, 255, 0.35);
  background: linear-gradient(180deg, rgba(0, 240, 255, 0.08), transparent);
}

.pc-title {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.14em;
  color: #5ffbf1;
  text-shadow: 0 0 12px rgba(95, 251, 241, 0.45);
}

.pc-meta {
  font-size: 11px;
  color: rgba(224, 247, 255, 0.75);
}

.pc-panel {
  flex: 1;
  overflow: auto;
  padding: 12px 14px;
  background: #050a12;
  border-radius: 0 0 9px 9px;
}

.pc-line {
  margin: 0 0 4px;
  font-size: 12px;
  line-height: 1.45;
  white-space: pre-wrap;
  word-break: break-word;
  color: #c8fff7;
  text-shadow: 0 0 6px rgba(0, 240, 255, 0.15);
}

.pc-empty {
  font-size: 12px;
  color: rgba(200, 255, 247, 0.35);
  font-style: italic;
}
</style>
