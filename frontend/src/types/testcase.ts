/**
 * 测试用例 REST 扁平结构（后端多表继承对外仍统一 JSON）
 */
export type TestCaseRouteType =
  | 'functional'
  | 'api'
  | 'performance'
  | 'security'
  | 'ui-automation'

/** 列表/详情行（与 DRF TestCaseSerializer 对齐） */
export interface TestCaseRowBase {
  id: number
  case_name: string
  case_number?: number | null
  test_type: TestCaseRouteType | string
  level: string
  is_valid: boolean
  exec_count: number
  review_status: number
  archive_status: number
  module?: number | { id: number } | null
  creator_name?: string | null
  updater_name?: string | null
  create_time?: string | null
  update_time?: string | null
}

export interface FunctionalTestCaseFields {
  precondition?: string
  steps?: string
  expected_result?: string
}

export interface ApiTestCaseFields {
  api_url?: string
  api_method?: string
  api_headers?: Record<string, string>
  /** 后端 JSONField：对象/数组或历史字符串 */
  api_body?: string | Record<string, unknown> | unknown[]
  api_expected_status?: number | null
  api_extract_rules?: ApiVariableExtractRule[]
}

export interface ApiVariableExtractRule {
  variableName: string
  source: 'Body' | 'Header'
  expression: string
  currentValue?: string
}

export interface PerfTestCaseFields {
  concurrency?: number
  duration_seconds?: number
  target_rps?: number | null
}

export interface SecurityTestCaseFields {
  attack_surface?: string
  tool_preset?: string
}

export interface UITestCaseFields {
  app_under_test?: string
  primary_locator?: string
  automation_framework?: string
}

export type TestCaseRow = TestCaseRowBase &
  FunctionalTestCaseFields &
  ApiTestCaseFields &
  PerfTestCaseFields &
  SecurityTestCaseFields &
  UITestCaseFields

/** 弹窗表单（含 API 请求头 JSON 文本编辑） */
export interface TestCaseFormState {
  case_name: string
  level: string
  module: number | null
  api_url?: string
  api_method?: string
  api_headers_text?: string
  api_body?: string
  api_expected_status?: number | null
  concurrency?: number
  duration_seconds?: number
  target_rps?: number | null
  attack_surface?: string
  tool_preset?: string
  app_under_test?: string
  primary_locator?: string
  automation_framework?: string
}
