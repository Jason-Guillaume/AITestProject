<template>
  <div class="pm-page pm-page--sci">
    <!-- 搜索 -->
    <div class="pm-toolbar">
      <div class="pm-search-wrap">
        <el-input
          v-model="searchKw"
          class="pm-search-input"
          placeholder="请输入项目名称搜索"
          clearable
          @keyup.enter="loadProjects"
        >
          <template #append>
            <el-button type="primary" class="pm-search-btn" @click="loadProjects">
              <el-icon><Search /></el-icon>
            </el-button>
          </template>
        </el-input>
      </div>
    </div>

    <!-- 顶部：四种创建入口 -->
    <div class="hero-grid">
      <div
        v-for="t in templates"
        :key="t.key"
        class="hero-card"
        :class="'hero-card--' + t.variant"
        @click="createFromTemplate(t)"
      >
        <button type="button" class="hero-card__fab" @click.stop="createFromTemplate(t)">
          <el-icon><Plus /></el-icon>
        </button>
        <div class="hero-card__icon-wrap">
          <el-icon class="hero-card__icon" :size="26"><component :is="t.icon" /></el-icon>
        </div>
        <div class="hero-card__title">{{ t.name }}</div>
        <div class="hero-card__desc">{{ t.desc }}</div>
      </div>
    </div>

    <!-- 项目列表：三列卡片 -->
    <div class="pm-section-title">项目列表</div>
    <div class="pm-card-grid">
      <div
        v-for="p in filteredProjects"
        :key="p.id"
        class="pm-card"
        :class="{ 'pm-card--active': selectedId === p.id }"
        @click="setCurrentProject(p)"
      >
        <div class="pm-card__head">
          <div class="pm-card__head-left">
            <span class="pm-card__code-icon" aria-hidden="true">&lt;/&gt;</span>
            <span class="pm-card__name" :title="p.project_name">{{ p.project_name }}</span>
          </div>
          <el-tag :type="statusFor(p).type" effect="plain" round size="small" class="pm-card__status">
            {{ statusFor(p).label }}
          </el-tag>
        </div>

        <div class="pm-card__body">
          <div class="pm-card__thumb">
            <img v-if="isHttpUrl(p.icon)" :src="p.icon" class="thumb-img" alt="" />
            <div v-else class="thumb-placeholder thumb-placeholder--empty">
              {{ initials(p.project_name) }}
            </div>
          </div>
          <div class="pm-card__meta">
            <div class="meta-row">
              <span class="meta-k">父项目：</span>
              <span class="meta-v">{{ p.parent_name || '—' }}</span>
            </div>
            <div class="meta-row">
              <span class="meta-k">创建人：</span>
              <span class="meta-v">{{ p.creator_name || '—' }}</span>
            </div>
            <div class="meta-row">
              <span class="meta-k">创建时间：</span>
              <span class="meta-v">{{ formatDateTime(p.create_time) }}</span>
            </div>
            <div class="meta-row meta-row--desc">
              <span class="meta-k">项目描述：</span>
              <span class="meta-v ellipsis-2">{{ descPreview(p.description) }}</span>
            </div>
          </div>
        </div>

        <div class="pm-card__foot">
          <el-button type="primary" link @click.stop="editProject(p)">编辑</el-button>
          <el-button link type="primary" @click.stop="openReleaseDialog(p)">版本发布</el-button>
          <el-button link @click.stop="enterProject(p)">详情</el-button>
          <el-button link type="danger" @click.stop="delProject(p)">删除</el-button>
        </div>
      </div>

      <div class="pm-card pm-card--add" @click="openCreate">
        <el-icon class="pm-card--add__icon"><Plus /></el-icon>
        <span>新建项目</span>
      </div>
    </div>

    <el-dialog
      v-model="showCreateDialog"
      :title="editingProject ? '编辑项目' : '新建项目'"
      width="520px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
        <el-form-item label="项目名称" prop="project_name">
          <el-input v-model="form.project_name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="父项目" prop="parent">
          <el-select v-model="form.parent" placeholder="无（顶级项目）" clearable filterable class="w-full">
            <el-option
              v-for="opt in parentOptions"
              :key="opt.id"
              :label="opt.project_name"
              :value="opt.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="封面图" prop="icon">
          <div class="pm-cover-upload">
            <input
              type="file"
              accept="image/*"
              class="pm-cover-file"
              @change="onCoverFileChange"
            />

            <div class="pm-cover-preview" v-if="coverPreviewUrl || form.icon">
              <img :src="coverPreviewUrl || form.icon" alt="封面预览" />
            </div>

            <div class="pm-cover-preview pm-cover-preview--empty" v-else>
              <span>未上传</span>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="项目状态" prop="project_status">
          <el-select v-model="form.project_status" placeholder="请选择" class="w-full">
            <el-option :value="STATUS_IN_PROGRESS" label="进行中" />
            <el-option :value="STATUS_COMPLETED" label="已完成" />
          </el-select>
        </el-form-item>
        <el-form-item
          v-if="form.project_status === STATUS_IN_PROGRESS"
          label="进度 %"
          prop="progress"
        >
          <el-input-number
            v-model="form.progress"
            :min="0"
            :max="100"
            :step="5"
            controls-position="right"
            class="w-full"
          />
        </el-form-item>
        <el-form-item label="项目描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入项目描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitProject">确定</el-button>
      </template>
    </el-dialog>

    <!-- 版本发布：与「发布计划」同一套数据（ReleasePlan + project 关联） -->
    <el-dialog
      v-model="releaseDialogVisible"
      :title="releaseDialogTitle"
      width="720px"
      destroy-on-close
      class="cyber-dialog-dark pm-release-dialog"
    >
      <div class="cyber-page pm-release-dialog__body">
        <div class="pm-release-toolbar">
          <el-button type="primary" size="small" @click="openReleaseCreate">
            <el-icon><Plus /></el-icon>
            新建版本
          </el-button>
          <el-button text type="primary" size="small" @click="goReleasePlanPage">缺陷管理 · 发布计划（全部）</el-button>
        </div>
        <p class="pm-release-hint">
          此处创建的版本会写入发布计划表并绑定当前项目；测试计划「版本」下拉、顶栏当前项目筛选与此一致。
        </p>
        <el-table
          :data="projectReleases"
          v-loading="releaseLoading"
          size="small"
          class="pm-release-table admin-data-table"
        >
          <el-table-column prop="version_no" label="版本号" min-width="112" width="112" align="left" show-overflow-tooltip />
          <el-table-column prop="release_name" label="发布名称" min-width="160" align="left" show-overflow-tooltip />
          <el-table-column label="计划发布日期" min-width="176" width="176" align="center" class-name="col-datetime">
            <template #default="{ row }">{{ formatReleaseDate(row.release_date) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="104" align="center">
            <template #default="{ row }">
              <el-tag :type="releaseStatusTag(row.status)" size="small">
                {{ releaseStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <template #footer>
        <el-button @click="releaseDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="releaseFormVisible"
      title="新建版本（发布计划）"
      width="440px"
      destroy-on-close
      append-to-body
      class="cyber-dialog-dark"
    >
      <el-form ref="releaseFormRef" :model="releaseForm" :rules="releaseRules" label-width="108px">
        <el-form-item label="发布名称" prop="release_name">
          <el-input v-model="releaseForm.release_name" placeholder="如 电商 2026Q1 迭代" />
        </el-form-item>
        <el-form-item label="版本号" prop="version_no">
          <el-input v-model="releaseForm.version_no" placeholder="如 V1.0.0" />
        </el-form-item>
        <el-form-item label="计划发布日期" prop="release_date">
          <el-date-picker
            v-model="releaseForm.release_date"
            type="datetime"
            placeholder="选择日期时间"
            value-format="YYYY-MM-DDTHH:mm:ss"
            class="w-full"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="releaseFormVisible = false">取消</el-button>
        <el-button type="primary" :loading="releaseSaving" @click="submitReleaseCreate">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, markRaw } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Monitor, List, Grid, Setting } from '@element-plus/icons-vue'
