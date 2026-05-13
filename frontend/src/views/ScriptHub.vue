<template>
  <div class="script-hub script-hub--cyber">
    <section class="script-hub__workarea">
      <!-- Platform Adapter：紧贴布局区最上方（面包屑在 MainLayout 中） -->
      <div
        class="platform-adapter-bar glass-panel"
        role="toolbar"
        aria-label="Platform Adapter"
      >
        <span class="platform-adapter-bar__label">Platform Adapter</span>
        <el-radio-group
          v-model="activePlatform"
          class="platform-adapter-bar__group"
          size="small"
        >
          <el-radio-button value="web">
            Web
          </el-radio-button>
          <el-radio-button value="mobile">
            Mobile
          </el-radio-button>
          <el-radio-button value="api">
            API
          </el-radio-button>
        </el-radio-group>
        <span
          v-if="activePlatform === 'mobile'"
          class="platform-adapter-bar__telemetry"
        >
          Telemetry：设备未连接
        </span>
      </div>

      <div
        class="workstation-panel workstation-panel--ide"
        :class="{
          'is-inspector-open': inspectorOpen,
          [`layout-profile--${layoutProfile.inspectorVariant}`]: true,
        }"
      >
        <!-- 左：Node Explorer -->
        <aside class="workstation-panel__col workstation-panel__col--tree">
          <div
            v-show="activePlatform === 'web'"
            class="tree-pane"
          >
            <div class="tree-panel-head">
              Web · Node Explorer
            </div>
            <div class="script-tree-scroll">
              <el-tree
                :key="uiTreeKey"
                class="script-resource-tree"
                node-key="id"
                lazy
                :load="uiTree.load"
                :props="uiTree.treeProps"
                highlight-current
                @node-click="(data: HubTreeNode) => onTreeNodeClick('ui', data)"
              >
                <template #default="{ data }">
                  <span class="script-tree-node">
                    <el-icon class="script-tree-node__icon script-tree-node__icon--ui">
                      <component :is="treeNodeIcon('ui', data)" />
                    </el-icon>
                    <span class="script-tree-node__label">{{ data.label }}</span>
                  </span>
                </template>
              </el-tree>
            </div>
          </div>
          <div
            v-show="activePlatform === 'mobile'"
            class="tree-pane"
          >
            <div class="tree-panel-head">
              Mobile · Node Explorer
            </div>
            <div class="script-tree-scroll">
              <el-tree
                :key="mobileTreeKey"
                class="script-resource-tree"
                node-key="id"
                lazy
                :load="loadMobileTree"
                :props="mobileTreeProps"
                highlight-current
                @node-click="onMobileTreeNodeClick"
              >
                <template #default="{ data }">
                  <span class="script-tree-node">
                    <el-icon class="script-tree-node__icon script-tree-node__icon--mobile">
                      <component :is="treeNodeIcon('mobile', data)" />
                    </el-icon>
                    <span class="script-tree-node__label">{{ data.label }}</span>
                  </span>
                </template>
              </el-tree>
            </div>
          </div>
          <div
            v-show="activePlatform === 'api'"
            class="tree-pane"
          >
            <div class="tree-panel-head">
              API · Node Explorer
            </div>
            <div class="script-tree-scroll">
              <el-tree
                :key="apiTreeKey"
                class="script-resource-tree"
                node-key="id"
                lazy
                :load="apiTree.load"
                :props="apiTree.treeProps"
                highlight-current
                @node-click="(data: HubTreeNode) => onTreeNodeClick('api', data)"
              >
                <template #default="{ data }">
                  <span class="script-tree-node">
                    <el-icon class="script-tree-node__icon script-tree-node__icon--api">
                      <component :is="treeNodeIcon('api', data)" />
                    </el-icon>
                    <span class="script-tree-node__label">{{ data.label }}</span>
                  </span>
                </template>
              </el-tree>
            </div>
          </div>
        </aside>

        <!-- 中：Layout Configurator — 按平台切换主工作台；Telemetry 面板共用单例 -->
        <div class="workstation-panel__col workstation-panel__col--main ide-center">
          <header class="action-header">
            <el-button
              plain
              class="action-header__btn"
              :icon="DocumentChecked"
              :loading="saveLoading"
              :disabled="!canSave"
              @click="onSaveClick"
            >
              保存
            </el-button>
            <el-button
              plain
              class="action-header__btn action-header__btn--exec-config"
              :icon="Operation"
              @click="paramsDrawerVisible = true"
            >
              执行配置
            </el-button>
            <el-button
              plain
              class="action-header__btn action-header__btn--exec"
              :class="{ 'action-header__btn--exec-running': executeLoading }"
              :icon="VideoPlay"
              :loading="executeLoading"
              :disabled="activePlatform !== 'web'"
              @click="onExecuteClick"
            >
              执行
            </el-button>
            <el-button
              plain
              class="action-header__btn action-header__btn--stop"
              :icon="VideoPause"
              :disabled="!executeLoading"
              @click="onStopClick"
            >
              停止
            </el-button>
            <div class="action-header__spacer" />
          </header>

          <!-- 布局配置器：Mobile 壳与 Monaco 均保持挂载（v-show），切换平台不销毁编辑器，仅由 watch 清空模型 -->
          <component
            :is="MobileWorkspaceShell"
            v-show="activePlatform === 'mobile'"
            class="workspace-main-mount workspace-main-mount--mobile"
          />
          <div
            v-show="activePlatform !== 'mobile'"
            class="editor-stack workspace-main-mount"
          >
            <p
              class="editor-path"
              :title="editorChromeTitle"
            >
              {{ editorChromeTitle }}
            </p>
            <div
              v-loading="editorLoading"
              class="monaco-wrap"
            >
              <p
                v-if="!isEditorReady"
                class="editor-defer-hint"
              >
                编辑器初始化中（500ms 受控唤醒）…
              </p>
              <MonacoEditor
                v-if="isEditorReady"
                v-model="editorContent"
                :language="editorLanguage"
                :read-only="editorReadOnly"
                copilot-bridge-id="automation-center-main"
                :copilot-label="editorChromeTitle"
              />
            </div>
          </div>

          <div class="bottom-telemetry-zone">
            <div class="bottom-telemetry-zone__row">
              <el-tabs
                v-model="bottomTab"
                class="bottom-tabs bottom-telemetry-zone__tabs"
              >
                <el-tab-pane
                  label="Telemetry（遥测流）"
                  name="telemetry"
                >
                  <div class="bottom-pane bottom-pane--terminal">
                    <TerminalTerminal
                      ref="hubTerminalRef"
                      :fit-when-active="bottomTab === 'telemetry'"
                    />
                  </div>
                </el-tab-pane>
                <el-tab-pane
                  label="Artifacts（产物）"
                  name="artifacts"
                >
                  <div class="bottom-pane bottom-pane--artifacts">
                    <el-empty
                      description="Artifacts：报告截图、日志包、结构化导出将汇总于此（执行结束后可从 Telemetry 侧栏进入 Analysis Lab）"
                      :image-size="56"
                    />
                  </div>
                </el-tab-pane>
              </el-tabs>
              <button
                v-show="showAnalysisLabDeepLink && bottomTab === 'telemetry'"
                type="button"
                class="analysis-lab-glow-btn"
                title="打开 Analysis Lab 深度报告（演示深链）"
                @click="goAnalysisLabDeepLink"
              >
                [↗ Analysis Lab]
              </button>
            </div>
          </div>

          <button
            v-show="!inspectorOpen"
            type="button"
            class="inspector-reopen"
            title="展开 Inspector"
            @click="inspectorOpen = true"
          >
            ⟨
          </button>
        </div>

        <!-- 右：Inspector — Layout Configurator 多态面板 -->
        <aside
          v-show="inspectorOpen"
          class="workstation-panel__col workstation-panel__col--inspector"
        >
          <div class="inspector-head">
            <span class="inspector-head__title">{{ inspectorHeadTitle }}</span>
            <el-button
              text
              type="primary"
              class="inspector-head__collapse"
              @click="inspectorOpen = false"
            >
              折叠
            </el-button>
          </div>
          <div class="inspector-body">
            <section class="inspector-block">
              <h4 class="inspector-block__h">
                节点元数据 (Node Metadata)
              </h4>
              <p class="inspector-block__placeholder">
                {{ inspectorMetadataPlaceholder }}
              </p>
            </section>
            <section class="inspector-block">
              <h4 class="inspector-block__h">
                最近一次 Telemetry 状态
              </h4>
              <p class="inspector-block__mono inspector-block__mono--status">
                {{ lastTelemetryStatusDisplay }}
              </p>
            </section>
          </div>
        </aside>
      </div>
    </section>

    <!-- 参数抽屉：执行配置收纳，主栏保持极简 -->
    <el-drawer
      v-model="paramsDrawerVisible"
      title="执行配置"
      direction="rtl"
      size="360px"
      append-to-body
      class="params-drawer params-drawer--cyber"
    >
      <div class="params-drawer__body">
        <template v-if="activePlatform === 'web'">
          <p class="params-drawer__hint">
            Web 运行器参数；与 Inspector 解耦，保持主栏极简。
          </p>
          <div class="params-drawer__row params-drawer__row--top">
            <span class="params-drawer__label">Browser Type</span>
            <el-select
              v-model="browserType"
              size="small"
              class="params-drawer__select"
              :disabled="executeLoading"
            >
              <el-option
                label="Chrome"
                value="chrome"
              />
              <el-option
                label="Edge"
                value="edge"
              />
              <el-option
                label="Firefox"
                value="firefox"
              />
            </el-select>
          </div>
          <div class="params-drawer__row params-drawer__row--top params-drawer__row--switch">
            <span class="params-drawer__label">Headless</span>
            <el-switch
              v-model="isHeadless"
              inline-prompt
              active-text="无头"
              inactive-text="有头"
              class="headless-switch--cyber"
              :disabled="executeLoading"
            />
          </div>
          <div class="params-drawer__row params-drawer__row--top">
            <span class="params-drawer__label">并行度 (parallel)</span>
            <el-input-number
              v-model="parallelCount"
              :min="1"
              :max="50"
              size="small"
              controls-position="right"
            />
          </div>
        </template>
        <template v-else-if="activePlatform === 'mobile'">
          <p class="params-drawer__hint">
            移动端执行上下文（占位）；Telemetry 接通后由设备服务回填。
          </p>
          <div class="params-drawer__row params-drawer__row--top">
            <span class="params-drawer__label">Device</span>
            <el-select
              v-model="mobileDevicePlaceholder"
              size="small"
              class="params-drawer__select"
              disabled
              placeholder="选择设备（占位）"
            >
              <el-option
                label="— 暂无设备 —"
                value=""
              />
            </el-select>
          </div>
          <div class="params-drawer__row params-drawer__row--top">
            <span class="params-drawer__label">Package Name</span>
            <el-input
              v-model="mobilePackageName"
              size="small"
              clearable
              placeholder="com.example.app（占位）"
              class="params-drawer__input"
            />
          </div>
        </template>
        <template v-else>
          <p class="params-drawer__hint">
            API 场景由运行器读取环境与鉴权；此处保留扩展位，后续可收纳超时与重试策略。
          </p>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import {
  computed,
  defineAsyncComponent,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import {
  Monitor,
  Folder,
  Document,
  Reading,
  Link,
  Tickets,
  DocumentChecked,
  VideoPlay,
  VideoPause,
  Iphone,
  Operation,
} from '@element-plus/icons-vue'
import type { Component } from 'vue'
import { ElMessage } from 'element-plus'
import TerminalTerminal from '@/components/script/TerminalTerminal.vue'
import { useScriptHubSelectionStore } from '@/stores/scriptHubSelectionStore'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import request from '@/utils/request'
import {
  createScriptHubTreeLoader,
  type HubTreeNode,
  type ScriptHubEdition,
} from '@/composables/useScriptHubTrees'

const MonacoEditor = defineAsyncComponent(() => import('@/components/MonacoEditor/index.vue'))
const MobileWorkspaceShell = defineAsyncComponent(
  () => import('@/components/automation-center/MobileWorkspaceShell.vue'),
)

const router = useRouter()

const hubSelection = useScriptHubSelectionStore()
const { selectedScriptId, activePlatform } = storeToRefs(hubSelection)

const workspaceStore = useWorkspaceStore()
const { selectedProjectId, selectedEnvironmentId } = storeToRefs(workspaceStore)

const uiTreeKey = ref(0)
const apiTreeKey = ref(0)
const mobileTreeKey = ref(0)

const uiTree = createScriptHubTreeLoader('ui', (id) => hubSelection.setSelectedScriptId(id))
const apiTree = createScriptHubTreeLoader('api', (id) => hubSelection.setSelectedScriptId(id))

const mobileTreeProps = { label: 'label', children: 'children', isLeaf: 'isLeaf' }

function loadMobileTree(
  node: { level: number; data: HubTreeNode },
  resolve: (data: HubTreeNode[]) => void,
) {
  if (node.level === 0) {
    resolve([
      {
        id: 'mobile-catalog-placeholder',
        label: 'Mobile Node 目录（接入中）',
        kind: 'mobile-placeholder',
        isLeaf: true,
      },
    ])
  } else {
    resolve([])
  }
}

function onMobileTreeNodeClick(data: HubTreeNode) {
  if (data.kind === 'mobile-placeholder') {
    ElMessage.info('移动端 Node 目录尚未接入，无法选中')
    return
  }
}

watch(activePlatform, () => {
  hubSelection.setSelectedScriptId(null)
  uiTreeKey.value += 1
  apiTreeKey.value += 1
  mobileTreeKey.value += 1
})

function treeNodeIcon(edition: ScriptHubEdition | 'mobile', d: HubTreeNode): Component {
  if (edition === 'mobile') {
    if (d.kind === 'mobile-placeholder') return Iphone
    return Document
  }
  if (edition === 'ui') {
    if (d.kind === 'project') return Monitor
    if (d.kind === 'dir') return Folder
    if (d.kind === 'file') return Document
    if (d.kind === 'online') return Reading
  }
  if (edition === 'api') {
    if (d.kind === 'api-group') return Link
    if (d.kind === 'api-case') return Tickets
  }
  return Document
}

const inspectorOpen = ref(true)

/** Layout Configurator：主区壳层与 Inspector 变体（扩展新平台时在此聚合） */
const layoutProfile = computed(() => ({
  mainWorkspace: activePlatform.value === 'mobile' ? 'shell-mobile' : 'shell-editor',
  inspectorVariant:
    activePlatform.value === 'web'
      ? 'web-inspector'
      : activePlatform.value === 'mobile'
        ? 'mobile-inspector'
        : 'api-inspector',
}))

const inspectorHeadTitle = computed(() => {
  if (activePlatform.value === 'web') return 'Inspector · Web'
  if (activePlatform.value === 'mobile') return 'Inspector · Mobile'
  return 'Inspector · API'
})

const paramsDrawerVisible = ref(false)

const platformChromeLabel = computed(() => {
  if (activePlatform.value === 'web') return 'Web'
  if (activePlatform.value === 'mobile') return 'Mobile'
  return 'API'
})

const editorChromeTitle = computed(() => `[${platformChromeLabel.value}] · ${editorDisplayPath.value}`)

const inspectorMetadataPlaceholder = computed(() =>
  selectedScriptId.value
    ? `Node ID: ${selectedScriptId.value}\n（详细元数据将对接后端）`
    : '未选中 Node',
)

/** 最近一次运行结束时的进程退出码（由 Telemetry 轮询回填） */
const hubLastExitCode = ref<number | null>(null)

type HubRunOutcome = 'idle' | 'success' | 'failed' | 'cancelled'

/** 最近一次执行终态（用于 Inspector 文案，与 executeLoading 配合） */
const hubLastRunOutcome = ref<HubRunOutcome>('idle')

const lastTelemetryStatusDisplay = computed(() => {
  if (executeLoading.value) return 'Telemetry 采集中…'
  switch (hubLastRunOutcome.value) {
    case 'success':
      return `已完成 · 退出码 ${hubLastExitCode.value ?? 0}`
    case 'failed':
      return hubLastExitCode.value != null
        ? `失败 · 退出码 ${hubLastExitCode.value}`
        : '失败 · 未建立有效执行上下文'
    case 'cancelled':
      return '已取消 / 已中断'
    default:
      return '— 空闲（等待执行）'
  }
})

/** 演示闭环：执行自然结束后展示，跳转固定 Mock 深链 */
const showAnalysisLabDeepLink = ref(false)

function goAnalysisLabDeepLink() {
  const id = hubExecutionDbId.value
  if (id == null || !Number.isFinite(id)) {
    ElMessage.warning('暂无执行记录 ID，无法打开 Analysis Lab 报告')
    return
  }
  void router.push({
    name: 'AnalysisLabReportDepth',
    params: { id: String(id) },
  })
}

const isEditorReady = ref(false)
let editorReadyTimer: ReturnType<typeof setTimeout> | undefined

const editorContent = ref('')
const editorLanguage = ref('python')
const editorDisplayPath = ref('未选择可编辑 Node')
const editorProjectId = ref<string | null>(null)
const editorWorkspacePath = ref<string | null>(null)
const editorReadOnly = ref(false)
const editorLoading = ref(false)
const saveLoading = ref(false)
const executeLoading = ref(false)
/** 浏览器无头模式（执行配置抽屉） */
const isHeadless = ref(true)
/** Web 浏览器类型（写入请求体 browser） */
const browserType = ref('chrome')
/** UI 执行并行度（写入请求体 parallel） */
const parallelCount = ref(1)
/** Mobile 抽屉占位 */
const mobileDevicePlaceholder = ref('')
const mobilePackageName = ref('')
const bottomTab = ref<'telemetry' | 'artifacts'>('telemetry')

const hubTerminalRef = ref<InstanceType<typeof TerminalTerminal> | null>(null)

/** 当前一次「执行」对应的数据库执行记录 id（用于日志 / cancel 轮询） */
const hubExecutionDbId = ref<number | null>(null)
const hubLastTelemetryWritten = ref(0)
let hubPollTimer: ReturnType<typeof setTimeout> | null = null
let hubPollInFlight = false
let hubPollTicks = 0

interface EngineLogEntry {
  timestamp: string
  type: string
  message: string
}

function stopHubExecutionPoll() {
  if (hubPollTimer != null) {
    clearTimeout(hubPollTimer)
    hubPollTimer = null
  }
  hubPollInFlight = false
}

function formatEngineTelemetryLine(entry: EngineLogEntry): string {
  const t =
    entry.timestamp && !Number.isNaN(Date.parse(entry.timestamp))
      ? new Date(entry.timestamp).toLocaleTimeString()
      : ''
  const msg = String(entry.message ?? '').replace(/\r\n/g, '\n').replace(/\n/g, '\r\n')
  const prefix = t ? `[${t}] ` : ''
  if (entry.type === 'stderr') {
    return `\u001b[31m${prefix}\u001b[0m\u001b[31m${msg}\u001b[0m\r\n`
  }
  if (entry.type === 'system') {
    return `\u001b[36m${prefix}\u001b[0m${msg}\r\n`
  }
  return `\u001b[32m${prefix}\u001b[0m${msg}\r\n`
}

function hubPollDelayMs() {
  hubPollTicks += 1
  if (hubPollTicks <= 48) return 250
  if (hubPollTicks <= 120) return 400
  return 600
}

function resolveUiScriptPkForExecute(): number | null {
  const sid = selectedScriptId.value
  if (!sid?.startsWith('ui:')) return null
  const parsed = parseUiScriptId(sid)
  if (!parsed || parsed.kind === 'dir') return null
  const n = Number(parsed.pid)
  return Number.isFinite(n) && n > 0 ? n : null
}

async function runHubExecutionPollLoop() {
  if (!executeLoading.value || hubExecutionDbId.value == null) {
    stopHubExecutionPoll()
    return
  }
  if (hubPollInFlight) return
  hubPollInFlight = true
  try {
    const id = hubExecutionDbId.value
    const [{ data: logsData }, { data: statusData }] = await Promise.all([
      request.get(`/assistant/ui-script-executions/${id}/logs/`, { params: { start: 0, end: -1 } }),
      request.get(`/assistant/ui-script-executions/${id}/status_detail/`),
    ])
    const raw = (logsData.logs || []) as EngineLogEntry[]
    if (raw.length > hubLastTelemetryWritten.value) {
      for (let i = hubLastTelemetryWritten.value; i < raw.length; i++) {
        hubTerminalRef.value?.writeLog(formatEngineTelemetryLine(raw[i]))
      }
      hubLastTelemetryWritten.value = raw.length
    }

    const st = String(statusData.execution?.status ?? '')
    if (['success', 'failed', 'timeout', 'cancelled'].includes(st)) {
      stopHubExecutionPoll()
      const rc = statusData.execution?.return_code
      if (st === 'success') {
        hubLastRunOutcome.value = 'success'
        hubLastExitCode.value = typeof rc === 'number' ? rc : 0
        hubTerminalRef.value?.writeLog('\u001b[32m[DONE]\u001b[0m  Telemetry run finished successfully.\r\n')
      } else if (st === 'cancelled') {
        hubLastRunOutcome.value = 'cancelled'
        hubLastExitCode.value = null
        hubTerminalRef.value?.writeLog('\u001b[33m[CANCEL]\u001b[0m  Telemetry run stopped.\r\n')
      } else {
        hubLastRunOutcome.value = 'failed'
        hubLastExitCode.value = typeof rc === 'number' ? rc : 1
        const errMsg = statusData.execution?.error_message || 'Unknown error'
        hubTerminalRef.value?.writeLog(`\u001b[31m[FAIL]\u001b[0m  ${String(errMsg)}\r\n`)
      }
      executeLoading.value = false
      if (hubExecutionDbId.value != null) {
        showAnalysisLabDeepLink.value = true
      }
      hubPollInFlight = false
      return
    }

    const delay = hubPollDelayMs()
    hubPollTimer = setTimeout(() => {
      hubPollInFlight = false
      void runHubExecutionPollLoop()
    }, delay)
  } catch (e: unknown) {
    const err = e as { response?: { status?: number }; message?: string }
    const msg =
      err.response?.status === 404
        ? '日志接口 404：执行记录可能已失效。'
        : `轮询失败：${err.message || '未知错误'}`
    hubTerminalRef.value?.writeLog(`\u001b[31m[POLL]\u001b[0m  ${msg}\r\n`)
    hubPollTimer = setTimeout(() => {
      hubPollInFlight = false
      void runHubExecutionPollLoop()
    }, 800)
  }
}

const canSave = computed(() => {
  if (!editorProjectId.value || !editorWorkspacePath.value || editorReadOnly.value) return false
  return true
})

/** 递增世代，丢弃过期的异步加载结果（避免 axios 取消误触全局错误提示） */
let editorLoadGeneration = 0

onMounted(() => {
  editorReadyTimer = window.setTimeout(() => {
    isEditorReady.value = true
    editorReadyTimer = undefined
  }, 500)
})

onBeforeUnmount(() => {
  stopHubExecutionPoll()
  if (editorReadyTimer != null) {
    clearTimeout(editorReadyTimer)
    editorReadyTimer = undefined
  }
  editorLoadGeneration += 1
})

function parseUiScriptId(id: string) {
  const parts = id.split(':')
  if (parts[0] !== 'ui' || parts.length < 3) return null
  const mode = parts[1]
  if (mode === 'project') return { kind: 'project' as const, pid: parts[2] }
  if (mode === 'online') return { kind: 'online' as const, pid: parts[2] }
  if (mode === 'file') {
    const pid = parts[2]
    const rel = parts.slice(3).join(':')
    if (pid && rel) return { kind: 'file' as const, pid, rel }
  }
  if (mode === 'dir') {
    const pid = parts[2]
    const rel = parts.slice(3).join(':')
    if (pid && rel) return { kind: 'dir' as const, pid, rel }
  }
  return null
}

function isStale(gen: number) {
  return gen !== editorLoadGeneration
}

async function loadEditorForScriptId(id: string | null) {
  const gen = ++editorLoadGeneration

  if (id == null || id === '') {
    editorLoading.value = false
    editorContent.value = ''
    editorLanguage.value = 'python'
    editorDisplayPath.value = '未选择可编辑 Node'
    editorProjectId.value = null
    editorWorkspacePath.value = null
    editorReadOnly.value = true
    return
  }

  if (id.startsWith('ui:')) {
    const parsed = parseUiScriptId(id)
    if (!parsed) {
      editorLoading.value = false
      editorContent.value = ''
      editorReadOnly.value = true
      editorProjectId.value = null
      editorWorkspacePath.value = null
      editorDisplayPath.value = id
      return
    }
    if (parsed.kind === 'dir') {
      editorLoading.value = false
      editorContent.value = ''
      editorLanguage.value = 'python'
      editorDisplayPath.value = `projects/${parsed.pid}/${parsed.rel}/`
      editorProjectId.value = null
      editorWorkspacePath.value = null
      editorReadOnly.value = true
      return
    }

    editorLoading.value = true
    try {
      if (parsed.kind === 'project' || parsed.kind === 'online') {
        const { data: d } = await request.get(`/assistant/ui-scripts/${parsed.pid}/online_content/`)
        if (isStale(gen)) return
        const payload = d as { content?: string; entry_point?: string; language?: string }
        editorContent.value = payload.content ?? ''
        editorLanguage.value = guessLangFromOnline(payload.entry_point, payload.language)
        editorWorkspacePath.value = '__online__'
        editorProjectId.value = parsed.pid
        editorReadOnly.value = false
        editorDisplayPath.value = `projects/${parsed.pid}/__online__`
      } else if (parsed.kind === 'file') {
        const { data: d } = await request.get(`/assistant/ui-scripts/${parsed.pid}/workspace_file/`, {
          params: { path: parsed.rel },
        })
        if (isStale(gen)) return
        const payload = d as { content?: string; path?: string }
        editorContent.value = payload.content ?? ''
        const rel = String(payload.path || parsed.rel)
        editorLanguage.value = languageFromPath(rel)
        editorWorkspacePath.value = rel
        editorProjectId.value = parsed.pid
        editorReadOnly.value = false
        editorDisplayPath.value = `projects/${parsed.pid}/${rel}`
      }
    } catch (e: unknown) {
      if (isStale(gen)) return
      const err = e as { response?: { data?: { error?: string; detail?: string } }; message?: string }
      const msg =
        err?.response?.data?.error ||
        err?.response?.data?.detail ||
        err?.message ||
        '加载失败'
      ElMessage.error(String(msg))
    } finally {
      if (!isStale(gen)) editorLoading.value = false
    }
    return
  }

  if (id.startsWith('api:')) {
    editorLoading.value = true
    try {
      await Promise.resolve()
      if (isStale(gen)) return
      editorContent.value = mockApiScenarioContent(id)
      editorLanguage.value = 'yaml'
      editorDisplayPath.value = `scenarios/${id.replace(/^api:/, '').replace(/:/g, '/')}.yaml`
      editorProjectId.value = null
      editorWorkspacePath.value = null
      editorReadOnly.value = false
    } finally {
      if (!isStale(gen)) editorLoading.value = false
    }
    return
  }

}

watch(
  selectedScriptId,
  (id) => {
    void loadEditorForScriptId(id)
  },
  { flush: 'post', immediate: true },
)

function languageFromPath(p: string) {
  const lower = p.toLowerCase()
  if (lower.endsWith('.py')) return 'python'
  if (lower.endsWith('.json')) return 'json'
  if (lower.endsWith('.js')) return 'javascript'
  if (lower.endsWith('.ts')) return 'typescript'
  if (lower.endsWith('.yaml') || lower.endsWith('.yml')) return 'yaml'
  if (lower.endsWith('.xml')) return 'xml'
  if (lower.endsWith('.html') || lower.endsWith('.htm')) return 'html'
  if (lower.endsWith('.css')) return 'css'
  if (lower.endsWith('.md')) return 'markdown'
  if (lower.endsWith('.sh')) return 'shell'
  return 'python'
}

function guessLangFromOnline(entry?: string, lang?: string) {
  if (lang) {
    const m = String(lang).toLowerCase()
    if (m.includes('python')) return 'python'
    if (m.includes('json')) return 'json'
    if (m.includes('java')) return 'java'
  }
  return languageFromPath(String(entry || ''))
}

function mockApiScenarioContent(key: string) {
  return `# ${key}\nname: mock-scenario\nversion: 1\nsteps:\n  - get:\n      url: https://example.com/health\n`
}

/** 树点击：仅更新 Pinia selectedScriptId；编辑器由 watch(selectedScriptId) 统一拉取，保证单一 Monaco 实例不重复挂载。 */
function onTreeNodeClick(edition: ScriptHubEdition, data: HubTreeNode) {
  if (edition === 'ui') uiTree.onNodeClick(null, data)
  else if (edition === 'api') apiTree.onNodeClick(null, data)
}

async function onSaveClick() {
  if (!canSave.value || !editorProjectId.value || !editorWorkspacePath.value) {
    ElMessage.warning('当前内容不可保存（请选择 Web 可写工作区或在线 Node）')
    return
  }
  saveLoading.value = true
  try {
    if (editorWorkspacePath.value === '__online__') {
      if (!editorContent.value.trim()) {
        ElMessage.warning('在线 Node 内容不能为空')
        return
      }
      await request.put(`/assistant/ui-scripts/${editorProjectId.value}/online_content/`, {
        content: editorContent.value,
      })
    } else {
      await request.put(`/assistant/ui-scripts/${editorProjectId.value}/workspace_file/`, {
        path: editorWorkspacePath.value,
        content: editorContent.value,
      })
    }
    ElMessage.success('已保存')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { error?: string; detail?: string } }; message?: string }
    const d = err?.response?.data
    const msg =
      (typeof d?.error === 'string' && d.error) ||
      (typeof d?.detail === 'string' && d.detail) ||
      err?.message ||
      '保存失败'
    ElMessage.error(String(msg))
  } finally {
    saveLoading.value = false
  }
}

