<script setup lang="ts">
/**
 * 资产中心 (Asset Hub) — IDE 向资源管理
 * - 监听 Pinia activePlatform + 本页平台切换，刷新资产
 * - 上传 / 批量删除 / Module 树右键 / 面包屑
 */
import { ref, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ElTableV2, ElAutoResizer } from 'element-plus'
import {
  Search,
  Rank,
  Switch,
  Download,
  Upload,
  Monitor,
  Iphone,
  Link,
  Refresh,
} from '@element-plus/icons-vue'
import { useScriptHubSelectionStore } from '@/stores/scriptHubSelectionStore'
import { useAutomationCenterHubStore } from '@/stores/automationCenterHubStore'
import ExplorerNodeContextMenu from '@/components/explorer/ExplorerNodeContextMenu.vue'
import request from '@/utils/request'
import {
  ASSET_OVERVIEW_NODE_ID,
  createUiScriptUpload,
  getAssetHubOverview,
  postAssetHubSync,
  type AssetHubPlatform,
} from '@/api/assetHub'
import {
  mergeRegisteredRowsWithPhysicalMock,
  sortRowsPendingFirst,
} from '@/composables/useAssetHubPhysicalScan'
import {
  dismissAssetHubRelPaths,
  filterDismissedAssetHubRows,
} from '@/composables/useAssetHubDismissedOrphans'
import UploadDialog, { type UploadFormPayload } from '@/components/asset-hub/UploadDialog.vue'
import CyberStatusChip from '@/components/asset-hub/CyberStatusChip.vue'
import { buildAssetHubV2Columns } from '@/composables/assetHubV2Columns'

type HubPlat = 'web' | 'mobile' | 'api' | 'miniprogram' | 'h5'
type AssetPlat = 'web' | 'mobile' | 'api'

interface ModuleNode {
  id: string
  label: string
  children?: ModuleNode[]
}

interface AssetNodeRow {
  id: string
  /** 后端 UIScriptUpload.id，存在时批量删除走 PATCH 软删 */
  backendId?: number
  moduleId: string
  moduleLabel: string
  name: string
  owner: string
  lastSuccessRate: number
  environment: string
  platform: AssetPlat
  lastResult: 'success' | 'failed' | 'unknown'
  isActive: boolean
  techStack?: 'PYTHON' | 'JAVA'
  architecture?: 'POM' | 'LINEAR' | 'SCRIPT'
  /** 工作区相对路径（物理扫描） */
  relPath?: string
  /** registered：与 DB 入口一致；pending_init：磁盘存在但未登记为入口 */
  syncState?: 'registered' | 'pending_init'
}

function storeToAssetPlat(p: HubPlat): AssetPlat {
  if (p === 'mobile') return 'mobile'
  if (p === 'api') return 'api'
  return 'web'
}

/** 按平台分组的演示数据（后续替换为 fetchNodes({ platform }) ） */
function buildDataset(): Record<AssetPlat, { tree: ModuleNode[]; nodes: AssetNodeRow[] }> {
  return {
    web: {
      tree: [
        { id: ASSET_OVERVIEW_NODE_ID, label: '全部脚本 (总览)', children: [] },
        {
          id: 'mod-regression',
          label: 'Regression',
          children: [
            { id: 'mod-reg-web', label: 'Web · LoginFlow' },
            { id: 'mod-reg-api', label: 'API · Orders' },
          ],
        },
        { id: 'mod-shared', label: 'Shared' },
      ],
      nodes: [
        {
          id: 'web-n1',
          backendId: undefined,
          moduleId: 'mod-reg-web',
          moduleLabel: 'Regression / Web · LoginFlow',
          name: 'login_flow.py',
          owner: 'alice',
          lastSuccessRate: 96,
          environment: 'staging-chrome',
          platform: 'web',
          lastResult: 'success',
          isActive: true,
        },
        {
          id: 'web-n2',
          backendId: undefined,
          moduleId: 'mod-reg-web',
          moduleLabel: 'Regression / Web · LoginFlow',
          name: 'sso_callback.py',
          owner: 'bob',
          lastSuccessRate: 72,
          environment: 'staging-firefox',
          platform: 'web',
          lastResult: 'failed',
          isActive: true,
        },
        {
          id: 'web-n3',
          moduleId: 'mod-shared',
          moduleLabel: 'Shared',
          name: 'common_utils.py',
          owner: 'devops',
          lastSuccessRate: 100,
          environment: 'shared',
          platform: 'web',
          lastResult: 'success',
          isActive: true,
        },
      ],
    },
    mobile: {
      tree: [
        { id: ASSET_OVERVIEW_NODE_ID, label: '全部脚本 (总览)', children: [] },
        {
          id: 'mod-smoke',
          label: 'Smoke',
          children: [{ id: 'mod-smoke-mobile', label: 'Mobile · Health' }],
        },
      ],
      nodes: [
        {
          id: 'mob-n1',
          moduleId: 'mod-smoke-mobile',
          moduleLabel: 'Smoke / Mobile · Health',
          name: 'health_check.py',
          owner: 'carol',
          lastSuccessRate: 88,
          environment: 'device-farm-01',
          platform: 'mobile',
          lastResult: 'success',
          isActive: true,
        },
      ],
    },
    api: {
      tree: [
        { id: ASSET_OVERVIEW_NODE_ID, label: '全部脚本 (总览)', children: [] },
        { id: 'mod-api-root', label: 'API Scenarios' },
      ],
      nodes: [
        {
          id: 'api-n1',
          moduleId: 'mod-api-root',
          moduleLabel: 'API Scenarios',
          name: 'scenario_login.yaml',
          owner: 'alice',
          lastSuccessRate: 91,
          environment: 'mock-server',
          platform: 'api',
          lastResult: 'success',
          isActive: true,
        },
      ],
    },
  }
}

const hubSelection = useScriptHubSelectionStore()
const automationHub = useAutomationCenterHubStore()
const router = useRouter()

/** 列表超过该数量时使用 el-table-v2 虚拟滚动（降低 DOM 压力） */
const ASSET_TABLE_VIRTUAL_MIN = 50
/** 避免 resetAndFetchNodes 同步 assetPlatform 时反向触发 setActivePlatform 造成循环 */
const syncingPlatformFromStore = ref(false)

