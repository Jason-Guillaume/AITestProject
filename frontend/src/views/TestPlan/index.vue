<template>
  <div class="page-wrap cyber-page admin-list-page">
    <el-card class="admin-list-card" shadow="never">
      <div class="admin-toolbar-row">
        <div class="admin-toolbar-row__left">
          <el-button type="primary" @click="showDialog = true">
            <el-icon><Plus /></el-icon> 新增测试计划
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
          <el-button
            v-if="isSelectMode && !isRecycleMode && selectedIds.length > 0"
            type="warning"
            plain
            @click="openBatchUpdateStatus"
          >
            批量修改状态
          </el-button>
          <el-button
            v-if="isSelectMode && !isRecycleMode && selectedIds.length > 0"
            type="success"
            plain
            :loading="batchCopying"
            @click="batchCopySelected"
          >
            批量复制
          </el-button>
        </div>
        <div class="admin-toolbar-row__right">
          <el-input
            v-model="searchKw"
            placeholder="请输入测试计划名称"
            clearable
            class="search-input"
          >
            <template #suffix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
      </div>

      <div class="admin-table-panel">
        <el-table
          :data="filteredList"
          v-loading="loading"
          stripe
          border
          class="admin-data-table"
          size="default"
          @selection-change="onSelectionChange"
        >
          <el-table-column v-if="isSelectMode" type="selection" width="44" fixed="left" />
          <el-table-column prop="plan_name" label="测试计划名称" min-width="168" align="left">
            <template #default="{ row }">
              <el-button link type="primary" @click="router.push(`/test-plan/${row.id}`)">{{ row.plan_name }}</el-button>
            </template>
          </el-table-column>
          <el-table-column prop="id" label="ID" min-width="88" width="88" align="left" />
          <el-table-column prop="iteration" label="关联迭代" min-width="112" align="center" show-overflow-tooltip />
          <el-table-column prop="version" label="版本号" min-width="104" width="104" align="center" />
          <el-table-column prop="environment" label="测试环境" min-width="112" width="112" align="center" />
          <el-table-column prop="req_count" label="需求数" min-width="104" width="104" align="center" />
          <el-table-column prop="case_count" label="用例数" min-width="104" width="104" align="center" />
          <el-table-column label="用例覆盖率" min-width="120" width="120" align="center">
            <template #default="{ row }">{{ row.coverage_rate }}%</template>
          </el-table-column>
          <el-table-column label="计划状态" min-width="120" width="120" align="center">
            <template #default="{ row }">
              <el-tag :type="planTagType(row.plan_status)" size="small">{{ planLabel(row.plan_status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="测试进度" min-width="140" align="center">
            <template #default="{ row }">
              <el-progress :percentage="Number(row.pass_rate)" :color="progressColor(row.pass_rate)" :show-text="false" />
            </template>
          </el-table-column>
          <el-table-column prop="defect_count" label="缺陷数" min-width="104" width="104" align="center" />
          <el-table-column prop="testers_display" label="测试人员" min-width="136" align="center" show-overflow-tooltip />
          <el-table-column label="操作" min-width="200" width="200" fixed="right" align="center">
            <template #default="{ row }">
              <div v-if="isRecycleMode" class="recycle-row-actions">
                <el-button link type="success" size="small" :disabled="isSelectMode" @click="restoreRow(row)">恢复</el-button>
                <el-button link type="danger" size="small" :disabled="isSelectMode" @click="hardDeleteRow(row)">彻底删除</el-button>
              </div>
              <TableActionGroup
                v-else
                :row="row"
                :actions="planTableActions(row)"
                @action="handlePlanTableAction"
              />
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          :page-size="PAGE_SIZE"
          :total="total"
          layout="total, prev, pager, next, jumper"
          background
          @current-change="loadList"
        />
      </div>
    </el-card>

    <el-dialog v-model="showDialog" title="新增测试计划" width="500px" class="cyber-dialog-dark">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="计划名称" prop="plan_name">
          <el-input v-model="form.plan_name" placeholder="请输入计划名称" />
        </el-form-item>
        <el-form-item label="关联迭代" prop="iteration">
          <el-input v-model="form.iteration" placeholder="如 迭代2" />
        </el-form-item>
        <el-form-item label="测试环境" prop="environment">
          <el-select v-model="form.environment" placeholder="请选择">
            <el-option label="TEST" value="TEST" />
            <el-option label="PROD" value="PROD" />
          </el-select>
        </el-form-item>
        <el-form-item label="版本" prop="version">
          <el-select v-model="form.version" placeholder="请选择版本">
            <el-option v-for="r in releases" :key="r.id" :label="r.version_no" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="测试人员">
          <el-select
            v-model="form.testers"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            placeholder="请选择测试人员（可选）"
            style="width: 100%"
          >
            <el-option
              v-for="u in userOptions"
              :key="u.id"
              :label="u.real_name || u.username || String(u.id)"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="测试周期">
          <el-date-picker v-model="form.dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="batchUpdateVisible" title="批量修改计划状态" width="420px" class="cyber-dialog-dark" destroy-on-close>
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        title="将对已选计划应用同一状态更新；若某些记录无权限，会被跳过。"
        class="mb-3"
      />
      <el-form label-width="110px">
        <el-form-item label="目标状态">
          <el-select v-model="batchStatus" placeholder="请选择">
            <el-option label="未开始" :value="1" />
            <el-option label="进行中" :value="2" />
            <el-option label="已完成" :value="3" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchUpdateVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="batchUpdating"
          :disabled="selectedIds.length === 0 || batchStatus == null"
          @click="submitBatchUpdateStatus"
        >
          应用到 {{ selectedIds.length }} 条
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CopyDocument, Delete, Edit, FolderOpened, Plus, Search, View } from '@element-plus/icons-vue'
import TableActionGroup from '@/components/common/TableActionGroup.vue'
import {
  getPlansApi,
  createPlanApi,
  deletePlanApi,
  batchUpdatePlansApi,
  batchCopyPlansApi,
  getPlansRecycleApi,
  restorePlanApi,
  hardDeletePlanApi,
  bulkSoftDeletePlansApi,
  bulkRestorePlansApi,
  bulkHardDeletePlansApi,
} from '@/api/execution'
import { getReleasesApi } from '@/api/project'
import { getUsersApi } from '@/api/system'

const router = useRouter()
const list = ref([])
const releases = ref([])
const userOptions = ref([])
const loading = ref(false)
const searchKw = ref('')
const showDialog = ref(false)
const saving = ref(false)
const formRef = ref()
const page = ref(1)
const PAGE_SIZE = 10
const selectedIds = ref([])
const batchDeleting = ref(false)
const batchRestoring = ref(false)
const batchHardDeleting = ref(false)
const batchUpdateVisible = ref(false)
const batchUpdating = ref(false)
const batchStatus = ref(null)
const batchCopying = ref(false)
const isRecycleMode = ref(false)
const isSelectMode = ref(false)
function planTableActions(row) {
  if (row.plan_status === 3) {
    return [
      { key: 'report', tooltip: '查看报告', icon: View, type: 'primary' },
      { key: 'copy', tooltip: '复制计划', icon: CopyDocument, type: 'success' },
      { key: 'archive', tooltip: '归档计划', icon: FolderOpened, type: 'warning' },
    ]
  }
  return [
    { key: 'edit', tooltip: '编辑计划', icon: Edit, type: 'primary' },
    { key: 'copy', tooltip: '复制计划', icon: CopyDocument, type: 'success' },
    { key: 'delete', tooltip: '删除计划', icon: Delete, type: 'danger' },
  ]
}

function handlePlanTableAction(action, row) {
  if (action === 'report') router.push('/test-report')
  else if (action === 'edit') router.push(`/test-plan/${row.id}`)
  else if (action === 'copy') ElMessage.info('复制功能开发中')
  else if (action === 'archive') ElMessage.info('归档功能开发中')
  else if (action === 'delete') delItem(row)
}
const total = ref(0)
const form = ref({ plan_name: '', iteration: '', environment: 'TEST', version: null, testers: [], dateRange: [] })
const rules = {
  plan_name: [{ required: true, message: '请输入计划名称', trigger: 'blur' }],
  environment: [{ required: true, message: '请选择测试环境', trigger: 'change' }],
  version: [{ required: true, message: '请选择版本', trigger: 'change' }],
}

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

function normalizeReleases(payload) {
  if (Array.isArray(payload)) return payload
  if (payload?.results && Array.isArray(payload.results)) return payload.results
  if (payload?.data && Array.isArray(payload.data)) return payload.data
  return []
}

function normalizeUsers(payload) {
  if (Array.isArray(payload)) return payload
  if (payload?.results && Array.isArray(payload.results)) return payload.results
  if (payload?.data && Array.isArray(payload.data)) return payload.data
  return []
}

async function loadUsersForPlan() {
  try {
    const { data } = await getUsersApi({ page_size: 500 })
    userOptions.value = normalizeUsers(data)
  } catch {
    userOptions.value = []
  }
}

async function loadReleasesForPlan() {
  try {
    const pid = localStorage.getItem('current_project_id')
    const params = {}
    if (pid) params.project = Number(pid)
    const { data } = await getReleasesApi(params)
    releases.value = normalizeReleases(data)
  } catch {
    releases.value = []
  }
}

const filteredList = computed(() => {
  const q = (searchKw.value || '').trim()
  if (!q) return list.value
  return list.value.filter((i) => String(i.plan_name ?? '').includes(q))
})

function planLabel(v) { return { 1: '未开始', 2: '进行中', 3: '已完成' }[v] || '-' }
function planTagType(v) { return { 1: 'info', 2: 'warning', 3: 'success' }[v] || '' }
function progressColor(rate) { return rate >= 80 ? '#52c41a' : rate >= 50 ? '#faad14' : '#ff4d4f' }
function formatDate(dt) { return dt ? dt.slice(0, 10) : '-' }

async function loadList() {
  loading.value = true
  try {
    const api = isRecycleMode.value ? getPlansRecycleApi : getPlansApi
    const { data } = await api({ page: page.value, page_size: PAGE_SIZE })
    const rows = normalizeListResponse(data)
    list.value = rows
    total.value = normalizeTotal(data, rows)
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '加载失败'
    ElMessage.error(typeof msg === 'string' ? msg : '加载测试计划失败')
    list.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function toggleSelectMode() {
  isSelectMode.value = !isSelectMode.value
  if (!isSelectMode.value) selectedIds.value = []
}

function toggleRecycleMode() {
  isRecycleMode.value = !isRecycleMode.value
  selectedIds.value = []
  isSelectMode.value = false
  batchUpdateVisible.value = false
  page.value = 1
  loadList()
}

async function delItem(row) {
  try {
    await ElMessageBox.confirm(`确定将「${row.plan_name ?? row.id}」移入回收站？`, '警告', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deletePlanApi(row.id)
    ElMessage.success('已移入回收站')
    loadList()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.message || '删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '删除失败')
  }
}

function onSelectionChange(rows) {
  if (!isSelectMode.value) return
  selectedIds.value = (rows || []).map((r) => r.id).filter((id) => id != null)
}

async function batchSoftDelete() {
  if (!selectedIds.value.length) return
  try {
    await ElMessageBox.confirm(`确定将选中的 ${selectedIds.value.length} 条测试计划移入回收站？`, '警告', { type: 'warning' })
  } catch {
    return
  }
  batchDeleting.value = true
  try {
    const { data } = await bulkSoftDeletePlansApi({ ids: selectedIds.value })
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
    const { data } = await bulkRestorePlansApi({ ids: selectedIds.value })
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
    await ElMessageBox.confirm(`确定彻底删除选中的 ${selectedIds.value.length} 条测试计划？此操作不可恢复。`, '警告', { type: 'error' })
  } catch {
    return
  }
  batchHardDeleting.value = true
  try {
    const { data } = await bulkHardDeletePlansApi({ ids: selectedIds.value })
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

async function restoreRow(row) {
  try {
    await restorePlanApi(row.id)
    ElMessage.success('已恢复')
    loadList()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '恢复失败'
    ElMessage.error(typeof msg === 'string' ? msg : '恢复失败')
  }
}

async function hardDeleteRow(row) {
  try {
    await ElMessageBox.confirm(`确定彻底删除「${row.plan_name ?? row.id}」？此操作不可恢复。`, '警告', { type: 'error' })
  } catch {
    return
  }
  try {
    await hardDeletePlanApi(row.id)
    ElMessage.success('已彻底删除')
    loadList()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '彻底删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '彻底删除失败')
  }
}

function openBatchUpdateStatus() {
  batchStatus.value = null
  batchUpdateVisible.value = true
}

async function submitBatchUpdateStatus() {
  if (!selectedIds.value.length || batchStatus.value == null) return
  try {
    await ElMessageBox.confirm(
      `确认将 ${selectedIds.value.length} 条计划状态批量更新为「${planLabel(batchStatus.value)}」？`,
      '确认',
      { type: 'warning' },
    )
  } catch {
    return
  }
  batchUpdating.value = true
  try {
    const { data } = await batchUpdatePlansApi({ ids: selectedIds.value, patch: { plan_status: batchStatus.value } })
    const d = data?.data && typeof data.data === 'object' ? data.data : data
    const updated = Number(d?.updated ?? 0)
    const missing = Array.isArray(d?.missing_ids) ? d.missing_ids.length : 0
    const errors = Array.isArray(d?.errors) ? d.errors.length : 0
    if (errors) ElMessage.warning(`已更新 ${updated} 条；缺失/无权限 ${missing} 条；失败 ${errors} 条`)
    else ElMessage.success(`已更新 ${updated} 条；缺失/无权限 ${missing} 条`)
    batchUpdateVisible.value = false
    loadList()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '批量更新失败'
    ElMessage.error(typeof msg === 'string' ? msg : '批量更新失败')
  } finally {
    batchUpdating.value = false
  }
}

async function batchCopySelected() {
  if (!selectedIds.value.length) return
  let suffix = '（复制）'
  try {
    const { value } = await ElMessageBox.prompt('请输入复制后名称后缀（可留空）', '批量复制', {
      inputValue: suffix,
      confirmButtonText: '复制',
      cancelButtonText: '取消',
    })
    suffix = String(value ?? '').trim() || '（复制）'
  } catch {
    return
  }
  batchCopying.value = true
  try {
    const { data } = await batchCopyPlansApi({ ids: selectedIds.value, name_suffix: suffix })
    const d = data?.data && typeof data.data === 'object' ? data.data : data
    const created = Number(d?.created ?? 0)
    const missing = Array.isArray(d?.missing_ids) ? d.missing_ids.length : 0
    const errors = Array.isArray(d?.errors) ? d.errors.length : 0
    if (errors) ElMessage.warning(`已复制 ${created} 条；缺失/无权限 ${missing} 条；失败 ${errors} 条`)
    else ElMessage.success(`已复制 ${created} 条；缺失/无权限 ${missing} 条`)
    selectedIds.value = []
    loadList()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '批量复制失败'
    ElMessage.error(typeof msg === 'string' ? msg : '批量复制失败')
  } finally {
    batchCopying.value = false
  }
}

async function submit() {
  await formRef.value.validate()
  saving.value = true
  const payload = { ...form.value }
  if (payload.dateRange?.length === 2) {
    payload.start_date = payload.dateRange[0]
    payload.end_date = payload.dateRange[1]
  }
  delete payload.dateRange
  if (!Array.isArray(payload.testers)) payload.testers = []
  try {
    await createPlanApi(payload)
    ElMessage.success('创建成功')
    showDialog.value = false
    form.value = { plan_name: '', iteration: '', environment: 'TEST', version: null, testers: [], dateRange: [] }
    loadList()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.message || '创建失败'
    ElMessage.error(typeof msg === 'string' ? msg : '创建失败')
  } finally {
    saving.value = false
  }
}

watch(showDialog, async (open) => {
  if (open) {
    form.value = { plan_name: '', iteration: '', environment: 'TEST', version: null, testers: [], dateRange: [] }
    formRef.value?.resetFields?.()
    await Promise.all([loadReleasesForPlan(), loadUsersForPlan()])
    if (!releases.value.length) {
      ElMessage.warning(
        '当前项目下暂无发布版本。请先在「项目管理」卡片中点击「版本发布」新建版本，并确认顶栏已选择对应项目；也可在「缺陷管理 → 发布计划」中维护。',
      )
    }
  }
})

onMounted(async () => {
  loadList()
  await loadReleasesForPlan()
})
</script>

<style scoped>
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  flex-shrink: 0;
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

/* flex 垂直居中时补全横向：表头 th / 表体 td 与 align 一致 */
.page-wrap :deep(.el-table .cell) {
  display: flex !important;
  align-items: center !important;
  width: 100% !important;
  box-sizing: border-box;
}

.page-wrap :deep(.el-table .el-table__cell.is-center .cell) {
  justify-content: center !important;
  text-align: center !important;
}

.page-wrap :deep(.el-table .el-table__cell.is-left .cell) {
  justify-content: flex-start !important;
  text-align: left !important;
}

.page-wrap :deep(.el-table .el-table__cell.is-right .cell) {
  justify-content: flex-end !important;
  text-align: right !important;
}
</style>
