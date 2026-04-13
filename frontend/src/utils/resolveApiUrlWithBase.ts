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

/** 若完整 URL 落在当前环境 Base 下，则写回为相对路径，便于换环境后仍拼接正确域名 */
export function relativizeApiUrlIfUnderBase(baseRaw: string, fullUrl: string): string {
  const u = (fullUrl || '').trim()
  if (!u || !/^https?:\/\//i.test(u)) return u
  const base = (baseRaw || '').trim().replace(/\/+$/, '')
  if (!base) return u
  const ub = u.replace(/\/+$/, '')
  const bb = base.replace(/\/+$/, '')
  if (ub.toLowerCase() === bb.toLowerCase()) return '/'
  const prefix = `${bb}/`
  if (u.toLowerCase().startsWith(prefix.toLowerCase())) {
    const rest = u.slice(prefix.length)
    return rest.startsWith('/') ? rest : `/${rest}`
  }
  return u
}