async function onExecuteClick() {
  if (executeLoading.value) return
  if (activePlatform.value !== 'web') {
    ElMessage.warning('当前仅在 Web 平台支持后端 Node 执行。')
    return
  }
  const scriptPk = resolveUiScriptPkForExecute()
  if (scriptPk == null) {
    ElMessage.warning('请先选择可执行的 Web Node（工程 / 在线入口 / 工作区文件）；目录不可执行。')
    return
  }

  stopHubExecutionPoll()
  hubExecutionDbId.value = null
  hubLastTelemetryWritten.value = 0
  hubPollTicks = 0
  hubLastExitCode.value = null
  hubLastRunOutcome.value = 'idle'
  showAnalysisLabDeepLink.value = false
  executeLoading.value = true

  bottomTab.value = 'telemetry'
  await nextTick()
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      hubTerminalRef.value?.fit()
      const modeLabel = isHeadless.value ? 'Headless' : 'Headed'
      hubTerminalRef.value?.writeLog(
        `[\u001b[35mPROMPT\u001b[0m]  Execution Mode: \u001b[36m${modeLabel}\u001b[0m\r\n`,
      )
      hubTerminalRef.value?.writeLog(
        '[\u001b[36mAITESTA\u001b[0m]  Submitting UI Node run · streaming Telemetry (Redis poll)…\r\n',
      )
    })
  })

  console.log(
    '[AutomationCenter] execute context —',
    'ProjectID:',
    selectedProjectId.value,
    'EnvID:',
    selectedEnvironmentId.value,
    'SelectedScriptId:',
    selectedScriptId.value,
    'script_id:',
    scriptPk,
  )

  try {
    const { data } = await request.post('/assistant/ui-script-executions/execute/', {
      script_id: scriptPk,
      triggered_by: 'script_hub',
      browser: browserType.value,
      headless: isHeadless.value,
      parallel: parallelCount.value,
      workspace_project_id: selectedProjectId.value ?? undefined,
      test_environment_id: selectedEnvironmentId.value ?? undefined,
    })
    const dbId = typeof data.id === 'number' ? data.id : Number(data.id)
    if (!Number.isFinite(dbId)) {
      throw new Error('响应中缺少有效的执行记录 id')
    }
    hubExecutionDbId.value = dbId
    hubTerminalRef.value?.writeLog(
      `[\u001b[32mINFO\u001b[0m]  Accepted · db_id=\u001b[33m${dbId}\u001b[0m · runner=\u001b[35m${String(data.execution_id ?? '')}\u001b[0m\r\n`,
    )
    hubPollInFlight = false
    void runHubExecutionPollLoop()
  } catch (e: unknown) {
    executeLoading.value = false
    hubExecutionDbId.value = null
    hubLastRunOutcome.value = 'failed'
    hubLastExitCode.value = null
    showAnalysisLabDeepLink.value = false
    const err = e as { response?: { data?: { error?: string; detail?: string } }; message?: string }
    const d = err.response?.data
    const msg =
      (typeof d?.error === 'string' && d.error) ||
      (typeof d?.detail === 'string' && d.detail) ||
      err.message ||
      '执行请求失败'
    hubTerminalRef.value?.writeLog(`\u001b[31m[HTTP]\u001b[0m  ${msg}\r\n`)
    ElMessage.error(String(msg))
  }
}

