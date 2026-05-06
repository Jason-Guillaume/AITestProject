import type { ComputedRef, Ref } from 'vue'
import type { TreeNodeData, Project } from '@/composables/useImmersiveScriptHubUi'

export type Edition = 'ui' | 'api' | 'perf'

export interface HubTreeNode extends TreeNodeData {
  kind?: string
  scriptKey?: string
  project?: Project
}

/** provide 为普通对象 + Ref / reactive 字段，勿再包一层 reactive，以免丢失 Ref */
export interface ScriptWorkbenchInject {
  edition: Ref<Edition>
  /** Web UI */
  uiTreeKey: Ref<number>
  loadUiTreeNode: (node: { level: number; data: HubTreeNode }, resolve: (data: HubTreeNode[]) => void) => void | Promise<void>
  onUiTreeClick: (data: HubTreeNode) => void
  editorContent: Ref<string>
  editorLanguage: Ref<string>
  editorPath: Ref<string | null>
  editorTitle: Ref<string>
  editorLoading: Ref<boolean>
  canSaveEditor: ComputedRef<boolean>
  saveLoading: Ref<boolean>
  saveEditor: () => void | Promise<void>
  executionConfig: { browser: string; headless: boolean; parallel: number }
  openImport: () => void
  runExecution: () => void | Promise<void>
  stopExecution: () => void | Promise<void>
  stopExecutionLoading: Ref<boolean>
  selectedProject: Ref<Project | null>
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  uiStore: any
  mainTab: Ref<'code' | 'report' | 'terminal'>
  pomLoading: Ref<boolean>
  pomRows: Ref<unknown[]>
  loadPomReports: () => void | Promise<void>
  onPomRowClick: (row: unknown) => void | Promise<void>
  reportIframeUrl: Ref<string | null>
  exportLogs: () => void
  clearLogView: () => void | Promise<void>
  terminalScrollRef: Ref<HTMLElement | null>
  monacoKeyUi: ComputedRef<string>
  /** API */
  apiTreeKey: Ref<number>
  loadApiTreeNode: (node: { level: number; data: HubTreeNode }, resolve: (data: HubTreeNode[]) => void) => void
  onApiTreeClick: (data: HubTreeNode) => void
  apiScripts: Record<string, string>
  selectedApiScriptKey: Ref<string>
  apiLatest: { runAt: string; checksPct: number; p95: number; steps: number; series: number[] }
  apiReportRows: Ref<{ name: string; latency: number; ok: string }[]>
  runApiMock: () => void
  chartApiRef: Ref<HTMLElement | null>
  mockTerminalLines: Ref<string[]>
  /** Performance */
  perfForm: { vus: number; durationSec: number; qpsThreshold: number }
  perfScripts: Record<string, string>
  selectedPerfScriptKey: Ref<string>
  perfLatest: { runAt: string; rps: number; p95ms: number; checksPct: number; series: number[] }
  perfDetailRows: Ref<{ metric: string; value: string }[]>
  runPerfMock: () => void
  chartPerfRef: Ref<HTMLElement | null>
}

export const SCRIPT_WORKBENCH_INJECT = Symbol('scriptWorkbench') as import('vue').InjectionKey<ScriptWorkbenchInject>