const moduleTreeData = ref<ModuleNode[]>([])
const allNodes = ref<AssetNodeRow[]>([])
const moduleTreeKey = ref(0)
const pageLoading = ref(false)
const syncLoading = ref(false)

const searchKw = ref('')
const resultFilter = ref<'all' | 'success' | 'failed' | 'unknown'>('all')
const activeModuleId = ref<string>('')
const crumbTrail = ref<{ id: string; label: string }[]>([])

/** 本页平台分段（与 Store 双向同步，解决未挂在 AutomationCenterLayout 时不同步的问题） */
const assetPlatform = ref<AssetPlat>('web')

const tableRef = ref<{ clearSelection: () => void } | null>(null)
/** 与表格多选同步（含 Table V2 复选） */
const selectedIdList = ref<string[]>([])
const selectedRows = computed(() => {
  const set = new Set(selectedIdList.value)
  return allNodes.value.filter((r) => set.has(r.id))
})

function clearTableSelection() {
  selectedIdList.value = []
  tableRef.value?.clearSelection()
}

/** 必须在 applyPlatformDataset 之前声明：immediate watch 会立刻调用 apply，避免 TDZ 报错导致整页白屏 */
const highlightedRowId = ref<string | null>(null)
let highlightClearTimer: ReturnType<typeof setTimeout> | null = null

function rowClassName({ row }: { row: AssetNodeRow }) {
  const cls: string[] = []
  if (row.syncState === 'pending_init') cls.push('asset-hub__row--pending')
  if (selectedIdList.value.includes(row.id)) cls.push('asset-hub__row--selected')
  if (highlightedRowId.value && row.id === highlightedRowId.value) cls.push('asset-hub__row--highlight')
  return cls.join(' ')
}

function flashHighlightRow(id: string) {
  highlightedRowId.value = id
  if (highlightClearTimer) clearTimeout(highlightClearTimer)
  highlightClearTimer = setTimeout(() => {
    highlightedRowId.value = null
    highlightClearTimer = null
  }, 5000)
}

const platformHeadIcon = computed(() => {
  if (assetPlatform.value === 'mobile') return Iphone
  if (assetPlatform.value === 'api') return Link
  return Monitor
})

function deepClone<T>(x: T): T {
  return JSON.parse(JSON.stringify(x)) as T
}

function mapApiRow(r: Record<string, unknown>): AssetNodeRow {
  const plat = (r.platform as string) || 'web'
  const ap: AssetPlat = plat === 'mobile' ? 'mobile' : plat === 'api' ? 'api' : 'web'
  const moduleId = String(r.moduleId ?? '').trim()
  const rawLabel = String(r.moduleLabel ?? '').trim()
  const moduleLabel = moduleId ? rawLabel || moduleId : rawLabel || '未分类'
  return {
    id: String(r.id),
    backendId: r.backendId != null ? Number(r.backendId) : undefined,
    moduleId,
    moduleLabel,
    name: String(r.name ?? ''),
    owner: String(r.owner ?? '—'),
    lastSuccessRate: Number(r.lastSuccessRate) || 0,
    environment: String(r.environment ?? '—'),
    platform: ap,
    lastResult: (r.lastResult as AssetNodeRow['lastResult']) || 'unknown',
    isActive: Boolean(r.isActive),
    techStack: r.techStack as AssetNodeRow['techStack'],
    architecture: r.architecture as AssetNodeRow['architecture'],
    relPath: r.relPath != null ? String(r.relPath) : undefined,
    syncState: (r.syncState as AssetNodeRow['syncState']) || 'registered',
  }
}

/** 与后端 asset_hub_provider 对齐拉取；失败时回落本地演示数据 */
async function loadPlatformData(p: AssetPlat) {
  pageLoading.value = true
  try {
    const data = await getAssetHubOverview(p as AssetHubPlatform)
    if (data?.tree && Array.isArray(data.rows)) {
      moduleTreeData.value = data.tree as ModuleNode[]
      const mapped = data.rows.map((row) => mapApiRow(row as Record<string, unknown>))
      allNodes.value = filterDismissedAssetHubRows(
        mergeRegisteredRowsWithPhysicalMock(mapped, { platform: p as AssetHubPlatform }),
      )
      moduleTreeKey.value += 1
      highlightedRowId.value = null
      clearTableSelection()
      return
    }
  } catch (e) {
    console.warn('[AssetHub] asset_hub_overview 不可用，使用演示数据', e)
  } finally {
    pageLoading.value = false
  }
  const pack = buildDataset()[p]
  moduleTreeData.value = deepClone(pack.tree)
  allNodes.value = filterDismissedAssetHubRows(
    mergeRegisteredRowsWithPhysicalMock(deepClone(pack.nodes), { platform: p as AssetHubPlatform }),
  )
  moduleTreeKey.value += 1
  highlightedRowId.value = null
  clearTableSelection()
}

/**
 * 平台切换后的唯一入口：统一走后端 Shadow Sync 装配结果，并默认「全部脚本 (总览)」。
 */
async function resetAndFetchNodes() {
  const p = storeToAssetPlat(hubSelection.activePlatform)
  syncingPlatformFromStore.value = true
  assetPlatform.value = p
  searchKw.value = ''
  resultFilter.value = 'all'
  await loadPlatformData(p)
  activeModuleId.value = ASSET_OVERVIEW_NODE_ID
  crumbTrail.value = []
  nextTick(() => {
    syncingPlatformFromStore.value = false
  })
}

/** 深度监听全局 activePlatform（含嵌套对象变更时的引用更新） */
watch(
  () => hubSelection.activePlatform,
  () => {
    void resetAndFetchNodes()
  },
  { deep: true, immediate: true },
)

/** 本页 Radio 切换 → 写回 Store → 触发上一 watch 完成同一套 reset */
watch(assetPlatform, (p) => {
  if (syncingPlatformFromStore.value) return
  hubSelection.setActivePlatform(p)
})

const initDialogVisible = ref(false)
const initMode = ref<'create' | 'edit'>('create')
const initEditRow = ref<AssetNodeRow | null>(null)
const initHintRelPath = ref('')
const initSubmitting = ref(false)

function openInitDialog(mode: 'create' | 'edit', row?: AssetNodeRow) {
  initMode.value = mode
  if (mode === 'edit' && row) {
    initEditRow.value = row
    initHintRelPath.value = (row.relPath || row.name || '').replace(/\\/g, '/')
  } else {
    initEditRow.value = null
    initHintRelPath.value = ''
  }
  initDialogVisible.value = true
}

