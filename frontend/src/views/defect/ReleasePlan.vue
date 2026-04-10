<template>
  <div class="page-wrap cyber-page release-plan-page">
    <div class="page-toolbar defect-toolbar">
      <div class="defect-toolbar__actions">
        <el-button type="primary" size="default" @click="openCreate">
          <el-icon><Plus /></el-icon> 新增发布计划
        </el-button>
      </div>
      <div class="defect-toolbar__filters">
        <el-select
          v-model="filterProjectId"
          placeholder="按项目筛选"
          clearable
          filterable
          size="default"
          class="release-filter"
          @change="onFilterProject"
        >
          <el-option
            v-for="p in projectOptions"
            :key="p.id"
            :label="p.project_name"
            :value="p.id"
          />
        </el-select>
      </div>
    </div>

    <div class="table-card cyber-glass release-table-card">
      <el-table :data="list" v-loading="loading" class="admin-data-table">
        <template #empty>
          <el-empty description="暂无发布计划数据" :image-size="88" />
        </template>
        <el-table-column prop="id" label="ID" width="80" align="left" />
        <el-table-column prop="project_name" label="所属项目" min-width="120" align="center" show-overflow-tooltip>
          <template #default="{ row }">{{ row.project_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="release_name" label="发布名称" min-width="140" align="left" show-overflow-tooltip>
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/defect/release/${row.id}`)">{{ row.release_name }}</el-button>
          </template>
        </el-table-column>
        <el-table-column prop="version_no" label="版本号" min-width="104" width="104" align="center" show-overflow-tooltip />
        <el-table-column label="计划发布日期" min-width="168" width="168" align="center" class-name="col-datetime">
          <template #default="{ row }">{{ formatDate(row.release_date) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="releaseTag(row.status)" size="small">{{ releaseLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="creator_name" label="创建人" min-width="104" width="104" align="center" show-overflow-tooltip />
        <el-table-column label="创建时间" min-width="176" width="176" align="center" class-name="col-datetime">
          <template #default="{ row }">{{ formatDate(row.create_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" min-width="220" width="220" fixed="right" align="center" class-name="col-release-actions">
          <template #default="{ row }">
            <TableActionGroup :row="row" :actions="releaseTableActions" @action="handleReleaseTableAction" />
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
          @current-change="load"
        />
      </div>
    </div>

    <el-dialog v-model="showDialog" :title="editing ? '编辑发布计划' : '新增发布计划'" width="440px" class="cyber-dialog-dark">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
        <el-form-item label="所属项目" prop="project">
          <el-select
            v-model="form.project"
            placeholder="可选，与项目管理中的版本发布一致"
            clearable
            filterable
            class="w-full"
          >
            <el-option
              v-for="p in projectOptions"
              :key="p.id"
              :label="p.project_name"
              :value="p.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="发布名称" prop="release_name">
          <el-input v-model="form.release_name" placeholder="请输入发布名称" />
        </el-form-item>
        <el-form-item label="版本号" prop="version_no">
          <el-input v-model="form.version_no" placeholder="如 V1.0.0" />
        </el-form-item>
        <el-form-item label="计划发布日期" prop="release_date">
          <el-date-picker v-model="form.release_date" type="datetime" placeholder="请选择日期" value-format="YYYY-MM-DDTHH:mm:ss" />
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Plus, View } from '@element-plus/icons-vue'
import TableActionGroup from '@/components/common/TableActionGroup.vue'
import {
  getProjectsApi,
  getReleasesApi,
  createReleaseApi,
  updateReleaseApi,
  deleteReleaseApi,
} from '@/api/project'

const PAGE_SIZE = 10
const releaseTableActions = [
  { key: 'detail', tooltip: '查看详情', icon: View, type: 'primary' },
  { key: 'edit', tooltip: '编辑计划', icon: Edit, type: 'primary' },
  { key: 'delete', tooltip: '删除计划', icon: Delete, type: 'danger' },
]

function handleReleaseTableAction(action, row) {
  if (action === 'detail') router.push(`/defect/release/${row.id}`)
  else if (action === 'edit') editItem(row)
  else if (action === 'delete') delItem(row)
}

const router = useRouter()
const list = ref([])
const loading = ref(false)
const showDialog = ref(false)
const editing = ref(null)
const saving = ref(false)
const formRef = ref()
const page = ref(1)
const total = ref(0)
const filterProjectId = ref(null)
const projectOptions = ref([])
const form = ref({ project: null, release_name: '', version_no: '', release_date: '' })
const rules = {
  release_name: [{ required: true, message: '请输入发布名称', trigger: 'blur' }],
  version_no: [{ required: true, message: '请输入版本号', trigger: 'blur' }],
  release_date: [{ required: true, message: '请选择计划发布日期', trigger: 'change' }],
}

function releaseLabel(v) { return { 1: '待发布', 2: '已发布', 3: '已取消' }[v] || '-' }
function releaseTag(v) { return { 1: 'warning', 2: 'success', 3: 'info' }[v] || '' }
function formatDate(dt) { return dt ? dt.slice(0, 16).replace('T', ' ') : '-' }

function normalizeList(payload) {
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

async function loadProjectOptions() {
  try {
    const { data } = await getProjectsApi()
    projectOptions.value = normalizeList(data)
  } catch {
    projectOptions.value = []
  }
}

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: PAGE_SIZE }
    if (filterProjectId.value) params.project = filterProjectId.value
    const { data } = await getReleasesApi(params)
    const rows = normalizeList(data)
    list.value = rows
    total.value = normalizeTotal(data, rows)
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.message || '加载失败'
    ElMessage.error(typeof msg === 'string' ? msg : '加载失败')
    list.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function onFilterProject() {
  page.value = 1
  load()
}

function openCreate() {
  editing.value = null
  form.value = { project: null, release_name: '', version_no: '', release_date: '' }
  showDialog.value = true
}

function editItem(row) {
  editing.value = row
  const pid = row.project != null && typeof row.project === 'object' ? row.project.id : row.project
  form.value = {
    project: pid ?? null,
    release_name: row.release_name,
    version_no: row.version_no,
    release_date: row.release_date,
  }
  showDialog.value = true
}

async function delItem(row) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.release_name}」？`, '警告', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteReleaseApi(row.id)
    ElMessage.success('删除成功')
    load()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.message || '删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '删除失败')
  }
}

async function submit() {
  await formRef.value.validate()
  saving.value = true
  const payload = { ...form.value }
  try {
    if (editing.value) {
      await updateReleaseApi(editing.value.id, payload)
      ElMessage.success('更新成功')
    } else {
      await createReleaseApi(payload)
      ElMessage.success('创建成功')
    }
    showDialog.value = false
    editing.value = null
    load()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.message || '保存失败'
    ElMessage.error(typeof msg === 'string' ? msg : '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await loadProjectOptions()
  load()
})
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

.release-filter {
  width: 240px;
}

.w-full {
  width: 100%;
}

.release-plan-page .release-table-card.cyber-glass {
  padding: 20px 22px 18px;
}

.release-actions {
  display: inline-flex;
  flex-wrap: nowrap;
  align-items: center;
  justify-content: center;
  gap: 2px;
  white-space: nowrap;
}

.release-plan-page :deep(.col-release-actions .cell) {
  flex-wrap: nowrap !important;
  justify-content: center !important;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.release-plan-page :deep(.el-empty__description) {
  color: rgba(255, 255, 255, 0.55);
}
.release-plan-page :deep(.el-empty) {
  padding: 28px 16px;
}
</style>
