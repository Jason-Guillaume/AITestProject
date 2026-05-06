/**
 * 紧急封印：为 true 时不建立 Dashboard SSE、日志/压测 WebSocket 等长连接，
 * 避免主线程被重连拖死。恢复实时能力时改为 false 并重新构建前端。
 */
export const EMERGENCY_DISABLE_REALTIME_CONNECTIONS = false;