async function onStopClick() {
  if (!executeLoading.value) return
  const id = hubExecutionDbId.value
  if (id != null) {
    try {
      await request.post(`/assistant/ui-script-executions/${id}/cancel/`)
      hubTerminalRef.value?.writeLog(
        '\u001b[33m[STOP]\u001b[0m  Cancel requested · waiting for runner to exit…\r\n',
      )
      ElMessage.success('已发送停止请求')
    } catch (e: unknown) {
      stopHubExecutionPoll()
      executeLoading.value = false
      hubLastRunOutcome.value = 'failed'
      showAnalysisLabDeepLink.value = false
      const err = e as { response?: { data?: { error?: string } }; message?: string }
      const msg = err.response?.data?.error || err.message || '停止失败'
      hubTerminalRef.value?.writeLog(`\u001b[31m[STOP]\u001b[0m  ${String(msg)}\r\n`)
      ElMessage.error(String(msg))
    }
  } else {
    stopHubExecutionPoll()
    executeLoading.value = false
    hubLastRunOutcome.value = 'cancelled'
    hubLastExitCode.value = null
    showAnalysisLabDeepLink.value = false
    hubTerminalRef.value?.writeLog(
      '\u001b[33m[STOP]\u001b[0m  No execution id; UI reset.\r\n',
    )
    ElMessage.info('已复位执行状态')
  }
}
</script>

