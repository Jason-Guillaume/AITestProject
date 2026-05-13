<template>
  <div class="cyber-page admin-list-page pipeline-list-page">
    <el-card
      class="admin-list-card"
      shadow="never"
    >
      <template #header>
        <div class="card-header-row">
          <div class="card-header-row__title">
            <span class="page-title">流水线列表</span>
            <span class="page-sub">查看与进入各流水线的控制台与日志</span>
          </div>
        </div>
      </template>

      <div class="admin-toolbar-row">
        <div class="admin-toolbar-row__left">
          <el-button
            type="primary"
            @click="router.push('/pipelines/new')"
          >
            <el-icon class="el-icon--left">
              <Plus />
            </el-icon>
            新建项目
          </el-button>
          <el-button
            type="primary"
            :loading="loading"
            @click="loadList"
          >
            <el-icon class="el-icon--left">
              <Refresh />
            </el-icon>
            刷新
          </el-button>
        </div>
        <div class="admin-toolbar-row__right">
          <el-input
            v-model="keyword"
            clearable
            placeholder="按名称或仓库地址筛选"
            style="width: 260px"
            @keyup.enter="noop"
          >
            <template #suffix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>
      </div>

      <el-table
        v-loading="loading"
        class="admin-data-table"
        :data="filteredRows"
        border
        stripe
        row-key="id"
      >
        <template #empty>
          <el-empty
            description="暂无流水线数据"
            :image-size="88"
          />
        </template>
        <el-table-column
          prop="id"
          label="ID"
          width="88"
          align="center"
        />
        <el-table-column
          prop="name"
          label="名称"
          min-width="160"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              @click="goDetail(row.id)"
            >
              {{ row.name || `流水线 #${row.id}` }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column
          label="类型"
          width="120"
          align="center"
        >
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="row.kind === 1 ? 'warning' : 'info'"
            >
              {{ kindLabel(row.kind) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="repo_url"
          label="代码仓库"
          min-width="200"
          show-overflow-tooltip
        />
        <el-table-column
          label="状态"
          width="120"
          align="center"
        >
          <template #default="{ row }">
            <el-tag
              :type="statusTagType(row.status)"
              size="small"
            >
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="创建时间"
          width="176"
          align="center"
        >
          <template #default="{ row }">
            {{ formatDate(row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column
          label="操作"
          width="200"
          fixed="right"
          align="center"
        >
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              size="small"
              @click="goDetail(row.id)"
            >
              控制台
            </el-button>
            <el-button
              link
              type="danger"
              size="small"
              :loading="deletingId === row.id"
              @click="onDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import { deletePipelineApi, getPipelinesApi } from '@/api/project'

const router = useRouter()
const loading = ref(false)
const rows = ref<PipelineRow[]>([])
const keyword = ref('')
const deletingId = ref<number | null>(null)

interface PipelineRow {
  id: number
  name?: string
  kind?: number
  repo_url?: string
  status?: number
  create_time?: string
}

function kindLabel(kind?: number) {
  return kind === 1 ? '流水线脚本' : '自由风格'
}

function noop() {}

function normalizeListPayload(data: unknown): PipelineRow[] {
  if (Array.isArray(data)) return data as PipelineRow[]
  if (data && typeof data === 'object' && Array.isArray((data as { results?: unknown }).results)) {
    return (data as { results: PipelineRow[] }).results
  }
  return []
}

function formatDate(dt?: string) {
  return dt ? dt.slice(0, 16).replace('T', ' ') : '—'
}

const STATUS_LABELS: Record<number, string> = {
  0: '待执行',
  1: '运行中',
  2: '成功',
  3: '失败',
}

function statusLabel(status?: number) {
  if (status === undefined || status === null) return '—'
  return STATUS_LABELS[status] ?? `状态 ${status}`
}

function statusTagType(status?: number): 'info' | 'warning' | 'success' | 'danger' | '' {
  if (status === 1) return 'warning'
  if (status === 2) return 'success'
  if (status === 3) return 'danger'
  return 'info'
}

const filteredRows = computed(() => {
  const q = keyword.value.trim().toLowerCase()
  if (!q) return rows.value
  return rows.value.filter((r) => {
    const name = String(r.name || '').toLowerCase()
    const repo = String(r.repo_url || '').toLowerCase()
    const kt = kindLabel(r.kind).toLowerCase()
    return name.includes(q) || repo.includes(q) || kt.includes(q)
  })
})

async function loadList() {
  loading.value = true
  try {
    const { data } = await getPipelinesApi()
    rows.value = normalizeListPayload(data)
  } catch {
    rows.value = []
  } finally {
    loading.value = false
  }
}

function goDetail(id: number) {
  router.push(`/pipelines/${id}`)
}

async function onDelete(row: PipelineRow) {
  try {
    await ElMessageBox.confirm(`确定删除流水线「${row.name || row.id}」吗？（软删除，可从数据库恢复）`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  deletingId.value = row.id
  try {
    await deletePipelineApi(row.id)
    ElMessage.success('已删除')
    await loadList()
  } catch {
    /* request 拦截器已提示 */
  } finally {
    deletingId.value = null
  }
}

onMounted(() => {
  loadList()
})
</script>

<style scoped>
.pipeline-list-page {
  padding: 16px;
  min-height: calc(100vh - 120px);
  box-sizing: border-box;
}

.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-header-row__title {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.page-sub {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.admin-toolbar-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.admin-toolbar-row__left,
.admin-toolbar-row__right {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
