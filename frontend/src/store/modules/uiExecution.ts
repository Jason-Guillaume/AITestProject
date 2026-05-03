import { defineStore } from 'pinia'
import request from '@/utils/request' // 项目统一的 axios 实例

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
  /** 运行中、尚未写入 result_stats 时为 true，不展示假数字 */
  pending?: boolean
}

/** 刷新页面后恢复「最后一次执行」的元数据，日志从接口再拉 */
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

/**
 * UI 自动化执行状态 Store
 * 用于在页面切换时保留执行 ID、轮询状态、日志等信息，防止页面卸载导致状态丢失。
 */
export const useUiExecutionStore = defineStore('uiExecution', {
  state: () => ({
    currentProjectId: null as string | null,
    currentExecutionId: null as number | null,
    /** 后端返回的 execution_id 字符串，用于日志区固定标题行 */
    runExecutionIdStr: null as string | null,
    runHeaderTime: null as string | null,
    isRunning: false,
    logs: [] as ExecutionLog[],
    result: null as ExecutionResult | null,
    _pollTimer: null as NodeJS.Timeout | null,
    /** 执行开始后轮询次数，用于前几秒更高频拉日志（近实时） */
    _pollTickCount: 0,
    /** 防止上一轮未结束又排下一轮，避免请求堆积 */
    _pollInFlight: false,
    /** 连续多轮引擎日志为空（用于提示 Redis/线程问题） */
    _emptyLogStreak: 0,
  }),
  actions: {
    /** 发起执行请求 */
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
        // 必须 await 首轮拉取，否则首屏会长时间停留在「等待执行」且看不到前缀/引擎日志
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

    /** 请求停止当前执行（线性与 POM；有头/无头均适用），随后拉取一次状态与日志 */
    async requestStop() {
      if (!this.currentExecutionId) return
      await request.post(`/assistant/ui-script-executions/${this.currentExecutionId}/cancel/`)
      await this.pollLogs()
    },

    /** 添加日志并限制最大条数 */
    addLog(message: string, level: ExecutionLog['level'] = 'info') {
      this.logs.push({ time: new Date().toLocaleTimeString(), level, message })
      const MAX = 1000
      if (this.logs.length > MAX) {
        this.logs.splice(0, this.logs.length - MAX)
      }
    },

    /** 固定前缀 + Redis 引擎日志（不再整段替换，避免「执行 ID」等提示被轮询刷没） */
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

    /** 下一轮轮询间隔（ms）：前几秒密集，之后略降，减轻后端压力 */
    _nextPollDelayMs() {
      this._pollTickCount += 1
      if (this._pollTickCount <= 48) return 250
      if (this._pollTickCount <= 120) return 400
      return 600
    },

    /** 轮询日志和执行状态（日志与状态并行请求，缩短间隔以贴近实时） */
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

    /** 清理轮询计时器，防止内存泄漏 */
    clearPolling() {
      if (this._pollTimer) {
        clearTimeout(this._pollTimer)
        this._pollTimer = null
      }
      this.isRunning = false
      this._pollInFlight = false
    },

    /** 将当前执行元数据写入 sessionStorage，便于刷新页面后恢复并从 Redis 重拉日志 */
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

    /** 从 sessionStorage 恢复元数据（不恢复 logs，由 pollLogs 填充） */
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

    /** 工作台挂载后：若有未结束或刚恢复的执行，继续轮询 */
    async resumeAfterRemount() {
      if (!this.currentExecutionId) return
      this._pollInFlight = false
      await this.pollLogs()
    },

    /** 同脚本再次选中且仍在运行时，解除轮询互斥并立即拉一次日志 */
    kickPoll() {
      this._pollInFlight = false
      void this.pollLogs()
    },

    /**
     * 仅清空控制台展示（执行已结束时可点）。保留当前所选脚本 ID，便于接着点「开始执行」；
     * 与「换脚本」的 reset 不同，不会误清切换前的对比需求（可先导出再清空）。
     */
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

    /** 重置状态（在切换项目或手动清空时使用） */
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
