<template>
  <div class="webui-workbench">
    <!-- 顶部面包屑导航 -->
    <div class="breadcrumb-bar">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/script-hub' }">
          <el-icon><HomeFilled /></el-icon>
          脚本执行中心
        </el-breadcrumb-item>
        <el-breadcrumb-item>Web UI 自动化工作台</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- 主体内容区 -->
    <div class="workbench-content">
      <!-- 左侧：工程管理面板 -->
      <div class="left-panel">
        <el-card class="panel-card">
          <template #header>
            <div class="card-header">
              <span class="header-title">
                <el-icon><FolderOpened /></el-icon>
                工程列表
              </span>
              <el-button
                type="primary"
                size="small"
                :icon="Plus"
                @click="handleImportProject"
              >
                导入工程
              </el-button>
            </div>
          </template>

          <div class="project-list">
            <el-empty
              v-if="projects.length === 0"
              description="暂无工程，请先导入"
              :image-size="120"
            />
            <div
              v-for="project in projects"
              :key="project.id"
              class="project-item"
              :class="{ active: selectedProject?.id === project.id }"
              @click="selectProject(project)"
            >
              <div class="project-info">
                <el-icon class="project-icon"><Document /></el-icon>
                <div class="project-details">
                  <div class="project-name">{{ project.name }}</div>
                  <div class="project-meta">
                    <el-tag size="small" :type="project.framework === 'Selenium' ? 'success' : 'primary'">
                      {{ project.framework }}
                    </el-tag>
                    <span class="project-type">{{ project.type }}</span>
                  </div>
                </div>
              </div>
              <el-dropdown trigger="click" @command="handleProjectAction">
                <el-icon class="more-icon"><MoreFilled /></el-icon>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item :command="{ action: 'edit', project }">
                      <el-icon><Edit /></el-icon>
                      编辑
                    </el-dropdown-item>
                    <el-dropdown-item :command="{ action: 'delete', project }" divided>
                      <el-icon><Delete /></el-icon>
                      删除
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 右侧：脚本执行面板 -->
      <div class="right-panel">
        <el-card class="panel-card">
          <template #header>
            <div class="card-header">
              <span class="header-title">
                <el-icon><VideoPlay /></el-icon>
                执行控制台
              </span>
              <el-button
                type="success"
                size="small"
                :icon="VideoPlay"
                :disabled="!selectedProject"
                :loading="isExecuting"
                @click="handleExecute"
              >
                {{ isExecuting ? '执行中...' : '开始执行' }}
              </el-button>
            </div>
          </template>

          <div v-if="!selectedProject" class="empty-state">
            <el-empty description="请先选择一个工程" :image-size="150" />
          </div>

          <div v-else class="execution-panel">
            <!-- 执行配置 -->
            <div class="config-section">
              <h4 class="section-title">执行配置</h4>
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
              <h4 class="section-title">执行日志</h4>
              <div class="log-container">
                <div v-if="executionLogs.length === 0" class="log-empty">
                  等待执行...
                </div>
                <div
                  v-for="(log, index) in executionLogs"
                  :key="index"
                  class="log-line"
                  :class="log.level"
                >
                  <span class="log-time">{{ log.time }}</span>
                  <span class="log-content">{{ log.message }}</span>
                </div>
              </div>
            </div>

            <!-- 执行结果统计 -->
            <div v-if="executionResult" class="result-section">
              <h4 class="section-title">执行结果</h4>
              <el-row :gutter="16">
                <el-col :span="6">
                  <div class="stat-card total">
                    <div class="stat-value">{{ executionResult.total }}</div>
                    <div class="stat-label">总用例数</div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="stat-card success">
                    <div class="stat-value">{{ executionResult.passed }}</div>
                    <div class="stat-label">通过</div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="stat-card failed">
                    <div class="stat-value">{{ executionResult.failed }}</div>
                    <div class="stat-label">失败</div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="stat-card skipped">
                    <div class="stat-value">{{ executionResult.skipped }}</div>
                    <div class="stat-label">跳过</div>
                  </div>
                </el-col>
              </el-row>
            </div>
          </div>
        </el-card>
      </div>
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
        <el-form-item label="工程路径" required>
          <el-input
            v-model="importForm.path"
            placeholder="请输入工程文件路径或上传 ZIP 包"
          >
            <template #append>
              <el-button :icon="Upload">上传</el-button>
            </template>
          </el-input>
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  HomeFilled,
  FolderOpened,
  Plus,
  Document,
  MoreFilled,
  Edit,
  Delete,
  VideoPlay,
  Upload
} from '@element-plus/icons-vue'

