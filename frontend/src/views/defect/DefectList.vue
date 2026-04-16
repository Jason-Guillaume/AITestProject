<template>
  <div class="page-wrap defect-list--cyber cyber-page">
    <div class="page-toolbar defect-toolbar">
      <div class="defect-toolbar__actions">
        <el-button type="default" size="default" @click="router.push('/defect/board')">任务看板</el-button>
        <el-button type="primary" size="default" @click="router.push('/defect/detail')">
          <el-icon><Plus /></el-icon> 新增缺陷
        </el-button>
        <el-button class="filter-btn" :type="isRecycleMode ? 'warning' : ''" @click="toggleRecycleMode">
          {{ isRecycleMode ? '返回列表' : '回收站' }}
        </el-button>
        <el-button class="filter-btn" :type="isSelectMode ? 'info' : ''" @click="toggleSelectMode">
          {{ isSelectMode ? '取消选择' : '选择' }}
          <span v-if="isSelectMode && selectedIds.length" style="margin-left: 6px">（{{ selectedIds.length }}）</span>
        </el-button>

        <el-button
          v-if="isSelectMode && !isRecycleMode && selectedIds.length > 0"
          type="danger"
          plain
          :loading="batchDeleting"
          @click="batchSoftDelete"
        >
          批量删除（{{ selectedIds.length }}）
        </el-button>
        <el-button
          v-if="isSelectMode && isRecycleMode && selectedIds.length > 0"
          type="success"
          plain
          :loading="batchRestoring"
          @click="batchRestore"
        >
          批量恢复（{{ selectedIds.length }}）
        </el-button>
        <el-button
          v-if="isSelectMode && isRecycleMode && selectedIds.length > 0"
          type="danger"
          plain
          :loading="batchHardDeleting"
          @click="batchHardDelete"
        >
          彻底删除（{{ selectedIds.length }}）
        </el-button>
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
      <el-table class="defect-table--cyber admin-data-table" :data="list" v-loading="loading" @selection-change="onSelectionChange">
        <template #empty>
          <el-empty description="暂无缺陷数据" :image-size="88" />
        </template>
        <el-table-column v-if="isSelectMode" type="selection" width="48" align="center" />
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
        <el-table-column v-if="isRecycleMode" label="操作" min-width="160" width="160" fixed="right" align="center">
          <template #default="{ row }">
            <div class="recycle-row-actions">
              <el-button link type="success" size="small" :disabled="isSelectMode" @click="restoreRow(row)">恢复</el-button>
              <el-button link type="danger" size="small" :disabled="isSelectMode" @click="hardDeleteRow(row)">彻底删除</el-button>
            </div>
          </template>
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
import { Plus, Search } from '@element-plus/icons-vue'
import {
  getDefectsApi,
  getDefectsRecycleApi,
  deleteDefectApi,
  restoreDefectApi,
  hardDeleteDefectApi,
  bulkSoftDeleteDefectsApi,
  bulkRestoreDefectsApi,
  bulkHardDeleteDefectsApi,
} from '@/api/defect'

const PAGE_SIZE = 10

const router = useRouter()
const list = ref([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const filters = ref({ severity: null, status: null, priority: null, keyword: '' })
const isRecycleMode = ref(false)
const isSelectMode = ref(false)
const selectedIds = ref([])
const batchDeleting = ref(false)
const batchRestoring = ref(false)
const batchHardDeleting = ref(false)

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

function toggleSelectMode() {
  isSelectMode.value = !isSelectMode.value
  if (!isSelectMode.value) selectedIds.value = []
}

function toggleRecycleMode() {
  isRecycleMode.value = !isRecycleMode.value
  selectedIds.value = []
  isSelectMode.value = false
  page.value = 1
  loadList()
}

function onSelectionChange(rows) {
  if (!isSelectMode.value) return
  selectedIds.value = (rows || []).map((r) => r.id).filter((id) => id != null)
}

async function batchSoftDelete() {
  if (!selectedIds.value.length) return
  try {
    await ElMessageBox.confirm(`确定将选中的 ${selectedIds.value.length} 条缺陷移入回收站？`, '警告', { type: 'warning' })
  } catch {
    return
  }
  batchDeleting.value = true
  try {
    const { data } = await bulkSoftDeleteDefectsApi({ ids: selectedIds.value })
    const deleted = Number(data?.deleted ?? data?.data?.deleted ?? 0)
    const skipped = Number(data?.skipped ?? data?.data?.skipped ?? 0)
    ElMessage.success(`已删除 ${deleted} 条；跳过 ${skipped} 条`)
    selectedIds.value = []
    loadList()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '批量删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '批量删除失败')
  } finally {
    batchDeleting.value = false
  }
}

async function batchRestore() {
  if (!selectedIds.value.length) return
  batchRestoring.value = true
  try {
    const { data } = await bulkRestoreDefectsApi({ ids: selectedIds.value })
    const restored = Number(data?.restored ?? data?.data?.restored ?? 0)
    const skipped = Number(data?.skipped ?? data?.data?.skipped ?? 0)
    ElMessage.success(`已恢复 ${restored} 条；跳过 ${skipped} 条`)
    selectedIds.value = []
    loadList()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '批量恢复失败'
    ElMessage.error(typeof msg === 'string' ? msg : '批量恢复失败')
  } finally {
    batchRestoring.value = false
  }
}

async function batchHardDelete() {
  if (!selectedIds.value.length) return
  try {
    await ElMessageBox.confirm(`确定彻底删除选中的 ${selectedIds.value.length} 条缺陷？此操作不可恢复。`, '警告', { type: 'error' })
  } catch {
    return
  }
  batchHardDeleting.value = true
  try {
    const { data } = await bulkHardDeleteDefectsApi({ ids: selectedIds.value })
    const count = Number(data?.count ?? data?.data?.count ?? 0)
    ElMessage.success(`已彻底删除 ${count} 条`)
    selectedIds.value = []
    loadList()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '彻底删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '彻底删除失败')
  } finally {
    batchHardDeleting.value = false
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
    const api = isRecycleMode.value ? getDefectsRecycleApi : getDefectsApi
    const { data } = await api(params)
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

async function restoreRow(row) {
  try {
    await restoreDefectApi(row.id)
    ElMessage.success('已恢复')
    loadList()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '恢复失败'
    ElMessage.error(typeof msg === 'string' ? msg : '恢复失败')
  }
}

async function hardDeleteRow(row) {
  try {
    await ElMessageBox.confirm(`确定彻底删除「${row.defect_no || row.id}」？此操作不可恢复。`, '警告', { type: 'error' })
  } catch {
    return
  }
  try {
    await hardDeleteDefectApi(row.id)
    ElMessage.success('已彻底删除')
    loadList()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '彻底删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '彻底删除失败')
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

.filter-btn {
  border-color: rgba(0, 255, 255, 0.25);
  color: #00d8ff;
  background: rgba(20, 28, 47, 0.5);
}

.filter-btn:hover {
  border-color: rgba(0, 216, 255, 0.45);
  color: #5ee7ff;
  background: rgba(0, 216, 255, 0.08);
}

.recycle-row-actions {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
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
