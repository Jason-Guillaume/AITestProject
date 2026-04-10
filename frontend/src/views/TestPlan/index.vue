<template>
  <div class="page-wrap cyber-page admin-list-page">
    <el-card class="admin-list-card" shadow="never">
      <div class="admin-toolbar-row">
        <div class="admin-toolbar-row__left">
          <el-button type="primary" @click="showDialog = true">
            <el-icon><Plus /></el-icon> 新增测试计划
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
        <el-table :data="filteredList" v-loading="loading" stripe border class="admin-data-table" size="default">
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
              <TableActionGroup :row="row" :actions="planTableActions(row)" @action="handlePlanTableAction" />
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CopyDocument, Delete, Edit, FolderOpened, Plus, Search, View } from '@element-plus/icons-vue'
import TableActionGroup from '@/components/common/TableActionGroup.vue'
import { getPlansApi, createPlanApi, deletePlanApi } from '@/api/execution'
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
    const { data } = await getPlansApi({ page: page.value, page_size: PAGE_SIZE })
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

async function delItem(row) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.plan_name ?? row.id}」？`, '警告', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deletePlanApi(row.id)
    ElMessage.success('删除成功')
    loadList()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.message || '删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '删除失败')
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
