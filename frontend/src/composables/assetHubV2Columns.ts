/**
 * Asset Hub · el-table-v2 列定义（大数据集虚拟滚动）
 */
import type { Column } from 'element-plus'
import { h } from 'vue'
import { ElButton, ElCheckbox, ElProgress } from 'element-plus'
import CyberStatusChip from '@/components/asset-hub/CyberStatusChip.vue'
import type { CyberStatusVariant } from '@/components/asset-hub/cyberStatusTypes'

/** 除「Node/路径」外各列固定宽度之和，须与 el-table 列宽一致 */
export const ASSET_HUB_V2_FIXED_WIDTH_SUM =
  48 + 128 + 100 + 120 + 118 + 96 + 168

export interface AssetHubV2Row {
  id: string
  name: string
  relPath?: string
  moduleLabel: string
  owner: string
  lastSuccessRate: number
  environment: string
  platform: string
  lastResult: 'success' | 'failed' | 'unknown'
  isActive: boolean
  syncState?: 'registered' | 'pending_init'
}

export interface AssetHubV2ColumnCtx {
  selectedIds: () => string[]
  toggleSelect: (id: string, checked: boolean) => void
  syncStateLabel: (s?: AssetHubV2Row['syncState']) => string
  resultLabel: (r: AssetHubV2Row['lastResult']) => string
  onInit: (row: AssetHubV2Row) => void
  onQuickDebug: (row: AssetHubV2Row) => void
  isGhostRunnerRow: (row: AssetHubV2Row) => boolean
}

function nodePathCell(rowData: AssetHubV2Row) {
  const path = rowData.relPath?.trim() || '—'
  return h('div', { class: 'asset-hub__node-cell' }, [
    h('span', { class: 'asset-hub__node-name' }, rowData.name),
    h('span', { class: 'asset-hub__node-path' }, path),
  ])
}

export function buildAssetHubV2Columns(
  ctx: AssetHubV2ColumnCtx,
  tableInnerWidth: number,
): Column<AssetHubV2Row>[] {
  const tw = Math.max(0, Math.floor(tableInnerWidth))
  /** 列宽总和须等于 el-table-v2 的 width，避免横向滚动 */
  const nodeW = Math.max(0, tw - ASSET_HUB_V2_FIXED_WIDTH_SUM)

  const sel = (): Column<AssetHubV2Row> => ({
    key: '__sel',
    width: 48,
    title: '',
    headerClass: 'asset-hub-v2__col-sel',
    cellRenderer: ({ rowData }) =>
      h(ElCheckbox, {
        modelValue: ctx.selectedIds().includes(rowData.id),
        'onUpdate:modelValue': (v: boolean) => ctx.toggleSelect(rowData.id, v),
      }),
  })

  const nodePath: Column<AssetHubV2Row> = {
    key: 'namePath',
    dataKey: 'name',
    title: 'Node / 脚本',
    width: nodeW,
    cellRenderer: ({ rowData }) => nodePathCell(rowData),
  }

  const sync: Column<AssetHubV2Row> = {
    key: 'syncState',
    dataKey: 'syncState',
    title: '同步状态',
    width: 128,
    cellRenderer: ({ rowData }) => {
      const pending = rowData.syncState === 'pending_init'
      const variant: CyberStatusVariant = pending ? 'sync-pending' : 'sync-ready'
      return h(CyberStatusChip, {
        variant,
        label: ctx.syncStateLabel(rowData.syncState),
      })
    },
  }

  const lastExec: Column<AssetHubV2Row> = {
    key: 'lastResult',
    dataKey: 'lastResult',
    title: '最近执行',
    width: 118,
    cellRenderer: ({ rowData }) => {
      let variant: CyberStatusVariant = 'exec-unknown'
      if (rowData.lastResult === 'success') variant = 'exec-success'
      else if (rowData.lastResult === 'failed') variant = 'exec-failed'
      return h(CyberStatusChip, {
        variant,
        label: ctx.resultLabel(rowData.lastResult),
      })
    },
  }

  const status: Column<AssetHubV2Row> = {
    key: 'isActive',
    dataKey: 'isActive',
    title: '运行状态',
    width: 96,
    cellRenderer: ({ rowData }) =>
      h(CyberStatusChip, {
        variant: rowData.isActive ? 'run-on' : 'run-off',
        label: rowData.isActive ? '启用' : '停用',
      }),
  }

  const progress: Column<AssetHubV2Row> = {
    key: 'lastSuccessRate',
    dataKey: 'lastSuccessRate',
    title: '上次成功率',
    width: 120,
    cellRenderer: ({ rowData }) =>
      h(ElProgress, {
        percentage: rowData.lastSuccessRate,
        strokeWidth: 10,
        status: rowData.lastSuccessRate >= 90 ? 'success' : undefined,
      }),
  }

  const actions: Column<AssetHubV2Row> = {
    key: 'actions',
    width: 168,
    title: '操作',
    fixed: 'right',
    cellRenderer: ({ rowData }) => {
      const kids: ReturnType<typeof h>[] = []
      if (rowData.syncState === 'pending_init') {
        kids.push(
          h(
            ElButton,
            {
              link: true,
              type: 'warning',
              size: 'small',
              onClick: () => ctx.onInit(rowData),
            },
            () => '初始化',
          ),
        )
      }
      if (ctx.isGhostRunnerRow(rowData)) {
        kids.push(
          h(
            ElButton,
            {
              link: true,
              type: 'primary',
              size: 'small',
              class: 'asset-hub__quick-debug-btn',
              onClick: () => ctx.onQuickDebug(rowData),
            },
            () => '⚡ 快速调试',
          ),
        )
      }
      if (!kids.length) {
        return h('span', { class: 'asset-hub__op-placeholder' }, '—')
      }
      return h('span', { class: 'asset-hub-v2__actions' }, kids)
    },
  }

  return [
    sel(),
    nodePath,
    sync,
    {
      key: 'owner',
      dataKey: 'owner',
      title: '负责人',
      width: 100,
      cellRenderer: ({ rowData }) =>
        h('span', { class: 'asset-hub__cell-mono' }, String(rowData.owner ?? '')),
    },
    progress,
    lastExec,
    status,
    actions,
  ]
}
