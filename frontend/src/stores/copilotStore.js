import { defineStore } from 'pinia'

/**
 * 全局 AI Copilot：右侧抽屉与 Monaco / 工作流页面的桥接。
 * Monaco 实例在 mount 时 registerBridge，focus 时 setActiveBridgeId。
 */
export const useCopilotStore = defineStore('copilot', {
  state: () => ({
    drawerOpen: false,
    /** @type {Record<string, { getValue: () => string, setValue: (v: string) => void, insertAtCursor: (v: string) => void, getLanguage: () => string, isReadOnly: () => boolean, getLabel: () => string, focus?: () => void }>} */
    bridges: {},
    activeBridgeId: null,
    /** 由各业务页写入：失败日志、报告摘要等 */
    workflowContext: {
      executionLogId: null,
      executionLogLabel: '',
      scenario: '',
      reportId: null,
      reportHint: '',
    },
  }),

  getters: {
    activeBridge(state) {
      const id = state.activeBridgeId
      if (id && state.bridges[id]) return { id, ...state.bridges[id] }
      const keys = Object.keys(state.bridges)
      if (keys.length === 1) {
        const only = keys[0]
        return { id: only, ...state.bridges[only] }
      }
      return null
    },
  },

  actions: {
    toggleDrawer() {
      this.drawerOpen = !this.drawerOpen
    },
    openDrawer() {
      this.drawerOpen = true
    },
    closeDrawer() {
      this.drawerOpen = false
    },

    registerBridge(id, api) {
      if (!id || !api) return
      this.bridges[id] = api
      if (!this.activeBridgeId) this.activeBridgeId = id
    },

    unregisterBridge(id) {
      if (!id) return
      delete this.bridges[id]
      if (this.activeBridgeId === id) {
        const keys = Object.keys(this.bridges)
        this.activeBridgeId = keys.length ? keys[keys.length - 1] : null
      }
    },

    setActiveBridgeId(id) {
      if (id && this.bridges[id]) this.activeBridgeId = id
    },

    /** @param {Partial<typeof this.workflowContext>} patch */
    patchWorkflowContext(patch) {
      this.workflowContext = { ...this.workflowContext, ...patch }
    },

    clearWorkflowContext() {
      this.workflowContext = {
        executionLogId: null,
        executionLogLabel: '',
        scenario: '',
        reportId: null,
        reportHint: '',
      }
    },
  },
})
