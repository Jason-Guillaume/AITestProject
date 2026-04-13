/**
 * 从「需求」首句/首行抽取业务模块名（纯本地规则：正则 + 归一化）。
 * 不调用大模型，便于预测与离线扩展；登录等仅为规则示例之一。
 */

const GENERIC_REJECT = /^(以下|如下|上述|当前|本|该|此)(系统|需求|功能|场景|模块)?$/i
const TRAILING_JUNK =
  /(?:的)?(?:相关)?(?:接口|API|api)?(?:测试)?(?:用例|场景|流程|功能|模块|系统)?$/i
const LEADING_JUNK = /^(请|帮我|帮忙|希望)?(?:测试|验证|检查|覆盖|编写|设计|生成|准备|规划)?/i

/** 取首句：到第一个句号类或换行；无则前 160 字（避免整篇当「首句」） */
export function pickFirstSentenceOrLine(raw: string): string {
  const t = String(raw || '')
    .replace(/\r\n/g, '\n')
    .trim()
  if (!t) return ''
  const firstLine = t.split(/\n/)[0]?.trim() || t
  const cut = firstLine.search(/[。！？!?]/)
  if (cut === -1) return firstLine.slice(0, 160).trim()
  return firstLine.slice(0, cut).trim()
}

function normalizeModuleCandidate(s: string): string {
  let x = String(s || '')
    .replace(/\s+/g, '')
    .replace(LEADING_JUNK, '')
    .replace(TRAILING_JUNK, '')
    .trim()
  x = x.replace(/^(对|针对|关于|为|围绕|围绕)/, '')
  x = x.replace(/^(的|模块|功能|流程|场景)+/, '')
  x = x.replace(/(的|模块|功能|流程|场景)+$/g, '')
  return x.trim()
}

function isWeakName(x: string): boolean {
  if (!x || x.length < 2 || x.length > 36) return true
  if (GENERIC_REJECT.test(x)) return true
  if (/^(用户|我们|系统|平台|应用|软件|项目)$/.test(x)) return true
  if (/接口测试|安全测试|性能测试|功能测试|UI自动化|自动化测试/.test(x)) return true
  return false
}

type RegexRule = { re: RegExp; group: number }

/**
 * 从需求文本抽取业务模块名；优先首句内高置信模式，其次首句内任意「」书名号片段。
 */
export function extractBusinessModuleNameFromRequirement(raw: string): string {
  const hay = pickFirstSentenceOrLine(raw)
  if (!hay) return ''

  const rules: RegexRule[] = [
    { re: /请为\s*[「『【]([^」』】]{2,32})[」』】]/, group: 1 },
    { re: /(?:请|帮)(?:我)?为\s*[「『【]([^」』】]{2,32})[」』】]/, group: 1 },
    { re: /请为\s*([^，。；;：\s]{2,26}?)接口(?:生成|编写|设计|准备|规划)/, group: 1 },
    { re: /请为\s*([^，。；;：\s]{2,26}?)(?:生成|编写|设计|准备|规划)(?:测试)?用例/, group: 1 },
    { re: /为\s*[「『【]([^」』】]{2,32})[」』】]\s*(?:编写|设计|生成|准备|规划|产出)/, group: 1 },
    { re: /针对\s*[「『【]([^」』】]{2,32})[」』】]/, group: 1 },
    { re: /关于\s*[「『【]([^」』】]{2,32})[」』】]/, group: 1 },
    { re: /(?:围绕|围绕)\s*[「『【]([^」』】]{2,32})[」』】]/, group: 1 },
    { re: /测试\s*[「『【]([^」』】]{2,32})[」』】]/, group: 1 },
    { re: /针对\s*《([^》]{2,32})》/, group: 1 },
    { re: /关于\s*《([^》]{2,32})》/, group: 1 },
    { re: /《([^》]{2,32})》\s*(?:模块|功能|流程|场景)?/, group: 1 },
    {
      re: /针对\s*([^，。；;：:\s]{2,26}?)(?:模块|功能|流程|场景|系统|接口)(?:[，。；;：:\s]|$)/,
      group: 1,
    },
    {
      re: /关于\s*([^，。；;：:\s]{2,26}?)(?:的|模块|功能)(?:[，。；;：:\s]|$)/,
      group: 1,
    },
    {
      re: /(?:编写|设计|生成|准备|规划)\s*([^，。；;：:\s]{2,26}?)(?:模块|功能|流程|场景)?(?:相关)?(?:的)?(?:接口|API)?(?:测试)?(?:用例)?[，。:：]/,
      group: 1,
    },
    { re: /^请(?:我)?为\s*([^，。；;：:\s]{2,22}?)(?:流程|模块|功能|场景)?[，。:：]/u, group: 1 },
    { re: /^围绕\s*([^，。；;：:\s]{2,22}?)(?:模块|功能|流程|场景)?[，。:：]/u, group: 1 },
    { re: /^(?:验证|测试)\s*([^，。；;：:\s]{2,22}?)(?:模块|功能|流程|场景|接口)?[，。:：]/u, group: 1 },
  ]

  const tried = new Set<string>()
  const tryPush = (rawCap: string | undefined): string | null => {
    if (!rawCap) return null
    const n = normalizeModuleCandidate(rawCap)
    if (!n || isWeakName(n)) return null
    const k = n.toLowerCase()
    if (tried.has(k)) return null
    tried.add(k)
    return n
  }

  for (const { re, group } of rules) {
    const m = hay.match(re)
    const hit = tryPush(m?.[group])
    if (hit) return hit
  }

  const bracket = [...hay.matchAll(/[「『【]([^」』】]{2,32})[」』】]/g)]
    .map((x) => x[1])
    .sort((a, b) => b.length - a.length)
  for (const seg of bracket) {
    const hit = tryPush(seg)
    if (hit) return hit
  }

  return ''
}
