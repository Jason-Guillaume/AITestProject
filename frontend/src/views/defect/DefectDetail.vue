<template>
  <div class="defect-detail-page">
    <div class="detail-layout">
      <!-- 左侧表单 -->
      <div class="form-panel glass-panel">
        <el-form ref="formRef" :model="form" :rules="rules" label-width="90px" label-position="left">
          <el-form-item label="缺陷ID">
            <el-input :value="form.defect_no || '系统自动生成'" disabled />
          </el-form-item>
          <el-form-item label="发现版本">
            <el-select v-model="form.release_version" placeholder="请选择" style="width:100%">
              <el-option v-for="r in releases" :key="r.id" :label="r.version_no" :value="r.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="模块">
            <el-select v-model="form.module" placeholder="请选择" clearable style="width:100%">
              <el-option v-for="m in modules" :key="m.id" :label="m.name" :value="m.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="优先级" prop="priority">
            <el-select v-model="form.priority" placeholder="请选择" style="width:100%">
              <el-option label="高" :value="1" />
              <el-option label="中" :value="2" />
              <el-option label="低" :value="3" />
            </el-select>
          </el-form-item>
          <el-form-item label="严重程度" prop="severity">
            <el-select v-model="form.severity" placeholder="请选择" style="width:100%">
              <el-option label="致命" :value="1" />
              <el-option label="严重" :value="2" />
              <el-option label="一般" :value="3" />
              <el-option label="建议" :value="4" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="isEdit" label="状态" prop="status">
            <el-select v-model="form.status" placeholder="请选择" style="width:100%">
              <el-option label="新缺陷" :value="1" />
              <el-option label="处理中" :value="2" />
              <el-option label="已拒绝" :value="3" />
              <el-option label="已关闭" :value="4" />
            </el-select>
          </el-form-item>
          <el-form-item label="处理人" prop="handler">
            <el-select v-model="form.handler" placeholder="请选择" style="width:100%">
              <el-option v-for="u in users" :key="u.id" :label="u.real_name || u.username" :value="u.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="附件">
            <el-upload
              drag
              action="#"
              :auto-upload="false"
              :on-change="onFileChange"
              accept=".doc,.docx,.xls,.xlsx,.pdf"
              class="defect-upload"
            >
              <div class="upload-inner">
                <el-icon class="upload-inner__icon"><UploadFilled /></el-icon>
                <div class="upload-inner__hint">点击或将文件拖拽上传</div>
                <div class="upload-inner__meta">支持格式：doc,docx,xls,xlsx,pdf，单个文件不能超过20MB</div>
              </div>
            </el-upload>
            <div v-if="attachmentName" class="attachment-name">
              <el-icon><Paperclip /></el-icon> {{ attachmentName }}
            </div>
          </el-form-item>
        </el-form>

        <!-- 底部按钮 -->
        <div class="form-actions">
          <el-button type="primary" :loading="saving" @click="submit(isEdit ? 'save' : 'create')">{{ isEdit ? '保存' : '创建' }}</el-button>
          <el-button v-if="!isEdit" :loading="saving" @click="submit('create_continue')">提交并继续创建</el-button>
          <el-button v-if="!isEdit" @click="submit('draft')">暂存</el-button>
          <el-button @click="router.push('/defect/list')">取消</el-button>
        </div>
      </div>

      <!-- 右侧内容区 -->
      <div class="content-panel glass-panel">
        <el-form-item label="缺陷名称" label-width="80px" class="name-item">
          <el-input v-model="form.defect_name" placeholder="请输入" class="defect-name-input" />
        </el-form-item>
        <div class="content-label">缺陷内容</div>
        <div class="rich-editor">
          <div class="editor-toolbar">
            <el-button-group size="small">
              <el-button><b>B</b></el-button>
              <el-button><i>I</i></el-button>
            </el-button-group>
            <el-button-group size="small" style="margin-left:4px">
              <el-button>有序列表</el-button>
              <el-button>无序列表</el-button>
            </el-button-group>
          </div>
          <el-input
            v-model="form.defect_content"
            type="textarea"
            :rows="16"
            placeholder="请输入文字"
            class="editor-textarea"
          />
          <div class="editor-footer">{{ form.defect_content?.length || 0 }}字</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled, Paperclip } from '@element-plus/icons-vue'
