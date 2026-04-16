import { defineStore } from 'pinia'

export const KNOWLEDGE_PURPOSE_TABS = [
  { label: '全部文档', value: 'all' },
  { label: '需求文档', value: 'requirement' },
  { label: '规范标准', value: 'standard' },
  { label: '报告/计划模版', value: 'template' },
]

const DEFAULT_COUNTS = { all: 0, requirement: 0, standard: 0, template: 0 }

function normalizePurpose(value) {
  const v = String(value || '').trim()
  if (!v) return 'all'
  if (KNOWLEDGE_PURPOSE_TABS.some((x) => x.value === v)) return v
  return 'all'
}

function normalizeCounts(counts) {
  const raw = counts && typeof counts === 'object' ? counts : {}
  return {
    all: Number(raw.all ?? 0),
    requirement: Number(raw.requirement ?? 0),
    standard: Number(raw.standard ?? 0),
    template: Number(raw.template ?? 0),
  }
}

export const useKnowledgeUiStore = defineStore('knowledgeUi', {
  state: () => ({
    activePurpose: 'all',
    purposeCounts: { ...DEFAULT_COUNTS },
  }),
  actions: {
    setActivePurpose(purpose) {
      this.activePurpose = normalizePurpose(purpose)
    },
    setPurposeCounts(counts) {
      this.purposeCounts = normalizeCounts(counts)
    },
  },
})

