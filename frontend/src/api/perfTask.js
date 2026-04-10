import request from "@/utils/request";

export function getPerfTasks(params) {
  return request.get("/perf/tasks/", { params });
}

export function createPerfTask(data) {
  return request.post("/perf/tasks/", data);
}

export function runPerfTask(taskId) {
  return request.post(`/perf/tasks/${taskId}/run/`);
}

export function deletePerfTask(taskId) {
  return request.delete(`/perf/tasks/${taskId}/`);
}
