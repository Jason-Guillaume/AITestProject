/**
 * 资产中心：用户从列表移除的「无 backendId」占位行（如 DEV Mock 幽灵文件），
 * 避免刷新/同步后再次合并出现。
 */
const STORAGE_KEY = 'asset-hub-dismissed-relpaths'

function normRel(p: string) {
  return p.replace(/\\/g, '/').trim().toLowerCase()
}

export function getDismissedRelPathSet(): Set<string> {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return new Set()
    const arr = JSON.parse(raw) as string[]
    return new Set(arr.map(normRel).filter(Boolean))
  } catch {
    return new Set()
  }
}

function saveSet(set: Set<string>) {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify([...set]))
}

/** 记录一批相对路径，合并 Mock 时会跳过 */
export function dismissAssetHubRelPaths(paths: string[]) {
  const set = getDismissedRelPathSet()
  for (const p of paths) {
    const k = normRel(p)
    if (k) set.add(k)
  }
  saveSet(set)
}

/** 过滤掉已被用户 dismiss 的行（按 relPath / name 匹配） */
export function filterDismissedAssetHubRows<T extends { relPath?: string; name?: string }>(rows: T[]): T[] {
  const dismissed = getDismissedRelPathSet()
  return rows.filter((r) => {
    const key = normRel((r.relPath || r.name || '').trim())
    if (!key) return true
    return !dismissed.has(key)
  })
}