<style scoped>
.script-hub--cyber {
  box-sizing: border-box;
  width: 100%;
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 20px 20px;
  color: rgba(255, 255, 255, 0.9);
}

.glass-panel {
  position: relative;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(12, 18, 32, 0.42);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow:
    0 0 0 1px rgba(0, 240, 255, 0.06) inset,
    0 8px 32px rgba(0, 0, 0, 0.35);
}

.script-hub__workarea {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.platform-adapter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px 16px;
  padding: 10px 16px;
  flex-shrink: 0;
}

.platform-adapter-bar__label {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: rgba(148, 163, 184, 0.85);
}

.platform-adapter-bar__group :deep(.el-radio-button__inner) {
  background: rgba(15, 23, 42, 0.65) !important;
  border-color: rgba(0, 240, 255, 0.2) !important;
  color: rgba(226, 232, 240, 0.88) !important;
  box-shadow: none !important;
}

.platform-adapter-bar__group :deep(.el-radio-button.is-active .el-radio-button__inner) {
  background: rgba(0, 240, 255, 0.12) !important;
  border-color: rgba(0, 240, 255, 0.55) !important;
  color: #00f0ff !important;
  box-shadow: 0 0 12px rgba(0, 240, 255, 0.22) !important;
}

.platform-adapter-bar__telemetry {
  margin-left: auto;
  font-size: 12px;
  font-family: ui-monospace, 'JetBrains Mono', Consolas, monospace;
  color: rgba(251, 191, 36, 0.85);
}

