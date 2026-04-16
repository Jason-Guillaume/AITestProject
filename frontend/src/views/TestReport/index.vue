<template>
  <div class="page-wrap cyber-page admin-list-page">
    <el-card class="admin-list-card" shadow="never">
      <div class="admin-toolbar-row">
        <div class="admin-toolbar-row__left">
          <el-button type="primary" @click="openCreate">
            <el-icon><Plus /></el-icon> 新增测试报告
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
            type="success"
            plain
            :loading="batchCopying"
            @click="batchCopySelected"
          >
            批量复制
          </el-button>
          <el-button
            v-if="isSelectMode && !isRecycleMode && selectedIds.length > 0"
            type="primary"
            plain
            :loading="batchRefreshing"
            @click="batchRefreshSelected"
          >
            批量刷新（从计划）
          </el-button>
          <el-button
            v-if="isSelectMode && !isRecycleMode && selectedIds.length > 0"
            type="warning"
            plain
            :loading="batchExecuting"
            @click="batchExecuteSelected"
          >
            批量执行
          </el-button>
        </div>
        <div class="admin-toolbar-row__right">
          <el-input v-model="searchKw" placeholder="请输入测试报告名称" clearable class="search-input">
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
          <el-table-column prop="report_name" label="测试报告名称" min-width="160" align="left">
            <template #default="{ row }">
              <el-button link type="primary" @click="router.push(`/test-report/${row.id}`)">{{ row.report_name }}</el-button>
            </template>
          </el-table-column>
          <el-table-column prop="id" label="ID" min-width="88" width="88" align="left" />
          <el-table-column label="创建方式" min-width="120" width="120" align="center">
            <template #default="{ row }">
              <el-tag :type="methodTagType(row.create_method)" size="small">{{ methodLabel(row.create_method) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" min-width="184" width="184" align="center" class-name="col-datetime">
            <template #default="{ row }">{{ formatDate(row.create_time) }}</template>
          </el-table-column>
          <el-table-column prop="environment" label="测试环境" min-width="112" width="112" align="center" />
          <el-table-column prop="req_count" label="需求数" min-width="104" width="104" align="center" />
          <el-table-column prop="case_count" label="用例数" min-width="104" width="104" align="center" />
          <el-table-column label="用例覆盖率" min-width="120" width="120" align="center">
            <template #default="{ row }">{{ row.coverage_rate }}%</template>
          </el-table-column>
          <el-table-column label="通过率" min-width="104" width="104" align="center">
            <template #default="{ row }">{{ row.pass_rate }}%</template>
          </el-table-column>
          <el-table-column prop="defect_count" label="缺陷数" min-width="104" width="104" align="center" />
          <el-table-column prop="creator_name" label="测试人员" min-width="120" align="center" show-overflow-tooltip />
          <el-table-column label="操作" min-width="240" width="240" fixed="right" align="center">
            <template #default="{ row }">
              <div v-if="isRecycleMode" class="recycle-row-actions">
                <el-button link type="success" size="small" :disabled="isSelectMode" @click="restoreRow(row)">恢复</el-button>
                <el-button link type="danger" size="small" :disabled="isSelectMode" @click="hardDeleteRow(row)">彻底删除</el-button>
              </div>
              <TableActionGroup
                v-else
                :row="row"
                :actions="reportTableActions(row)"
                @action="handleReportTableAction"
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

    <el-dialog v-model="showDialog" :title="editingId ? '编辑测试报告' : '新增测试报告'" width="480px" class="cyber-dialog-dark">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="报告名称" prop="report_name">
          <el-input v-model="form.report_name" placeholder="请输入报告名称" />
        </el-form-item>
        <el-form-item label="关联计划" prop="plan">
          <el-select v-model="form.plan" placeholder="请选择测试计划">
            <el-option v-for="p in plans" :key="p.id" :label="p.plan_name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="测试环境" prop="environment">
          <el-select v-model="form.environment">
            <el-option label="TEST" value="TEST" />
            <el-option label="PROD" value="PROD" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Plus, Reading, Search, View } from '@element-plus/icons-vue'
import TableActionGroup from '@/components/common/TableActionGroup.vue'
import {
  getReportsApi,
  createReportApi,
  updateReportApi,
  deleteReportApi,
  getPlansApi,
  batchDeleteReportsApi,
  batchCopyReportsApi,
  batchRefreshReportsFromPlanApi,
  batchExecuteReportsApi,
  getReportsRecycleApi,
  restoreReportApi,
  hardDeleteReportApi,
  bulkSoftDeleteReportsApi,
  bulkRestoreReportsApi,
  bulkHardDeleteReportsApi,
} from '@/api/execution'

const router = useRouter()
const list = ref([])
const plans = ref([])
const loading = ref(false)
const searchKw = ref('')
const showDialog = ref(false)
const saving = ref(false)
const editingId = ref(null)
const formRef = ref()
const page = ref(1)
const PAGE_SIZE = 10
const selectedIds = ref([])
const batchDeleting = ref(false)
const batchCopying = ref(false)
const batchRefreshing = ref(false)
const batchExecuting = ref(false)
const batchRestoring = ref(false)
const batchHardDeleting = ref(false)
const isRecycleMode = ref(false)
const isSelectMode = ref(false)
function reportTableActions(row) {
  return [
    { key: 'detail', tooltip: '查看详情', icon: View, type: 'primary' },
    {
      key: 'plan',
      tooltip: planIdOf(row) ? '查看计划' : '无关联计划',
      icon: Reading,
      type: 'success',
      disabled: !planIdOf(row),
    },
    { key: 'edit', tooltip: '编辑报告', icon: Edit, type: 'primary' },
    { key: 'delete', tooltip: '删除报告', icon: Delete, type: 'danger' },
  ]
}

function handleReportTableAction(action, row) {
  if (action === 'detail') router.push(`/test-report/${row.id}`)
  else if (action === 'plan' && planIdOf(row)) router.push(`/test-plan/${planIdOf(row)}`)
  else if (action === 'edit') openEdit(row)
  else if (action === 'delete') delItem(row)
}
const total = ref(0)
const form = ref({ report_name: '', plan: null, environment: 'TEST' })
const rules = {
  report_name: [{ required: true, message: '请输入报告名称', trigger: 'blur' }],
  plan: [{ required: true, message: '请选择测试计划', trigger: 'change' }],
  environment: [{ required: true, message: '请选择测试环境', trigger: 'change' }],
}

const filteredList = computed(() => {
  const q = (searchKw.value || '').trim()
  if (!q) return list.value
  return list.value.filter((i) => String(i.report_name ?? '').includes(q))
})

function planIdOf(row) {
  const p = row?.plan_id ?? row?.plan
  if (p == null) return null
  return typeof p === 'object' ? p.id : p
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

function methodLabel(v) { return { 1: '新建生成', 2: '定期生成', 3: '计划生成' }[v] || '-' }
function methodTagType(v) { return { 1: 'primary', 2: 'success', 3: 'warning' }[v] || '' }
function formatDate(dt) { return dt ? dt.slice(0, 16).replace('T', ' ') : '-' }

async function loadPlans() {
  try {
    const { data } = await getPlansApi({ page_size: 500 })
    plans.value = normalizeListResponse(data)
  } catch {
    plans.value = []
  }
}

async function loadList() {
  loading.value = true
  try {
    const api = isRecycleMode.value ? getReportsRecycleApi : getReportsApi
    const { data } = await api({ page: page.value, page_size: PAGE_SIZE })
    const rows = normalizeListResponse(data)
    list.value = rows
    total.value = normalizeTotal(data, rows)
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '加载失败'
    ElMessage.error(typeof msg === 'string' ? msg : '加载报告失败')
    list.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.value = { report_name: '', plan: null, environment: 'TEST' }
  showDialog.value = true
}

function openEdit(row) {
  editingId.value = row.id
  form.value = {
    report_name: row.report_name,
    plan: planIdOf(row),
    environment: row.environment || 'TEST',
  }
  showDialog.value = true
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

async function delItem(row) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.report_name}」？`, '警告', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteReportApi(row.id)
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
    await ElMessageBox.confirm(`确定将选中的 ${selectedIds.value.length} 条测试报告移入回收站？`, '警告', { type: 'warning' })
  } catch {
    return
  }
  batchDeleting.value = true
  try {
    const { data } = await bulkSoftDeleteReportsApi({ ids: selectedIds.value })
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
    const { data } = await bulkRestoreReportsApi({ ids: selectedIds.value })
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
    await ElMessageBox.confirm(`确定彻底删除选中的 ${selectedIds.value.length} 条测试报告？此操作不可恢复。`, '警告', { type: 'error' })
  } catch {
    return
  }
  batchHardDeleting.value = true
  try {
    const { data } = await bulkHardDeleteReportsApi({ ids: selectedIds.value })
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
    await restoreReportApi(row.id)
    ElMessage.success('已恢复')
    loadList()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '恢复失败'
    ElMessage.error(typeof msg === 'string' ? msg : '恢复失败')
  }
}

async function hardDeleteRow(row) {
  try {
    await ElMessageBox.confirm(`确定彻底删除「${row.report_name ?? row.id}」？此操作不可恢复。`, '警告', { type: 'error' })
  } catch {
    return
  }
  try {
    await hardDeleteReportApi(row.id)
    ElMessage.success('已彻底删除')
    loadList()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '彻底删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '彻底删除失败')
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
    const { data } = await batchCopyReportsApi({ ids: selectedIds.value, name_suffix: suffix })
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

async function batchRefreshSelected() {
  if (!selectedIds.value.length) return
  batchRefreshing.value = true
  try {
    const { data } = await batchRefreshReportsFromPlanApi({ ids: selectedIds.value })
    const updated = Number(data?.updated ?? data?.data?.updated ?? 0)
    const missing = Array.isArray(data?.missing_ids) ? data.missing_ids.length : Array.isArray(data?.data?.missing_ids) ? data.data.missing_ids.length : 0
    const errors = Array.isArray(data?.errors) ? data.errors.length : Array.isArray(data?.data?.errors) ? data.data.errors.length : 0
    if (errors) ElMessage.warning(`已刷新 ${updated} 条；缺失 ${missing} 条；失败 ${errors} 条`)
    else ElMessage.success(`已刷新 ${updated} 条；缺失 ${missing} 条`)
    loadList()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '批量刷新失败'
    ElMessage.error(typeof msg === 'string' ? msg : '批量刷新失败')
  } finally {
    batchRefreshing.value = false
  }
}

async function batchExecuteSelected() {
  if (!selectedIds.value.length) return
  let envId = ''
  try {
    const { value } = await ElMessageBox.prompt('请输入 environment_id（可留空）', '批量执行测试报告', {
      inputValue: '',
      confirmButtonText: '执行',
      cancelButtonText: '取消',
    })
    envId = String(value ?? '').trim()
  } catch {
    return
  }
  batchExecuting.value = true
  try {
    const payload = { ids: selectedIds.value }
    if (envId) payload.environment_id = Number(envId)
    const { data } = await batchExecuteReportsApi(payload)
    const triggered = Number(data?.triggered ?? data?.data?.triggered ?? 0)
    const missing = Array.isArray(data?.missing_ids) ? data.missing_ids.length : Array.isArray(data?.data?.missing_ids) ? data.data.missing_ids.length : 0
    const errors = Array.isArray(data?.errors) ? data.errors.length : Array.isArray(data?.data?.errors) ? data.data.errors.length : 0
    if (errors) ElMessage.warning(`已触发 ${triggered} 条；缺失 ${missing} 条；失败 ${errors} 条`)
    else ElMessage.success(`已触发 ${triggered} 条；缺失 ${missing} 条`)
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '批量执行失败'
    ElMessage.error(typeof msg === 'string' ? msg : '批量执行失败')
  } finally {
    batchExecuting.value = false
  }
}

async function submit() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (editingId.value) {
      await updateReportApi(editingId.value, { ...form.value })
      ElMessage.success('更新成功')
    } else {
      const now = new Date().toISOString()
      await createReportApi({ ...form.value, start_time: now, end_time: now })
      ElMessage.success('创建成功')
    }
    showDialog.value = false
    loadList()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.message || '保存失败'
    ElMessage.error(typeof msg === 'string' ? msg : '保存失败')
  } finally {
    saving.value = false
  }
}

watch(showDialog, async (open) => {
  if (open) await loadPlans()
  else editingId.value = null
})

onMounted(async () => {
  loadList()
  await loadPlans()
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
</style>
