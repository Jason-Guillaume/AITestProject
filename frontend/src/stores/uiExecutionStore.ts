import { defineStore } from 'pinia'
import request from '@/utils/request'

export interface ExecutionLog {
  time: string
  level: 'info' | 'success' | 'warning' | 'error'
  message: string
}

export interface ExecutionResult {
  total: number
  passed: number
  failed: number
  skipped: number
  pending?: boolean
}

const UI_EXEC_SESSION_KEY = 'aitesta-webui-execution-v1'

function resultStatsFromRedisOrFallback(redisStatus: unknown, executionStatus: string): ExecutionResult {
  const rs = redisStatus as Record<string, unknown> | null | undefined
  const st = rs?.result_stats as Record<string, unknown> | undefined
  if (st && typeof st.total === 'number') {
    return {
      total: Number(st.total) || 0,
      passed: Number(st.passed) || 0,
      failed: Number(st.failed) || 0,
      skipped: Number(st.skipped) || 0,
      pending: false,
    }
  }
  const terminal = ['success', 'failed', 'timeout', 'cancelled']
  if (!terminal.includes(executionStatus)) {
    return { total: 0, passed: 0, failed: 0, skipped: 0, pending: true }
  }
  const ok = executionStatus === 'success'
  return {
    total: 1,
    passed: ok ? 1 : 0,
    failed: ok ? 0 : 1,
    skipped: 0,
    pending: false,
  }
}