/* 主内容：赛博毛玻璃 + 微弱青场外发光 */
.workstation-panel {
  box-sizing: border-box;
  flex: 1;
  min-height: 320px;
  padding: 14px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow:
    0 0 28px rgba(0, 240, 255, 0.12),
    0 0 1px rgba(0, 240, 255, 0.35);
}

.workstation-panel--ide {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 14px;
  align-items: stretch;
  min-height: 0;
  position: relative;
}

.workstation-panel--ide.is-inspector-open {
  grid-template-columns: 260px minmax(0, 1fr) 220px;
}

.ide-center {
  min-width: 0;
  position: relative;
}

.workstation-panel__col {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.workstation-panel__col--tree {
  padding: 10px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(0, 0, 0, 0.12);
  min-height: 240px;
}

.tree-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.tree-panel-head {
  flex-shrink: 0;
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(148, 163, 184, 0.75);
  margin-bottom: 8px;
}

.script-tree-scroll {
  flex: 1;
  min-height: 180px;
  max-height: min(52vh, 440px);
  overflow: auto;
  margin: 0 -4px;
  padding: 0 4px;
}

.workstation-panel__col--main {
  gap: 10px;
  min-height: 0;
}

.workspace-main-mount {
  flex: 1;
  min-height: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.workstation-panel__col--inspector {
  padding: 10px;
  border-radius: 10px;
  border: 1px solid rgba(0, 240, 255, 0.12);
  background: rgba(0, 0, 0, 0.18);
  min-height: 200px;
  max-height: min(70vh, 640px);
  overflow: auto;
}

.inspector-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.inspector-head__title {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(0, 240, 255, 0.75);
}

.inspector-head__collapse {
  font-size: 12px !important;
  color: #00f0ff !important;
}

.inspector-block {
  margin-bottom: 14px;
}

.inspector-block__h {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 600;
  color: rgba(203, 213, 225, 0.92);
}

.inspector-block__placeholder {
  margin: 0;
  font-size: 11px;
  line-height: 1.5;
  color: rgba(148, 163, 184, 0.88);
  white-space: pre-wrap;
  word-break: break-all;
}

.inspector-block__mono {
  margin: 0;
  font-size: 13px;
  font-family: ui-monospace, 'JetBrains Mono', Consolas, monospace;
  color: rgba(52, 211, 153, 0.9);
}

.inspector-block__mono--status {
  line-height: 1.5;
  color: rgba(167, 243, 208, 0.88);
}

.inspector-block__desc {
  margin: 0 0 8px;
  font-size: 11px;
  line-height: 1.45;
  color: rgba(148, 163, 184, 0.88);
}

.inspector-block__placeholder--sub {
  margin-top: 8px;
}

.inspector-element-input {
  margin-bottom: 8px;
}

.inspector-element-btn {
  width: 100%;
  --el-button-bg-color: rgba(0, 240, 255, 0.12);
  --el-button-border-color: rgba(0, 240, 255, 0.35);
  --el-button-hover-bg-color: rgba(0, 240, 255, 0.2);
}

.inspector-divider {
  margin: 12px 0 !important;
  border-color: rgba(255, 255, 255, 0.08) !important;
}

.inspector-reopen {
  position: absolute;
  top: 40px;
  right: 0;
  z-index: 2;
  width: 22px;
  height: 64px;
  padding: 0;
  border-radius: 6px 0 0 6px;
  border: 1px solid rgba(0, 240, 255, 0.25);
  background: rgba(12, 18, 32, 0.85);
  color: #00f0ff;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  box-shadow: -2px 0 12px rgba(0, 240, 255, 0.12);
}

.inspector-reopen:hover {
  border-color: rgba(0, 240, 255, 0.5);
  box-shadow: -2px 0 16px rgba(0, 240, 255, 0.22);
}

.action-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  padding: 4px 2px 2px;
}

.action-header__spacer {
  flex: 1;
  min-width: 8px;
}

.action-header__btn {
  border-width: 1px !important;
  border-style: solid !important;
  border-color: rgba(0, 240, 255, 0.22) !important;
  color: rgba(226, 232, 240, 0.92) !important;
  background: rgba(0, 240, 255, 0.04) !important;
  box-shadow: 0 0 0 1px rgba(0, 240, 255, 0.04);
}

.action-header__btn:hover {
  border-color: rgba(0, 240, 255, 0.55) !important;
  box-shadow: 0 0 12px rgba(0, 240, 255, 0.18);
}

.action-header__btn--stop {
  border-color: rgba(248, 113, 113, 0.35) !important;
}

.action-header__btn--stop:not(:disabled):hover {
  border-color: rgba(248, 113, 113, 0.6) !important;
  box-shadow: 0 0 12px rgba(248, 113, 113, 0.2);
}

.action-header__btn--exec-running {
  animation: neon-breathe 1.35s ease-in-out infinite;
}

.action-header__btn--exec-config {
  border-color: rgba(167, 139, 250, 0.42) !important;
  box-shadow:
    0 0 0 1px rgba(167, 139, 250, 0.08),
    0 0 10px rgba(129, 140, 248, 0.12);
}

.action-header__btn--exec-config:hover {
  border-color: rgba(192, 132, 252, 0.75) !important;
  box-shadow:
    0 0 14px rgba(167, 139, 250, 0.28),
    0 0 22px rgba(0, 240, 255, 0.1);
}

@keyframes neon-breathe {
  0%,
  100% {
    box-shadow:
      0 0 6px rgba(0, 240, 255, 0.25),
      0 0 14px rgba(0, 240, 255, 0.12);
    border-color: rgba(0, 240, 255, 0.45) !important;
  }
  50% {
    box-shadow:
      0 0 16px rgba(0, 240, 255, 0.55),
      0 0 28px rgba(0, 240, 255, 0.22);
    border-color: rgba(0, 240, 255, 0.85) !important;
  }
}

.editor-stack {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 220px;
  min-width: 0;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(0, 0, 0, 0.14);
  padding: 8px 10px 10px;
}

.editor-path {
  margin: 0 0 6px;
  font-size: 11px;
  line-height: 1.4;
  color: rgba(0, 240, 255, 0.72);
  font-family: ui-monospace, 'JetBrains Mono', Consolas, monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.monaco-wrap {
  flex: 1;
  min-height: 200px;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.monaco-wrap :deep(.monaco-editor-root) {
  flex: 1;
  min-height: 200px;
}

.editor-defer-hint {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0;
  font-size: 12px;
  color: rgba(148, 163, 184, 0.75);
  letter-spacing: 0.06em;
}

.bottom-tabs {
  flex: 1;
  min-height: 140px;
  max-height: min(28vh, 260px);
  display: flex;
  flex-direction: column;
}

.bottom-tabs :deep(.el-tabs__header) {
  margin: 0;
}

.bottom-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.bottom-pane {
  padding: 8px 0;
  min-height: 100px;
}

.bottom-pane--terminal {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  padding: 4px 0 0;
}

.bottom-pane--artifacts {
  min-height: 120px;
}

.bottom-telemetry-zone {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  min-height: 140px;
  max-height: min(28vh, 260px);
}

.bottom-telemetry-zone__row {
  display: flex;
  flex-direction: row;
  align-items: stretch;
  gap: 10px;
  min-height: 0;
  flex: 1;
}

.bottom-telemetry-zone__tabs {
  flex: 1;
  min-width: 0;
  min-height: 0;
}

.bottom-telemetry-zone .bottom-tabs {
  max-height: none;
}

.analysis-lab-glow-btn {
  flex-shrink: 0;
  align-self: flex-end;
  margin-bottom: 6px;
  cursor: pointer;
  padding: 8px 14px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-family: ui-monospace, 'JetBrains Mono', Consolas, monospace;
  color: rgba(10, 22, 28, 0.95);
  background: linear-gradient(135deg, rgba(0, 240, 255, 0.92), rgba(167, 139, 250, 0.88));
  border: 1px solid rgba(0, 240, 255, 0.75);
  border-radius: 10px;
  box-shadow:
    0 0 16px rgba(0, 240, 255, 0.55),
    0 0 32px rgba(167, 139, 250, 0.35),
    0 0 48px rgba(0, 240, 255, 0.15);
  animation: analysis-lab-pulse 2.2s ease-in-out infinite;
  transition:
    transform 0.18s ease,
    filter 0.18s ease;
}

.analysis-lab-glow-btn:hover {
  transform: translateY(-2px) scale(1.02);
  filter: brightness(1.08);
  box-shadow:
    0 0 22px rgba(0, 240, 255, 0.75),
    0 0 40px rgba(167, 139, 250, 0.45);
}

@keyframes analysis-lab-pulse {
  0%,
  100% {
    box-shadow:
      0 0 12px rgba(0, 240, 255, 0.45),
      0 0 28px rgba(167, 139, 250, 0.28);
  }
  50% {
    box-shadow:
      0 0 22px rgba(0, 240, 255, 0.72),
      0 0 42px rgba(167, 139, 250, 0.42);
  }
}

.script-resource-tree {
  background: transparent !important;
  --el-tree-node-hover-bg-color: rgba(0, 240, 255, 0.08);
  --el-tree-text-color: rgba(226, 232, 240, 0.92);
  --el-tree-expand-icon-color: rgba(0, 240, 255, 0.65);
}

.script-resource-tree :deep(.el-tree-node__content) {
  background: transparent !important;
  border-radius: 6px;
  border: none !important;
}

.script-resource-tree :deep(.el-tree-node:focus > .el-tree-node__content) {
  background: rgba(0, 240, 255, 0.06) !important;
}

.script-resource-tree :deep(.el-tree-node.is-current > .el-tree-node__content) {
  background: rgba(0, 240, 255, 0.1) !important;
  box-shadow: 0 0 12px rgba(0, 240, 255, 0.12);
}

.script-tree-node {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.script-tree-node__icon {
  flex-shrink: 0;
  font-size: 15px;
}

.script-tree-node__icon--ui {
  color: rgba(0, 240, 255, 0.75);
  filter: drop-shadow(0 0 6px rgba(0, 240, 255, 0.35));
}

.script-tree-node__icon--api {
  color: rgba(129, 140, 248, 0.9);
  filter: drop-shadow(0 0 6px rgba(129, 140, 248, 0.35));
}

.script-tree-node__icon--mobile {
  color: rgba(244, 114, 182, 0.9);
  filter: drop-shadow(0 0 6px rgba(244, 114, 182, 0.35));
}

.script-tree-node__label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

@media (max-width: 1100px) {
  .workstation-panel--ide.is-inspector-open {
    grid-template-columns: 260px minmax(0, 1fr);
  }

  .workstation-panel__col--inspector {
    grid-column: 1 / -1;
    max-height: 220px;
  }

  .inspector-reopen {
    display: none;
  }
}

@media (max-width: 900px) {
  .workstation-panel--ide,
  .workstation-panel--ide.is-inspector-open {
    grid-template-columns: 1fr;
  }

  .workstation-panel__col--tree {
    min-height: 220px;
  }

  .script-tree-scroll {
    max-height: 280px;
  }
}
</style>

<!-- el-drawer 挂载到 body，需非 scoped 才能命中 -->
<style>
.params-drawer.params-drawer--cyber.el-drawer {
  --el-drawer-bg-color: transparent;
  background: rgba(8, 12, 22, 0.58) !important;
  backdrop-filter: blur(22px);
  -webkit-backdrop-filter: blur(22px);
  box-shadow: -16px 0 56px rgba(0, 0, 0, 0.5);
}

.params-drawer--cyber .el-drawer__header {
  margin-bottom: 0;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 240, 255, 0.12);
}

.params-drawer--cyber .el-drawer__title {
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: rgba(226, 232, 240, 0.95);
}

.params-drawer--cyber .el-drawer__body {
  padding: 16px 18px 24px;
  color: rgba(226, 232, 240, 0.9);
  background: linear-gradient(165deg, rgba(12, 18, 32, 0.42), rgba(6, 10, 20, 0.28));
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

.params-drawer__body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.params-drawer__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.params-drawer__row--top {
  align-items: flex-start;
}

.params-drawer__row--switch {
  align-items: center;
}

.params-drawer__label {
  font-size: 12px;
  font-weight: 600;
  color: rgba(203, 213, 225, 0.92);
  flex-shrink: 0;
}

.params-drawer__hint {
  margin: 0;
  font-size: 11px;
  line-height: 1.5;
  color: rgba(148, 163, 184, 0.88);
}

.params-drawer__select {
  flex: 1;
  min-width: 0;
}

.params-drawer__input {
  flex: 1;
  min-width: 0;
}

/* Drawer 内开关：与 scoped 区视觉一致（drawer 挂 body） */
.params-drawer--cyber .headless-switch--cyber .el-switch:not(.is-checked) .el-switch__core {
  border-color: rgba(167, 139, 250, 0.42);
  background: rgba(30, 27, 48, 0.88);
  box-shadow:
    0 0 6px rgba(139, 92, 246, 0.2),
    0 0 14px rgba(167, 139, 250, 0.1);
}

.params-drawer--cyber .headless-switch--cyber .el-switch.is-checked .el-switch__core {
  background-color: #00f0ff;
  border-color: #00f0ff;
  box-shadow:
    0 0 8px rgba(0, 240, 255, 0.5),
    0 0 20px rgba(0, 240, 255, 0.32);
}

.params-drawer--cyber .headless-switch--cyber .el-switch.is-checked .el-switch__inner {
  color: rgba(8, 20, 26, 0.92);
}

.params-drawer--cyber .headless-switch--cyber .el-switch:not(.is-checked) .el-switch__inner {
  color: rgba(230, 214, 255, 0.92);
}
</style>
