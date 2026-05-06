import { defineStore } from 'pinia'

/**
 * 控制「Dashboard SSE」等在自动化指挥中心首屏是否允许建立，避免与 Monaco / 批量请求争用主线程。
 */
export const useUiRealtimeStore = defineStore('uiRealtime', {
  state: () => ({
    /** 仅当路由为 /automation-center 且此项为 true 时，MiniStatusBar 才连接 dashboard/stream */
    dashboardSseArmedOnAutomationCenter: false,
  }),
  actions: {
    armDashboardSse() {
      this.dashboardSseArmedOnAutomationCenter = true
    },
    /** 进入自动化指挥中心时复位，需用户「执行」或切到「终端」后再连接 */
    resetAutomationCenterSseGate() {
      this.dashboardSseArmedOnAutomationCenter = false
    },
  },
})
