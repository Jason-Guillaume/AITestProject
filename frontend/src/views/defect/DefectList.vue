<template>
  <div class="page-wrap defect-list--cyber cyber-page">
    <div class="page-toolbar defect-toolbar">
      <div class="defect-toolbar__actions">
        <el-button type="default" size="default" @click="router.push('/defect/board')">任务看板</el-button>
        <el-button type="primary" size="default" @click="router.push('/defect/detail')">
          <el-icon><Plus /></el-icon> 新增缺陷
        </el-button>
        <el-dropdown trigger="click">
          <el-button size="default">
            更多操作<el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="batchDelete">批量删除</el-dropdown-item>
              <el-dropdown-item @click="onExportStub">批量导出</el-dropdown-item>
              <el-dropdown-item @click="onBatchStatusStub">批量修改状态</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
      <div class="defect-toolbar__filters">
        <el-select v-model="filters.severity" placeholder="严重程度" clearable size="default" class="filter-select filter-select--severity" @change="loadList">
          <el-option label="致命" :value="1" />
          <el-option label="严重" :value="2" />
          <el-option label="一般" :value="3" />
          <el-option label="建议" :value="4" />
        </el-select>
        <el-select v-model="filters.status" placeholder="缺陷状态" clearable size="default" class="filter-select filter-select--status" @change="loadList">
          <el-option label="新缺陷" :value="1" />
          <el-option label="处理中" :value="2" />
          <el-option label="已拒绝" :value="3" />
          <el-option label="已关闭" :value="4" />
        </el-select>
        <el-select v-model="filters.priority" placeholder="优先级" clearable size="default" class="filter-select filter-select--priority" @change="loadList">
          <el-option label="高" :value="1" />
          <el-option label="中" :value="2" />
          <el-option label="低" :value="3" />
        </el-select>
        <el-input
          v-model="filters.keyword"
          placeholder="缺陷ID / 名称"
          clearable
          size="default"
          class="filter-search"
          @keyup.enter="loadList"
        >
          <template #suffix><el-icon><Search /></el-icon></template>
        </el-input>
      </div>
    </div>

    <div class="table-card cyber-table-panel">
      <el-table class="defect-table--cyber admin-data-table" :data="list" v-loading="loading" @selection-change="selected = $event">
        <template #empty>
          <el-empty description="暂无缺陷数据" :image-size="88" />
        </template>
        <el-table-column type="selection" width="48" align="center" />
        <el-table-column prop="defect_no" label="缺陷ID" min-width="100" width="100" align="left" />
        <el-table-column prop="defect_name" label="缺陷名称" min-width="168" align="left" show-overflow-tooltip>
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/defect/detail/${row.id}`)">{{ row.defect_name }}</el-button>
          </template>
        </el-table-column>
        <el-table-column prop="release_version_no" label="发布版本" min-width="112" width="112" align="center" />
        <el-table-column label="严重程度" width="90" align="center">
          <template #default="{ row }">
            <span :class="`severity-${row.severity}`">{{ severityLabel(row.severity) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="优先级" width="70" align="center">
          <template #default="{ row }">{{ priorityLabel(row.priority) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="handler_name" label="处理人" min-width="104" width="104" align="center" show-overflow-tooltip />
        <el-table-column prop="creator_name" label="创建人" min-width="104" width="104" align="center" show-overflow-tooltip />
        <el-table-column label="创建时间" min-width="176" width="176" align="center" class-name="col-datetime">
          <template #default="{ row }">{{ formatDate(row.create_time) }}</template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          :page-size="PAGE_SIZE"
          :total="total"
          layout="total, prev, pager, next"
          background
          @current-change="loadList"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, ArrowDown } from '@element-plus/icons-vue'
import { getDefectsApi, deleteDefectApi } from '@/api/defect'

const PAGE_SIZE = 10

const router = useRouter()
const list = ref([])
const selected = ref([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const filters = ref({ severity: null, status: null, priority: null, keyword: '' })

function severityLabel(v) { return { 1: '致命', 2: '严重', 3: '一般', 4: '建议' }[v] || '-' }
function priorityLabel(v) { return { 1: '高', 2: '中', 3: '低' }[v] || '-' }
function statusLabel(v) { return { 1: '新缺陷', 2: '处理中', 3: '已拒绝', 4: '已关闭' }[v] || '-' }
function statusTagType(v) { return { 1: 'danger', 2: 'warning', 3: 'info', 4: 'success' }[v] || '' }
function formatDate(dt) { return dt ? dt.slice(0, 16).replace('T', ' ') : '-' }

function normalizeListResponse(payload) {
  if (Array.isArray(payload)) return payload
  if (payload?.results && Array.isArray(payload.results)) return payload.results
  if (payload?.data && Array.isArray(payload.data)) return payload.data
  return []
}

function normalizeTotal(payload, rows) {
  const c = payload?.count
  if (typeof c === 'number' && !Number.isNaN(c)) return c
  return rows.length
}

function onExportStub() { ElMessage.info('批量导出功能开发中') }
function onBatchStatusStub() { ElMessage.info('批量修改状态开发中') }

async function batchDelete() {
  if (!selected.value.length) {
    ElMessage.warning('请先勾选要删除的缺陷')
    return
  }
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selected.value.length} 条缺陷？`, '警告', { type: 'warning' })
  } catch {
    return
  }
  try {
    await Promise.all(selected.value.map((row) => deleteDefectApi(row.id)))
    ElMessage.success('删除成功')
    selected.value = []
    loadList()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.message || '删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '删除失败')
  }
}