import {
  getProjectsApi,
  createProjectApi,
  updateProjectApi,
  deleteProjectApi,
  getReleasesApi,
  createReleaseApi,
} from '@/api/project'
import { useAppContextStore } from '@/stores/appContextStore'

const router = useRouter()
const appContextStore = useAppContextStore()

const projects = ref([])
const searchKw = ref('')
const showCreateDialog = ref(false)
const editingProject = ref(null)
const saving = ref(false)
const formRef = ref()
const selectedId = ref(null)

// 封面图：本地文件上传与预览
const coverFile = ref(null) // File
const coverPreviewUrl = ref(null) // ObjectURL

function revokeCoverPreview() {
  if (coverPreviewUrl.value) {
    URL.revokeObjectURL(coverPreviewUrl.value)
    coverPreviewUrl.value = null
  }
}

function onCoverFileChange(ev) {
  const file = ev?.target?.files?.[0] || null
  coverFile.value = file
  revokeCoverPreview()
  if (file) {
    coverPreviewUrl.value = URL.createObjectURL(file)
  }
}

onBeforeUnmount(() => {
  revokeCoverPreview()
})

const STATUS_IN_PROGRESS = 1
const STATUS_COMPLETED = 2

const form = ref({
  project_name: '',
  description: '',
  parent: null,
  icon: '',
  project_status: STATUS_IN_PROGRESS,
  progress: 0,
})

