import type { Project } from '@/composables/useImmersiveScriptHubUi'
import { mapScriptRow } from '@/composables/useImmersiveScriptHubUi'
import request from '@/utils/request'

export type ScriptHubEdition = 'ui' | 'api' | 'perf'

export interface HubTreeNode {
  id: string
  label: string
  /** Web UI workspace */
  kind?:
    | 'project'
    | 'dir'
    | 'file'
    | 'online'
    | 'api-group'
    | 'api-case'
    | 'perf-root'
    | 'perf-script'
    | 'mobile-placeholder'
  projectId?: string
  /** 工作区内相对路径（正斜杠） */
  relPath?: string
  /** API / Performance 叶子业务键 */
  scriptKey?: string
  isLeaf?: boolean
  project?: Project
}

const workspaceFilesCache = new Map<string, string[]>()

function normalizePath(p: string) {
  return p.replace(/\\/g, '/').replace(/^\/+/, '')
}

/** 仅展开一层：从扁平 files 列表推导直接子节点，避免一次性挂载整棵 trie */
function childrenFromWorkspaceFiles(files: string[], projectId: string, prefix: string): HubTreeNode[] {
  const normalized = files.map(normalizePath).filter(Boolean)
  const pfx = normalizePath(prefix).replace(/\/+$/, '')

  const meta = new Map<string, { hasNested: boolean; exactFile: boolean }>()

  for (const f of normalized) {
    let rel: string
    if (!pfx) {
      if (!f.includes('/')) {
        rel = f
      } else {
        rel = f
      }
    } else {
      if (f === pfx) continue
      if (!f.startsWith(pfx + '/')) continue
      rel = f.slice(pfx.length + 1)
    }

    const parts = rel.split('/').filter(Boolean)
    if (parts.length === 0) continue

    const head = parts[0]
    const rest = parts.length > 1
    const m = meta.get(head) || { hasNested: false, exactFile: false }
    if (rest) m.hasNested = true
    else m.exactFile = true
    meta.set(head, m)
  }

  const entries = [...meta.entries()].sort(([a], [b]) => a.localeCompare(b))

  return entries.map(([name, m]) => {
    const pathFull = pfx ? `${pfx}/${name}` : name
    const hasDirUnder = normalized.some((f) => f.startsWith(pathFull + '/'))
    const isDir = m.hasNested || hasDirUnder
    const isLeaf = !isDir && m.exactFile

    return {
      id: `${isLeaf ? 'f' : 'd'}-${projectId}-${pathFull}`,
      label: name,
      projectId,
      relPath: pathFull,
      kind: isLeaf ? 'file' : 'dir',
      isLeaf,
    }
  })
}

export function selectionIdForNode(edition: ScriptHubEdition, data: HubTreeNode): string | null {
  if (edition === 'ui') {
    if (data.kind === 'project' && data.projectId) return `ui:project:${data.projectId}`
    if (data.kind === 'online' && data.projectId) return `ui:online:${data.projectId}`
    if (data.kind === 'file' && data.projectId && data.relPath) return `ui:file:${data.projectId}:${data.relPath}`
    if (data.kind === 'dir' && data.projectId && data.relPath) return `ui:dir:${data.projectId}:${data.relPath}`
    return null
  }
  if (edition === 'api') {
    if (data.scriptKey) return data.scriptKey
    return null
  }
  if (edition === 'perf') {
    if (data.scriptKey) return data.scriptKey
    return null
  }
  return null
}

/** 与资产中心 asset_hub_overview 同源：均基于 UIScriptUpload 活动记录 */
async function loadProjectsForTree(): Promise<Project[]> {
  const { data } = await request.get('/assistant/ui-scripts/', { params: { show_deleted: false } })
  const scripts = Array.isArray(data) ? data : (data as { results?: unknown[] }).results || []
  return scripts.map((row: unknown) => mapScriptRow(row as Record<string, unknown>))
}

