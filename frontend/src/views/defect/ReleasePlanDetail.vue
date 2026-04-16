<template>
  <div class="release-detail cyber-page">
    <div class="detail-header">
      <div class="detail-header__left">
        <span class="release-version">{{ detail.version_no || '—' }}</span>
        <span class="release-name">{{ detail.release_name || '发布计划详情' }}</span>
        <el-tag :type="releaseTag(detail.status)" size="small">{{ releaseLabel(detail.status) }}</el-tag>
      </div>
      <div class="detail-header__right">
        <span class="update-tip">最近更新：{{ detail.updater_name || '—' }} {{ formatDate(detail.update_time) }}</span>
      </div>
    </div>

    <div class="detail-body">
      <div class="left-panel cyber-glass">
        <div class="panel-title">发布信息（与后端 ReleasePlan 一致）</div>
        <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" label-position="left" size="small">
          <el-form-item label="所属项目">
            <span class="ro">{{ detail.project_name || '—' }}</span>
          </el-form-item>
          <el-form-item label="发布名称" prop="release_name">
            <el-input v-model="form.release_name" placeholder="发布名称" />
          </el-form-item>
          <el-form-item label="版本号" prop="version_no">
            <el-input v-model="form.version_no" placeholder="如 V1.0.0" />
          </el-form-item>
          <el-form-item label="计划发布日" prop="release_date">
            <el-date-picker
              v-model="form.release_date"
              type="datetime"
              format="YYYY/MM/DD HH:mm"
              value-format="YYYY-MM-DDTHH:mm:ss"
              style="width: 220px"
            />
          </el-form-item>
          <el-form-item label="状态" prop="status">
            <el-select v-model="form.status" style="width: 160px">
              <el-option label="待发布" :value="1" />
              <el-option label="已发布" :value="2" />
              <el-option label="已取消" :value="3" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saving" @click="saveRelease">保存</el-button>
          </el-form-item>
        </el-form>

        <div class="panel-title" style="margin-top: 16px">关联缺陷</div>
        <el-table :data="defectList" size="small" v-loading="defectLoading" class="admin-data-table">
          <template #empty>
            <el-empty description="暂无关联缺陷" :image-size="72" />
          </template>
          <el-table-column prop="defect_no" label="缺陷ID" min-width="96" width="96" align="left" />
          <el-table-column prop="defect_name" label="缺陷标题" min-width="120" align="left" show-overflow-tooltip>
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="$router.push(`/defect/detail/${row.id}`)">{{
                row.defect_name
              }}</el-button>
            </template>
          </el-table-column>
          <el-table-column label="等级" width="72" align="center">
            <template #default="{ row }">{{ severityLabel(row.severity) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="88" align="center">
            <template #default="{ row }">
              <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="handler_name" label="处理人" min-width="96" width="96" align="center" show-overflow-tooltip />
        </el-table>
      </div>

      <div class="right-panel cyber-glass">
        <div class="panel-title">风险简报（ORM 聚合，无大模型）</div>
        <div class="risk-toolbar">
          <span class="risk-toolbar__label">执行统计窗口（天）</span>
          <el-input-number v-model="briefDays" :min="1" :max="90" size="small" controls-position="right" />
          <el-button type="primary" size="small" :loading="briefLoading" @click="loadRiskBrief">刷新简报</el-button>
        </div>
        <el-skeleton v-if="briefLoading && !briefData" :rows="4" animated />
        <template v-else-if="briefData">
          <el-descriptions :column="2" size="small" border class="risk-desc">
            <el-descriptions-item label="关联用例">{{ briefData.coverage?.linked_cases ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="测试计划（总数）">{{ briefData.coverage?.test_plans?.total ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="计划·未开始">{{ briefData.coverage?.test_plans?.not_started ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="计划·进行中">{{ briefData.coverage?.test_plans?.in_progress ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="计划·已完成">{{ briefData.coverage?.test_plans?.completed ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="缺陷·未关闭">{{ briefData.defects?.open_not_closed ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="缺陷·总数">{{ briefData.defects?.total ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="API 执行·窗口内总次数">{{ briefData.executions?.total_runs ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="API 执行·通过">{{ briefData.executions?.passed ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="API 执行·未通过">{{ briefData.executions?.failed ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="近窗从未执行用例数">{{ briefData.executions?.never_executed_cases ?? 0 }}</el-descriptions-item>
          </el-descriptions>
          <div class="panel-title" style="margin-top: 14px">从未执行用例（与上方统计窗口天数一致）</div>
          <div class="risk-toolbar">
            <el-button type="primary" size="small" :loading="neverLoading" @click="loadNeverExecuted">加载清单</el-button>
            <el-button size="small" :disabled="neverExporting" :loading="neverExporting" @click="exportNeverCsv">
              导出 CSV
            </el-button>
            <span v-if="neverTotal != null" class="never-total">合计 {{ neverTotal }} 条（列表最多展示 500 条）</span>
          </div>
          <el-table
            :data="neverItems"
            size="small"
            v-loading="neverLoading"
            class="admin-data-table"
            max-height="280"
            empty-text="点击「加载清单」"
          >
            <el-table-column prop="id" label="用例ID" width="88" align="center" />
            <el-table-column prop="case_name" label="标题" min-width="160" show-overflow-tooltip />
            <el-table-column prop="test_type" label="类型" width="100" align="center" />
            <el-table-column prop="module_name" label="模块" min-width="120" show-overflow-tooltip />
          </el-table>
          <div class="panel-title" style="margin-top: 14px">Markdown 摘要</div>
          <pre class="risk-md">{{ briefData.markdown || '—' }}</pre>
        </template>
        <el-empty v-else description="暂无简报数据" :image-size="72" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  getReleaseDetailApi,
  updateReleaseApi,
  getReleaseRiskBriefApi,
  getReleaseNeverExecutedCasesApi,
  downloadReleaseNeverExecutedCsv,
} from '@/api/project'
import { getDefectsApi } from '@/api/defect'

const route = useRoute()
const detail = ref({})
const defectList = ref([])
const defectLoading = ref(false)
const formRef = ref()
const saving = ref(false)
const briefLoading = ref(false)
const briefDays = ref(7)
const briefData = ref(null)
const neverLoading = ref(false)
const neverExporting = ref(false)
const neverItems = ref([])
const neverTotal = ref(null)
const form = ref({
  release_name: '',
  version_no: '',
  release_date: '',
  status: 1,
})
const rules = {
  release_name: [{ required: true, message: '请输入发布名称', trigger: 'blur' }],
  version_no: [{ required: true, message: '请输入版本号', trigger: 'blur' }],
  release_date: [{ required: true, message: '请选择日期', trigger: 'change' }],
}

function releaseLabel(v) {
  return { 1: '待发布', 2: '已发布', 3: '已取消' }[v] || '-'
}
function releaseTag(v) {
  return { 1: 'warning', 2: 'success', 3: 'info' }[v] || ''
}
function severityLabel(v) {
  return { 1: '致命', 2: '严重', 3: '一般', 4: '建议' }[v] || '-'
}
function statusLabel(v) {
  return { 1: '新缺陷', 2: '处理中', 3: '已拒绝', 4: '已关闭' }[v] || '-'
}
function statusTag(v) {
  return { 1: 'danger', 2: 'warning', 3: 'info', 4: 'success' }[v] || ''
}
function formatDate(dt) {
  return dt ? dt.slice(0, 16).replace('T', ' ') : ''
}

function normalizeListPayload(payload) {
  if (Array.isArray(payload)) return payload
  if (payload?.results && Array.isArray(payload.results)) return payload.results
  if (payload?.data && Array.isArray(payload.data)) return payload.data
  return []
}

function syncFormFromDetail() {
  const d = detail.value || {}
  form.value = {
    release_name: d.release_name ?? '',
    version_no: d.version_no ?? '',
    release_date: d.release_date ?? '',
    status: d.status ?? 1,
  }
}

async function loadRiskBrief() {
  const id = route.params.id
  if (!id) return
  briefLoading.value = true
  try {
    const { data } = await getReleaseRiskBriefApi(id, { days: briefDays.value })
    briefData.value = data?.data ?? data ?? null
    neverItems.value = []
    neverTotal.value = null
  } catch (err) {
    briefData.value = null
    const msg = err?.response?.data?.detail || err?.response?.data?.msg || err?.message || '加载简报失败'
    ElMessage.error(typeof msg === 'string' ? msg : '加载简报失败')
  } finally {
    briefLoading.value = false
  }
}

async function loadNeverExecuted() {
  const id = route.params.id
  if (!id) return
  neverLoading.value = true
  try {
    const { data } = await getReleaseNeverExecutedCasesApi(id, { days: briefDays.value, limit: 500 })
    neverItems.value = Array.isArray(data?.items) ? data.items : []
    neverTotal.value = Number(data?.total ?? neverItems.value.length) || 0
  } catch (err) {
    neverItems.value = []
    neverTotal.value = null
    const msg = err?.response?.data?.detail || err?.response?.data?.msg || err?.message || '加载失败'
    ElMessage.error(typeof msg === 'string' ? msg : '加载从未执行清单失败')
  } finally {
    neverLoading.value = false
  }
}

async function exportNeverCsv() {
  const id = route.params.id
  if (!id) return
  neverExporting.value = true
  try {
    await downloadReleaseNeverExecutedCsv(id, { days: briefDays.value, limit: 200000 })
  } catch (err) {
    const msg = err?.message || err?.response?.data?.detail || '导出失败'
    ElMessage.error(typeof msg === 'string' ? msg : '导出失败')
  } finally {
    neverExporting.value = false
  }
}

async function saveRelease() {
  const id = route.params.id
  if (!id) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  saving.value = true
  try {
    await updateReleaseApi(id, { ...form.value })
    ElMessage.success('保存成功')
    const { data } = await getReleaseDetailApi(id)
    detail.value = data?.data || data || {}
    syncFormFromDetail()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.message || '保存失败'
    ElMessage.error(typeof msg === 'string' ? msg : '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  const id = route.params.id
  if (!id) return
  defectLoading.value = true
  try {
    const { data } = await getReleaseDetailApi(id)
    detail.value = data?.data || data || {}
    syncFormFromDetail()
    await loadRiskBrief()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.message || '加载失败'
    ElMessage.error(typeof msg === 'string' ? msg : '加载发布计划失败')
  }
  try {
    const defRes = await getDefectsApi({ release_version: id, page_size: 500 })
    defectList.value = normalizeListPayload(defRes.data)
  } catch {
    defectList.value = []
  } finally {
    defectLoading.value = false
  }
})
</script>

<style scoped>
.release-detail {
  background: transparent;
  border-radius: 10px;
  padding: 0;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding: 16px 18px;
  border-radius: 10px;
  background: rgba(20, 28, 47, 0.6);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 255, 255, 0.15);
}

.detail-header__left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.release-version {
  font-size: 16px;
  font-weight: 700;
  font-family: ui-monospace, 'Cascadia Code', monospace;
  color: #00d8ff;
  text-shadow: 0 0 12px rgba(0, 216, 255, 0.35);
}

.release-name {
  font-size: 15px;
  font-weight: 600;
  color: #e2e8f0;
}
.update-tip {
  font-size: 12px;
  color: rgba(226, 232, 240, 0.55);
}
.detail-body {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}
.left-panel {
  flex: 0 0 460px;
}
.right-panel {
  flex: 1;
  min-width: 0;
}
.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 12px;
}
.ro {
  font-size: 13px;
  color: rgba(226, 232, 240, 0.85);
}

.left-panel :deep(.el-form-item__label),
.right-panel :deep(.el-form-item__label) {
  color: rgba(226, 232, 240, 0.75);
}

.left-panel :deep(.el-input__wrapper),
.left-panel :deep(.el-textarea__inner),
.right-panel :deep(.el-input__wrapper) {
  background: rgba(10, 16, 28, 0.45);
  box-shadow: none;
  border: 1px solid rgba(0, 255, 255, 0.1);
  color: #e2e8f0;
}

.release-detail :deep(.el-empty__description) {
  color: rgba(226, 232, 240, 0.55);
}

.release-detail :deep(.right-panel .el-empty__description) {
  color: rgba(226, 232, 240, 0.5);
}

.risk-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.risk-toolbar__label {
  font-size: 12px;
  color: rgba(226, 232, 240, 0.65);
}
.never-total {
  font-size: 12px;
  color: rgba(226, 232, 240, 0.6);
}
.risk-desc {
  margin-top: 4px;
}
.risk-md {
  margin: 0;
  padding: 12px;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
  background: rgba(10, 16, 28, 0.45);
  border: 1px solid rgba(0, 255, 255, 0.12);
  border-radius: 8px;
  color: rgba(226, 232, 240, 0.88);
  max-height: 320px;
  overflow: auto;
}
</style>
