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
        <div class="panel-title">测试结果</div>
        <el-empty description="暂无与版本绑定的用例执行数据（需执行/报告模块对接）" :image-size="72" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getReleaseDetailApi, updateReleaseApi } from '@/api/project'
import { getDefectsApi } from '@/api/defect'

const route = useRoute()
const detail = ref({})
const defectList = ref([])
const defectLoading = ref(false)
const formRef = ref()
const saving = ref(false)
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
</style>
