import { defineStore } from 'pinia'

/**
 * 自动化指挥中心侧栏树 / 资产列表联动刷新
 */
export const useAutomationCenterHubStore = defineStore('automationCenterHub', {
  state: () => ({
    /** 递增后 WebAutomationTree 等可强制重挂载刷新 */
    explorerRefreshTick: 0,
  }),
  actions: {
    bumpExplorerRefresh() {
      this.explorerRefreshTick += 1
    },
  },
})
