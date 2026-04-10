import request from "@/utils/request";

/** 创建 k6 压测会话并异步执行 */
export function createK6Session(data) {
  return request.post("/perf/k6-sessions/", data);
}

/** 查询会话详情（含脚本快照与 summary） */
export function getK6Session(runId) {
  return request.get(`/perf/k6-sessions/${runId}/`);
}
