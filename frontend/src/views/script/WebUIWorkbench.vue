<template>
  <div class="webui-workbench">
    <header class="wb-page-head">
      <el-breadcrumb separator="/" class="wb-crumb">
        <el-breadcrumb-item :to="{ path: '/script-hub' }">
          <el-icon><HomeFilled /></el-icon>
          脚本执行中心
        </el-breadcrumb-item>
        <el-breadcrumb-item>Web UI 工作台</el-breadcrumb-item>
      </el-breadcrumb>
      <p class="wb-page-desc">管理脚本、执行浏览器自动化；删除的脚本可在回收站恢复或彻底清理。</p>
    </header>

    <div class="wb-layout">
      <!-- 左侧 -->
      <aside class="wb-aside">
        <div class="wb-aside-top">
          <el-radio-group v-model="listMode" class="wb-mode-tabs" size="default" @change="onModeTabChange">
            <el-radio-button label="active">我的脚本</el-radio-button>
            <el-radio-button label="trash">回收站{{ trashCount > 0 ? ` (${trashCount})` : '' }}</el-radio-button>
          </el-radio-group>
        </div>

        <div class="wb-toolbar">
          <template v-if="listMode === 'active'">
            <el-button type="primary" class="wb-btn-primary" :icon="Plus" @click="handleImportProject">导入脚本</el-button>
            <template v-if="selectedProjects.length > 0">
              <el-button text bg class="wb-btn-ghost" @click="handleBatchMove">移动</el-button>
              <el-button text bg type="danger" class="wb-btn-ghost" @click="handleBatchDelete">
                移入回收站 ({{ selectedProjects.length }})
              </el-button>
            </template>
          </template>
          <template v-else>
            <el-button
              v-if="selectedProjects.length > 0"
              text
              bg
              class="wb-btn-ghost"
              @click="handleBatchRestore"
            >
              恢复所选 ({{ selectedProjects.length }})
            </el-button>
            <el-button
              v-if="selectedProjects.length > 0"
              text
              bg
              type="danger"
              class="wb-btn-ghost"
              @click="handleBatchPurge"
            >
              彻底删除所选
            </el-button>
            <el-button
              v-if="projects.length > 0"
              text
              type="danger"
              class="wb-btn-link-danger"
              @click="handleEmptyTrash"
            >
              清空回收站
            </el-button>
          </template>
        </div>

        <div v-if="projects.length > 0" class="wb-list-head">
          <el-checkbox v-model="selectAll" :indeterminate="isIndeterminate" @change="handleSelectAll">
            全选
          </el-checkbox>
          <span v-if="selectedProjects.length" class="wb-select-hint">已选 {{ selectedProjects.length }} 项</span>
        </div>

        <div class="wb-list">
          <el-empty
            v-if="projects.length === 0"
            :description="listMode === 'active' ? '暂无脚本，点击「导入脚本」上传' : '回收站为空'"
            :image-size="88"
            class="wb-empty"
          />
          <div
            v-for="project in projects"
            :key="project.id"
            class="wb-item"
            :class="{
              'wb-item--active': selectedProject?.id === project.id,
              'wb-item--checked': selectedProjects.includes(project.id),
            }"
          >
            <el-checkbox
              :model-value="selectedProjects.includes(project.id)"
              class="wb-item-check"
              @change="(val: boolean) => handleProjectSelect(project.id, val)"
              @click.stop
            />
            <div class="wb-item-body" @click="selectProject(project)">
              <div class="wb-item-icon">
                <el-icon><Document /></el-icon>
              </div>
              <div class="wb-item-text">
                <div class="wb-item-title">
                  <span class="wb-item-name">{{ project.name }}</span>
                  <el-tag v-if="listMode === 'active' && !project.is_active" size="small" effect="plain" type="info" round>
                    已禁用
                  </el-tag>
                </div>
                <div class="wb-item-meta">
                  <span class="wb-chip">{{ project.framework }}</span>
                  <span class="wb-type">{{ project.type }}</span>
                  <span v-if="listMode === 'trash' && project.deleted_at" class="wb-deleted-at">
                    删除于 {{ formatDeletedAt(project.deleted_at) }}
                  </span>
                </div>
              </div>
            </div>
            <el-dropdown trigger="click" @command="handleProjectAction" @click.stop>
              <button type="button" class="wb-item-more" aria-label="更多">
                <el-icon><MoreFilled /></el-icon>
              </button>
              <template #dropdown>
                <el-dropdown-menu>
                  <template v-if="listMode === 'active'">
                    <el-dropdown-item v-if="!project.is_active" :command="{ action: 'toggle_active', project }">
                      启用脚本
                    </el-dropdown-item>
                    <el-dropdown-item v-else :command="{ action: 'toggle_active', project }">停用脚本</el-dropdown-item>
                    <el-dropdown-item :command="{ action: 'edit', project }" divided>
                      <el-icon><Edit /></el-icon>
                      重命名
                    </el-dropdown-item>
                    <el-dropdown-item :command="{ action: 'delete', project }" divided>
                      <el-icon><Delete /></el-icon>
                      移入回收站
                    </el-dropdown-item>
                  </template>
                  <template v-else>
                    <el-dropdown-item :command="{ action: 'restore', project }">
                      <el-icon><RefreshLeft /></el-icon>
                      恢复到列表
                    </el-dropdown-item>
                    <el-dropdown-item :command="{ action: 'purge', project }" divided class="danger-item">
                      <el-icon><Delete /></el-icon>
                      彻底删除
                    </el-dropdown-item>
                  </template>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </aside>

      <!-- 右侧 -->
      <main class="wb-main">
        <div class="wb-main-head">
          <div class="wb-main-title">
            <el-icon v-if="listMode === 'active'"><VideoPlay /></el-icon>
            <el-icon v-else><Delete /></el-icon>
            <span>{{ listMode === 'active' ? '执行控制台' : '回收站' }}</span>
          </div>
          <div v-if="listMode === 'active'" class="wb-run-actions">
            <el-button
              type="primary"
              class="wb-run-btn"
              :icon="VideoPlay"
              :disabled="!selectedProject"
              :loading="uiStore.isRunning"
              @click="handleExecute"
            >
              {{ uiStore.isRunning ? '执行中…' : '开始执行' }}
            </el-button>
            <el-button
              type="danger"
              plain
              class="wb-stop-btn"
              :icon="VideoPause"
              :disabled="!uiStore.isRunning || !uiStore.currentExecutionId || stopExecutionLoading"
              :loading="stopExecutionLoading"
              @click="handleStopExecution"
            >
              停止
            </el-button>
          </div>
        </div>

        <div v-if="listMode === 'trash'" class="wb-trash-panel">
          <p class="wb-trash-tip">
            回收站中的脚本不会出现在「我的脚本」中，也无法执行。恢复后可再次运行；彻底删除将删除数据库记录并清理工作空间文件，不可恢复。
          </p>
          <template v-if="selectedProject">
            <div class="wb-trash-card">
              <h3 class="wb-trash-name">{{ selectedProject.name }}</h3>
              <p class="wb-trash-sub">{{ selectedProject.framework }} · {{ selectedProject.type }}</p>
              <div class="wb-trash-btns">
                <el-button type="primary" @click="restoreOne(selectedProject)">恢复至我的脚本</el-button>
                <el-button type="danger" plain @click="purgeOne(selectedProject)">彻底删除</el-button>
              </div>
            </div>
          </template>
          <el-empty v-else description="在左侧选择一个脚本，可进行恢复或彻底删除" :image-size="120" />
        </div>

        <div v-else-if="!selectedProject" class="wb-empty-main">
          <el-empty description="请选择一个脚本以配置执行并查看日志" :image-size="140" />
        </div>

        <div v-else class="execution-panel">
            <!-- 执行配置 -->
            <div class="config-section">
              <h4 class="section-title">执行配置</h4>
              <div class="wb-exec-hint-row">
                <span class="wb-exec-hint-inline">
                  浏览器在<strong>运行 Django 的机器</strong>上启动。无头时平台会为常见 Selenium（Chrome/Edge/Firefox）自动加无头参数；有头时不改脚本行为。
                </span>
                <el-popover placement="bottom-start" :width="420" trigger="click">
                  <template #reference>
                    <el-button link type="primary" size="small">查看详细说明</el-button>
                  </template>
                  <div class="wb-popover-body">
                    <p><strong>为什么本地看不到窗口？</strong>若后端与浏览器不在同一环境（远程服务器、无桌 Docker），有头模式也不会出现在你当前这台电脑的桌面上。</p>
                    <p><strong>无头/有头如何生效？</strong>无头：平台通过启动器 / pytest 插件在子进程内为 Selenium 合并无头参数（Playwright 等需脚本自行处理）。有头：不注入补丁。若仍写死 <code>headless=True</code> 可能冲突。</p>
                    <p><strong>为什么没有日志？</strong>日志来自 Redis；若接口报错或脚本长时间不输出，界面会提示。已开启子进程 <code>PYTHONUNBUFFERED</code> 以尽早刷出 print。</p>
                  </div>
                </el-popover>
              </div>
              <el-form :model="executionConfig" label-width="100px" size="default">
                <el-form-item label="浏览器">
                  <el-select v-model="executionConfig.browser" placeholder="选择浏览器">
                    <el-option label="Chrome" value="chrome" />
                    <el-option label="Firefox" value="firefox" />
                    <el-option label="Edge" value="edge" />
                  </el-select>
                </el-form-item>
                <el-form-item label="执行模式">
                  <el-radio-group v-model="executionConfig.headless">
                    <el-radio :label="false">有头模式</el-radio>
                    <el-radio :label="true">无头模式</el-radio>
                  </el-radio-group>
                </el-form-item>
                <el-form-item label="并发数">
                  <el-input-number
                    v-model="executionConfig.parallel"
                    :min="1"
                    :max="10"
                  />
                </el-form-item>
              </el-form>
            </div>

            <!-- 执行日志 -->
            <div class="log-section">
              <div class="wb-log-section-head">
                <h4 class="section-title">执行日志</h4>
                <div class="wb-log-actions">
                  <el-button
                    text
                    type="primary"
                    size="small"
                    :icon="Download"
                    :disabled="uiStore.logs.length === 0"
                    @click="handleExportLogs"
                  >
                    导出日志
                  </el-button>
                  <el-button
                    text
                    type="danger"
                    size="small"
                    :disabled="uiStore.isRunning || uiStore.logs.length === 0"
                    @click="handleClearLogView"
                  >
                    清空控制台
                  </el-button>
                </div>
              </div>
              <div ref="logScrollRef" class="log-container">
                <div v-if="uiStore.logs.length === 0" class="log-empty">
                  等待执行...
                </div>
                <div
                  v-for="(log, index) in uiStore.logs"
                  :key="index"
                  class="log-line"
                  :class="log.level"
                >
                  <span class="log-time">{{ log.time }}</span>
                  <span class="log-content">{{ log.message }}</span>
                </div>
              </div>
            </div>

            <!-- 执行结果统计：运行中不展示假数字；结束后用 Redis 中的 result_stats 或 junit 解析结果 -->
            <div v-if="uiStore.result?.pending" class="result-section result-section--pending">
              <h4 class="section-title">执行结果</h4>
              <p class="wb-result-pending">
                统计中… 用例数将在本次执行结束并写入 Redis 后更新（pytest 工程优先读取工作区
                <code>test-results/junit.xml</code>；线性脚本按单次执行计 1 条）。
              </p>
            </div>
            <div v-else-if="uiStore.result" class="result-section">
              <h4 class="section-title">执行结果</h4>
              <el-row :gutter="16">
                <el-col :span="6">
                  <div class="stat-card total">
                <div class="stat-value">{{ uiStore.result.total }}</div>
                    <div class="stat-label">总用例数</div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="stat-card success">
                <div class="stat-value">{{ uiStore.result.passed }}</div>
                    <div class="stat-label">通过</div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="stat-card failed">
                <div class="stat-value">{{ uiStore.result.failed }}</div>
                    <div class="stat-label">失败</div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="stat-card skipped">
                <div class="stat-value">{{ uiStore.result.skipped }}</div>
                    <div class="stat-label">跳过</div>
                  </div>
                </el-col>
              </el-row>
            </div>
        </div>
      </main>
    </div>

    <!-- 导入工程对话框 -->
    <el-dialog
      v-model="importDialogVisible"
      title="导入 Web UI 自动化工程"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="importForm" label-width="100px">
        <el-form-item label="工程名称" required>
          <el-input v-model="importForm.name" placeholder="请输入工程名称" />
        </el-form-item>
        <el-form-item label="框架类型" required>
          <el-select v-model="importForm.framework" placeholder="选择框架">
            <el-option label="Selenium" value="Selenium" />
            <el-option label="Playwright" value="Playwright" />
          </el-select>
        </el-form-item>
        <el-form-item label="工程类型" required>
          <el-radio-group v-model="importForm.type">
            <el-radio label="线性脚本">线性脚本</el-radio>
            <el-radio label="POM 工程">POM 工程</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item
          v-if="importForm.type === 'POM 工程'"
          label="执行入口"
          required
        >
          <el-input
            v-model="importForm.entryPoint"
            placeholder="ZIP 解压后的相对路径，例如 tests/test_login.py 或 src/main.py"
          />
        </el-form-item>
        <el-form-item label="工程路径" required>
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            accept=".py,.zip"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :file-list="fileList"
            style="width: 100%"
          >
            <el-input
              v-model="importForm.path"
              placeholder="请输入工程文件路径或点击上传按钮选择文件"
              readonly
            >
              <template #append>
                <el-button :icon="Upload">上传</el-button>
              </template>
            </el-input>
          </el-upload>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="importForm.description"
            type="textarea"
            :rows="3"
            placeholder="工程描述（可选）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleConfirmImport">确认导入</el-button>
      </template>
    </el-dialog>

    <!-- 批量移动对话框 -->
    <el-dialog
      v-model="moveDialogVisible"
      title="批量移动工程"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form label-width="100px">
        <el-form-item label="选中工程">
          <el-tag type="info">{{ selectedProjects.length }} 个工程</el-tag>
        </el-form-item>
        <el-form-item label="目标文件夹" required>
          <el-input
            v-model="moveToFolder"
            placeholder="请输入目标文件夹路径"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="moveDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleConfirmMove">确认移动</el-button>
      </template>
    </el-dialog>

    <!-- 重命名（对接后端 PATCH） -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑工程名称"
      width="480px"
      :close-on-click-modal="false"
    >
      <el-form label-width="90px">
        <el-form-item label="名称" required>
          <el-input v-model="editForm.name" maxlength="255" show-word-limit placeholder="脚本显示名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="editSaving" @click="handleConfirmEditName">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  HomeFilled,
  Plus,
  Document,
  MoreFilled,
  Edit,
  Delete,
  VideoPlay,
  VideoPause,
  Download,
  Upload,
  RefreshLeft,
} from '@element-plus/icons-vue'
import request from '@/utils/request'
import { useUiExecutionStore } from '@/store/modules/uiExecution'