import { createDefectApi, getDefectDetailApi, updateDefectApi } from '@/api/defect'
import { getReleasesApi } from '@/api/project'
import { getModulesApi } from '@/api/testcase'
import { getUsersApi } from '@/api/system'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => Boolean(route.params.id))
const saving = ref(false)
const formRef = ref()
const attachmentName = ref('')
const releases = ref([])
const modules = ref([])
const users = ref([])

const form = ref({
  defect_no: '',
  defect_name: '',
  release_version: null,
  module: null,
  priority: 2,
  severity: 3,
  status: 1,
  handler: null,
  defect_content: '',
})

const rules = {
  defect_name: [{ required: true, message: '请输入缺陷名称', trigger: 'blur' }],
  priority: [{ required: true, message: '请选择优先级', trigger: 'change' }],
  severity: [{ required: true, message: '请选择严重程度', trigger: 'change' }],
  handler: [{ required: true, message: '请选择处理人', trigger: 'change' }],
}

function onFileChange(file) {
  attachmentName.value = file.name
}

function fkId(val) {
  if (val == null) return null
  return typeof val === 'object' ? val.id : val
}

function normalizeListPayload(payload) {
  if (Array.isArray(payload)) return payload
  if (payload?.results && Array.isArray(payload.results)) return payload.results
  if (payload?.data && Array.isArray(payload.data)) return payload.data
  return []
}

function applyDetailPayload(raw) {
  const x = raw || {}
  form.value = {
    defect_no: x.defect_no ?? '',
    defect_name: x.defect_name ?? '',
    release_version: fkId(x.release_version),
    module: fkId(x.module),
    priority: x.priority ?? 2,
    severity: x.severity ?? 3,
    status: x.status ?? 1,
    handler: fkId(x.handler),
    defect_content: x.defect_content ?? '',
  }
}

function buildApiPayload() {
  const f = form.value
  return {
    defect_name: f.defect_name,
    priority: f.priority,
    severity: f.severity,
    status: f.status ?? 1,
    defect_content: f.defect_content || '',
    release_version: f.release_version || null,
    module: f.module || null,
    handler: f.handler || null,
  }
}

function emptyForm() {
  form.value = {
    defect_no: '',
    defect_name: '',
    release_version: null,
    module: null,
    priority: 2,
    severity: 3,
    status: 1,
    handler: null,
    defect_content: '',
  }
}

async function submit(action) {
  if (action !== 'draft') {
    try {
      await formRef.value.validate()
    } catch {
      return
    }
  }
  saving.value = true
  try {
    const id = route.params.id
    const payload = buildApiPayload()
    if (!id) {
      delete payload.defect_no
    } else {
      payload.defect_no = form.value.defect_no
    }
    if (id) {
      await updateDefectApi(id, payload)
      ElMessage.success('保存成功')
    } else {
      await createDefectApi(payload)
      ElMessage.success(action === 'draft' ? '已暂存' : '创建成功')
    }
    if (action === 'create_continue') {
      emptyForm()
      attachmentName.value = ''
      formRef.value?.resetFields?.()
    } else if (!id) {
      router.push('/defect/list')
    } else {
      const { data: refreshed } = await getDefectDetailApi(id)
      applyDetailPayload(refreshed?.data || refreshed || {})
    }
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.message || '操作失败'
    ElMessage.error(typeof msg === 'string' ? msg : '操作失败')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  const ds = route.query.defaultStatus
  if (ds != null && !route.params.id) {
    const n = Number(ds)
    if (!Number.isNaN(n) && n >= 1 && n <= 4) form.value.status = n
  }
  const id = route.params.id
  if (id) {
    try {
      const { data } = await getDefectDetailApi(id)
      const raw = data?.data || data || {}
      applyDetailPayload(raw)
    } catch (err) {
      const msg = err?.response?.data?.msg || err?.message || '加载失败'
      ElMessage.error(typeof msg === 'string' ? msg : '加载缺陷失败')
    }
  }
  try {
    const pidRaw = localStorage.getItem('current_project_id')
    const projectParam =
      pidRaw != null && pidRaw !== '' && !Number.isNaN(Number(pidRaw))
        ? { project: Number(pidRaw) }
        : {}
    const [rRes, mRes, uRes] = await Promise.all([
      getReleasesApi({ page_size: 500 }),
      getModulesApi(projectParam),
      getUsersApi({ page_size: 500 }),
    ])
    releases.value = normalizeListPayload(rRes.data)
    modules.value = normalizeListPayload(mRes.data)
    users.value = normalizeListPayload(uRes.data)
  } catch {
    releases.value = []
    modules.value = []
    users.value = []
  }
})
</script>