async function loadList() {
  loading.value = true
  const params = { page: page.value, page_size: PAGE_SIZE }
  if (filters.value.severity) params.severity = filters.value.severity
  if (filters.value.status) params.status = filters.value.status
  if (filters.value.priority) params.priority = filters.value.priority
  const kw = (filters.value.keyword || '').trim()
  if (kw) params.search = kw
  try {
    const { data } = await getDefectsApi(params)
    const rows = normalizeListResponse(data)
    list.value = rows
    total.value = normalizeTotal(data, rows)
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '加载失败'
    ElMessage.error(typeof msg === 'string' ? msg : '加载缺陷列表失败')
    list.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

onMounted(loadList)
</script>

<style scoped>
.page-wrap {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.defect-toolbar.page-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
  padding: 14px 18px;
  border-radius: 10px;
  border: 1px solid rgba(0, 255, 255, 0.12);
  background: rgba(20, 28, 47, 0.55);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.defect-toolbar__actions,
.defect-toolbar__filters {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.defect-list--cyber .filter-select--severity {
  width: 128px;
}
.defect-list--cyber .filter-select--status {
  width: 128px;
}
.defect-list--cyber .filter-select--priority {
  width: 112px;
}
.defect-list--cyber .filter-search {
  width: min(280px, 100%);
}

.defect-list--cyber :deep(.defect-table--cyber .el-empty__description) {
  color: rgba(255, 255, 255, 0.55);
}
.defect-list--cyber :deep(.defect-table--cyber .el-empty) {
  padding: 32px 16px;
}

.cyber-table-panel.table-card {
  background: transparent;
  border-radius: 10px;
  padding: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10px);
}

.defect-list--cyber :deep(.defect-table--cyber) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(255, 255, 255, 0.05);
  --el-table-row-hover-bg-color: rgba(0, 255, 255, 0.05);
  --el-table-border-color: transparent;
  --el-table-text-color: rgba(255, 255, 255, 0.88);
  --el-table-header-text-color: rgba(255, 255, 255, 0.72);
}

.defect-list--cyber :deep(.defect-table--cyber .el-table__inner-wrapper::before),
.defect-list--cyber :deep(.defect-table--cyber::before) {
  display: none;
}

.defect-list--cyber :deep(.defect-table--cyber .el-table__header-wrapper th.el-table__cell) {
  background: rgba(255, 255, 255, 0.05) !important;
  border-right: none !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
  font-weight: 600;
}

.defect-list--cyber :deep(.defect-table--cyber .el-table__body-wrapper .el-table__body td.el-table__cell) {
  background: transparent !important;
  border-right: none !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
}

.defect-list--cyber :deep(.defect-table--cyber .el-table__body-wrapper .el-table__body tr:last-child td.el-table__cell) {
  border-bottom: none !important;
}

.defect-list--cyber :deep(.defect-table--cyber .el-table__body tr:hover > td.el-table__cell) {
  background-color: rgba(0, 255, 255, 0.05) !important;
}

.defect-list--cyber :deep(.defect-table--cyber .el-table__empty-block) {
  background: transparent;
}

.defect-list--cyber :deep(.defect-table--cyber .el-loading-mask) {
  background-color: rgba(10, 16, 29, 0.55);
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  background: transparent;
}

.defect-list--cyber .pagination-wrap :deep(.el-pagination) {
  --el-pagination-bg-color: transparent;
  --el-pagination-text-color: rgba(255, 255, 255, 0.65);
  --el-pagination-button-color: rgba(255, 255, 255, 0.78);
  --el-pagination-button-disabled-bg-color: transparent;
  --el-pagination-hover-color: #00d8ff;
}

.defect-list--cyber .pagination-wrap :deep(.el-pager li) {
  background: transparent !important;
  border: 1px solid transparent;
  border-radius: 4px;
  transition: color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.defect-list--cyber .pagination-wrap :deep(.el-pager li.is-active) {
  color: #00ffff !important;
  border-color: rgba(0, 255, 255, 0.5);
  box-shadow: 0 0 12px rgba(0, 255, 255, 0.2);
  background: rgba(0, 255, 255, 0.06) !important;
  font-weight: 600;
}

.defect-list--cyber .pagination-wrap :deep(.el-pagination .btn-prev),
.defect-list--cyber .pagination-wrap :deep(.el-pagination .btn-next) {
  background: transparent !important;
}

.defect-list--cyber .pagination-wrap :deep(.el-pagination__jump .el-input__wrapper),
.defect-list--cyber .pagination-wrap :deep(.el-pagination__sizes .el-select .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.06);
  box-shadow: none;
}

.severity-1 { color: #ff6b6b; font-weight: 600; }
.severity-2 { color: #ffa94d; font-weight: 600; }
.severity-3 { color: rgba(255, 255, 255, 0.72); }
.severity-4 { color: rgba(255, 255, 255, 0.45); }
</style>