const rules = {
  project_name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
}

const templates = [
  {
    key: 'agile',
    name: '创建敏捷研发项目',
    desc: '适用于互联网产品迭代与持续交付',
    variant: 'blue',
    icon: markRaw(Monitor),
  },
  {
    key: 'waterfall',
    name: '创建瀑布流研发项目',
    desc: '适用于阶段清晰、文档驱动的传统研发',
    variant: 'blue',
    icon: markRaw(List),
  },
  {
    key: 'kanban',
    name: '轻量团队看板',
    desc: '小团队快速协作与可视化进度',
    variant: 'blue',
    icon: markRaw(Grid),
  },
  {
    key: 'general',
    name: '通用项目管理',
    desc: '自由灵活的项目与任务组织方式',
    variant: 'purple',
    icon: markRaw(Setting),
  },
]

const filteredProjects = computed(() => {
  if (!searchKw.value) return projects.value
  return projects.value.filter((p) => (p.project_name || '').includes(searchKw.value.trim()))
})

const parentOptions = computed(() => {
  const selfId = editingProject.value?.id
  return projects.value.filter((p) => !selfId || p.id !== selfId)
})

/** 支持 http(s) 与后端返回的相对媒体路径（如 /media/...） */
function isHttpUrl(s) {
  const t = (s || '').trim()
  if (!t) return false
  if (/^https?:\/\//i.test(t)) return true
  return t.startsWith('/')
}

function initials(name) {
  const t = (name || '项').trim()
  return t.slice(0, 2)
}

function clampProgress(n) {
  const x = Number(n)
  if (Number.isNaN(x)) return 0
  return Math.min(100, Math.max(0, Math.round(x)))
}

/** 状态文案来自库表 choices（project_status_display），进度来自 progress */
function statusFor(p) {
  const st = Number(p.project_status)
  const name = (p.project_status_display || '').trim() || (st === STATUS_COMPLETED ? '已完成' : '进行中')
  if (st === STATUS_COMPLETED) {
    return { label: name, type: 'success' }
  }
  const pct = clampProgress(p.progress)
  return { label: `${name} · ${pct}%`, type: 'warning' }
}

function descPreview(desc) {
  const t = (desc || '').trim()
  if (!t) return '暂无描述'
  return t
}

function formatDateTime(dt) {
  if (!dt) return '—'
  const s = typeof dt === 'string' ? dt.slice(0, 19) : String(dt)
  return s.replace('T', ' ')
}

function setCurrentProject(project) {
  if (!project || project.id == null) return
  selectedId.value = project.id
  appContextStore.setActiveProject({
    id: project.id,
    name: project.project_name || '',
  })
}

async function loadProjects() {
  try {
    const { data } = await getProjectsApi()
    const list = Array.isArray(data) ? data : (data?.results || data?.data || [])
    projects.value = list
    const storedProjectId = localStorage.getItem('current_project_id')
    const matched = list.find((p) => String(p.id) === String(storedProjectId))
    if (matched) {
      selectedId.value = matched.id
      appContextStore.setActiveProject({
        id: matched.id,
        name: matched.project_name || '',
      })
    } else if (selectedId.value != null) {
      const stillExists = list.some((p) => p.id === selectedId.value)
      if (!stillExists) selectedId.value = null
    }
  } catch {
    /* silent */
  }
}

function openCreate() {
  editingProject.value = null
  coverFile.value = null
  revokeCoverPreview()
  form.value = {
    project_name: '',
    description: '',
    parent: null,
    icon: '',
    project_status: STATUS_IN_PROGRESS,
    progress: 0,
  }
  showCreateDialog.value = true
}

function editProject(p) {
  editingProject.value = p
  coverFile.value = null
  revokeCoverPreview()
  form.value = {
    project_name: p.project_name || '',
    description: p.description || '',
    parent: p.parent ?? null,
    icon: p.icon || '',
    project_status:
      p.project_status != null ? Number(p.project_status) : STATUS_IN_PROGRESS,
    progress: clampProgress(p.progress),
  }
  showCreateDialog.value = true
}

async function delProject(p) {
  await ElMessageBox.confirm(`确定删除项目「${p.project_name}」吗？`, '警告', { type: 'warning' })
  await deleteProjectApi(p.id)
  ElMessage.success('删除成功')
  if (selectedId.value === p.id) selectedId.value = null
  loadProjects()
  window.dispatchEvent(new Event('app:projects-updated'))
}

function enterProject(p) {
  ElMessage.info(`进入项目：${p.project_name}`)
}

function createFromTemplate() {
  openCreate()
}

async function submitProject() {
  await formRef.value.validate()
  saving.value = true
  try {
    const fd = new FormData()
    fd.append('project_name', form.value.project_name)

    const desc = form.value.description ?? ''
    fd.append('description', desc)

    // parent: create 时允许缺失（null）；update 时允许通过空字符串清空（后端按 allow_null 处理）
    if (editingProject.value) {
      fd.append('parent', form.value.parent ?? '')
    } else if (form.value.parent != null) {
      fd.append('parent', String(form.value.parent))
    }

    fd.append('project_status', String(form.value.project_status))
    fd.append('progress', String(clampProgress(form.value.progress)))

    // 封面图文件：仅当用户选择了新文件时才上传
    if (coverFile.value) {
      fd.append('cover_image', coverFile.value)
    }

    if (editingProject.value) {
      await updateProjectApi(editingProject.value.id, fd)
      ElMessage.success('更新成功')
    } else {
      await createProjectApi(fd)
      ElMessage.success('创建成功')
    }
    showCreateDialog.value = false
    editingProject.value = null
    loadProjects()
    // 通知顶栏刷新项目下拉（避免顶栏仍显示旧 projects 列表）
    window.dispatchEvent(new Event('app:projects-updated'))
  } catch (e) {
    const msg =
      e?.response?.data?.msg ||
      e?.response?.data?.detail ||
      (typeof e?.response?.data === 'string' ? e.response.data : null) ||
      e?.message ||
      '保存失败'
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

/* —— 版本发布（关联 ReleasePlan.project）—— */
const releaseDialogVisible = ref(false)
const releaseTargetProject = ref(null)
const projectReleases = ref([])
const releaseLoading = ref(false)
const releaseFormVisible = ref(false)
const releaseSaving = ref(false)
const releaseFormRef = ref()
const releaseForm = ref({ release_name: '', version_no: '', release_date: '' })
const releaseRules = {
  release_name: [{ required: true, message: '请输入发布名称', trigger: 'blur' }],
  version_no: [{ required: true, message: '请输入版本号', trigger: 'blur' }],
  release_date: [{ required: true, message: '请选择计划发布日期', trigger: 'change' }],
}

const releaseDialogTitle = computed(() => {
  const p = releaseTargetProject.value
  return p ? `版本发布 — ${p.project_name || ''}` : '版本发布'
})

function normalizeReleaseList(payload) {
  if (Array.isArray(payload)) return payload
  if (payload?.results && Array.isArray(payload.results)) return payload.results
  if (payload?.data && Array.isArray(payload.data)) return payload.data
  return []
}

function releaseStatusLabel(v) {
  return { 1: '待发布', 2: '已发布', 3: '已取消' }[v] || '—'
}

function releaseStatusTag(v) {
  return { 1: 'warning', 2: 'success', 3: 'info' }[v] || 'info'
}

function formatReleaseDate(dt) {
  if (!dt) return '—'
  return String(dt).slice(0, 16).replace('T', ' ')
}

async function openReleaseDialog(p) {
  releaseTargetProject.value = p
  releaseDialogVisible.value = true
  await loadProjectReleases(p.id)
}

async function loadProjectReleases(projectId) {
  releaseLoading.value = true
  try {
    const { data } = await getReleasesApi({ project: projectId })
    projectReleases.value = normalizeReleaseList(data)
  } catch (e) {
    projectReleases.value = []
    const msg = e?.response?.data?.msg || e?.message || '加载版本列表失败'
    ElMessage.error(typeof msg === 'string' ? msg : '加载失败')
  } finally {
    releaseLoading.value = false
  }
}

function openReleaseCreate() {
  releaseForm.value = { release_name: '', version_no: '', release_date: '' }
  releaseFormVisible.value = true
}

function goReleasePlanPage() {
  releaseDialogVisible.value = false
  router.push('/defect/release')
}

async function submitReleaseCreate() {
  const pid = releaseTargetProject.value?.id
  if (!pid) {
    ElMessage.error('未选择项目')
    return
  }
  await releaseFormRef.value.validate()
  releaseSaving.value = true
  try {
    await createReleaseApi({
      ...releaseForm.value,
      project: pid,
    })
    ElMessage.success('版本已创建（已关联发布计划）')
    releaseFormVisible.value = false
    await loadProjectReleases(pid)
  } catch (e) {
    const msg =
      e?.response?.data?.msg ||
      e?.response?.data?.detail ||
      (typeof e?.response?.data === 'string' ? e.response.data : null) ||
      e?.message ||
      '创建失败'
    ElMessage.error(typeof msg === 'string' ? msg : '创建失败')
  } finally {
    releaseSaving.value = false
  }
}

onMounted(loadProjects)
</script>

<style scoped>
/* 深色科幻：继承布局区渐变，页面壳透明 / 深蓝底 */
.pm-page--sci {
  --pm-cyan: #00e5ff;
  --pm-cyan-dim: rgba(0, 255, 255, 0.45);
  --pm-glass: rgba(30, 41, 59, 0.5);
  --pm-border: rgba(255, 255, 255, 0.1);
  margin: -16px;
  padding: 20px 20px 28px;
  min-height: 100%;
  background: transparent;
}

.pm-toolbar {
  margin-bottom: 18px;
}

.pm-search-wrap {
  max-width: 520px;
}

.pm-search-input :deep(.el-input__wrapper) {
  border-radius: 999px 0 0 999px;
  background: rgba(15, 23, 42, 0.55);
  box-shadow: none;
  border: 1px solid var(--pm-border);
}

.pm-search-input :deep(.el-input-group__append) {
  background: rgba(0, 229, 255, 0.15);
  border: 1px solid rgba(0, 255, 255, 0.2);
  border-left: none;
  border-radius: 0 999px 999px 0;
  box-shadow: none;
  padding: 0;
}

.pm-search-btn {
  border: none;
  margin: 0;
  height: 100%;
  padding: 0 18px;
  border-radius: 0 999px 999px 0;
  background: transparent !important;
  color: var(--pm-cyan) !important;
}

.hero-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 28px;
}

@media (max-width: 1200px) {
  .hero-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .hero-grid {
    grid-template-columns: 1fr;
  }
}

/* 顶部模板卡片：玻璃 + 细白边 + hover 霓虹青 */
.hero-card {
  position: relative;
  border-radius: 12px;
  padding: 20px 18px 22px;
  cursor: pointer;
  min-height: 128px;
  overflow: hidden;
  background: var(--pm-glass);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid var(--pm-border);
  box-shadow: none;
  transition:
    transform 0.28s ease,
    border-color 0.28s ease,
    box-shadow 0.28s ease;
}

.hero-card:hover {
  transform: translateY(-4px);
  border-color: var(--pm-cyan-dim);
  box-shadow: 0 0 24px rgba(0, 255, 255, 0.12);
}

.hero-card--blue,
.hero-card--purple {
  background: var(--pm-glass);
  border: 1px solid var(--pm-border);
  box-shadow: none;
}

.hero-card__fab {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid rgba(0, 255, 255, 0.25);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--pm-cyan);
  background: rgba(0, 255, 255, 0.06);
  box-shadow: none;
  transition: background 0.25s ease, border-color 0.25s ease, filter 0.25s ease;
}

.hero-card__fab:hover {
  background: rgba(0, 255, 255, 0.12);
  border-color: var(--pm-cyan-dim);
  filter: drop-shadow(0 0 8px rgba(0, 255, 255, 0.35));
}

.hero-card--purple .hero-card__fab {
  color: #c4b5fd;
  border-color: rgba(196, 181, 253, 0.35);
  background: rgba(139, 92, 246, 0.08);
}

.hero-card__icon-wrap {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: rgba(0, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--pm-cyan);
  margin-bottom: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.hero-card--purple .hero-card__icon-wrap {
  background: rgba(139, 92, 246, 0.1);
  color: #c4b5fd;
  border-color: rgba(196, 181, 253, 0.15);
}

.hero-card__title {
  font-size: 14px;
  font-weight: 700;
  color: #e8eaef;
  margin-bottom: 6px;
  padding-right: 48px;
}

.hero-card__desc {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.55;
  max-width: 92%;
}

.pm-section-title {
  font-size: 14px;
  font-weight: 600;
  color: #a8b5c4;
  margin-bottom: 14px;
}

.pm-card-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
}

@media (max-width: 1200px) {
  .pm-card-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 720px) {
  .pm-card-grid {
    grid-template-columns: 1fr;
  }
}

.pm-card {
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  background: var(--pm-glass);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid var(--pm-border);
  box-shadow: none;
  transition:
    transform 0.28s ease,
    border-color 0.28s ease,
    box-shadow 0.28s ease;
}

.pm-card:hover {
  transform: translateY(-4px);
  border-color: var(--pm-cyan-dim);
  box-shadow: 0 0 28px rgba(0, 255, 255, 0.1);
}

.pm-card--active {
  border-color: rgba(0, 255, 255, 0.55);
  box-shadow: 0 0 0 1px rgba(0, 255, 255, 0.2) inset, 0 0 32px rgba(0, 255, 255, 0.12);
}

.pm-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(10, 16, 28, 0.35);
}

