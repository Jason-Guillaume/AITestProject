import request from "@/utils/request";

export function listServerLogHosts(params) {
  return request.get("/server-logs/hosts/", { params });
}

export function createServerLogHost(data) {
  return request.post("/server-logs/hosts/", data);
}

export function updateServerLogHost(id, data) {
  return request.patch(`/server-logs/hosts/${id}/`, data);
}

export function deleteServerLogHost(id) {
  return request.delete(`/server-logs/hosts/${id}/`);
}

export function analyzeServerLog(data) {
  return request.post("/server-logs/analyze/", data, { timeout: 120000 });
}

export function analyzeServerLogWithContext(data) {
  return request.post("/server-logs/analyze-with-context/", data, { timeout: 180000 });
}

export function searchServerLogs(params) {
  return request.get("/server-logs/search/", { params });
}

export function getServerLogErrorTrend(params) {
  return request.get("/server-logs/agg/error-trend/", { params });
}

export function listServerLogAuditEvents(params) {
  return request.get("/server-logs/audit-events/", { params });
}

export function listLogServerOrganizationChoices() {
  return request.get("/server-logs/organization-choices/");
}

/** 异步 AI 工单草稿：入队（202） */
export function enqueueServerLogAutoTicket(data) {
  return request.post("/server-logs/auto-tickets/enqueue/", data, { timeout: 60000 });
}

/** 轮询任务状态与 draft JSON */
export function getServerLogAutoTicketJob(jobId) {
  return request.get(`/server-logs/auto-tickets/jobs/${jobId}/`);
}

/** 对已成功任务，用 draft 补建缺陷（201；已存在则 200 already_created） */
export function createDefectFromServerLogAutoTicketJob(jobId, data = {}) {
  return request.post(`/server-logs/auto-tickets/jobs/${jobId}/create-defect/`, data, { timeout: 60000 });
}
