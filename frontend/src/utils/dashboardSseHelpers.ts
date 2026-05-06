/** Dashboard SSE：指数退避与失败提示（与 EventSource 配合使用） */

export const DASHBOARD_SSE_MAX_RECONNECT_ATTEMPTS = 5;

/** 首次建立连接前让出主线程（ms） */
export const DASHBOARD_SSE_INITIAL_CONNECT_DELAY_MS = 400;

/** 第一次重试 2s，之后 4s、8s… 封顶 30s */
export function dashboardSseBackoffMs(zeroBasedAttempt: number): number {
  const base = 2000;
  const max = 30000;
  return Math.min(max, base * Math.pow(2, zeroBasedAttempt));
}

/**
 * 脚本中心「保险丝」Dashboard SSE：失败后禁止立即重连。
 * 第 1 次失败等 2s，第 2 次等 5s，之后按 ×2 递增，封顶 60s。
 */
export function scriptHubSseFuseBackoffMs(zeroBasedAttempt: number): number {
  const max = 60000;
  if (zeroBasedAttempt <= 0) return 2000;
  if (zeroBasedAttempt === 1) return 5000;
  return Math.min(max, 5000 * Math.pow(2, zeroBasedAttempt - 1));
}

export const DASHBOARD_SSE_FAILURE_MESSAGE = "实时日志连接失败，请手动刷新";