export function createScriptHubTreeLoader(
  edition: ScriptHubEdition,
  onSelect: (id: string | null) => void,
) {
  async function loadUiTreeNode(
    node: { level: number; data: HubTreeNode },
    resolve: (data: HubTreeNode[]) => void,
  ) {
    if (node.level === 0) {
      try {
        const projects = await loadProjectsForTree()
        resolve(
          projects.map((p) => ({
            id: `proj-${p.id}`,
            label: `${p.name} · ${p.type}`,
            kind: 'project' as const,
            projectId: p.id,
            project: p,
            isLeaf: false,
          })),
        )
      } catch (e) {
        console.warn('[ScriptHub] 加载脚本列表失败', e)
        resolve([])
      }
      return
    }

    const d = node.data
    if (d?.kind === 'project' && d.projectId) {
      try {
        const { data: wi } = await request.get(`/assistant/ui-scripts/${d.projectId}/workspace_info/`)
        const files: string[] = (wi as { files?: string[] }).files || []
        workspaceFilesCache.set(String(d.projectId), files)
        if (!files.length) {
          resolve([
            {
              id: `online-${d.projectId}`,
              label: '脚本内容（入口 / 在线）',
              kind: 'online' as const,
              projectId: d.projectId,
              isLeaf: true,
            },
          ])
          return
        }
        resolve(childrenFromWorkspaceFiles(files, d.projectId, ''))
      } catch (e) {
        console.warn('[ScriptHub] workspace_info 失败', e)
        resolve([
          {
            id: `online-${d.projectId}`,
            label: '脚本内容（入口 / 在线）',
            kind: 'online' as const,
            projectId: d.projectId,
            isLeaf: true,
          },
        ])
      }
      return
    }

    if (d?.kind === 'dir' && d.projectId && d.relPath != null) {
      const files = workspaceFilesCache.get(String(d.projectId)) || []
      resolve(childrenFromWorkspaceFiles(files, d.projectId, d.relPath))
      return
    }

    resolve([])
  }

  function loadApiTreeNode(
    treeNode: { level: number; data: HubTreeNode },
    resolve: (data: HubTreeNode[]) => void,
  ) {
    if (treeNode.level === 0) {
      resolve([
        {
          id: 'api-root',
          label: '接口场景库',
          kind: 'api-group',
          isLeaf: false,
        },
      ])
      return
    }
    const d = treeNode.data
    if (d.id === 'api-root') {
      resolve([
        { id: 'api-gr-reg', label: 'Regression', kind: 'api-group', isLeaf: false },
        { id: 'api-gr-smoke', label: 'Smoke', kind: 'api-group', isLeaf: false },
      ])
      return
    }
    if (d.id === 'api-gr-reg') {
      resolve([
        {
          id: 'api-case-reg-login',
          label: 'scenario_login.yaml',
          kind: 'api-case',
          scriptKey: 'api:regression:login',
          isLeaf: true,
        },
        {
          id: 'api-case-reg-order',
          label: 'scenario_order.yaml',
          kind: 'api-case',
          scriptKey: 'api:regression:order',
          isLeaf: true,
        },
      ])
      return
    }
    if (d.id === 'api-gr-smoke') {
      resolve([
        {
          id: 'api-case-smoke-health',
          label: 'health_check.yaml',
          kind: 'api-case',
          scriptKey: 'api:smoke:health',
          isLeaf: true,
        },
      ])
      return
    }
    resolve([])
  }

  function loadPerfTreeNode(
    treeNode: { level: number; data: HubTreeNode },
    resolve: (data: HubTreeNode[]) => void,
  ) {
    if (treeNode.level === 0) {
      resolve([
        {
          id: 'perf-root',
          label: 'k6 压测脚本',
          kind: 'perf-root',
          isLeaf: false,
        },
      ])
      return
    }
    const d = treeNode.data
    if (d.id === 'perf-root') {
      resolve([
        {
          id: 'perf-smoke',
          label: 'smoke.js',
          kind: 'perf-script',
          scriptKey: 'perf:smoke',
          isLeaf: true,
        },
        {
          id: 'perf-load',
          label: 'load.js',
          kind: 'perf-script',
          scriptKey: 'perf:load',
          isLeaf: true,
        },
      ])
      return
    }
    resolve([])
  }

  function onNodeClick(_evt: unknown, data: HubTreeNode) {
    const id = selectionIdForNode(edition, data)
    if (id != null) onSelect(id)
  }

  const treeProps = {
    label: 'label',
    children: 'children',
    isLeaf: 'isLeaf',
  } as const

  const load =
    edition === 'ui'
      ? loadUiTreeNode
      : edition === 'api'
        ? loadApiTreeNode
        : loadPerfTreeNode

  return { load, onNodeClick, treeProps }
}