.pm-card__head-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.pm-card__code-icon {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 700;
  color: var(--pm-cyan);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  letter-spacing: -0.5px;
  text-shadow: 0 0 10px rgba(0, 255, 255, 0.25);
}

.pm-card__name {
  font-size: 14px;
  font-weight: 600;
  color: #e8eaef;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pm-card__status {
  flex-shrink: 0;
}

.pm-card__status :deep(.el-tag) {
  background: rgba(255, 255, 255, 0.06) !important;
  border-color: rgba(255, 255, 255, 0.12) !important;
}

.pm-card__body {
  display: flex;
  gap: 12px;
  padding: 14px;
  background: rgba(15, 23, 42, 0.35);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.pm-card__thumb {
  width: 88px;
  height: 88px;
  flex-shrink: 0;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(10, 16, 28, 0.5);
}

.thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumb-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 1px;
}

.thumb-placeholder--empty {
  background: rgba(51, 65, 85, 0.6);
  color: #cbd5e1;
}

.pm-card__meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-row {
  display: flex;
  font-size: 12px;
  line-height: 1.45;
}

.meta-k {
  flex-shrink: 0;
  color: #8b9cb8;
  width: 72px;
}

.meta-v {
  color: #cbd5e1;
  word-break: break-all;
}

.meta-row--desc .meta-v {
  flex: 1;
  min-width: 0;
}

