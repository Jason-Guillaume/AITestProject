/**
 * 测试用例列表：按类型仅展示少量「短列」，长字段进抽屉详情。
 */
import type { TestCaseRow } from '@/types/testcase'

export type TestCaseRouteKey =
  | 'functional'
  | 'api'
  | 'performance'
  | 'security'
  | 'ui-automation'

export interface TypeExtraColumn {
  key: string
  label: string
  /** 未设置 width 时作为弹性列最小宽度 */
  minWidth: number
  /** 设置后表格使用该固定宽度，避免与「用例名称」等列互相挤压 */
  width?: number
  align: 'left' | 'center' | 'right'
  showTooltip: boolean
  cell: (row: TestCaseRow) => string
}

/** 主表仅保留短字段；API 地址、包名、定位符等一律不展示在表格中 */
export function getTypeExtraColumns(caseType: string): TypeExtraColumn[] {
  switch (caseType) {
    case 'api':
      return [
        {
          key: 'api_method',
          label: '方法',
          minWidth: 96,
          align: 'center',
          showTooltip: true,
          cell: (r) => String(r.api_method || '—'),
        },
        {
          key: 'api_expected_status',
          label: '期望码',
          minWidth: 100,
          align: 'center',
          showTooltip: true,
          cell: (r) =>
            r.api_expected_status != null ? String(r.api_expected_status) : '—',
        },
      ]
    case 'performance':
      return [
        {
          key: 'concurrency',
          label: '并发',
          minWidth: 100,
          width: 100,
          align: 'right',
          showTooltip: false,
          cell: (r) =>
            r.concurrency != null ? String(r.concurrency) : '—',
        },
        {
          key: 'duration_seconds',
          label: '时长(s)',
          minWidth: 100,
          width: 100,
          align: 'right',
          showTooltip: false,
          cell: (r) =>
            r.duration_seconds != null ? String(r.duration_seconds) : '—',
        },
        {
          key: 'target_rps',
          label: '目标 RPS',
          minWidth: 112,
          width: 112,
          align: 'right',
          showTooltip: true,
          cell: (r) =>
            r.target_rps != null ? String(r.target_rps) : '—',
        },
      ]
    case 'security':
      return [
        {
          key: 'tool_preset',
          label: '工具/模板',
          minWidth: 160,
          align: 'left',
          showTooltip: true,
          cell: (r) => String(r.tool_preset || '—'),
        },
      ]
    case 'ui-automation':
      return [
        {
          key: 'automation_framework',
          label: '框架',
          minWidth: 120,
          align: 'center',
          showTooltip: true,
          cell: (r) => String(r.automation_framework || '—'),
        },
      ]
    case 'functional':
    default:
      return []
  }
}

export interface DrawerField {
  label: string
  value: string
}

const pushField = (
  out: DrawerField[],
  label: string,
  value: unknown,
) => {
  const v =
    value === null || value === undefined || value === ''
      ? '—'
      : typeof value === 'object'
        ? JSON.stringify(value, null, 2)
        : String(value)
  out.push({ label, value: v })
}

/** 抽屉内：功能 / 安全 的扩展块（API、UI、性能 在页面内单独分区展示） */
export function getDrawerExtraFields(row: TestCaseRow): DrawerField[] {
  const tt = String(row.test_type || '').trim()
  const out: DrawerField[] = []

  if (tt === 'functional') {
    pushField(out, '前置条件', row.precondition)
    pushField(out, '操作步骤', row.steps)
    pushField(out, '预期结果', row.expected_result)
  } else if (tt === 'security') {
    pushField(out, '攻击面说明', row.attack_surface)
    pushField(out, '工具/模板', row.tool_preset)
  }

  return out
}

/** API 请求头在抽屉中的可读文本 */
export function drawerApiHeadersText(row: TestCaseRow): string {
  const h = row.api_headers
  if (h == null) return '—'
  if (typeof h === 'object' && !Array.isArray(h)) {
    const keys = Object.keys(h as object)
    if (keys.length === 0) return '—'
    return JSON.stringify(h, null, 2)
  }
  return String(h)
}

export function isDrawerTailFieldPreformatted(f: DrawerField): boolean {
  return ['前置条件', '操作步骤', '预期结果', '攻击面说明'].includes(f.label)
}

/** 列表编号：前缀 + 数据库主键 id，如 API-25 */
export function formatCaseDisplayId(row: TestCaseRow): string {
  const tt = String(row?.test_type ?? '')
  const prefixMap: Record<string, string> = {
    functional: 'FUN',
    api: 'API',
    performance: 'PERF',
    security: 'SEC',
    'ui-automation': 'UI',
  }
  const prefix = prefixMap[tt] || 'TC'
  const id = row?.id
  if (id != null && !Number.isNaN(Number(id))) return `${prefix}-${id}`
  return `${prefix}-?`
}