interface Project {
  id: string
  name: string
  framework: string
  type: string
  path: string
  description?: string
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

// 工程列表
const projects = ref<Project[]>([])
const selectedProject = ref<Project | null>(null)

// 导入对话框
const importDialogVisible = ref(false)
const importForm = reactive({
  name: '',
  framework: 'Selenium',
  type: '线性脚本',
  path: '',
  description: ''
})

// 执行配置
const executionConfig = reactive({
  browser: 'chrome',
  headless: false,
  parallel: 1
})

// 执行状态
const isExecuting = ref(false)
const executionLogs = ref<ExecutionLog[]>([])
const executionResult = ref<ExecutionResult | null>(null)

// 选择工程
const selectProject = (project: Project) => {
  selectedProject.value = project
  executionLogs.value = []
  executionResult.value = null
}

// 打开导入对话框
const handleImportProject = () => {
  importDialogVisible.value = true
  // 重置表单
  Object.assign(importForm, {
    name: '',
    framework: 'Selenium',
    type: '线性脚本',
    path: '',
    description: ''
  })
}

// 确认导入
const handleConfirmImport = () => {
  if (!importForm.name || !importForm.framework || !importForm.path) {
    ElMessage.warning('请填写必填项')
    return
  }

  const newProject: Project = {
    id: Date.now().toString(),
    name: importForm.name,
    framework: importForm.framework,
    type: importForm.type,
    path: importForm.path,
    description: importForm.description
  }

  projects.value.push(newProject)
  importDialogVisible.value = false
  ElMessage.success('工程导入成功')
}

// 工程操作
const handleProjectAction = ({ action, project }: { action: string; project: Project }) => {
  if (action === 'edit') {
    ElMessage.info('编辑功能开发中...')
  } else if (action === 'delete') {
    ElMessageBox.confirm('确认删除该工程吗？', '提示', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    }).then(() => {
      projects.value = projects.value.filter(p => p.id !== project.id)
      if (selectedProject.value?.id === project.id) {
        selectedProject.value = null
      }
      ElMessage.success('删除成功')
    }).catch(() => {})
  }
}

// 执行脚本
const handleExecute = () => {
  if (!selectedProject.value) return

  isExecuting.value = true
  executionLogs.value = []
  executionResult.value = null

  // 模拟执行日志
  const addLog = (message: string, level: ExecutionLog['level'] = 'info') => {
    executionLogs.value.push({
      time: new Date().toLocaleTimeString(),
      level,
      message
    })
  }

  addLog(`开始执行工程: ${selectedProject.value.name}`, 'info')
  addLog(`浏览器: ${executionConfig.browser}, 模式: ${executionConfig.headless ? '无头' : '有头'}`, 'info')

  // 模拟执行过程
  setTimeout(() => {
    addLog('正在初始化测试环境...', 'info')
  }, 500)

  setTimeout(() => {
    addLog('测试用例加载完成，共 15 个用例', 'success')
  }, 1000)

  setTimeout(() => {
    addLog('开始执行测试用例...', 'info')
  }, 1500)

  setTimeout(() => {
    addLog('用例 1: test_login - 通过', 'success')
  }, 2000)

  setTimeout(() => {
    addLog('用例 2: test_search - 通过', 'success')
  }, 2500)

  setTimeout(() => {
    addLog('用例 3: test_checkout - 失败: 元素未找到', 'error')
  }, 3000)

  setTimeout(() => {
    addLog('执行完成！', 'success')
    executionResult.value = {
      total: 15,
      passed: 12,
      failed: 2,
      skipped: 1
    }
    isExecuting.value = false
    ElMessage.success('执行完成')
  }, 4000)
}
</script>

<style scoped>
.webui-workbench {
  min-height: 100vh;
  background-color: #141414;
  padding: 20px;
}

/* 面包屑导航 */
.breadcrumb-bar {
  background: rgba(255, 255, 255, 0.03);
  padding: 12px 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.breadcrumb-bar :deep(.el-breadcrumb__inner) {
  color: #a0a0a0;
  transition: color 0.3s;
}

.breadcrumb-bar :deep(.el-breadcrumb__inner:hover) {
  color: #409eff;
}

.breadcrumb-bar :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
  color: #ffffff;
}