.ellipsis-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.pm-card__foot {
  padding: 10px 14px 12px;
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 4px;
  background: rgba(10, 16, 28, 0.4);
}

.pm-release-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 10px;
}

.pm-release-hint {
  margin: 0 0 12px;
  font-size: 12px;
  line-height: 1.5;
  color: rgba(148, 163, 184, 0.95);
}

.pm-release-table {
  border-radius: 8px;
}

.pm-card__foot :deep(.el-button) {
  color: #94a3b8;
}

.pm-card__foot :deep(.el-button--primary) {
  color: var(--pm-cyan);
}

.pm-card__foot :deep(.el-button:hover) {
  color: var(--pm-cyan);
}

/* 新建卡片：虚线、全透明底、灰/青加号 */
.pm-card--add {
  min-height: 220px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  gap: 10px;
  background: transparent !important;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  border: 1px dashed rgba(255, 255, 255, 0.22);
  color: #94a3b8;
  box-shadow: none;
}

.pm-card--add:hover {
  transform: translateY(-4px);
  border-color: var(--pm-cyan-dim);
  border-style: dashed;
  color: #a5f3fc;
  box-shadow: 0 0 24px rgba(0, 255, 255, 0.08);
  background: transparent !important;
}

.pm-card--add__icon {
  font-size: 36px;
  color: #8b9cb8;
  transition: color 0.28s ease, filter 0.28s ease;
}

.pm-card--add:hover .pm-card--add__icon {
  color: var(--pm-cyan);
  filter: drop-shadow(0 0 10px rgba(0, 255, 255, 0.45));
}

.w-full {
  width: 100%;
}

/* 封面图上传：小预览 + 聚焦霓虹青边 */
.pm-cover-upload {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.pm-cover-file {
  width: 100%;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: rgba(226, 232, 240, 0.9);
  outline: none;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.pm-cover-file:focus,
.pm-cover-file:focus-visible {
  border-color: rgba(0, 229, 255, 0.55);
  box-shadow:
    0 0 0 1px rgba(0, 229, 255, 0.35),
    0 0 22px rgba(0, 229, 255, 0.14);
}

.pm-cover-preview {
  width: 78px;
  height: 52px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid rgba(0, 229, 255, 0.18);
  background: rgba(10, 16, 28, 0.45);
  box-shadow: 0 0 18px rgba(0, 229, 255, 0.08);
}

.pm-cover-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.pm-cover-preview--empty {
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(148, 163, 184, 0.9);
  font-size: 12px;
  letter-spacing: 0.02em;
}
</style>
