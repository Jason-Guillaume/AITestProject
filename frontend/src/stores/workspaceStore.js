import { defineStore } from 'pinia'
import { getProjectsApi } from '@/api/project'
import { getEnvironments } from '@/api/environment'
import { useAppContextStore } from '@/stores/appContextStore'

const CURRENT_PROJECT_LS = 'current_project_id'
const CURRENT_ENVIRONMENT_LS = 'current_test_environment_id'

/** 列表类数据短时缓存，减少路由/多组件同时挂载时的重复请求 */
const WORKSPACE_LIST_TTL_MS = 5 * 60 * 1000

function normalizeList(payload) {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.results)) return payload.results
  if (Array.isArray(payload?.data)) return payload.data
  return []
}

function scriptHubSeed(projectId) {
  if (projectId == null || projectId === '') return 0
  const digits = String(projectId).replace(/\D/g, '')
  const n = parseInt(digits || '0', 10)
  return Number.isFinite(n) ? n : String(projectId).length * 7
}

export const useWorkspaceStore = defineStore('workspace', {
  state: () => ({
    projectOptions: [],
    envOptions: [],
    selectedProjectId: null,
    selectedEnvironmentId: null,
    projectsLoading: false,
    environmentsLoading: false,
    /** 最近一次成功拉取时间戳（含空列表），用于 TTL 跳过网络 */
    projectsFetchedAt: null,
    envsFetchedAt: null,
    _projectsInflight: null,
    _envsInflight: null,
    _workspaceBootstrapInflight: null,
  }),

  getters: {
    /**
     * Script Hub 卡片用临时指标（按当前选中项目派生，后续可换真实 API）。
     */
    scriptHubCardMetrics() {
      const pid = this.selectedProjectId
      const proj = this.projectOptions.find((p) => String(p.id) === String(pid))
      const projectName = proj?.project_name || ''
      const seed = scriptHubSeed(pid)
      const hasProject = pid != null && pid !== ''

      const statusCycle = ['success', 'failed', 'idle']
      const st = hasProject ? statusCycle[seed % statusCycle.length] : 'idle'

      return {
        projectName: projectName || (hasProject ? '当前项目' : '未选择项目'),
        hasProject,
        /** Web UI：当前项目下脚本数（mock） */
        webUiScriptCount: hasProject ? (seed % 9) + 1 : 0,
        /** Web UI：上次执行状态（mock，可与 uiExecution 覆盖） */
        lastWebUiExecutionStatus: st,
        lastWebUiExecutionAt: hasProject
          ? new Date(Date.now() - (seed * 997) % 72_000_000).toLocaleString()
          : '—',
        /** Performance：最后一次压测报告 ID（mock） */
        lastLoadTestReportId: hasProject ? `RPT-K6-${10000 + (seed % 89999)}` : '—',
        /** API：场景数 mock */
        apiScenarioCount: hasProject ? (seed % 15) + 2 : 0,
        /** API：健康度进度条 0–100（mock） */
        apiHealthPercent: hasProject ? Math.min(100, 45 + (seed % 45)) : 0,
        /** POM 报告归档数（mock） */
        pomReportCount: hasProject ? (seed % 8) : 0,
      }
    },
  },

  actions: {
    _syncProjectContextById(projectId) {
      const appContext = useAppContextStore()
      const p = this.projectOptions.find((item) => String(item.id) === String(projectId))
      if (!p) {
        appContext.setActiveProject({ id: null, name: '' })
        return
      }
      appContext.setActiveProject({ id: p.id, name: p.project_name || '' })
    },

    _syncEnvironmentContextById(environmentId) {
      const appContext = useAppContextStore()
      const e = this.envOptions.find((item) => String(item.id) === String(environmentId))
      if (!e) {
        appContext.setActiveEnvironment({ id: null, name: '' })
        return
      }
      appContext.setActiveEnvironment({ id: e.id, name: e.name || '' })
    },

    setSelectedProjectId(projectId) {
      this.selectedProjectId = projectId == null || projectId === '' ? null : String(projectId)
      this._syncProjectContextById(this.selectedProjectId)
    },

    setSelectedEnvironmentId(environmentId) {
      this.selectedEnvironmentId =
        environmentId == null || environmentId === '' ? null : String(environmentId)
      this._syncEnvironmentContextById(this.selectedEnvironmentId)
    },

    _isProjectsCacheFresh() {
      if (this.projectsFetchedAt == null) return false
      return Date.now() - this.projectsFetchedAt < WORKSPACE_LIST_TTL_MS
    },

    _isEnvsCacheFresh() {
      if (this.envsFetchedAt == null) return false
      return Date.now() - this.envsFetchedAt < WORKSPACE_LIST_TTL_MS
    },

    /**
     * 项目 + 环境一次聚合（Promise.all），多入口重复调用会共享同一 in-flight。
     * @param {{ force?: boolean }} [opts]
     */
    async ensureWorkspaceContext(opts = {}) {
      const { force = false } = opts
      if (
        !force &&
        this._isProjectsCacheFresh() &&
        this._isEnvsCacheFresh()
      ) {
        return
      }
      if (this._workspaceBootstrapInflight && !force) {
        return this._workspaceBootstrapInflight
      }
      const run = Promise.all([
        this.fetchProjects({ force }),
        this.fetchEnvironments({ force }),
      ]).finally(() => {
        this._workspaceBootstrapInflight = null
      })
      this._workspaceBootstrapInflight = run
      return run
    },

    /**
     * @param {{ force?: boolean }} [opts]
     * force 为 true 时始终重新请求（如 app:projects-updated）
     */
    async fetchProjects(opts = {}) {
      const { force = false } = opts
      if (!force && this._isProjectsCacheFresh()) {
        return
      }

      if (this._projectsInflight && !force) {
        return this._projectsInflight
      }

      const run = (async () => {
        this.projectsLoading = true
        const appContext = useAppContextStore()
        try {
          const { data } = await getProjectsApi()
          const list = normalizeList(data)
          this.projectOptions = list
          this.projectsFetchedAt = Date.now()

          const stored = localStorage.getItem(CURRENT_PROJECT_LS)
          const matched = list.find((item) => String(item.id) === String(stored))
          this.selectedProjectId = matched ? String(matched.id) : list[0] ? String(list[0].id) : null

          if (this.selectedProjectId != null) {
            this._syncProjectContextById(this.selectedProjectId)
          } else {
            appContext.setActiveProject({ id: null, name: '' })
          }
        } catch {
          this.projectOptions = []
          this.selectedProjectId = null
          this.projectsFetchedAt = Date.now()
          appContext.setActiveProject({ id: null, name: '' })
        } finally {
          this.projectsLoading = false
        }
      })()

      this._projectsInflight = run
      try {
        await run
      } finally {
        if (this._projectsInflight === run) {
          this._projectsInflight = null
        }
      }
    },

    /**
     * @param {{ force?: boolean }} [opts]
     */
    async fetchEnvironments(opts = {}) {
      const { force = false } = opts
      if (!force && this._isEnvsCacheFresh()) {
        return
      }

      if (this._envsInflight && !force) {
        return this._envsInflight
      }

      const run = (async () => {
        this.environmentsLoading = true
        const appContext = useAppContextStore()
        try {
          const { data } = await getEnvironments({ page_size: 500 })
          const list = normalizeList(data)
          this.envOptions = list
          this.envsFetchedAt = Date.now()

          const stored = localStorage.getItem(CURRENT_ENVIRONMENT_LS)
          const matched = list.find((item) => String(item.id) === String(stored))
          this.selectedEnvironmentId = matched
            ? String(matched.id)
            : list[0]
              ? String(list[0].id)
              : null

          if (this.selectedEnvironmentId != null) {
            this._syncEnvironmentContextById(this.selectedEnvironmentId)
          } else {
            appContext.setActiveEnvironment({ id: null, name: '' })
          }
        } catch {
          this.envOptions = []
          this.selectedEnvironmentId = null
          this.envsFetchedAt = Date.now()
          appContext.setActiveEnvironment({ id: null, name: '' })
        } finally {
          this.environmentsLoading = false
        }
      })()

      this._envsInflight = run
      try {
        await run
      } finally {
        if (this._envsInflight === run) {
          this._envsInflight = null
        }
      }
    },
  },
})
