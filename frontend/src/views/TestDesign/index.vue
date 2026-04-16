<template>
  <div class="page-wrap cyber-page admin-list-page">
    <el-card class="admin-list-card" shadow="never">
      <div class="admin-toolbar-row">
        <div class="admin-toolbar-row__left">
          <el-button type="primary" @click="showDialog = true">
            <el-icon><Plus /></el-icon> 新增测试设计
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
            :loading="batchArchiving"
            @click="batchArchiveSelected"
          >
            批量归档
          </el-button>
          <el-dropdown
            v-if="isSelectMode && !isRecycleMode && selectedIds.length > 0"
            trigger="click"
            :disabled="selectedIds.length === 0"
            @command="batchSetReviewStatus"
          >
            <el-button plain>
              批量评审状态
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="1">未评审</el-dropdown-item>
                <el-dropdown-item command="2">评审中</el-dropdown-item>
                <el-dropdown-item command="3">已评审</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <div class="admin-toolbar-row__right">
          <el-input v-model="searchKw" placeholder="请输入测试设计名称" clearable class="search-input">
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
          <el-table-column label="测试设计名称" min-width="180" align="left">
            <template #default="{ row }">
              <el-button link type="primary" @click="router.push(`/test-design/${row.id}`)">{{ row.design_name }}</el-button>
            </template>
          </el-table-column>
          <el-table-column prop="req_count" label="需求数量" min-width="112" width="112" align="center" />
          <el-table-column prop="point_count" label="测试点数量" min-width="128" width="128" align="center" />
          <el-table-column prop="case_count" label="用例数量" min-width="112" width="112" align="center" />
          <el-table-column label="评审状态" min-width="120" width="120" align="center">
            <template #default="{ row }">
              <el-tag :type="reviewTagType(row.review_status)" size="small">{{ reviewLabel(row.review_status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="归档状态" min-width="120" width="120" align="center">
            <template #default="{ row }">
              <el-tag :type="row.archive_status === 2 ? 'success' : 'warning'" size="small">
                {{ row.archive_status === 2 ? '已归档' : '未归档' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="updater_name" label="更新人" min-width="112" width="112" align="center" show-overflow-tooltip />
          <el-table-column label="更新时间" min-width="184" width="184" align="center" class-name="col-datetime">
            <template #default="{ row }">{{ formatDate(row.update_time) }}</template>
          </el-table-column>
          <el-table-column prop="creator_name" label="创建人" min-width="112" width="112" align="center" show-overflow-tooltip />
          <el-table-column label="创建时间" min-width="184" width="184" align="center" class-name="col-datetime">
            <template #default="{ row }">{{ formatDate(row.create_time) }}</template>
          </el-table-column>
          <el-table-column label="操作" min-width="216" width="216" fixed="right" align="center">
            <template #default="{ row }">
              <div v-if="isRecycleMode" class="recycle-row-actions">
                <el-button link type="success" size="small" :disabled="isSelectMode" @click="restoreRow(row)">恢复</el-button>
                <el-button link type="danger" size="small" :disabled="isSelectMode" @click="hardDeleteRow(row)">彻底删除</el-button>
              </div>
              <TableActionGroup
                v-else
                :row="row"
                :actions="designTableActions"
                @action="handleDesignTableAction"
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

    <el-dialog v-model="showDialog" title="新增测试设计" width="440px" class="cyber-dialog-dark">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="设计名称" prop="design_name">
          <el-input v-model="form.design_name" placeholder="请输入设计名称" />
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
import { ArrowDown, CopyDocument, Delete, Edit, Plus, Search } from '@element-plus/icons-vue'
import TableActionGroup from '@/components/common/TableActionGroup.vue'
import {
  getDesignsApi,
  createDesignApi,
  deleteDesignApi,
  batchUpdateDesignsApi,
  getDesignsRecycleApi,
  restoreDesignApi,
  hardDeleteDesignApi,
  bulkSoftDeleteDesignsApi,
  bulkRestoreDesignsApi,
  bulkHardDeleteDesignsApi,
} from '@/api/testcase'

const router = useRouter()
const list = ref([])
const loading = ref(false)
const searchKw = ref('')
const showDialog = ref(false)
const saving = ref(false)
const formRef = ref()
const form = ref({ design_name: '' })
const rules = { design_name: [{ required: true, message: '请输入设计名称', trigger: 'blur' }] }
const page = ref(1)
const PAGE_SIZE = 10
const selectedIds = ref([])
const batchDeleting = ref(false)
const batchArchiving = ref(false)
const batchRestoring = ref(false)
const batchHardDeleting = ref(false)
const isRecycleMode = ref(false)
const isSelectMode = ref(false)
const designTableActions = [
  { key: 'edit', tooltip: '编辑设计', icon: Edit, type: 'primary' },
  { key: 'copy', tooltip: '复制设计', icon: CopyDocument, type: 'success' },
  { key: 'delete', tooltip: '删除设计', icon: Delete, type: 'danger' },
]

function handleDesignTableAction(action, row) {
  if (action === 'edit') router.push(`/test-design/${row.id}`)
  else if (action === 'copy') copyItem(row)
  else if (action === 'delete') delItem(row)
}
const total = ref(0)

/** DRF 无全局分页时接口可能直接返回数组，不能只用 results/data */
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

const filteredList = computed(() => {
  const q = (searchKw.value || '').trim()
  if (!q) return list.value
  return list.value.filter((i) => String(i.design_name ?? '').includes(q))
})

function reviewLabel(v) { return { 1: '未评审', 2: '评审中', 3: '已评审' }[v] || '-' }
function reviewTagType(v) { return { 1: 'info', 2: 'warning', 3: 'success' }[v] || '' }
function formatDate(dt) { return dt ? dt.slice(0, 16).replace('T', ' ') : '-' }

async function loadList() {
  loading.value = true
  try {
    const api = isRecycleMode.value ? getDesignsRecycleApi : getDesignsApi
    const { data } = await api({ page: page.value, page_size: PAGE_SIZE })
    const rows = normalizeListResponse(data)
    list.value = rows
    total.value = normalizeTotal(data, rows)
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '加载失败'
    ElMessage.error(typeof msg === 'string' ? msg : '加载测试设计失败')
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
  page.value = 1
  loadList()
}

async function copyItem(row) {
  const base = String(row.design_name ?? '未命名')
  try {
    await createDesignApi({
      design_name: `${base}_复制`,
      req_count: row.req_count ?? 0,
      point_count: row.point_count ?? 0,
      case_count: row.case_count ?? 0,
    })
    ElMessage.success('复制成功')
    loadList()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.message || '复制失败'
    ElMessage.error(typeof msg === 'string' ? msg : '复制失败')
  }
}

async function delItem(row) {
  try {
    await ElMessageBox.confirm(`确定将「${row.design_name ?? row.id}」移入回收站？`, '警告', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteDesignApi(row.id)
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
    await ElMessageBox.confirm(`确定将选中的 ${selectedIds.value.length} 条测试设计移入回收站？`, '警告', { type: 'warning' })
  } catch {
    return
  }
  batchDeleting.value = true
  try {
    const { data } = await bulkSoftDeleteDesignsApi({ ids: selectedIds.value })
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
    const { data } = await bulkRestoreDesignsApi({ ids: selectedIds.value })
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
    await ElMessageBox.confirm(`确定彻底删除选中的 ${selectedIds.value.length} 条测试设计？此操作不可恢复。`, '警告', { type: 'error' })
  } catch {
    return
  }
  batchHardDeleting.value = true
  try {
    const { data } = await bulkHardDeleteDesignsApi({ ids: selectedIds.value })
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
    await restoreDesignApi(row.id)
    ElMessage.success('已恢复')
    loadList()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '恢复失败'
    ElMessage.error(typeof msg === 'string' ? msg : '恢复失败')
  }
}

async function hardDeleteRow(row) {
  try {
    await ElMessageBox.confirm(`确定彻底删除「${row.design_name ?? row.id}」？此操作不可恢复。`, '警告', { type: 'error' })
  } catch {
    return
  }
  try {
    await hardDeleteDesignApi(row.id)
    ElMessage.success('已彻底删除')
    loadList()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '彻底删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '彻底删除失败')
  }
}

async function batchArchiveSelected() {
  if (!selectedIds.value.length) return
  batchArchiving.value = true
  try {
    const { data } = await batchUpdateDesignsApi({ ids: selectedIds.value, patch: { archive_status: 2 } })
    const updated = Number(data?.updated ?? data?.data?.updated ?? 0)
    const missing = Array.isArray(data?.missing_ids) ? data.missing_ids.length : Array.isArray(data?.data?.missing_ids) ? data.data.missing_ids.length : 0
    const errors = Array.isArray(data?.errors) ? data.errors.length : Array.isArray(data?.data?.errors) ? data.data.errors.length : 0
    if (errors) ElMessage.warning(`已归档 ${updated} 条；缺失 ${missing} 条；失败 ${errors} 条`)
    else ElMessage.success(`已归档 ${updated} 条；缺失 ${missing} 条`)
    loadList()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '批量归档失败'
    ElMessage.error(typeof msg === 'string' ? msg : '批量归档失败')
  } finally {
    batchArchiving.value = false
  }
}

async function batchSetReviewStatus(cmd) {
  const v = Number(cmd)
  if (!selectedIds.value.length) return
  if (![1, 2, 3].includes(v)) return
  try {
    const { data } = await batchUpdateDesignsApi({ ids: selectedIds.value, patch: { review_status: v } })
    const updated = Number(data?.updated ?? data?.data?.updated ?? 0)
    const missing = Array.isArray(data?.missing_ids) ? data.missing_ids.length : Array.isArray(data?.data?.missing_ids) ? data.data.missing_ids.length : 0
    const errors = Array.isArray(data?.errors) ? data.errors.length : Array.isArray(data?.data?.errors) ? data.data.errors.length : 0
    if (errors) ElMessage.warning(`已更新 ${updated} 条；缺失 ${missing} 条；失败 ${errors} 条`)
    else ElMessage.success(`已更新 ${updated} 条；缺失 ${missing} 条`)
    loadList()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '批量更新失败'
    ElMessage.error(typeof msg === 'string' ? msg : '批量更新失败')
  }
}

async function submit() {
  await formRef.value.validate()
  saving.value = true
  try {
    await createDesignApi({ ...form.value })
    ElMessage.success('创建成功')
    showDialog.value = false
    form.value = { design_name: '' }
    loadList()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.message || '创建失败'
    ElMessage.error(typeof msg === 'string' ? msg : '创建失败')
  } finally {
    saving.value = false
  }
}

watch(showDialog, (open) => {
  if (open) {
    form.value = { design_name: '' }
    formRef.value?.resetFields?.()
  }
})

onMounted(loadList)
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