export const useUiExecutionStore = defineStore('uiExecution', {
  state: () => ({
    currentProjectId: null as string | null,
    currentExecutionId: null as number | null,
    runExecutionIdStr: null as string | null,
    runHeaderTime: null as string | null,
    isRunning: false,
    logs: [] as ExecutionLog[],
    result: null as ExecutionResult | null,
    _pollTimer: null as NodeJS.Timeout | null,
    _pollTickCount: 0,
    _pollInFlight: false,
    _emptyLogStreak: 0,
  }),
  actions: {
    async startExecution(projectId: string, config: { browser: string; headless: boolean; parallel: number }) {
      if (this.isRunning) return
      this.isRunning = true
      this.currentProjectId = projectId
      this.currentExecutionId = null
      this.runExecutionIdStr = null
      this.runHeaderTime = null
      this.logs = []
      this.result = null
      this._pollTickCount = 0
      this._pollInFlight = false
      this._emptyLogStreak = 0

      try {
        const { data } = await request.post('/assistant/ui-script-executions/execute/', {
          script_id: Number(projectId),
          triggered_by: 'manual',
          browser: config.browser,
          headless: config.headless,
          parallel: config.parallel,
        })
        this.currentExecutionId = data.id
        this.runExecutionIdStr = typeof data.execution_id === 'string' ? data.execution_id : String(data.execution_id ?? '')
        this.runHeaderTime = new Date().toLocaleTimeString()
        this.persistSnapshotToSession()
        await this.pollLogs()
      } catch (e) {
        this.isRunning = false
        this.currentExecutionId = null
        this.runExecutionIdStr = null
        this.runHeaderTime = null
        if (typeof window !== 'undefined') {
          try {
            sessionStorage.removeItem(UI_EXEC_SESSION_KEY)
          } catch {
            /* ignore */
          }
        }
        throw e
      }
    },

    async requestStop() {
      if (!this.currentExecutionId) return
      await request.post(`/assistant/ui-script-executions/${this.currentExecutionId}/cancel/`)
      await this.pollLogs()
    },

    addLog(message: string, level: ExecutionLog['level'] = 'info') {
      this.logs.push({ time: new Date().toLocaleTimeString(), level, message })
      const MAX = 1000
      if (this.logs.length > MAX) {
        this.logs.splice(0, this.logs.length - MAX)
      }
    },

    _buildLogView(remote: ExecutionLog[]) {
      const t = this.runHeaderTime || new Date().toLocaleTimeString()
      const prefix: ExecutionLog[] = []
      if (this.runExecutionIdStr) {
        prefix.push({ time: t, level: 'info', message: `执行 ID: ${this.runExecutionIdStr}` })
      }
      prefix.push({
        time: t,
        level: 'info',
        message:
          '日志约每 0.25～0.5 秒刷新（来自 Redis）。浏览器与驱动在跑 Django 的机器上执行；远程打开本页时窗口不会出现在你当前电脑。无头/有头均可能在启动后数十秒至数分钟内几乎无新日志（冷启动、收集用例、打开首屏）。项目 drivers/ 下放置 chromedriver.exe 等可显著减少冷启动等待。',
      })
      this.logs = [...prefix, ...remote]
    },

    _nextPollDelayMs() {
      this._pollTickCount += 1
      if (this._pollTickCount <= 48) return 250
      if (this._pollTickCount <= 120) return 400
      return 600
    },

    async pollLogs() {
      if (!this.currentExecutionId) return
      if (this._pollInFlight) return
      this._pollInFlight = true
      try {
        const id = this.currentExecutionId
        const [{ data: logsData }, { data: statusData }] = await Promise.all([
          request.get(`/assistant/ui-script-executions/${id}/logs/`, {
            params: { start: 0, end: -1 },
          }),
          request.get(`/assistant/ui-script-executions/${id}/status_detail/`),
        ])

        const execution = statusData.execution
        const rawList = logsData.logs || []
        let remote = rawList.map((log: any) => ({
          time: new Date(log.timestamp).toLocaleTimeString(),
          level: log.type === 'stderr' ? 'error' : log.type === 'system' ? 'info' : 'success',
          message: log.message,
        }))

        if (rawList.length === 0 && ['pending', 'running'].includes(execution.status)) {
          this._emptyLogStreak += 1
        } else {
          this._emptyLogStreak = 0
        }
        if (this._emptyLogStreak >= 16) {
          remote = [
            ...remote,
            {
              time: new Date().toLocaleTimeString(),
              level: 'warning' as const,
              message:
                '数秒内仍无引擎日志：多为 Redis 未启动或与 Django 的 REDIS_HOST/PORT 不一致（此前日志会静默丢失）。请在后端控制台看是否有「无法连接 Redis」或执行异常；本机可运行 redis-cli ping 自检。',
            },
          ]
        }

        this._buildLogView(remote)

        const redis = statusData.redis_status || {}
        this.result = resultStatsFromRedisOrFallback(redis, execution.status)

        if (['success', 'failed', 'timeout', 'cancelled'].includes(execution.status)) {
          this.isRunning = false
          if (this._pollTimer) {
            clearTimeout(this._pollTimer)
            this._pollTimer = null
          }
          if (execution.status === 'success') {
            this.addLog('执行完成！', 'success')
          } else if (execution.status === 'cancelled') {
            this.addLog('执行已停止。', 'warning')
          } else {
            this.addLog(`执行失败: ${execution.error_message || '未知错误'}`, 'error')
          }
          this._pollInFlight = false
        } else {
          const delay = this._nextPollDelayMs()
          this._pollTimer = setTimeout(() => {
            this._pollInFlight = false
            this.pollLogs()
          }, delay)
        }
        this.persistSnapshotToSession()
      } catch (e: any) {
        console.error('轮询异常:', e)
        const status = e?.response?.status
        const detail =
          status === 404
            ? '日志接口 404：执行记录可能已过期，请重新发起执行。'
            : `拉取日志失败（${status ?? '无状态码'}）：${e?.message || '未知错误'}。请确认后端可连 Redis、且 Django 已重启。`
        this._buildLogView([
          {
            time: new Date().toLocaleTimeString(),
            level: 'error',
            message: detail,
          },
        ])
        const delay = 800
        this._pollTimer = setTimeout(() => {
          this._pollInFlight = false
          this.pollLogs()
        }, delay)
      }
    },

    clearPolling() {
      if (this._pollTimer) {
        clearTimeout(this._pollTimer)
        this._pollTimer = null
      }
      this.isRunning = false
      this._pollInFlight = false
    },

    persistSnapshotToSession() {
      if (typeof window === 'undefined' || !this.currentExecutionId) return
      try {
        sessionStorage.setItem(
          UI_EXEC_SESSION_KEY,
          JSON.stringify({
            v: 1,
            currentProjectId: this.currentProjectId,
            currentExecutionId: this.currentExecutionId,
            runExecutionIdStr: this.runExecutionIdStr,
            runHeaderTime: this.runHeaderTime,
            isRunning: this.isRunning,
          })
        )
      } catch {
        /* 隐私模式或配额 */
      }
    },

    restoreFromSessionStorage() {
      if (typeof window === 'undefined') return
      try {
        const raw = sessionStorage.getItem(UI_EXEC_SESSION_KEY)
        if (!raw) return
        const o = JSON.parse(raw) as Record<string, unknown>
        if (o.v !== 1 || o.currentExecutionId == null) return
        this.currentProjectId =
          o.currentProjectId != null ? String(o.currentProjectId) : null
        this.currentExecutionId =
          typeof o.currentExecutionId === 'number'
            ? o.currentExecutionId
            : Number(o.currentExecutionId)
        if (!Number.isFinite(this.currentExecutionId)) return
        this.runExecutionIdStr =
          o.runExecutionIdStr != null ? String(o.runExecutionIdStr) : null
        this.runHeaderTime = o.runHeaderTime != null ? String(o.runHeaderTime) : null
        this.isRunning = !!o.isRunning
        this.logs = []
        this.result = null
        this._pollTickCount = 0
        this._emptyLogStreak = 0
        this._pollTimer = null
        this._pollInFlight = false
      } catch {
        /* ignore */
      }
    },

    async resumeAfterRemount() {
      if (!this.currentExecutionId) return
      this._pollInFlight = false
      await this.pollLogs()
    },

    kickPoll() {
      this._pollInFlight = false
      void this.pollLogs()
    },

    clearLogViewOnly() {
      if (this.isRunning) return
      const pid = this.currentProjectId
      this.logs = []
      this.result = null
      this.currentExecutionId = null
      this.runExecutionIdStr = null
      this.runHeaderTime = null
      this.isRunning = false
      this._pollTickCount = 0
      this._emptyLogStreak = 0
      if (this._pollTimer) {
        clearTimeout(this._pollTimer)
        this._pollTimer = null
      }
      this._pollInFlight = false
      this.currentProjectId = pid
      if (typeof window !== 'undefined') {
        try {
          sessionStorage.removeItem(UI_EXEC_SESSION_KEY)
        } catch {
          /* ignore */
        }
      }
    },

    reset() {
      if (typeof window !== 'undefined') {
        try {
          sessionStorage.removeItem(UI_EXEC_SESSION_KEY)
        } catch {
          /* ignore */
        }
      }
      this.currentProjectId = null
      this.currentExecutionId = null
      this.runExecutionIdStr = null
      this.runHeaderTime = null
      this.isRunning = false
      this.logs = []
      this.result = null
      this._pollTickCount = 0
      this._emptyLogStreak = 0
      this.clearPolling()
    },
  },
})
