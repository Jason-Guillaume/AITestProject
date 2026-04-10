/**
 * Maps each test case route type to a dedicated system-role instruction.
 * Merged with the user’s requirement in the client before POST to AI generation APIs.
 */
/** 与后端 AI 生成接口拼接；后端另有系统提示强制 JSON 内简体中文，此处保持中文侧重一致。 */
export const AI_TEST_TYPE_SYSTEM_PROMPTS = {
  functional:
    '你是一名资深测试工程师。请根据下列用户需求，侧重 UI 功能场景，覆盖前置条件、操作步骤与预期结果。最终由服务端要求模型输出 JSON 数组，且用例内全部自然语言必须为简体中文。',

  api:
    '你是一名接口测试工程师。请根据用户需求，侧重 HTTP 方法、URL、请求头/体、断言与异常场景。输出格式由服务端统一为 JSON；用例内描述性文字须全部为简体中文（URL/方法名等技术字面量可保留）。',

  performance:
    '你是一名性能测试工程师。请根据用户需求，侧重负载场景、指标（时延/吞吐等）、测试数据、步骤与通过准则。用例正文须为简体中文。',

  security:
    '你是一名安全测试工程师。请根据用户需求，侧重威胁与攻击面、前置、步骤与安全预期。用例正文须为简体中文。',

  'ui-automation':
    '你是一名 UI 自动化工程师。请侧重稳定定位、页面路径、等待同步、数据与断言。用例正文须为简体中文。',
}

const DEFAULT_TEST_TYPE = 'functional'

/**
 * @param {string} testType - e.g. functional | api | performance | security | ui-automation
 * @param {string} userRequirement - raw requirement from the dialog (trimmed by caller recommended)
 * @returns {string} Combined prompt for the API `requirement` field
 */
/** 「查看示例」一键填入需求框的模板（可按测试类型扩展） */
export const AI_QUICK_START_BY_TYPE = {
  functional:
    '请为「订单支付」业务流程设计功能测试用例：覆盖正常支付、余额不足、优惠券叠加边界、支付超时取消、重复提交幂等等场景；前置条件需写明测试账号与数据准备。',
  api:
    '请根据下方接口定义，生成接口测试用例：覆盖 2xx 成功、典型 4xx（参数缺失/非法）、鉴权失败、超时与重试；每条需可落地的断言思路（状态码、关键字段）。',
  performance:
    '请设计性能测试场景：目标接口为订单列表查询；并发 200、P95 响应时间 < 500ms、错误率 < 0.1%；说明加压模型、预热、监控指标与通过准则。',
  security:
    '请针对该模块进行 SQL 注入与越权漏洞探测，输出攻击 Payload 及修复建议。',
  'ui-automation':
    '请为登录页编写 UI 自动化用例：使用稳定定位（data-testid 优先）、显式等待网络与动画、断言错误提示文案与跳转；可粘贴页面 HTML 片段辅助定位。',
}

export function mergeTestTypePromptWithRequirement(testType, userRequirement) {
  const key = String(testType || '').trim() || DEFAULT_TEST_TYPE
  const system =
    AI_TEST_TYPE_SYSTEM_PROMPTS[key] ?? AI_TEST_TYPE_SYSTEM_PROMPTS[DEFAULT_TEST_TYPE]
  const user = String(userRequirement ?? '').trim()
  return `${system}\n\n---\n【用户需求（主要输入，可为中文）】\n${user}\n\n【刚性要求】服务端将要求模型：仅输出 JSON 数组，且 caseName、precondition、steps、expectedResult、module_name 等所有字符串取值必须全部为简体中文；不要用英文写用例句子。`
}
