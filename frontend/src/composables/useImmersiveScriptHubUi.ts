/**
 * Web UI 自动化：脚本列表、工作区树、Monaco 读写、执行（Pinia）
 * 供 ScriptHub 沉浸式工作台与 WebUIWorkbench 共用逻辑。
 */
import { ref, reactive, computed, watch, nextTick, type Ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'
import { useUiExecutionStore } from '@/stores/uiExecutionStore'

export interface Project {
  id: string
  name: string
  framework: string
  type: string
  path: string
  description?: string
  is_active: boolean
  deleted_at?: string | null
}

export interface TreeNodeData {
  id: string
  label: string
  projectId?: string
  path?: string
  isScriptRoot?: boolean
  isLeaf?: boolean
  children?: TreeNodeData[]
  project?: Project
}

type TrieNode = { file: boolean; sub: Record<string, TrieNode> }

export function buildFileTreeFromPaths(files: string[], projectId: string): TreeNodeData[] {
  const root: Record<string, TrieNode> = {}
  for (const raw of files) {
    const parts = raw.replace(/\\/g, '/').split('/').filter(Boolean)
    let cur = root
    for (let i = 0; i < parts.length; i++) {
      const name = parts[i]
      if (!cur[name]) cur[name] = { file: false, sub: {} }
      if (i === parts.length - 1) {
        cur[name].file = true
      }
      cur = cur[name].sub
    }
  }

  function walk(obj: Record<string, TrieNode>, basePath: string): TreeNodeData[] {
    return Object.keys(obj)
      .sort()
      .map((name) => {
        const node = obj[name]
        const full = basePath ? `${basePath}/${name}` : name
        const subKeys = Object.keys(node.sub)
        if (node.file && subKeys.length === 0) {
          return {
            id: `f-${projectId}-${full}`,
            label: name,
            path: full,
            projectId,
            isLeaf: true,
          }
        }
        const children = walk(node.sub, full)
        return {
          id: `d-${projectId}-${full}`,
          label: name,
          path: full,
          projectId,
          isLeaf: children.length === 0,
          children,
        }
      })
  }

  return walk(root, '')
}

export function mapScriptRow(script: Record<string, unknown>): Project {
  const st = script.script_type as string | undefined
  let typeLabel = '脚本'
  if (st === 'LINEAR') typeLabel = '线性脚本'
  else if (st === 'POM') typeLabel = 'POM'
  return {
    id: String(script.id),
    name: String(script.name ?? ''),
    framework: String(script.framework ?? 'AUTO'),
    type: typeLabel,
    path: String(script.workspace_path ?? ''),
    description: '',
    is_active: script.is_active !== false && script.is_active !== 0,
    deleted_at: (script.deleted_at as string | null | undefined) ?? null,
  }
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

function guessLangFromApi(entry?: string, lang?: string) {
  if (lang) {
    const m = String(lang).toLowerCase()
    if (m.includes('python')) return 'python'
    if (m.includes('json')) return 'json'
    if (m.includes('java')) return 'java'
  }
  return languageFromPath(String(entry || ''))
}

export function useImmersiveScriptHubUi(logScrollRef?: Ref<HTMLElement | null>) {
  const projects = ref<Project[]>([])
  const selectedProject = ref<Project | null>(null)
  const uiStore = useUiExecutionStore()
  const stopExecutionLoading = ref(false)

  const executionConfig = reactive({
    browser: 'chrome',
    headless: false,
    parallel: 1,
  })

  const editorContent = ref('')
  const editorLanguage = ref('python')
  const editorReadOnly = ref(false)
  const editorPath = ref<string | null>(null)
  const editorTitle = ref('')
  const editorProjectId = ref<string | null>(null)
  const editorLoading = ref(false)
  const saveLoading = ref(false)

  const canSaveEditor = computed(() => {
    if (!editorPath.value || !editorProjectId.value || editorReadOnly.value) return false
    return true
  })

  const selectProject = (project: Project) => {
    const nextId = String(project.id)
    const storeScriptId = uiStore.currentProjectId != null ? String(uiStore.currentProjectId) : ''
    const prevSelectedId = selectedProject.value?.id != null ? String(selectedProject.value.id) : ''
    selectedProject.value = project
    if (prevSelectedId && prevSelectedId !== nextId) {
      if (editorProjectId.value && String(editorProjectId.value) !== nextId) {
        editorPath.value = null
        editorContent.value = ''
        editorTitle.value = ''
        editorProjectId.value = null
      }
    }
    if (storeScriptId !== nextId) {
      uiStore.reset()
    } else if (uiStore.currentExecutionId != null && uiStore.isRunning) {
      uiStore.kickPoll()
    }
  }

  async function loadWorkspaceFile(projectId: string, relPath: string) {
    editorLoading.value = true
    try {
      const { data } = await request.get(`/assistant/ui-scripts/${projectId}/workspace_file/`, {
        params: { path: relPath },
      })
      editorContent.value = (data as { content?: string }).content ?? ''
      editorLanguage.value = languageFromPath(String((data as { path?: string }).path || relPath))
      editorReadOnly.value = false
      editorPath.value = String((data as { path?: string }).path || relPath)
      editorProjectId.value = projectId
      editorTitle.value = String((data as { path?: string }).path || relPath)
      const p = projects.value.find((x) => x.id === String(projectId))
      if (p) selectProject(p)
    } catch (e: unknown) {
      const err = e as { response?: { data?: { error?: string } }; message?: string }
      const msg = err?.response?.data?.error || err?.message || '加载失败'
      ElMessage.error(String(msg))
      editorPath.value = null
    } finally {
      editorLoading.value = false
    }
  }

  async function loadOnlineScript(projectId: string) {
    editorLoading.value = true
    try {
      const { data } = await request.get(`/assistant/ui-scripts/${projectId}/online_content/`)
      const d = data as { content?: string; entry_point?: string; language?: string }
      editorContent.value = d.content ?? ''
      editorLanguage.value = guessLangFromApi(d.entry_point, d.language)
      editorReadOnly.value = false
      editorPath.value = '__online__'
      editorProjectId.value = projectId
      editorTitle.value = '在线脚本（入口）'
      const p = projects.value.find((x) => x.id === String(projectId))
      if (p) selectProject(p)
    } catch (e: unknown) {
      const err = e as { response?: { data?: { error?: string; detail?: string } }; message?: string }
      const msg =
        err?.response?.data?.error || err?.response?.data?.detail || err?.message || '加载失败'
      ElMessage.error(String(msg))
      editorPath.value = null
    } finally {
      editorLoading.value = false
    }
  }

  async function saveEditor() {
    if (!canSaveEditor.value || !editorProjectId.value || !editorPath.value) return
    saveLoading.value = true
    try {
      if (editorPath.value === '__online__') {
        if (!editorContent.value.trim()) {
          ElMessage.warning('在线脚本内容不能为空')
          return
        }
        await request.put(`/assistant/ui-scripts/${editorProjectId.value}/online_content/`, {
          content: editorContent.value,
        })
      } else {
        await request.put(`/assistant/ui-scripts/${editorProjectId.value}/workspace_file/`, {
          path: editorPath.value,
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

  async function loadProjects(opts?: { selectServerId?: number }) {
    try {
      const { data } = await request.get('/assistant/ui-scripts/', { params: { show_deleted: false } })
      const scripts = Array.isArray(data) ? data : (data as { results?: unknown[] }).results || []
      projects.value = scripts.map((script: unknown) => mapScriptRow(script as Record<string, unknown>))
      const sid = opts?.selectServerId
      if (sid != null && Number.isFinite(Number(sid))) {
        const match = projects.value.find((p) => p.id === String(sid))
        if (match) selectProject(match)
      }
    } catch (e: unknown) {
      const err = e as { message?: string }
      ElMessage.error('加载脚本列表失败：' + (err?.message || '未知错误'))
    }
  }

  async function loadUiChildrenForProject(projectId: string): Promise<TreeNodeData[]> {
    try {
      const { data: wi } = await request.get(`/assistant/ui-scripts/${projectId}/workspace_info/`)
      const files: string[] = (wi as { files?: string[] }).files || []
      if (!files.length) {
        return [
          {
            id: `online-${projectId}`,
            label: '脚本内容（入口 / 在线）',
            path: '__online__',
            projectId,
            isLeaf: true,
          },
        ]
      }
      return buildFileTreeFromPaths(files, projectId)
    } catch {
      return [
        {
          id: `online-${projectId}`,
          label: '脚本内容（入口 / 在线）',
          path: '__online__',
          projectId,
          isLeaf: true,
        },
      ]
    }
  }

  async function runExecution() {
    if (!selectedProject.value) return
    const sid = Number(selectedProject.value.id)
    if (!Number.isFinite(sid) || sid <= 0) {
      ElMessage.warning('当前工程未关联后端脚本，请先导入')
      return
    }
    if (!selectedProject.value.is_active) {
      try {
        await ElMessageBox.confirm(
          '当前脚本已禁用，无法执行。是否立即启用并开始执行？',
          '脚本已禁用',
          { type: 'warning', confirmButtonText: '启用并执行', cancelButtonText: '取消' },
        )
        await request.post(`/assistant/ui-scripts/${sid}/toggle_active/`)
        await loadProjects({ selectServerId: sid })
        const match = projects.value.find((p) => p.id === String(sid))
        if (match) selectProject(match)
      } catch {
        return
      }
    }
    try {
      await uiStore.startExecution(String(sid), executionConfig)
    } catch (e: unknown) {
      const err = e as { response?: { data?: { error?: string; detail?: string } }; message?: string }
      const d = err?.response?.data
      const detail =
        (typeof d?.error === 'string' && d.error) ||
        (typeof d?.detail === 'string' && d.detail) ||
        err?.message ||
        '未知错误'
      ElMessage.error('执行启动失败：' + detail)
    }
  }

  async function stopExecution() {
    if (!uiStore.currentExecutionId || !uiStore.isRunning) return
    stopExecutionLoading.value = true
    try {
      await uiStore.requestStop()
      ElMessage.success('已发送停止请求')
    } catch (e: unknown) {
      const err = e as { response?: { data?: { error?: string; detail?: string } }; message?: string }
      const d = err?.response?.data
      const detail =
        (typeof d?.error === 'string' && d.error) ||
        (typeof d?.detail === 'string' && d.detail) ||
        err?.message ||
        '未知错误'
      ElMessage.error('停止失败：' + detail)
    } finally {
      stopExecutionLoading.value = false
    }
  }

  function exportLogs() {
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

  async function clearLogView() {
    if (uiStore.isRunning || uiStore.logs.length === 0) return
    try {
      await ElMessageBox.confirm(
        '清空后控制台恢复为「等待执行」；可先导出日志留存副本。',
        '清空控制台',
        { type: 'warning', confirmButtonText: '清空', cancelButtonText: '取消' },
      )
      uiStore.clearLogViewOnly()
      ElMessage.success('已清空')
    } catch {
      /* cancel */
    }
  }

  watch(
    () => uiStore.logs.length,
    async () => {
      await nextTick()
      const el = logScrollRef?.value
      if (el) el.scrollTop = el.scrollHeight
    },
  )

  return {
    projects,
    selectedProject,
    selectProject,
    loadProjects,
    loadUiChildrenForProject,
    loadWorkspaceFile,
    loadOnlineScript,
    editorContent,
    editorLanguage,
    editorReadOnly,
    editorPath,
    editorTitle,
    editorProjectId,
    editorLoading,
    saveLoading,
    canSaveEditor,
    saveEditor,
    executionConfig,
    uiStore,
    stopExecutionLoading,
    runExecution,
    stopExecution,
    exportLogs,
    clearLogView,
  }
}