interface Project {
  id: string
  name: string
  framework: string
  type: string
  path: string
  description?: string
  /** 与后端 UIScriptUpload.is_active 一致；为 false 时不可执行 */
  is_active: boolean
  deleted_at?: string | null
  inTrash?: boolean
}

interface ExecutionLog {
  time: string
  level: 'info' | 'success' | 'warning' | 'error'
  message: string
}

interface ExecutionResult {
  total: number
  passed: number
  failed: number
  skipped: number
}

// 工程列表（active / trash 共用同一列表容器，由 listMode 决定数据源）
const projects = ref<Project[]>([])
const listMode = ref<'active' | 'trash'>('active')
const trashCount = ref(0)
const selectedProject = ref<Project | null>(null)

function mapScriptRow(script: any, inTrash: boolean): Project {
  const st = script.script_type
  let typeLabel = '脚本'
  if (st === 'LINEAR') typeLabel = '线性脚本'
  else if (st === 'POM') typeLabel = 'POM'
  return {
    id: String(script.id),
    name: script.name,
    framework: script.framework || 'AUTO',
    type: typeLabel,
    path: script.workspace_path || '',
    description: '',
    is_active: script.is_active !== false && script.is_active !== 0,
    deleted_at: script.deleted_at ?? null,
    inTrash,
  }
}

