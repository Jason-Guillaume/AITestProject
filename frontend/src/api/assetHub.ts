/**
 * 资产中心统一数据源（与后端 assistant.services.asset_hub_provider 对齐）。
 * 执行中心 Node 树使用的项目列表同源：UIScriptUpload + workspace 扫描。
 */
import request from '@/utils/request'

export const ASSET_OVERVIEW_NODE_ID = '__asset_overview__'

export type AssetHubPlatform = 'web' | 'mobile' | 'api'

export interface AssetHubOverviewPayload {
  platform: string
  tree: unknown[]
  rows: Record<string, unknown>[]
  scanned_projects?: number
}

export async function getAssetHubOverview(platform: AssetHubPlatform) {
  const { data } = await request.get<AssetHubOverviewPayload>('/assistant/ui-scripts/asset_hub_overview/', {
    params: { platform },
  })
  return data
}

export async function postAssetHubSync(platform: AssetHubPlatform) {
  const { data } = await request.post<AssetHubOverviewPayload & { sync?: boolean; message?: string }>(
    '/assistant/ui-scripts/asset_hub_sync/',
    { platform },
  )
  return data
}

/** 与 Web UI 工作台「导入脚本」相同：multipart 创建 UIScriptUpload 并落盘工作区 */
export async function createUiScriptUpload(formData: FormData) {
  const { data } = await request.post<Record<string, unknown>>('/assistant/ui-scripts/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}
