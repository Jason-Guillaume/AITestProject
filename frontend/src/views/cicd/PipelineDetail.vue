<template>
  <div
    class="cicd-detail cicd-detail--cyber min-h-[calc(100vh-120px)] bg-slate-900 text-slate-100 px-4 pb-6 pt-4 box-border selection:bg-cyan-500/30"
  >
    <header class="cicd-detail__header mb-4 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="cicd-detail__title">
          流水线日志 <span class="cicd-detail__en">Run / Logs</span>
        </h1>
        <p class="cicd-detail__meta text-sm text-slate-400">
          ID {{ pipelineId }}
          <template v-if="pipeline?.name"> · {{ pipeline.name }}</template>
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <el-button size="small" class="!bg-slate-800 !border-slate-600" @click="goBack">
          <el-icon class="el-icon--left"><ArrowLeft /></el-icon>
          返回列表
        </el-button>
        <el-button type="primary" size="small" :loading="triggering" @click="onTrigger">
          <el-icon class="el-icon--left"><VideoPlay /></el-icon>
          立即执行
        </el-button>
      </div>
    </header>

    <section
      v-loading="loading"
      class="rounded-xl border border-cyan-500/15 bg-gradient-to-br from-slate-950/95 via-slate-900/90 to-slate-950/95 p-4 shadow-[0_0_32px_rgba(0,0,0,0.45)]"
    >
      <div v-if="!loading && !logText && !loadError" class="py-10">
        <el-empty description="暂无运行日志：可先返回列表「立即执行」或确认远端 last_run / run 字段" :image-size="80" />
      </div>
      <el-alert v-if="loadError" type="warning" :closable="false" show-icon class="mb-3" :title="loadError" />
      <pre
        v-if="logText"
        class="cicd-detail__log mt-0 max-h-[min(70vh,720px)] overflow-auto rounded-lg border border-slate-700/80 bg-slate-950/90 p-4 text-[13px] leading-relaxed text-slate-200 shadow-inner"
        >{{ logText }}</pre
      >
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, VideoPlay } from '@element-plus/icons-vue'
import { getPipelines, getRunDetails, triggerBuild } from '@/api/cicd'

const route = useRoute()
const router = useRouter()

const pipelineId = computed(() => String(route.params.id ?? ''))

const loading = ref(true)
const triggering = ref(false)
const loadError = ref('')
const pipeline = ref<Record<string, unknown> | null>(null)
const logText = ref('')

function goBack() {
  router.push({ name: 'CicdPipelines' }).catch(() => {})
}

function pickRunId(row: Record<string, unknown>): string | undefined {
  const keys = ['last_run_id', 'latest_run_id', 'current_run_id', 'run_id', 'lastRunId']
  for (const k of keys) {
    const v = row[k]
    if (v != null && String(v).trim() !== '') return String(v)
  }
  return undefined
}

function formatRunPayload(data: unknown): string {
  if (data == null) return ''
  if (typeof data === 'string') return data
  if (typeof data !== 'object') return String(data)
  const o = data as Record<string, unknown>
  const text =
    o.log ??
    o.logs ??
    o.output ??
    o.stdout ??
    o.stderr ??
    o.message ??
    o.detail
  if (typeof text === 'string') return text
  try {
    return JSON.stringify(data, null, 2)
  } catch {
    return String(data)
  }
}

async function load() {
  loading.value = true
  loadError.value = ''
  logText.value = ''
  pipeline.value = null
  const id = pipelineId.value
  if (!id) {
    loading.value = false
    loadError.value = '路由参数缺失'
    return
  }
  try {
    const { data } = await getPipelines()
    const list = (Array.isArray(data) ? data : []) as Record<string, unknown>[]
    const row = list.find((r) => String(r.id ?? '') === id) ?? null
    pipeline.value = row

    const runId = row ? pickRunId(row) : undefined
    if (runId) {
      try {
        const res = await getRunDetails(runId)
        logText.value = formatRunPayload(res.data) || '（运行记录为空）'
      } catch {
        loadError.value = '无法加载运行详情（GET /runs/:runId），仅展示流水线基本信息'
        logText.value = row ? JSON.stringify(row, null, 2) : ''
      }
    } else {
      logText.value = row ? JSON.stringify(row, null, 2) : '未找到该流水线（请返回列表刷新）'
    }
  } catch {
    loadError.value = '加载流水线列表失败'
  } finally {
    loading.value = false
  }
}

async function onTrigger() {
  const id = pipelineId.value
  if (!id) return
  triggering.value = true
  try {
    await triggerBuild(id, {})
    ElMessage.success('已触发运行')
    await load()
  } catch (e: unknown) {
    const msg =
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
      '触发失败'
    ElMessage.error(msg)
  } finally {
    triggering.value = false
  }
}

watch(
  () => route.params.id,
  () => {
    void load()
  },
)

onMounted(() => {
  void load()
})
</script>

<style scoped>
.cicd-detail__title {
  margin: 0 0 6px;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.cicd-detail__en {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: #22d3ee;
  text-shadow: 0 0 12px rgba(34, 211, 238, 0.35);
}

.cicd-detail__meta {
  margin: 0;
}
</style>