function formatDeletedAt(iso?: string | null) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return String(iso)
  }
}

async function refreshTrashCount() {
  try {
    const { data } = await request.get('/assistant/ui-scripts/trash/')
    trashCount.value = typeof data.count === 'number' ? data.count : (data.results || []).length
  } catch {
    trashCount.value = 0
  }
}

async function loadTrashList() {
  try {
    const { data } = await request.get('/assistant/ui-scripts/trash/')
    const scripts = Array.isArray(data.results) ? data.results : []
    trashCount.value = typeof data.count === 'number' ? data.count : scripts.length
    projects.value = scripts.map((s: any) => mapScriptRow(s, true))
  } catch (e: any) {
    ElMessage.error('加载回收站失败：' + (e?.message || '未知错误'))
  }
}

async function loadCurrentList(opts?: { selectServerId?: number }) {
  if (listMode.value === 'active') await loadProjects(opts)
  else await loadTrashList()
}

/** 用户切换「我的脚本 / 回收站」时刷新列表（程序内改 v-model 不会触发，避免与导入后的定向刷新打架） */
async function onModeTabChange() {
  selectedProjects.value = []
  selectAll.value = false
  isIndeterminate.value = false
  selectedProject.value = null
  uiStore.reset()
  await loadCurrentList()
}