/* 主体内容区 */
.workbench-content {
  display: flex;
  gap: 20px;
  height: calc(100vh - 140px);
}

.left-panel {
  width: 350px;
  flex-shrink: 0;
}

.right-panel {
  flex: 1;
  overflow: hidden;
}

/* 卡片样式 */
.panel-card {
  background: linear-gradient(135deg, #1a1a1a 0%, #0f0f0f 100%);
  border: 1px solid rgba(64, 158, 255, 0.15);
  border-radius: 12px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-card :deep(.el-card__header) {
  background: rgba(64, 158, 255, 0.05);
  border-bottom: 1px solid rgba(64, 158, 255, 0.15);
  padding: 16px 20px;
}

.panel-card :deep(.el-card__body) {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

/* 工程列表 */
.project-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.project-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.project-item:hover {
  background: rgba(64, 158, 255, 0.08);
  border-color: rgba(64, 158, 255, 0.3);
  transform: translateX(4px);
}

.project-item.active {
  background: rgba(64, 158, 255, 0.15);
  border-color: rgba(64, 158, 255, 0.5);
  box-shadow: 0 0 15px rgba(64, 158, 255, 0.2);
}

.project-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.project-icon {
  font-size: 24px;
  color: #409eff;
}

.project-details {
  flex: 1;
}

.project-name {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 6px;
}

.project-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.project-type {
  font-size: 12px;
  color: #8c8c8c;
}

.more-icon {
  font-size: 18px;
  color: #8c8c8c;
  cursor: pointer;
  transition: color 0.3s;
}

.more-icon:hover {
  color: #409eff;
}

/* 执行面板 */
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.execution-panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
  height: 100%;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 16px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(64, 158, 255, 0.2);
}

/* 配置区域 */
.config-section :deep(.el-form-item__label) {
  color: #a0a0a0;
}

.config-section :deep(.el-input__inner),
.config-section :deep(.el-select) {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

/* 日志区域 */
.log-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.log-container {
  flex: 1;
  background: #0a0a0a;
  border: 1px solid rgba(64, 158, 255, 0.2);
  border-radius: 8px;
  padding: 12px;
  overflow-y: auto;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
}

.log-empty {
  color: #666666;
  text-align: center;
  padding: 20px;
}

.log-line {
  padding: 4px 0;
  line-height: 1.6;
}

.log-time {
  color: #666666;
  margin-right: 12px;
}

.log-content {
  color: #a0a0a0;
}

.log-line.info .log-content {
  color: #409eff;
}

.log-line.success .log-content {
  color: #67c23a;
}

.log-line.warning .log-content {
  color: #e6a23c;
}

.log-line.error .log-content {
  color: #f56c6c;
}

/* 结果统计 */
.result-section {
  margin-top: auto;
}

.stat-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 12px;
  color: #8c8c8c;
}

.stat-card.total .stat-value {
  color: #409eff;
}

.stat-card.success .stat-value {
  color: #67c23a;
}

.stat-card.failed .stat-value {
  color: #f56c6c;
}

.stat-card.skipped .stat-value {
  color: #e6a23c;
}

/* 对话框样式 */
:deep(.el-dialog) {
  background: linear-gradient(135deg, #1a1a1a 0%, #0f0f0f 100%);
  border: 1px solid rgba(64, 158, 255, 0.3);
}

:deep(.el-dialog__title) {
  color: #ffffff;
}

:deep(.el-form-item__label) {
  color: #a0a0a0;
}

:deep(.el-input__inner),
:deep(.el-textarea__inner) {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

/* 滚动条样式 */
.log-container::-webkit-scrollbar,
.panel-card :deep(.el-card__body)::-webkit-scrollbar {
  width: 6px;
}

.log-container::-webkit-scrollbar-track,
.panel-card :deep(.el-card__body)::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 3px;
}

.log-container::-webkit-scrollbar-thumb,
.panel-card :deep(.el-card__body)::-webkit-scrollbar-thumb {
  background: rgba(64, 158, 255, 0.3);
  border-radius: 3px;
}

.log-container::-webkit-scrollbar-thumb:hover,
.panel-card :deep(.el-card__body)::-webkit-scrollbar-thumb:hover {
  background: rgba(64, 158, 255, 0.5);
}
</style>