const uploadDialogInitials = computed(() => {
  const r = initEditRow.value
  if (initMode.value === 'edit' && r) {
    const arch = r.architecture
    const designMode: 'POM' | 'LINEAR' = arch === 'POM' ? 'POM' : 'LINEAR'
    return {
      displayName: r.name.replace(/\.(py|yaml|yml|json|jar)$/i, '') || r.name,
      techStack: (r.techStack || 'PYTHON') as 'PYTHON' | 'JAVA',
      designMode,
    }
  }
  return {
    displayName: '',
    techStack: 'PYTHON' as const,
    designMode: 'LINEAR' as const,
  }
})

function formatUiScriptApiError(e: unknown): string {
  const err = e as { response?: { data?: unknown }; message?: string }
  const d = err.response?.data
  if (typeof d === 'string') return d
  if (d && typeof d === 'object') {
    const o = d as Record<string, unknown>
    if (typeof o.error === 'string') return o.error
    if (typeof o.detail === 'string') return o.detail
    return Object.entries(o)
      .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : String(v)}`)
      .join('；')
  }
  return err.message || '请求失败'
}

async function onUploadDialogSubmit(payload: UploadFormPayload) {
  if (initMode.value === 'create') {
    if (!payload.files.length) {
      ElMessage.warning('请上传脚本文件')
      return
    }
    const raw = payload.files[0]

    if (payload.techStack === 'JAVA') {
      ElMessage.warning('Java 请使用左侧「Web UI 工作台」→「导入脚本」上传 JAR/ZIP；成功后返回资产中心点「一键同步」即可看到')
      return
    }

    const lower = raw.name.toLowerCase()
    if (payload.designMode === 'LINEAR' && !lower.endsWith('.py')) {
      ElMessage.warning('线性脚本当前仅支持上传 .py（与后端登记一致）')
      return
    }
    if (payload.designMode === 'POM' && !lower.endsWith('.zip')) {
      ElMessage.warning('POM 模式请上传 .zip 工程包，并填写 ZIP 内执行入口路径')
      return
    }

    const title = payload.displayName.trim() || raw.name.replace(/\.(py|zip)$/i, '')
    const formData = new FormData()
    formData.append('name', title)
    formData.append('script_type', payload.designMode)
    formData.append('language', 'PYTHON')
    formData.append('framework', 'AUTO')
    formData.append(
      'entry_point',
      payload.designMode === 'POM' ? String(payload.pomEntryPath || '').trim() : raw.name,
    )
    formData.append('file_path', raw)

    initSubmitting.value = true
    try {
      await createUiScriptUpload(formData)
      initDialogVisible.value = false
      ElMessage.success('脚本已写入服务端，工作台「我的脚本」可打开执行')
      await loadPlatformData(assetPlatform.value)
      automationHub.bumpExplorerRefresh()
      activeModuleId.value = ASSET_OVERVIEW_NODE_ID
      crumbTrail.value = []
    } catch (e: unknown) {
      ElMessage.error(formatUiScriptApiError(e))
    } finally {
      initSubmitting.value = false
    }
    return
  }

  const row = initEditRow.value
  if (!row) return

  if (row.backendId != null) {
    initSubmitting.value = true
    try {
      const ep = (row.relPath || row.name || '').replace(/^\/+/, '')
      await request.patch(`/assistant/ui-scripts/${row.backendId}/`, {
        name: payload.displayName.trim() || row.name,
        script_type: payload.designMode,
        language: payload.techStack,
        entry_point: ep || row.name,
      })
      initDialogVisible.value = false
      ElMessage.success('已保存，列表与工作台将按数据库刷新')
      await loadPlatformData(assetPlatform.value)
      automationHub.bumpExplorerRefresh()
      await nextTick()
      flashHighlightRow(row.id)
    } catch (e: unknown) {
      ElMessage.error(formatUiScriptApiError(e))
    } finally {
      initSubmitting.value = false
    }
    return
  }

  const idx = allNodes.value.findIndex((n) => n.id === row.id)
  if (idx < 0) {
    initDialogVisible.value = false
    return
  }
  initSubmitting.value = true
  try {
    const raw = payload.files[0]
    let name = payload.displayName.trim()
    if (raw) {
      const pickExt = raw.name.match(/(\.[a-z0-9]+)$/i)?.[0] || ''
      name = pickExt && !name.toLowerCase().endsWith(pickExt.toLowerCase()) ? `${name}${pickExt}` : name
    } else {
      const oldExt = row.name.match(/(\.[a-z0-9]+)$/i)?.[0] || ''
      name = oldExt && !name.toLowerCase().endsWith(oldExt.toLowerCase()) ? `${name}${oldExt}` : name
    }
    const updated: AssetNodeRow = {
      ...row,
      name,
      moduleId: row.moduleId,
      moduleLabel: row.moduleLabel,
      techStack: payload.techStack,
      architecture: payload.designMode,
      syncState: 'registered',
      relPath: raw ? String(raw.name) : row.relPath,
    }
    const next = [...allNodes.value]
    next[idx] = updated
    allNodes.value = next
    initDialogVisible.value = false
    ElMessage.success('已保存（本地演示数据，未关联服务端脚本 ID）')
    automationHub.bumpExplorerRefresh()
    await nextTick()
    flashHighlightRow(row.id)
  } finally {
    initSubmitting.value = false
  }
}

async function onOneClickSync() {
  syncLoading.value = true
  try {
    const res = await postAssetHubSync(assetPlatform.value as AssetHubPlatform)
    ElMessage.success(res?.message || '已同步')
    await loadPlatformData(assetPlatform.value)
    automationHub.bumpExplorerRefresh()
    activeModuleId.value = ASSET_OVERVIEW_NODE_ID
  } catch (e: unknown) {
    const err = e as { message?: string }
    ElMessage.error(err?.message || '同步失败')
  } finally {
    syncLoading.value = false
  }
}

function findPathToNode(nodes: ModuleNode[], targetId: string, path: { id: string; label: string }[] = []): { id: string; label: string }[] | null {
  for (const n of nodes) {
    const next = [...path, { id: n.id, label: n.label }]
    if (n.id === targetId) return next
    if (n.children?.length) {
      const hit = findPathToNode(n.children, targetId, next)
      if (hit) return hit
    }
  }
  return null
}

function onModuleClick(data: ModuleNode) {
  if (data.children?.length) return
  activeModuleId.value = data.id
  if (data.id === ASSET_OVERVIEW_NODE_ID) {
    crumbTrail.value = [{ id: ASSET_OVERVIEW_NODE_ID, label: '全部脚本 (总览)' }]
    return
  }
  const path = findPathToNode(moduleTreeData.value, data.id)
  crumbTrail.value = path || [{ id: data.id, label: data.label }]
}

function onSelectAllModules() {
  activeModuleId.value = ASSET_OVERVIEW_NODE_ID
  crumbTrail.value = []
}

function onCrumbClick(index: number) {
  if (index < 0 || index >= crumbTrail.value.length - 1) {
    onSelectAllModules()
    return
  }
  const seg = crumbTrail.value[index]
  activeModuleId.value = seg.id
  crumbTrail.value = crumbTrail.value.slice(0, index + 1)
}

function resultLabel(r: AssetNodeRow['lastResult']) {
  if (r === 'success') return '成功'
  if (r === 'failed') return '失败'
  return '未知 / 未跑'
}

function platformLabel(p: AssetPlat) {
  if (p === 'web') return 'Web'
  if (p === 'mobile') return 'Mobile'
  return 'API'
}

function syncStateLabel(s?: AssetNodeRow['syncState']) {
  if (s === 'pending_init') return '待初始化'
  return '已就绪'
}

const filteredNodes = computed(() => {
  const kw = searchKw.value.trim().toLowerCase()
  const isOverview =
    !activeModuleId.value || activeModuleId.value === ASSET_OVERVIEW_NODE_ID
  return allNodes.value.filter((row) => {
    if (!isOverview && row.moduleId !== activeModuleId.value) return false
    if (resultFilter.value !== 'all' && row.lastResult !== resultFilter.value) return false
    if (!kw) return true
    const blob = `${row.name} ${row.owner} ${row.environment} ${row.moduleLabel} ${row.relPath || ''}`.toLowerCase()
    return blob.includes(kw)
  })
})

/** 待初始化行置顶（与物理扫描 Mock 结合展示） */
const tableDisplayNodes = computed(() => sortRowsPendingFirst(filteredNodes.value))

const useVirtualTable = computed(() => tableDisplayNodes.value.length >= ASSET_TABLE_VIRTUAL_MIN)

function getV2Columns(tableWidth: number) {
  return buildAssetHubV2Columns(
    {
      selectedIds: () => selectedIdList.value,
      toggleSelect: (id, checked) => {
        const s = new Set(selectedIdList.value)
        if (checked) s.add(id)
        else s.delete(id)
        selectedIdList.value = [...s]
      },
      syncStateLabel,
      resultLabel,
      onInit: (row) => openInitDialog('edit', row as AssetNodeRow),
      onQuickDebug: (row) => void quickDebugWorkbench(row as AssetNodeRow),
      isGhostRunnerRow: (row) => isGhostRunnerRow(row as AssetNodeRow),
    },
    tableWidth,
  )
}

function v2RowClassName({ rowData }: { rowData: AssetNodeRow }) {
  const cls: string[] = ['asset-hub-v2__row']
  if (rowData.syncState === 'pending_init') cls.push('asset-hub-v2__row--pending')
  if (selectedIdList.value.includes(rowData.id)) cls.push('asset-hub-v2__row--selected')
  if (highlightedRowId.value === rowData.id) cls.push('asset-hub-v2__row--highlight')
  return cls.join(' ')
}

function isGhostRunnerRow(row: AssetNodeRow) {
  const p = (row.relPath || row.name || '').replace(/\\/g, '/').toLowerCase()
  return p.includes('ghost_runner.py')
}

async function quickDebugWorkbench(row: AssetNodeRow) {
  const rel = (row.relPath || row.name || '').replace(/\\/g, '/')
  try {
    const { data } = await request.get('/assistant/ui-scripts/', { params: { page_size: 1 } })
    const list = Array.isArray(data) ? data : (data as { results?: unknown[] })?.results ?? []
    const first = list[0] as { id?: string | number } | undefined
    const pid = first?.id
    if (pid != null) {
      await router.push({
        name: 'WebUIScriptWorkbench',
        query: { openProjectId: String(pid), openPath: rel },
      })
      return
    }
  } catch {
    /* 继续仅带路径跳转 */
  }
  await router.push({
    name: 'WebUIScriptWorkbench',
    query: { openPath: rel },
  })
}

watch([searchKw, resultFilter, activeModuleId], () => {
  clearTableSelection()
})

watch(
  tableDisplayNodes,
  () => {
    const allowed = new Set(tableDisplayNodes.value.map((r) => r.id))
    selectedIdList.value = selectedIdList.value.filter((id) => allowed.has(id))
  },
  { deep: true },
)

function onSelectionChange(rows: AssetNodeRow[]) {
  selectedIdList.value = rows.map((r) => r.id)
}

const hasSelection = computed(() => selectedRows.value.length > 0)

async function batchMoveDirectory() {
  if (!selectedRows.value.length) {
    ElMessage.warning('请先勾选要移动的 Node')
    return
  }
  try {
    const { value } = await ElMessageBox.prompt('目标目录（占位）', '批量移动目录', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputPlaceholder: '/Regression/Web',
    })
    ElMessage.success(`已记录将 ${selectedRows.value.length} 个 Node 移至「${value || '/'}」（占位）`)
  } catch {
    /* cancel */
  }
}

async function batchToggleScriptStatus() {
  if (!selectedRows.value.length) {
    ElMessage.warning('请先勾选要修改的 Node')
    return
  }
  const withBackend = selectedRows.value.filter((r) => r.backendId != null)
  const ghostOnly = selectedRows.value.filter((r) => r.backendId == null)
  if (!withBackend.length) {
    ElMessage.warning(
      ghostOnly.length
        ? '当前选中为扫描占位/演示行，无脚本工程 ID。请用「智能上传」登记后启用，或「批量删除」从本页移除'
        : '无可用脚本',
    )
    return
  }
  try {
    await ElMessageBox.confirm(
      `将 ${withBackend.length} 个脚本工程在服务端设为「启用」（is_active=true），以便执行与工作台一致？`,
      '批量启用',
      { type: 'info', confirmButtonText: '启用', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  let ok = 0
  for (const r of withBackend) {
    try {
      await request.patch(`/assistant/ui-scripts/${r.backendId}/`, { is_active: true })
      ok += 1
    } catch {
      /* 单条失败跳过 */
    }
  }
  await loadPlatformData(assetPlatform.value)
  automationHub.bumpExplorerRefresh()
  const extra =
    ghostOnly.length > 0
      ? `；另有 ${ghostOnly.length} 条为占位行未调用接口（可批量删除从列表隐藏）`
      : ''
  ElMessage.success(`已启用 ${ok} 个脚本工程${extra}`)
}

function batchExportPy() {
  if (!selectedRows.value.length) {
    ElMessage.warning('请先勾选要导出的 Node')
    return
  }
  const chunks = selectedRows.value.map(
    (r) => `# --- ${r.name} (module: ${r.moduleLabel}) ---\nprint("${r.id}")\n\n`,
  )
  const blob = new Blob(chunks, { type: 'text/x-python;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `asset-hub-export-${Date.now()}.py`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success(`已导出 ${selectedRows.value.length} 段合并 .py`)
}

async function batchSoftDelete() {
  if (!selectedRows.value.length) {
    ElMessage.warning('请先勾选要删除的 Node')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定将选中的 ${selectedRows.value.length} 个 Node 移入回收站？（软删除）`,
      '批量删除',
      { type: 'warning', confirmButtonText: '移入回收站', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  const dismissPaths: string[] = []
  for (const r of selectedRows.value) {
    if (r.backendId == null) {
      const p = (r.relPath || r.name || '').trim()
      if (p) dismissPaths.push(p)
    }
  }
  if (dismissPaths.length) dismissAssetHubRelPaths(dismissPaths)

  const backendIds = [...new Set(selectedRows.value.map((r) => r.backendId).filter((x): x is number => x != null))]
  let apiOk = 0
  for (const bid of backendIds) {
    try {
      await request.patch(`/assistant/ui-scripts/${bid}/`, { is_deleted: true })
      apiOk += 1
    } catch {
      /* 忽略单条失败 */
    }
  }
  const dropIds = new Set(selectedRows.value.map((r) => r.id))
  const dropBack = new Set(backendIds)
  allNodes.value = allNodes.value.filter((n) => {
    if (dropIds.has(n.id)) return false
    if (n.backendId != null && dropBack.has(n.backendId)) return false
    return true
  })
  clearTableSelection()
  ElMessage.success(`已处理移入回收站（脚本工程 ${apiOk} 个）`)
}

function removeNodeById(list: ModuleNode[], id: string): boolean {
  const i = list.findIndex((n) => n.id === id)
  if (i >= 0) {
    list.splice(i, 1)
    return true
  }
  for (const n of list) {
    if (n.children?.length && removeNodeById(n.children, id)) return true
  }
  return false
}

async function onFolderMenuCommand(cmd: string, data: ModuleNode) {
  if (data.id === ASSET_OVERVIEW_NODE_ID && (cmd === 'new-folder' || cmd === 'rename' || cmd === 'delete')) {
    ElMessage.warning('「全部脚本 (总览)」为虚拟根节点，请在工程节点上操作文件夹')
    return
  }
  if (cmd === 'copy-path') {
    try {
      await navigator.clipboard.writeText(data.id)
      ElMessage.success('已复制路径标识')
    } catch {
      ElMessage.error('复制失败')
    }
    return
  }
  if (cmd === 'new-folder') {
    try {
      const { value } = await ElMessageBox.prompt('新子文件夹名称', '新建子文件夹', {
        confirmButtonText: '创建',
        cancelButtonText: '取消',
        inputPlaceholder: 'NewFolder',
      })
      const name = (value || '').trim()
      if (!name) return
      const nid = `mod-${Date.now()}`
      const child: ModuleNode = { id: nid, label: name }
      if (!data.children) data.children = []
      data.children.push(child)
      moduleTreeKey.value += 1
      ElMessage.success('已添加子文件夹（本地）')
    } catch {
      /* cancel */
    }
    return
  }
  if (cmd === 'rename') {
    try {
      const { value } = await ElMessageBox.prompt('新名称', '重命名文件夹', {
        confirmButtonText: '保存',
        cancelButtonText: '取消',
        inputValue: data.label,
      })
      const name = (value || '').trim()
      if (!name) return
      data.label = name
      moduleTreeKey.value += 1
      ElMessage.success('已重命名（本地）')
    } catch {
      /* cancel */
    }
    return
  }
  if (cmd === 'delete') {
    try {
      await ElMessageBox.confirm(`删除文件夹「${data.label}」？（仅本地演示树）`, '删除文件夹', {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      })
    } catch {
      return
    }
    const root = moduleTreeData.value
    removeNodeById(root, data.id)
    if (activeModuleId.value === data.id) onSelectAllModules()
    moduleTreeKey.value += 1
    ElMessage.success('已删除文件夹（本地）')
  }
}
</script>

<template>
  <div class="asset-hub asset-hub--cyber">
    <header class="asset-hub__header">
      <div class="asset-hub__brand">
        <h1>资产中心 <span class="asset-hub__en">Asset Hub</span></h1>
        <p class="asset-hub__subtitle">数据与执行中心同源（UIScriptUpload + 工作区扫描）· 总览展示当前平台全部脚本</p>
      </div>

      <div class="asset-hub__toolbar-row">
        <div class="asset-hub__group asset-hub__group--filters">
          <el-input
            v-model="searchKw"
            class="asset-hub__search"
            clearable
            placeholder="关键字：名称 / 负责人 / 环境 / 模块"
            :prefix-icon="Search"
          />
          <el-select v-model="resultFilter" class="asset-hub__select" placeholder="上次执行结果">
            <el-option label="全部结果" value="all" />
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failed" />
            <el-option label="未知 / 未跑" value="unknown" />
          </el-select>
        </div>

        <div class="asset-hub__sep" />

        <div class="asset-hub__group asset-hub__group--platform">
          <span class="asset-hub__group-label">平台</span>
          <el-radio-group v-model="assetPlatform" size="small">
            <el-radio-button value="web">Web</el-radio-button>
            <el-radio-button value="mobile">Mobile</el-radio-button>
            <el-radio-button value="api">API</el-radio-button>
          </el-radio-group>
        </div>

        <div class="asset-hub__sep" />

        <div class="asset-hub__group asset-hub__group--upload">
          <span class="asset-hub__group-label">上传</span>
          <el-button type="primary" size="small" :icon="Upload" @click="openInitDialog('create')">智能上传</el-button>
        </div>

        <div class="asset-hub__sep" />

        <div class="asset-hub__group asset-hub__group--sync">
          <span class="asset-hub__group-label">同步</span>
          <el-button size="small" type="success" plain :icon="Refresh" :loading="syncLoading" @click="onOneClickSync">
            一键同步
          </el-button>
        </div>

        <div class="asset-hub__sep" />

        <div class="asset-hub__group asset-hub__group--batch">
          <span class="asset-hub__group-label">批量</span>
          <el-button :icon="Rank" size="small" :disabled="!hasSelection" @click="batchMoveDirectory">移动目录</el-button>
          <el-button :icon="Switch" size="small" :disabled="!hasSelection" @click="batchToggleScriptStatus">批量启用</el-button>
          <el-button :icon="Download" type="primary" size="small" plain :disabled="!hasSelection" @click="batchExportPy">
            导出 .py
          </el-button>
          <el-button
            type="danger"
            size="small"
            class="asset-hub__btn-bulk-delete"
            :disabled="!hasSelection"
            @click="batchSoftDelete"
          >
            批量删除
          </el-button>
        </div>
      </div>
    </header>

    <div v-loading="pageLoading" class="asset-hub__wide">
      <aside class="asset-hub__modules" aria-label="Module 树">
        <div class="asset-hub__modules-head">
          <el-icon class="asset-hub__plat-ico"><component :is="platformHeadIcon" /></el-icon>
          <span>Module</span>
          <el-tag size="small" type="info">{{ platformLabel(assetPlatform) }}</el-tag>
        </div>
        <el-button text type="primary" class="asset-hub__all-modules" @click="onSelectAllModules">
          全部脚本 (总览)
        </el-button>
        <el-tree
          :key="moduleTreeKey"
          :data="moduleTreeData"
          node-key="id"
          default-expand-all
          highlight-current
          :current-node-key="activeModuleId || undefined"
          @node-click="onModuleClick"
        >
          <template #default="{ data }">
            <ExplorerNodeContextMenu
              variant="folder"
              :disable-copy-path="!data?.id"
              :disable-new="data?.id === ASSET_OVERVIEW_NODE_ID"
              :disable-rename="data?.id === ASSET_OVERVIEW_NODE_ID"
              :disable-delete="data?.id === ASSET_OVERVIEW_NODE_ID"
              @command="(c: string) => onFolderMenuCommand(c, data)"
            >
              <span class="asset-hub__tree-label">{{ data.label }}</span>
            </ExplorerNodeContextMenu>
          </template>
        </el-tree>
      </aside>

      <section class="asset-hub__detail">
        <el-breadcrumb separator=">" class="asset-hub__breadcrumb">
          <el-breadcrumb-item>
            <a href="javascript:;" @click.prevent="onSelectAllModules">根</a>
          </el-breadcrumb-item>
          <el-breadcrumb-item v-for="(c, i) in crumbTrail" :key="c.id">
            <a href="javascript:;" @click.prevent="onCrumbClick(i)">{{ c.label }}</a>
          </el-breadcrumb-item>
        </el-breadcrumb>

        <div class="asset-hub__detail-head">
          <span class="asset-hub__detail-title">Node 列表</span>
          <div class="asset-hub__detail-actions">
            <el-button
              size="small"
              type="success"
              plain
              :icon="Refresh"
              :loading="syncLoading"
              @click="onOneClickSync"
            >
              一键同步物理文件
            </el-button>
            <el-button size="small" :icon="Rank" :disabled="!hasSelection" @click="batchMoveDirectory">批量移动目录</el-button>
            <el-button type="danger" size="small" plain :disabled="!hasSelection" @click="batchSoftDelete">
              批量删除
            </el-button>
          </div>
        </div>

        <div class="asset-hub__table-shell">
          <el-auto-resizer v-if="useVirtualTable" class="asset-hub__table-v2-wrap">
            <template #default="{ height, width }">
              <el-table-v2
                v-if="width > 8"
                :key="width"
                :columns="getV2Columns(width)"
                :data="tableDisplayNodes"
                :width="width"
                :height="height"
                :row-height="52"
                :header-height="40"
                row-key="id"
                :row-class="v2RowClassName"
                class="asset-hub__table-v2"
                fixed
              />
            </template>
          </el-auto-resizer>
        <el-table
          v-else
          ref="tableRef"
          :data="tableDisplayNodes"
          row-key="id"
          height="100%"
          style="width: 100%"
          class="asset-hub__table asset-hub__table--cyber"
          :row-class-name="rowClassName"
          @selection-change="onSelectionChange"
        >
          <el-table-column type="selection" width="48" fixed />
          <el-table-column label="Node / 脚本" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <div class="asset-hub__node-cell">
                <span class="asset-hub__node-name">{{ row.name }}</span>
                <span class="asset-hub__node-path">{{ row.relPath || '—' }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="同步状态" width="128" align="left">
            <template #default="{ row }">
              <CyberStatusChip
                :variant="row.syncState === 'pending_init' ? 'sync-pending' : 'sync-ready'"
                :label="syncStateLabel(row.syncState)"
              />
            </template>
          </el-table-column>
          <el-table-column prop="owner" label="负责人" width="100" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="asset-hub__cell-mono">{{ row.owner }}</span>
            </template>
          </el-table-column>
          <el-table-column label="上次成功率" width="120">
            <template #default="{ row }">
              <el-progress
                :percentage="row.lastSuccessRate"
                :stroke-width="10"
                :status="row.lastSuccessRate >= 90 ? 'success' : undefined"
              />
            </template>
          </el-table-column>
          <el-table-column label="最近执行" width="118" align="left">
            <template #default="{ row }">
              <CyberStatusChip
                :variant="
                  row.lastResult === 'success'
                    ? 'exec-success'
                    : row.lastResult === 'failed'
                      ? 'exec-failed'
                      : 'exec-unknown'
                "
                :label="resultLabel(row.lastResult)"
              />
            </template>
          </el-table-column>
          <el-table-column label="运行状态" width="96" align="left">
            <template #default="{ row }">
              <CyberStatusChip
                :variant="row.isActive ? 'run-on' : 'run-off'"
                :label="row.isActive ? '启用' : '停用'"
              />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="168" fixed="right" align="left">
            <template #default="{ row }">
              <span class="asset-hub__ops">
                <el-button
                  v-if="row.syncState === 'pending_init'"
                  link
                  type="warning"
                  size="small"
                  @click="openInitDialog('edit', row)"
                >
                  初始化
                </el-button>
                <el-button
                  v-if="isGhostRunnerRow(row)"
                  link
                  type="primary"
                  size="small"
                  class="asset-hub__quick-debug-btn"
                  @click="quickDebugWorkbench(row)"
                >
                  ⚡ 快速调试
                </el-button>
                <span v-if="row.syncState !== 'pending_init' && !isGhostRunnerRow(row)" class="asset-hub__op-placeholder"
                  >—</span
                >
              </span>
            </template>
          </el-table-column>
        </el-table>
        </div>
      </section>
    </div>

    <UploadDialog
      :key="`${initMode}-${initEditRow?.id ?? 'new'}`"
      v-model="initDialogVisible"
      :mode="initMode"
      :initial-display-name="uploadDialogInitials.displayName"
      :initial-tech-stack="uploadDialogInitials.techStack"
      :initial-design-mode="uploadDialogInitials.designMode"
      :hint-rel-path="initHintRelPath"
      :submit-loading="initSubmitting"
      @submit="onUploadDialogSubmit"
    />
  </div>
</template>

<style scoped>
.asset-hub {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  min-height: 480px;
  padding: 10px 14px 14px;
  box-sizing: border-box;
}

.asset-hub__header {
  flex: none;
  margin-bottom: 10px;
}

.asset-hub__brand h1 {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 600;
}

.asset-hub__en {
  font-size: 0.82rem;
  font-weight: 400;
  opacity: 0.75;
  margin-left: 6px;
}

.asset-hub__subtitle {
  margin: 4px 0 0;
  font-size: 12px;
  opacity: 0.72;
}

.asset-hub__toolbar-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 12px;
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--el-border-color);
  background: var(--el-fill-color-light);
}

.asset-hub__group {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.asset-hub__group-label {
  font-size: 12px;
  font-weight: 600;
  opacity: 0.75;
  margin-right: 2px;
}

.asset-hub__search {
  width: min(280px, 42vw);
  min-width: 160px;
}

.asset-hub__select {
  width: 140px;
}

.asset-hub__sep {
  width: 1px;
  height: 28px;
  background: var(--el-border-color);
  flex: none;
}

.asset-hub__upload :deep(.el-upload-dragger) {
  padding: 8px 12px;
  height: auto;
  min-height: 0;
}

.asset-hub__upload-icon {
  font-size: 18px;
}

.asset-hub__upload-text {
  font-size: 11px;
  margin-top: 2px;
  line-height: 1.2;
}

.asset-hub__btn-bulk-delete {
  font-weight: 600;
}

.asset-hub__wide {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 10px;
}

.asset-hub__modules {
  flex: 0 0 268px;
  display: flex;
  flex-direction: column;
  min-width: 200px;
  border: 1px solid var(--el-border-color);
  border-radius: 10px;
  padding: 8px;
  background: var(--el-fill-color-blank);
}

.asset-hub__modules-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 13px;
  padding: 2px 4px 8px;
}

.asset-hub__plat-ico {
  font-size: 18px;
  color: var(--el-color-primary);
}

.asset-hub__all-modules {
  justify-content: flex-start;
  margin-bottom: 6px;
}

.asset-hub__modules :deep(.el-tree) {
  flex: 1;
  overflow: auto;
}

.asset-hub__tree-label {
  flex: 1;
  min-width: 0;
}

.asset-hub__breadcrumb {
  margin-bottom: 8px;
  font-size: 13px;
}

.asset-hub__breadcrumb a {
  color: var(--el-color-primary);
  text-decoration: none;
}
.asset-hub__breadcrumb a:hover {
  text-decoration: underline;
}

.asset-hub--cyber .asset-hub__detail {
  border: 1px solid rgba(0, 243, 255, 0.2);
  background: linear-gradient(160deg, rgba(12, 16, 24, 0.95) 0%, rgba(8, 10, 18, 0.98) 100%);
  box-shadow: 0 0 32px rgba(0, 0, 0, 0.4);
}

.asset-hub__detail {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--el-border-color);
  border-radius: 10px;
  padding: 10px;
  background: var(--el-fill-color-blank);
}

.asset-hub__detail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.asset-hub__detail-title {
  font-size: 13px;
  font-weight: 600;
}

.asset-hub__detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.asset-hub__table-shell {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border-radius: 10px;
  overflow: hidden;
  background: rgba(16, 18, 23, 0.7);
  -webkit-backdrop-filter: blur(15px);
  backdrop-filter: blur(15px);
  transform: translateZ(0);
}

/* 禁止主表格区域横向滚动与横向滚动条 */
.asset-hub__table-shell :deep(.el-table__body-wrapper),
.asset-hub__table-shell :deep(.el-scrollbar__wrap) {
  overflow-x: hidden !important;
}

.asset-hub__table-shell :deep(.el-scrollbar__bar.is-horizontal) {
  display: none !important;
  height: 0 !important;
}

.asset-hub__table-shell ::-webkit-scrollbar:horizontal {
  height: 0;
}

.asset-hub__table-shell :deep(*::-webkit-scrollbar:horizontal) {
  height: 0;
}

.asset-hub__table-v2-wrap {
  flex: 1;
  min-width: 0;
  min-height: 200px;
}

.asset-hub__table {
  flex: 1;
  min-height: 200px;
}

:deep(.asset-hub__table--cyber.el-table) {
  --el-table-border-color: transparent;
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(12, 14, 18, 0.55);
  background: transparent;
  border: none;
  table-layout: fixed;
  width: 100% !important;
}

:deep(.asset-hub__table--cyber .el-table__body .el-table__cell) {
  vertical-align: middle;
}

:deep(.asset-hub__table--cyber.el-table--border::after),
:deep(.asset-hub__table--cyber.el-table--border::before),
:deep(.asset-hub__table--cyber.el-table__inner-wrapper::before) {
  display: none;
}

:deep(.asset-hub__table--cyber .el-table__cell) {
  border: none !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
}

:deep(.asset-hub__table--cyber thead th.el-table__cell) {
  border: none !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
}

:deep(.asset-hub__table--cyber .el-table__body tr) {
  transform: translateZ(0);
  transition:
    background 0.2s ease,
    box-shadow 0.22s ease;
}

:deep(.asset-hub__table--cyber .el-table__body tr:hover > td) {
  background: rgba(139, 92, 246, 0.05) !important;
  box-shadow: inset 0 0 42px rgba(139, 92, 246, 0.09) !important;
}

:deep(.asset-hub__table--cyber .el-table__body tr:hover > td:first-child) {
  box-shadow:
    inset 3px 0 0 0 #00e5ff,
    inset 0 0 42px rgba(139, 92, 246, 0.09) !important;
}

:deep(.asset-hub__table--cyber .asset-hub__row--selected > td) {
  background: rgba(0, 243, 255, 0.07) !important;
  box-shadow: inset 3px 0 0 0 rgba(0, 229, 255, 0.75) !important;
}

:deep(.asset-hub__table .asset-hub__row--highlight > td) {
  background-color: rgba(0, 229, 255, 0.1) !important;
}

:deep(.asset-hub__table .asset-hub__row--pending > td) {
  background-color: rgba(255, 152, 0, 0.08) !important;
}

.asset-hub__op-placeholder {
  font-size: 12px;
  opacity: 0.45;
}

.asset-hub__ops {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.asset-hub-upload-dialog__inner {
  padding-right: 4px;
}

.asset-hub-upload-dialog__hint {
  margin: 0 0 14px;
  font-size: 12px;
  line-height: 1.5;
  opacity: 0.82;
  color: var(--el-text-color-secondary);
}

.asset-hub-upload-dialog__drop :deep(.el-upload-dragger) {
  border-radius: 10px;
  border-style: dashed;
  border-color: rgba(0, 229, 255, 0.35);
  background: rgba(0, 229, 255, 0.04);
}

.asset-hub-upload-dialog__drop-icon {
  font-size: 36px;
  color: var(--el-color-primary);
  margin-bottom: 8px;
}

.asset-hub-upload-dialog__drop-title {
  font-size: 13px;
  font-weight: 600;
}

.asset-hub-upload-dialog__drop-sub {
  margin-top: 6px;
  font-size: 11px;
  opacity: 0.75;
}
</style>

<style>
/* Teleport 遮罩：毛玻璃（未加 scoped，否则无法作用到 body 下 overlay） */
.asset-hub-upload-overlay {
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  background: rgba(6, 12, 22, 0.48) !important;
}

.asset-hub-upload-dialog.el-dialog {
  border: 1px solid rgba(0, 229, 255, 0.35);
  border-radius: 12px;
  background: linear-gradient(160deg, rgba(18, 28, 42, 0.96) 0%, rgba(10, 16, 28, 0.98) 100%);
  box-shadow:
    0 0 0 1px rgba(0, 229, 255, 0.12),
    0 0 28px rgba(0, 229, 255, 0.22),
    0 16px 48px rgba(0, 0, 0, 0.55);
}

.asset-hub-upload-dialog .el-dialog__header {
  border-bottom: 1px solid rgba(0, 229, 255, 0.18);
  padding-bottom: 12px;
}

.asset-hub-upload-dialog .el-dialog__title {
  font-weight: 600;
  letter-spacing: 0.02em;
}

/* 等宽字体：路径与平台等（虚拟表 + 普通表共用） */
.asset-hub .asset-hub__cell-mono {
  font-family: ui-monospace, 'JetBrains Mono', 'Monaco', 'Consolas', monospace;
  font-size: 12px;
  letter-spacing: 0.02em;
  color: rgba(226, 232, 240, 0.92);
}

.asset-hub .asset-hub__node-cell {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  padding: 2px 0;
}

.asset-hub .asset-hub__node-name {
  font-family: ui-monospace, 'JetBrains Mono', 'Monaco', 'Consolas', monospace;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: rgba(226, 232, 240, 0.95);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.asset-hub .asset-hub__node-path {
  font-family: ui-monospace, 'JetBrains Mono', 'Monaco', 'Consolas', monospace;
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.03em;
  color: rgba(148, 163, 184, 0.72);
  line-height: 1.25;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Table V2 · 赛博行样式（非 scoped，穿透虚拟表格 DOM） */
.asset-hub .asset-hub__table-v2.el-table-v2 {
  font-size: 13px;
  --el-bg-color: transparent;
  background: transparent !important;
}

.asset-hub .asset-hub__table-v2 .el-table-v2__header-row {
  background: rgba(12, 14, 18, 0.55) !important;
}

.asset-hub .asset-hub__table-v2 .el-table-v2__header-cell {
  color: rgba(200, 245, 255, 0.88);
  border: none !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
}

.asset-hub .asset-hub__table-v2 .el-table-v2__row {
  transform: translateZ(0);
  transition:
    background 0.2s ease,
    box-shadow 0.22s ease;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.asset-hub .asset-hub__table-v2-wrap {
  overflow-x: hidden;
}

.asset-hub .asset-hub__table-v2-wrap :deep(.el-scrollbar__bar.is-horizontal) {
  display: none !important;
  height: 0 !important;
}

.asset-hub .asset-hub__table-v2-wrap :deep(.el-scrollbar__wrap) {
  overflow-x: hidden !important;
}

.asset-hub .asset-hub__table-v2 .el-table-v2__row-cell {
  border: none !important;
  box-shadow: none !important;
}

.asset-hub .asset-hub__table-v2 .el-table-v2__row:hover {
  background:
    linear-gradient(90deg, #00e5ff 0, #00e5ff 3px, transparent 3px) no-repeat,
    rgba(139, 92, 246, 0.055) !important;
  box-shadow: inset 0 0 44px rgba(139, 92, 246, 0.09);
}

.asset-hub .asset-hub-v2__row--pending .el-table-v2__row-cell {
  background: rgba(255, 152, 0, 0.07) !important;
}

.asset-hub .asset-hub-v2__row--selected .el-table-v2__row-cell {
  background: rgba(0, 243, 255, 0.07) !important;
  box-shadow: inset 3px 0 0 0 rgba(0, 229, 255, 0.75) !important;
}

.asset-hub .asset-hub-v2__row--highlight .el-table-v2__row-cell {
  background: rgba(0, 229, 255, 0.1) !important;
}
</style>