async function restoreOne(project: Project) {
  try {
    await request.post(`/assistant/ui-scripts/${project.id}/restore/`)
    ElMessage.success('已恢复到「我的脚本」')
    selectedProject.value = null
    await loadCurrentList()
    await refreshTrashCount()
  } catch (e: any) {
    const d = e?.response?.data
    const detail =
      (typeof d?.error === 'string' && d.error) ||
      (typeof d?.detail === 'string' && d.detail) ||
      e?.message ||
      '未知错误'
    ElMessage.error('恢复失败：' + detail)
  }
}

async function purgeOne(project: Project) {
  try {
    await ElMessageBox.confirm(
      `确定永久删除「${project.name}」吗？将删除工作空间文件且不可恢复。`,
      '彻底删除',
      { type: 'warning', confirmButtonText: '彻底删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    await request.post(`/assistant/ui-scripts/${project.id}/permanent_delete/`)
    ElMessage.success('已永久删除')
    if (selectedProject.value?.id === project.id) selectedProject.value = null
    selectedProjects.value = selectedProjects.value.filter((id) => id !== project.id)
    updateSelectAllState()
    await loadCurrentList()
    await refreshTrashCount()
  } catch (e: any) {
    const d = e?.response?.data
    const detail =
      (typeof d?.error === 'string' && d.error) ||
      (typeof d?.detail === 'string' && d.detail) ||
      e?.message ||
      '未知错误'
    ElMessage.error('删除失败：' + detail)
  }
}

async function handleBatchRestore() {
  if (!selectedProjects.value.length) return
  try {
    for (const id of selectedProjects.value) {
      await request.post(`/assistant/ui-scripts/${id}/restore/`)
    }
    ElMessage.success('已恢复所选脚本')
    selectedProjects.value = []
    updateSelectAllState()
    await loadCurrentList()
    await refreshTrashCount()
  } catch (e: any) {
    ElMessage.error('批量恢复失败：' + (e?.message || '未知错误'))
  }
}

async function handleBatchPurge() {
  if (!selectedProjects.value.length) return
  try {
    await ElMessageBox.confirm(
      `将永久删除选中的 ${selectedProjects.value.length} 个脚本，不可恢复。`,
      '彻底删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    for (const id of selectedProjects.value) {
      await request.post(`/assistant/ui-scripts/${id}/permanent_delete/`)
    }
    ElMessage.success('已彻底删除')
    if (selectedProject.value && selectedProjects.value.includes(selectedProject.value.id)) {
      selectedProject.value = null
    }
    selectedProjects.value = []
    updateSelectAllState()
    await loadCurrentList()
    await refreshTrashCount()
  } catch (e: any) {
    ElMessage.error('批量删除失败：' + (e?.message || '未知错误'))
  }
}

async function handleEmptyTrash() {
  if (!projects.value.length) return
  try {
    await ElMessageBox.confirm('清空回收站后将无法恢复，确定继续？', '清空回收站', {
      type: 'warning',
      confirmButtonText: '清空',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await request.post('/assistant/ui-scripts/empty_trash/')
    ElMessage.success('回收站已清空')
    selectedProject.value = null
    selectedProjects.value = []
    updateSelectAllState()
    await loadCurrentList()
    await refreshTrashCount()
  } catch (e: any) {
    const d = e?.response?.data
    const detail = (typeof d?.error === 'string' && d.error) || e?.message || '未知错误'
    ElMessage.error('清空失败：' + detail)
  }
}

// 批量选择
const selectedProjects = ref<string[]>([])
const selectAll = ref(false)
const isIndeterminate = ref(false)

// 导入对话框
const importDialogVisible = ref(false)
const importForm = reactive({
  name: '',
  framework: 'Selenium',
  type: '线性脚本',
  entryPoint: '',
  path: '',
  description: ''
})
const uploadRef = ref()
const fileList = ref<any[]>([])
const uploadedFile = ref<any>(null)

// 编辑名称
const editDialogVisible = ref(false)
const editSaving = ref(false)
const editForm = reactive({ id: '', name: '' })

// 执行配置
const executionConfig = reactive({
  browser: 'chrome',
  headless: false,
  parallel: 1
})

// 执行状态（已迁移到 Pinia Store）
const uiStore = useUiExecutionStore()
const stopExecutionLoading = ref(false)
const logScrollRef = ref<HTMLElement | null>(null)

watch(
  () => uiStore.logs.length,
  async () => {
    await nextTick()
    const el = logScrollRef.value
    if (el) el.scrollTop = el.scrollHeight
  }
)

// 选择工程：仅切换到「不同脚本」时清空执行区；同一脚本再次选中时保留日志（离开路由/刷新后再进来常见）
const selectProject = (project: Project) => {
  const nextId = String(project.id)
  const storeScriptId =
    uiStore.currentProjectId != null ? String(uiStore.currentProjectId) : ''
  selectedProject.value = project
  if (storeScriptId !== nextId) {
    uiStore.reset()
  } else if (uiStore.currentExecutionId != null && uiStore.isRunning) {
    uiStore.kickPoll()
  }
}

// 批量选择处理
const handleProjectSelect = (projectId: string, checked: boolean) => {
  if (checked) {
    if (!selectedProjects.value.includes(projectId)) {
      selectedProjects.value.push(projectId)
    }
  } else {
    selectedProjects.value = selectedProjects.value.filter(id => id !== projectId)
  }
  updateSelectAllState()
}

// 全选/取消全选
const handleSelectAll = (checked: boolean) => {
  if (checked) {
    selectedProjects.value = projects.value.map(p => p.id)
  } else {
    selectedProjects.value = []
  }
  updateSelectAllState()
}

// 更新全选状态
const updateSelectAllState = () => {
  const selectedCount = selectedProjects.value.length
  const totalCount = projects.value.length

  selectAll.value = selectedCount === totalCount && totalCount > 0
  isIndeterminate.value = selectedCount > 0 && selectedCount < totalCount
}

// 批量删除
const handleBatchDelete = () => {
  if (selectedProjects.value.length === 0) {
    ElMessage.warning('请先选择要删除的工程')
    return
  }

  ElMessageBox.confirm(
    `将选中的 ${selectedProjects.value.length} 个脚本移入回收站，可在回收站恢复或彻底删除。`,
    '移入回收站',
    {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      for (const projectId of selectedProjects.value) {
        await request.delete(`/assistant/ui-scripts/${projectId}/`)
      }

      if (selectedProject.value && selectedProjects.value.includes(selectedProject.value.id)) {
        selectedProject.value = null
      }

      selectedProjects.value = []
      updateSelectAllState()
      await loadCurrentList()
      await refreshTrashCount()
      ElMessage.success('已移入回收站')
    } catch (error) {
      ElMessage.error('操作失败：' + (error as Error).message)
    }
  }).catch(() => {})
}

// 批量移动对话框
const moveDialogVisible = ref(false)
const moveToFolder = ref('')

// 批量移动
const handleBatchMove = () => {
  if (selectedProjects.value.length === 0) {
    ElMessage.warning('请先选择要移动的工程')
    return
  }
  moveDialogVisible.value = true
  moveToFolder.value = ''
}

// 确认批量移动
const handleConfirmMove = async () => {
  if (!moveToFolder.value) {
    ElMessage.warning('请输入目标文件夹')
    return
  }

  try {
    // 调用后端API批量移动
      for (const projectId of selectedProjects.value) {
        await request.patch(`/assistant/ui-scripts/${projectId}/`, {
          folder: moveToFolder.value,
        })
      }

    ElMessage.success(`已将 ${selectedProjects.value.length} 个工程移动到 ${moveToFolder.value}`)
    moveDialogVisible.value = false
    selectedProjects.value = []
    updateSelectAllState()
  } catch (error) {
    ElMessage.error('批量移动失败：' + (error as Error).message)
  }
}

// 打开导入对话框
const handleImportProject = () => {
  importDialogVisible.value = true
  // 重置表单
  Object.assign(importForm, {
    name: '',
    framework: 'Selenium',
    type: '线性脚本',
    entryPoint: '',
    path: '',
    description: ''
  })
  fileList.value = []
  uploadedFile.value = null
}

// 文件选择处理
const handleFileChange = (file: any) => {
  uploadedFile.value = file.raw
  importForm.path = file.name
  fileList.value = [file]
}

// 文件移除处理
const handleFileRemove = () => {
  uploadedFile.value = null
  importForm.path = ''
  fileList.value = []
}

// 确认导入
const handleConfirmImport = async () => {
  if (!importForm.name || !importForm.framework || !importForm.path) {
    ElMessage.warning('请填写必填项')
    return
  }

  const isPom = importForm.type === 'POM 工程'
  if (isPom && !importForm.entryPoint?.trim()) {
    ElMessage.warning('POM 工程请填写 ZIP 内的执行入口相对路径（执行入口）')
    return
  }

  // 如果有上传的文件，调用后端API
  if (uploadedFile.value) {
    try {
      const formData = new FormData()
      formData.append('name', importForm.name)
      formData.append('script_type', importForm.type === '线性脚本' ? 'LINEAR' : 'POM')
      formData.append('language', 'PYTHON')
      formData.append('framework', 'AUTO')
      const entry =
        isPom
          ? importForm.entryPoint.trim()
          : uploadedFile.value.name
      formData.append('entry_point', entry)
      formData.append('file_path', uploadedFile.value)

      // 使用 axios，成功则返回 data；若请求失败会抛异常，直接捕获即可
      const { data } = await request.post('/assistant/ui-scripts/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      console.log('Upload response:', data)
      console.log('Script ID:', data.id)

      // 新建脚本默认 is_active=True，无需再 PATCH（此前仅有 multipart 解析器会导致 JSON 的 PATCH 415）

      ElMessage.success('工程导入成功')
      importDialogVisible.value = false

      listMode.value = 'active'
      await loadProjects({ selectServerId: data.id })
      await refreshTrashCount()
    } catch (error: any) {
      const d = error?.response?.data
      const fieldErr =
        d && typeof d === 'object'
          ? Object.entries(d)
              .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : String(v)}`)
              .join('；')
          : ''
      const detail =
        fieldErr ||
        (typeof d?.error === 'string' && d.error) ||
        (typeof d?.detail === 'string' && d.detail) ||
        error?.message ||
        '未知错误'
      ElMessage.error('导入失败：' + detail)
    }
  } else {
    // 没有文件，只是添加到本地列表
    const newProject: Project = {
      id: Date.now().toString(),
      name: importForm.name,
      framework: importForm.framework,
      type: importForm.type,
      path: importForm.path,
      description: importForm.description,
      is_active: true,
      deleted_at: null,
      inTrash: false,
    }

    projects.value.push(newProject)
    importDialogVisible.value = false
    ElMessage.success('工程导入成功')
  }
}

// 工程操作（与批量删除一致：调用后端软删除）
const handleProjectAction = ({ action, project }: { action: string; project: Project }) => {
  if (action === 'restore') {
    void restoreOne(project)
    return
  }
  if (action === 'purge') {
    void purgeOne(project)
    return
  }
  if (action === 'toggle_active') {
    const tip = project.is_active ? '确认停用该脚本？停用后将无法执行。' : '确认启用该脚本？'
    ElMessageBox.confirm(tip, '提示', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning',
    })
      .then(async () => {
        try {
          const { data } = await request.post(`/assistant/ui-scripts/${project.id}/toggle_active/`)
          ElMessage.success(typeof data?.message === 'string' ? data.message : '状态已更新')
          const sid = Number(project.id)
          await loadCurrentList(Number.isFinite(sid) ? { selectServerId: sid } : undefined)
        } catch (error: any) {
          const d = error?.response?.data
          const detail =
            (typeof d?.error === 'string' && d.error) ||
            (typeof d?.detail === 'string' && d.detail) ||
            error?.message ||
            '未知错误'
          ElMessage.error('操作失败：' + detail)
        }
      })
      .catch(() => {})
    return
  }
  if (action === 'edit') {
    editForm.id = project.id
    editForm.name = project.name
    editDialogVisible.value = true
  } else if (action === 'delete') {
    ElMessageBox.confirm('确认删除该工程吗？（将移入回收站）', '提示', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    }).then(async () => {
      try {
        await request.delete(`/assistant/ui-scripts/${project.id}/`)
        if (selectedProject.value?.id === project.id) {
          selectedProject.value = null
        }
        selectedProjects.value = selectedProjects.value.filter((id) => id !== project.id)
        updateSelectAllState()
        await loadCurrentList()
        await refreshTrashCount()
        ElMessage.success('已移入回收站')
      } catch (error: any) {
        const d = error?.response?.data
        const detail =
          (typeof d?.error === 'string' && d.error) ||
          (typeof d?.detail === 'string' && d.detail) ||
          error?.message ||
          '未知错误'
        ElMessage.error('删除失败：' + detail)
      }
    }).catch(() => {})
  }
}

const handleConfirmEditName = async () => {
  const name = editForm.name.trim()
  if (!name) {
    ElMessage.warning('请输入名称')
    return
  }
  editSaving.value = true
  try {
    await request.patch(`/assistant/ui-scripts/${editForm.id}/`, { name })
    editDialogVisible.value = false
    const sid = Number(editForm.id)
    await loadCurrentList(Number.isFinite(sid) ? { selectServerId: sid } : undefined)
    ElMessage.success('已保存')
  } catch (error: any) {
    const d = error?.response?.data
    const detail =
      (typeof d?.error === 'string' && d.error) ||
      (typeof d?.detail === 'string' && d.detail) ||
      error?.message ||
      '未知错误'
    ElMessage.error('保存失败：' + detail)
  } finally {
    editSaving.value = false
  }
}

// 执行脚本（委托给 Pinia Store）
const handleExecute = async () => {
  if (!selectedProject.value) return
  const sid = Number(selectedProject.value.id)
  if (!Number.isFinite(sid) || sid <= 0) {
    ElMessage.warning('当前工程未关联后端脚本，请先使用「导入工程」上传或刷新列表')
    return
  }
  // 后端对 is_active=false 会返回 400；此处提供一键启用
  if (!selectedProject.value.is_active) {
    try {
      await ElMessageBox.confirm(
        '当前脚本已禁用，无法执行。是否立即启用并开始执行？',
        '脚本已禁用',
        { type: 'warning', confirmButtonText: '启用并执行', cancelButtonText: '取消' }
      )
      await request.post(`/assistant/ui-scripts/${sid}/toggle_active/`)
      await loadCurrentList({ selectServerId: sid })
      const match = projects.value.find((p) => p.id === String(sid))
      if (match) selectProject(match)
    } catch {
      return
    }
  }
  try {
    await uiStore.startExecution(String(sid), executionConfig)
  } catch (e: any) {
    const d = e?.response?.data
    const detail =
      (typeof d?.error === 'string' && d.error) ||
      (typeof d?.detail === 'string' && d.detail) ||
      e?.message ||
      '未知错误'
    ElMessage.error('执行启动失败：' + detail)
  }
}

const handleStopExecution = async () => {
  if (!uiStore.currentExecutionId || !uiStore.isRunning) return
  stopExecutionLoading.value = true
  try {
    await uiStore.requestStop()
    ElMessage.success('已发送停止请求')
  } catch (e: any) {
    const d = e?.response?.data
    const detail =
      (typeof d?.error === 'string' && d.error) ||
      (typeof d?.detail === 'string' && d.detail) ||
      e?.message ||
      '未知错误'
    ElMessage.error('停止失败：' + detail)
  } finally {
    stopExecutionLoading.value = false
  }
}

function handleExportLogs() {
  if (uiStore.logs.length === 0) return
  const lines = uiStore.logs.map((l) => `[${l.time}] [${l.level}] ${l.message}`)
  const rawName = uiStore.runExecutionIdStr || String(uiStore.currentExecutionId ?? 'log')
  const safe = String(rawName).replace(/[\\/:*?"<>|]/g, '_').slice(0, 80)
  const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `webui-${safe}-${Date.now()}.txt`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('已导出日志')
}

async function handleClearLogView() {
  if (uiStore.isRunning || uiStore.logs.length === 0) return
  try {
    await ElMessageBox.confirm(
      '清空后控制台恢复为「等待执行」，不影响后端已保存的执行记录；可先使用「导出日志」留存副本。',
      '清空控制台',
      { type: 'warning', confirmButtonText: '清空', cancelButtonText: '取消' }
    )
    uiStore.clearLogViewOnly()
    ElMessage.success('已清空')
  } catch {
    /* 用户取消 */
  }
}

// 从后端加载脚本列表；可选在加载后选中指定后端脚本 ID（与执行使用的 script_id 一致）
const loadProjects = async (opts?: { selectServerId?: number }) => {
  try {
    // Axios 在请求失败时会抛异常，此处直接获取 data 即可
        const { data } = await request.get('/assistant/ui-scripts/', { params: { show_deleted: false } })

    // 后端返回的是数组，不是分页对象
    const scripts = Array.isArray(data) ? data : (data.results || [])

    projects.value = scripts.map((script: any) => mapScriptRow(script, false))

    const sid = opts?.selectServerId
    if (sid != null && Number.isFinite(Number(sid))) {
      const match = projects.value.find((p) => p.id === String(sid))
      if (match) {
        selectProject(match)
      }
    }
    await refreshTrashCount()
  } catch (error) {
    console.error('Failed to load projects:', error)
    ElMessage.error('加载脚本列表失败: ' + (error as Error).message)
  }
}

onMounted(async () => {
  uiStore.restoreFromSessionStorage()
  await refreshTrashCount()
  await loadProjects()
  const sid = uiStore.currentProjectId
  if (sid && listMode.value === 'active') {
    const match = projects.value.find((p) => p.id === String(sid))
    if (match) {
      selectedProject.value = match
    }
  }
  if (uiStore.currentExecutionId != null) {
    await uiStore.resumeAfterRemount()
  }
})

// 组件卸载时不清理轮询，让执行在后台继续
// 用户可以随时回到页面查看进度
onUnmounted(() => {
  // 注释掉清理轮询，让执行在后台继续
  // uiStore.clearPolling()
  console.log('页面卸载，但执行继续在后台运行')
})
</script>

<style scoped>
.webui-workbench {
  --wb-bg: #0b0d12;
  --wb-surface: #121722;
  --wb-surface2: #181f2e;
  --wb-border: rgba(148, 163, 184, 0.12);
  --wb-text: #e2e8f0;
  --wb-muted: #94a3b8;
  --wb-accent: #6366f1;
  --wb-accent-hover: #818cf8;
  --wb-danger: #f87171;
  min-height: 100vh;
  background: var(--wb-bg);
  padding: 20px 24px 28px;
  color: var(--wb-text);
  box-sizing: border-box;
}

.wb-page-head {
  margin-bottom: 20px;
}
.wb-crumb :deep(.el-breadcrumb__inner) {
  color: var(--wb-muted);
  font-weight: 500;
}
.wb-crumb :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
  color: var(--wb-text);
}
.wb-page-desc {
  margin: 10px 0 0;
  font-size: 13px;
  color: var(--wb-muted);
  max-width: 720px;
  line-height: 1.5;
}

.wb-layout {
  display: flex;
  gap: 20px;
  min-height: calc(100vh - 140px);
  align-items: stretch;
}

.wb-aside {
  width: 360px;
  flex-shrink: 0;
  background: var(--wb-surface);
  border: 1px solid var(--wb-border);
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
}

.wb-aside-top {
  padding: 14px 14px 10px;
  border-bottom: 1px solid var(--wb-border);
  background: var(--wb-surface2);
}

.wb-mode-tabs {
  width: 100%;
}
.wb-mode-tabs :deep(.el-radio-button__inner) {
  border-radius: 8px !important;
  border: 1px solid transparent !important;
  background: transparent;
  color: var(--wb-muted);
  box-shadow: none !important;
}
.wb-mode-tabs :deep(.el-radio-button.is-active .el-radio-button__inner) {
  background: var(--wb-accent) !important;
  border-color: var(--wb-accent) !important;
  color: #fff !important;
}

.wb-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--wb-border);
}
.wb-btn-primary {
  border-radius: 8px;
  font-weight: 500;
  --el-button-bg-color: var(--wb-accent);
  --el-button-border-color: var(--wb-accent);
  --el-button-hover-bg-color: var(--wb-accent-hover);
  --el-button-hover-border-color: var(--wb-accent-hover);
}
.wb-btn-ghost {
  border-radius: 8px;
  color: var(--wb-muted);
}
.wb-btn-link-danger {
  margin-left: auto;
  font-size: 13px;
}

.wb-list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  font-size: 13px;
  color: var(--wb-muted);
  border-bottom: 1px solid var(--wb-border);
}
.wb-select-hint {
  color: var(--wb-accent-hover);
  font-weight: 500;
}

.wb-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.wb-empty :deep(.el-empty__description) {
  color: var(--wb-muted);
}

.wb-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 10px;
  border-radius: 10px;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.02);
  transition: border-color 0.15s, background 0.15s;
}
.wb-item:hover {
  border-color: var(--wb-border);
  background: rgba(99, 102, 241, 0.06);
}
.wb-item--active {
  border-color: rgba(99, 102, 241, 0.45);
  background: rgba(99, 102, 241, 0.1);
}
.wb-item--checked {
  border-color: rgba(34, 197, 94, 0.25);
}
.wb-item-check {
  flex-shrink: 0;
}
.wb-item-body {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  cursor: pointer;
}
.wb-item-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: rgba(99, 102, 241, 0.15);
  color: var(--wb-accent-hover);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.wb-item-text {
  min-width: 0;
}
.wb-item-title {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 4px;
}
.wb-item-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--wb-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}
.wb-item-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--wb-muted);
}
.wb-chip {
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(148, 163, 184, 0.12);
  color: var(--wb-muted);
  font-weight: 500;
}
.wb-type {
  opacity: 0.85;
}
.wb-deleted-at {
  font-size: 11px;
  opacity: 0.8;
}
.wb-item-more {
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--wb-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.15s, background 0.15s;
}
.wb-item-more:hover {
  color: var(--wb-text);
  background: rgba(255, 255, 255, 0.06);
}

.wb-main {
  flex: 1;
  min-width: 0;
  background: var(--wb-surface);
  border: 1px solid var(--wb-border);
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
}
.wb-main-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--wb-border);
  background: var(--wb-surface2);
}
.wb-main-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 15px;
  font-weight: 600;
  color: var(--wb-text);
}
.wb-run-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.wb-run-btn {
  border-radius: 8px;
  font-weight: 500;
  --el-button-bg-color: var(--wb-accent);
  --el-button-border-color: var(--wb-accent);
}
.wb-stop-btn {
  border-radius: 8px;
  font-weight: 500;
}

.wb-trash-panel {
  flex: 1;
  padding: 20px 22px;
  overflow-y: auto;
}
.wb-trash-tip {
  font-size: 13px;
  color: var(--wb-muted);
  line-height: 1.6;
  margin: 0 0 20px;
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(248, 113, 113, 0.08);
  border: 1px solid rgba(248, 113, 113, 0.2);
}
.wb-trash-card {
  padding: 20px;
  border-radius: 12px;
  border: 1px solid var(--wb-border);
  background: rgba(255, 255, 255, 0.03);
}
.wb-trash-name {
  margin: 0 0 8px;
  font-size: 17px;
}
.wb-trash-sub {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--wb-muted);
}
.wb-trash-btns {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.wb-empty-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.wb-empty-main :deep(.el-empty__description) {
  color: var(--wb-muted);
}

.execution-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 18px 20px 22px;
  overflow-y: auto;
  min-height: 0;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--wb-text);
  margin: 0 0 12px;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  opacity: 0.85;
}

.wb-exec-hint-row {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px 12px;
  margin-bottom: 14px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.2);
  font-size: 12px;
  color: var(--wb-muted);
  line-height: 1.5;
}
.wb-exec-hint-inline code {
  font-size: 11px;
  padding: 1px 5px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.25);
  color: #c4b5fd;
}
.wb-popover-body {
  font-size: 13px;
  color: #334155;
  line-height: 1.6;
}
.wb-popover-body p {
  margin: 0 0 10px;
}
.wb-popover-body p:last-child {
  margin-bottom: 0;
}

.config-section :deep(.el-form-item__label) {
  color: var(--wb-muted);
}
.config-section :deep(.el-input__wrapper),
.config-section :deep(.el-select .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.04);
  box-shadow: none;
}

.wb-log-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}
.wb-log-section-head .section-title {
  margin: 0;
}
.wb-log-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.log-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 180px;
}
.log-container {
  flex: 1;
  background: #07080c;
  border: 1px solid var(--wb-border);
  border-radius: 10px;
  padding: 12px 14px;
  overflow-y: auto;
  font-family: ui-monospace, Consolas, monospace;
  font-size: 12px;
}
.log-empty {
  color: var(--wb-muted);
  text-align: center;
  padding: 16px;
}
.log-line {
  padding: 3px 0;
  line-height: 1.55;
}
.log-time {
  color: #64748b;
  margin-right: 10px;
}
.log-content {
  color: var(--wb-muted);
}
.log-line.info .log-content {
  color: #a5b4fc;
}
.log-line.success .log-content {
  color: #86efac;
}
.log-line.warning .log-content {
  color: #fcd34d;
}
.log-line.error .log-content {
  color: var(--wb-danger);
}

.result-section--pending {
  padding: 12px 0 4px;
}
.wb-result-pending {
  margin: 0;
  font-size: 13px;
  color: var(--wb-muted);
  line-height: 1.55;
}
.wb-result-pending code {
  font-size: 12px;
  color: var(--wb-text);
}

.stat-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--wb-border);
  border-radius: 10px;
  padding: 14px;
  text-align: center;
}
.stat-value {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 4px;
}
.stat-label {
  font-size: 11px;
  color: var(--wb-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.stat-card.total .stat-value {
  color: var(--wb-accent-hover);
}
.stat-card.success .stat-value {
  color: #4ade80;
}
.stat-card.failed .stat-value {
  color: var(--wb-danger);
}
.stat-card.skipped .stat-value {
  color: #fbbf24;
}

:deep(.el-dialog) {
  background: var(--wb-surface);
  border: 1px solid var(--wb-border);
  border-radius: 14px;
}
:deep(.el-dialog__title) {
  color: var(--wb-text);
}
:deep(.el-form-item__label) {
  color: var(--wb-muted);
}

.wb-list::-webkit-scrollbar,
.log-container::-webkit-scrollbar,
.execution-panel::-webkit-scrollbar {
  width: 6px;
}
.wb-list::-webkit-scrollbar-thumb,
.log-container::-webkit-scrollbar-thumb,
.execution-panel::-webkit-scrollbar-thumb {
  background: rgba(99, 102, 241, 0.35);
  border-radius: 4px;
}

:deep(.danger-item) {
  color: var(--wb-danger);
}
</style>
