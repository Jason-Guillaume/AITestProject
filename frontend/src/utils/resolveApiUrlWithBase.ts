/**
 * 将接口用例中的路径与登记环境的 Base URL 拼接。
 * 已是 http(s) 绝对地址时原样返回。
 */
export function resolveApiUrlWithBase(baseRaw: string, pathOrUrl: string): string {
  const u = (pathOrUrl || '').trim()
  if (!u) return ''
  if (/^https?:\/\//i.test(u)) return u
  const base = (baseRaw || '').trim().replace(/\/+$/, '')
  if (!base) return u
  if (u.startsWith('/')) return `${base}${u}`
  return `${base}/${u}`
}
