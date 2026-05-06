/**
 * 资产中心 · Physical Files ↔ DB 登记的 Mock / 合并逻辑
 *
 * 真实后端可在扫描任务里写入「物理独有文件」，前端仅需合并排序；
 * 本地开发用 MOCK_ORPHANS 模拟「磁盘有、资产表无」的幽灵文件。
 *
 * @module useAssetHubPhysicalScan
 */
import type { AssetHubPlatform } from '@/api/assetHub'

/** 与 AssetHub.vue 中 AssetNodeRow 对齐的最小结构（避免循环依赖可单独引用） */
export interface ScanAssetRow {
  id: string
  backendId?: number
  moduleId: string
  moduleLabel: string
  name: string
  platform?: string
  syncState?: 'registered' | 'pending_init'
  relPath?: string
  [key: string]: unknown
}

/** Mock：模拟物理目录发现但尚未写入 UIScriptUpload 的条目（仅前端演示） */
const MOCK_ORPHANS: Record<
  AssetHubPlatform,
  Array<Pick<ScanAssetRow, 'relPath' | 'name'> & { moduleId?: string; moduleLabel?: string }>
> = {
  web: [
    {
      relPath: '_orphan/ghost_runner.py',
      name: 'ghost_runner.py',
      moduleId: 'proj-mock-orphan',
      moduleLabel: '(物理扫描/Mock) 未挂载工程',
    },
  ],
  mobile: [],
  api: [],
}

/**
 * 合并「服务端返回行」与 Mock 幽灵文件，并打 pending_init。
 * 若 relPath 已在现有 rows 中出现则跳过 Mock，避免重复。
 */
export function mergeRegisteredRowsWithPhysicalMock<T extends ScanAssetRow>(
  serverRows: T[],
  options: { platform: AssetHubPlatform; mockOrphansEnabled?: boolean },
): T[] {
  const { platform, mockOrphansEnabled = import.meta.env.DEV } = options
  const existingRel = new Set(
    serverRows.map((r) => (r.relPath || r.name || '').replace(/\\/g, '/').toLowerCase()),
  )
  const merged = [...serverRows]
  if (!mockOrphansEnabled) return merged

  const orphans = MOCK_ORPHANS[platform] || []
  for (const o of orphans) {
    const key = (o.relPath || o.name).replace(/\\/g, '/').toLowerCase()
    if (existingRel.has(key)) continue
    existingRel.add(key)
    merged.push({
      id: `mock-physical-${platform}-${key.replace(/\//g, '_')}`,
      moduleId: o.moduleId || 'unassigned',
      moduleLabel: o.moduleLabel || '待挂载 Module',
      name: o.name,
      relPath: o.relPath,
      syncState: 'pending_init',
      platform,
      owner: '—',
      lastSuccessRate: 0,
      environment: 'local-disk',
      lastResult: 'unknown',
      isActive: false,
    } as unknown as T)
  }
  return merged
}

/** 待初始化置顶：pending_init 在前，其余保持原有相对顺序（稳定排序） */
export function sortRowsPendingFirst<T extends ScanAssetRow>(rows: T[]): T[] {
  const pending = rows.filter((r) => r.syncState === 'pending_init')
  const rest = rows.filter((r) => r.syncState !== 'pending_init')
  return [...pending, ...rest]
}
