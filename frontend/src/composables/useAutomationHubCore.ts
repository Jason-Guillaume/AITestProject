import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch,
} from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { useScriptHubSelectionStore } from '@/stores/scriptHubSelectionStore'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import request from '@/utils/request'
import type TerminalTerminal from '@/components/script/TerminalTerminal.vue'

type HubRunOutcome = 'idle' | 'success' | 'failed' | 'cancelled'

interface EngineLogEntry {
  timestamp: string
  type: string
  message: string
}

export type AutomationPlatform = 'web' | 'mobile' | 'api' | 'miniprogram' | 'h5'

/**
 * 自动化指挥中心共享运行时：编辑器、执行轮询、遥测写入、Inspector 状态。
 * 平台由当前路由 meta.platform 驱动，与 Pinia activePlatform 同步。
 */
export function useAutomationHubCore() {
  const route = useRoute()
  const router = useRouter()
  const hubSelection = useScriptHubSelectionStore()
  const { selectedScriptId } = storeToRefs(hubSelection)

  const workspaceStore = useWorkspaceStore()
  const { selectedProjectId, selectedEnvironmentId } = storeToRefs(workspaceStore)

  const activePlatform = computed<AutomationPlatform>(() => {
    const p = route.meta.platform
    if (p === 'web' || p === 'mobile' || p === 'api' || p === 'miniprogram' || p === 'h5') return p
    return 'web'
  })

  watch(
    activePlatform,
    (p) => {
      hubSelection.setActivePlatform(p)
      hubSelection.setSelectedScriptId(null)
    },
    { immediate: true },
  )

  const inspectorOpen = ref(true)

  const layoutProfile = computed(() => ({
    mainWorkspace:
      activePlatform.value === 'mobile'
        ? 'shell-mobile'
        : activePlatform.value === 'miniprogram' || activePlatform.value === 'h5'
          ? 'shell-cross-placeholder'
          : 'shell-editor',
    inspectorVariant:
      activePlatform.value === 'web'
        ? 'web-inspector'
        : activePlatform.value === 'mobile'
          ? 'mobile-inspector'
          : activePlatform.value === 'miniprogram'
            ? 'miniprogram-inspector'
            : activePlatform.value === 'h5'
              ? 'h5-inspector'
              : 'api-inspector',
  }))

  const inspectorHeadTitle = computed(() => {
    if (activePlatform.value === 'web') return 'Inspector · Web'
    if (activePlatform.value === 'mobile') return 'Inspector · Mobile'
    if (activePlatform.value === 'miniprogram') return 'Inspector · 小程序'
    if (activePlatform.value === 'h5') return 'Inspector · H5'
    return 'Inspector · API'
  })

  const paramsDrawerVisible = ref(false)

  const platformChromeLabel = computed(() => {
    if (activePlatform.value === 'web') return 'Web'
    if (activePlatform.value === 'mobile') return 'Mobile'
    if (activePlatform.value === 'miniprogram') return '小程序'
    if (activePlatform.value === 'h5') return 'H5'
    return 'API'
  })

  const editorChromeTitle = computed(() => `[${platformChromeLabel.value}] · ${editorDisplayPath.value}`)

  const inspectorMetadataPlaceholder = computed(() =>
    selectedScriptId.value
      ? `Node ID: ${selectedScriptId.value}\n（详细元数据将对接后端）`
      : '未选中 Node',
  )

  const hubLastExitCode = ref<number | null>(null)
  const hubLastRunOutcome = ref<HubRunOutcome>('idle')

  const executeLoading = ref(false)

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
  const isHeadless = ref(true)
  const browserType = ref('chrome')
  const parallelCount = ref(1)
  const mobileDevicePlaceholder = ref('')
  const mobilePackageName = ref('')
  const bottomTab = ref<'telemetry' | 'artifacts'>('telemetry')

  const hubTerminalRef = ref<InstanceType<typeof TerminalTerminal> | null>(null)

  const hubExecutionDbId = ref<number | null>(null)
  const hubLastTelemetryWritten = ref(0)
  let hubPollTimer: ReturnType<typeof setTimeout> | null = null
  let hubPollInFlight = false
  let hubPollTicks = 0

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

  function isStale(gen: number) {
    return gen !== editorLoadGeneration
  }

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
    }
  }

  watch(
    selectedScriptId,
    (id) => {
      void loadEditorForScriptId(id)
    },
    { flush: 'post', immediate: true },
  )

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

  const hub = reactive({
    activePlatform,
    inspectorOpen,
    layoutProfile,
    inspectorHeadTitle,
    paramsDrawerVisible,
    editorChromeTitle,
    inspectorMetadataPlaceholder,
    lastTelemetryStatusDisplay,
    showAnalysisLabDeepLink,
    isEditorReady,
    editorContent,
    editorLanguage,
    editorReadOnly,
    editorLoading,
    saveLoading,
    executeLoading,
    isHeadless,
    browserType,
    parallelCount,
    mobileDevicePlaceholder,
    mobilePackageName,
    bottomTab,
    hubExecutionDbId,
    canSave,
    onSaveClick,
    onExecuteClick,
    onStopClick,
    goAnalysisLabDeepLink,
    selectedProjectId,
  })

  return { hub, hubTerminalRef }
}
