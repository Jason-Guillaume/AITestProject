import { defineStore } from 'pinia'

/**
 * 自动化指挥中心：当前选中的 Node 标识（跨平台共享）。
 * 格式示例：ui:project:12、ui:file:12:src/a.py、api:regression:login
 */
export const useScriptHubSelectionStore = defineStore('scriptHubSelection', {
  state: () => ({
    /** @type {string | null} */
    selectedScriptId: null,
    /** Platform Adapter：web | mobile | api | miniprogram | h5（与路由 meta.platform 对齐） */
    /** @type {'web' | 'mobile' | 'api' | 'miniprogram' | 'h5'} */
    activePlatform: 'web',
  }),
  actions: {
    /** @param {string | null} id */
    setSelectedScriptId(id) {
      this.selectedScriptId = id
    },
    /** @param {'web' | 'mobile' | 'api' | 'miniprogram' | 'h5'} p */
    setActivePlatform(p) {
      if (p === 'web' || p === 'mobile' || p === 'api' || p === 'miniprogram' || p === 'h5') {
        this.activePlatform = p
      }
    },
  },
})
