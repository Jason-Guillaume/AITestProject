import request from "@/utils/request";

export function getScheduledTasks(params) {
  return request.get("/execution/scheduled-tasks/", { params });
}

export function getScheduledTaskDetail(id) {
  return request.get(`/execution/scheduled-tasks/${id}/`);
}

export function createScheduledTask(data) {
  return request.post("/execution/scheduled-tasks/", data);
}

export function updateScheduledTask(id, data) {
  return request.patch(`/execution/scheduled-tasks/${id}/`, data);
}

export function deleteScheduledTask(id) {
  return request.delete(`/execution/scheduled-tasks/${id}/`);
}

export function pauseScheduledTask(id) {
  return request.post(`/execution/scheduled-tasks/${id}/pause/`);
}

export function resumeScheduledTask(id) {
  return request.post(`/execution/scheduled-tasks/${id}/resume/`);
}

export function triggerScheduledTask(id) {
  return request.post(`/execution/scheduled-tasks/${id}/trigger/`);
}

export function getScheduledTaskLogs(params) {
  return request.get("/execution/scheduled-task-logs/", { params });
}