<style scoped>
.defect-detail-page {
  background: transparent;
  padding: 0;
}

.detail-layout {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}

/* 科幻玻璃数据卡片：无纯白底、无常规 box-shadow */
.glass-panel {
  background: rgba(20, 28, 47, 0.6);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 255, 255, 0.15);
  border-radius: 12px;
  padding: 20px;
  transition:
    border-color 0.25s ease,
    box-shadow 0.25s ease;
}

.glass-panel:hover {
  border-color: rgba(0, 255, 255, 0.28);
  box-shadow: 0 0 24px rgba(0, 216, 255, 0.1);
}

.form-panel {
  width: 320px;
  flex-shrink: 0;
}

.content-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.name-item {
  margin-bottom: 12px;
}

.defect-name-input :deep(.el-input__wrapper) {
  border-radius: 8px;
  background: rgba(10, 16, 28, 0.45);
  box-shadow: none;
  border: 1px solid rgba(0, 255, 255, 0.1);
}

.content-label {
  font-size: 13px;
  color: #a8b8d0;
  margin-bottom: 8px;
  font-weight: 500;
}

/* 右侧富文本区域：嵌套玻璃块，不用实色白底 */
.rich-editor {
  border: 1px solid rgba(0, 255, 255, 0.12);
  border-radius: 10px;
  overflow: hidden;
  flex: 1;
  background: rgba(12, 18, 32, 0.35);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.editor-toolbar {
  padding: 8px 12px;
  border-bottom: 1px solid rgba(0, 255, 255, 0.1);
  background: rgba(15, 22, 38, 0.55);
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.editor-toolbar :deep(.el-button) {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(0, 255, 255, 0.15);
  color: rgba(226, 232, 240, 0.88);
}

.editor-toolbar :deep(.el-button:hover) {
  border-color: rgba(0, 216, 255, 0.45);
  color: #00d8ff;
  box-shadow: 0 0 10px rgba(0, 216, 255, 0.12);
}

.editor-textarea :deep(.el-textarea__inner) {
  border: none;
  border-radius: 0;
  font-size: 13px;
  resize: none;
  background: rgba(8, 12, 22, 0.4);
  color: #e2e8f0;
  box-shadow: none;
}

.editor-footer {
  text-align: right;
  padding: 6px 12px;
  font-size: 12px;
  color: #6b7c99;
  border-top: 1px solid rgba(0, 255, 255, 0.1);
  background: rgba(15, 22, 38, 0.4);
}

.defect-upload {
  width: 100%;
}

.defect-upload :deep(.el-upload-dragger) {
  background: rgba(12, 18, 32, 0.45);
  border: 1px dashed rgba(0, 255, 255, 0.2);
  border-radius: 10px;
  box-shadow: none;
}

.defect-upload :deep(.el-upload-dragger:hover) {
  border-color: rgba(0, 255, 255, 0.35);
  background: rgba(0, 255, 255, 0.04);
}

.upload-inner {
  padding: 16px 0;
  text-align: center;
}

.upload-inner__icon {
  font-size: 32px;
  color: rgba(0, 255, 255, 0.35);
}

.upload-inner__hint {
  font-size: 13px;
  color: #8b9cb8;
  margin-top: 4px;
}

.upload-inner__meta {
  font-size: 12px;
  color: #6b7c99;
}

.attachment-name {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #5ee7ff;
  margin-top: 6px;
}

.form-actions {
  display: flex;
  gap: 8px;
  margin-top: 24px;
  flex-wrap: wrap;
}

/* 表单控件与暗色玻璃协调（不改变绑定，仅视觉） */
.form-panel :deep(.el-form-item__label) {
  color: #a8b8d0;
}

.form-panel :deep(.el-input__wrapper),
.form-panel :deep(.el-select .el-input__wrapper) {
  background: rgba(10, 16, 28, 0.45);
  box-shadow: none;
  border: 1px solid rgba(0, 255, 255, 0.1);
}

.form-panel :deep(.el-input.is-disabled .el-input__wrapper) {
  background: rgba(10, 16, 28, 0.35);
}

.content-panel :deep(.el-form-item__label) {
  color: #a8b8d0;
}
</style>
