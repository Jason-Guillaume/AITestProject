<template>
  <div
    class="cicd-hub cicd-hub--cyber min-h-[calc(100vh-120px)] bg-slate-900 text-slate-100 selection:bg-cyan-500/30 px-4 pb-6 pt-4 box-border"
  >
    <header class="cicd-hub__header">
      <div class="cicd-hub__brand">
        <h1 class="cicd-hub__title">
          流水线管理 <span class="cicd-hub__en">Pipelines</span>
        </h1>
        <p class="cicd-hub__subtitle">
          远端 CI 编排 · 点击行进入日志详情 · 与 Django「流水线列表」独立入口见下方
        </p>
      </div>

      <div class="cicd-hub__toolbar flex flex-wrap items-center gap-3">
        <div class="flex flex-wrap items-center gap-2">
          <el-tag v-if="healthChecked" :type="healthOk ? 'success' : 'danger'" size="small" effect="dark" round>
            {{ healthOk ? '编排服务在线' : '编排服务不可用' }}
          </el-tag>
          <el-tag v-else type="info" size="small" effect="dark" round>探测中…</el-tag>
        </div>
        <div class="hidden sm:block h-6 w-px bg-slate-600/80 shrink-0" aria-hidden="true" />
        <el-button type="primary" size="small" :loading="loading" @click="loadAll">
          <el-icon class="el-icon--left"><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button size="small" class="!bg-slate-800 !border-slate-600" @click="router.push('/pipelines')">
          <el-icon class="el-icon--left"><Link /></el-icon>
          Django 流水线列表
        </el-button>
        <el-input
          v-model="keyword"
          clearable
          size="small"
          placeholder="筛选：名称 / 分支 / 仓库"
          class="cicd-hub__search w-[min(280px,42vw)] min-w-[160px]"
          @keyup.enter="noop"
        >
          <template #prefix>
            <el-icon class="text-slate-400"><Search /></el-icon>
          </template>
        </el-input>
      </div>
    </header>

    <section
      class="cicd-hub__detail mt-4 rounded-xl border border-cyan-500/15 bg-gradient-to-br from-slate-950/95 via-slate-900/90 to-slate-950/95 p-3 shadow-[0_0_32px_rgba(0,0,0,0.45)] backdrop-blur-md sm:p-4"
    >
      <div class="cicd-hub__table-shell flex min-h-[320px] flex-col overflow-hidden rounded-lg border border-white/5 bg-slate-950/50">
        <el-table
          v-loading="loading"
          class="cicd-table"
          :data="filteredRows"
          row-key="id"
          stripe
          :row-class-name="() => 'cicd-table__row'"
          @row-click="onRowClick"
        >
          <template #empty>
            <el-empty description="暂无流水线数据或服务未连通" :image-size="72" />
          </template>
          <el-table-column prop="id" label="ID" width="88" align="center" />
          <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip />
          <el-table-column prop="branch" label="分支" width="130" show-overflow-tooltip />
          <el-table-column prop="repo_url" label="仓库" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.repo_url || row.repo || '—' }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="128" align="center">
            <template #default="{ row }">
              <span :class="['cicd-neon', neonStatusClass(row.status)]">{{ statusLabel(row.status) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="最近运行" width="172" align="center">
            <template #default="{ row }">{{ formatDate(row.last_run_at || row.updated_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right" align="center">
            <template #default="{ row }">
              <el-button
                type="primary"
                size="small"
                link
                class="!text-fuchsia-300"
                :loading="runningId === row.id"
                @click.stop="onRun(row)"
              >
                <el-icon class="el-icon--left"><VideoPlay /></el-icon>
                立即执行
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh, Search, VideoPlay, Link } from '@element-plus/icons-vue'
import { getHealth, getPipelines, triggerBuild } from '@/api/cicd'

const router = useRouter()

interface CicdPipelineRow {
  id: string | number
  name?: string
  branch?: string
  repo_url?: string
  repo?: string
  status?: string | number
  last_run_at?: string
  updated_at?: string
}

const loading = ref(false)
const rows = ref<CicdPipelineRow[]>([])
const keyword = ref('')
const healthChecked = ref(false)
const healthOk = ref(false)
const runningId = ref<string | number | null>(null)

function noop() {}

function formatDate(dt?: string) {
  return dt ? dt.slice(0, 19).replace('T', ' ') : '—'
}

function statusLabel(status?: string | number) {
  if (status === undefined || status === null || status === '') return '—'
  const map: Record<string, string> = {
    idle: '空闲',
    running: '运行中',
    success: '成功',
    failed: '失败',
    pending: '排队',
    queued: '排队',
    error: '失败',
    '0': '空闲',
    '1': '运行中',
    '2': '成功',
    '3': '失败',
  }
  const key = String(status).toLowerCase()
  return map[key] ?? map[String(status)] ?? String(status)
}

/** 霓虹标签：运行中紫、成功绿、失败红；其余弱显示 */
function neonStatusClass(status?: string | number) {
  const s = String(status ?? '').toLowerCase()
  if (s === '1' || s === 'running' || s === 'pending' || s === 'queued') return 'cicd-neon--run'
  if (s === '2' || s === 'success') return 'cicd-neon--ok'
  if (s === '3' || s === 'failed' || s === 'error') return 'cicd-neon--fail'
  return 'cicd-neon--idle'
}

const filteredRows = computed(() => {
  const q = keyword.value.trim().toLowerCase()
  if (!q) return rows.value
  return rows.value.filter((r) => {
    const name = String(r.name || '').toLowerCase()
    const branch = String(r.branch || '').toLowerCase()
    const repo = String(r.repo_url || r.repo || '').toLowerCase()
    return name.includes(q) || branch.includes(q) || repo.includes(q)
  })
})

async function checkHealth() {
  healthChecked.value = false
  try {
    await getHealth({ timeout: 8000 })
    healthOk.value = true
  } catch {
    healthOk.value = false
  } finally {
    healthChecked.value = true
  }
}

async function loadList() {
  loading.value = true
  try {
    const { data } = await getPipelines()
    rows.value = (data ?? []) as CicdPipelineRow[]
  } catch {
    rows.value = []
  } finally {
    loading.value = false
  }
}

async function loadAll() {
  await Promise.all([checkHealth(), loadList()])
}

function onRowClick(row: CicdPipelineRow) {
  router.push({ name: 'CicdPipelineDetail', params: { id: String(row.id) } })
}

async function onRun(row: CicdPipelineRow) {
  runningId.value = row.id
  try {
    await triggerBuild(row.id, {})
    ElMessage.success('已触发运行')
    await loadList()
  } catch (e: unknown) {
    const msg =
      (e as { response?: { data?: { detail?: string; message?: string } } })?.response?.data?.detail ||
      (e as { response?: { data?: { message?: string } } })?.response?.data?.message ||
      '触发失败，请检查远端 CI 接口或代理配置'
    ElMessage.error(msg)
  } finally {
    runningId.value = null
  }
}

onMounted(() => {
  loadAll()
})
</script>

<style scoped>
.cicd-hub__header {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.cicd-hub__title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: rgba(226, 232, 240, 0.98);
}

.cicd-hub__en {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.12em;
  color: #22d3ee;
  text-shadow: 0 0 14px rgba(34, 211, 238, 0.35);
}

.cicd-hub__subtitle {
  margin: 0;
  font-size: 12px;
  line-height: 1.55;
  color: rgba(148, 163, 184, 0.95);
  max-width: 52rem;
}

.cicd-neon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 3px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.cicd-neon--run {
  color: #e9d5ff;
  background: rgba(168, 85, 247, 0.12);
  border: 1px solid rgba(192, 132, 252, 0.55);
  box-shadow:
    0 0 14px rgba(168, 85, 247, 0.45),
    inset 0 0 16px rgba(168, 85, 247, 0.12);
}

.cicd-neon--ok {
  color: #bbf7d0;
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(52, 211, 153, 0.55);
  box-shadow:
    0 0 14px rgba(34, 197, 94, 0.4),
    inset 0 0 14px rgba(34, 197, 94, 0.1);
}

.cicd-neon--fail {
  color: #fecaca;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(248, 113, 113, 0.55);
  box-shadow:
    0 0 14px rgba(239, 68, 68, 0.42),
    inset 0 0 14px rgba(239, 68, 68, 0.1);
}

.cicd-neon--idle {
  color: rgba(148, 163, 184, 0.95);
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(71, 85, 105, 0.45);
}

/* 表格深色（Element Plus） */
.cicd-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: rgba(15, 23, 42, 0.35);
  --el-table-header-bg-color: rgba(15, 23, 42, 0.85);
  --el-table-header-text-color: rgba(226, 232, 240, 0.92);
  --el-table-text-color: rgba(226, 232, 240, 0.9);
  --el-table-row-hover-bg-color: rgba(34, 211, 238, 0.06);
  --el-table-border-color: rgba(51, 65, 85, 0.5);
  --el-fill-color-lighter: rgba(30, 41, 59, 0.5);
}

.cicd-table :deep(.el-table__inner-wrapper::before) {
  display: none;
}

.cicd-table :deep(.cicd-table__row) {
  cursor: pointer;
}

.cicd-hub__search :deep(.el-input__wrapper) {
  background-color: rgba(15, 23, 42, 0.65);
  box-shadow: 0 0 0 1px rgba(51, 65, 85, 0.6) inset;
}

.cicd-hub__search :deep(.el-input__inner) {
  color: rgba(226, 232, 240, 0.95);
}
</style>
