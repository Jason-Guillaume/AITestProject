import request from "@/utils/request";

export const getPlansApi = (params) => request.get("/execution/plans/", { params });
export const createPlanApi = (data) => request.post("/execution/plans/", data);
export const updatePlanApi = (id, data) => request.patch(`/execution/plans/${id}/`, data);
export const deletePlanApi = (id) => request.delete(`/execution/plans/${id}/`);
export const getPlanDetailApi = (id) => request.get(`/execution/plans/${id}/`);
export const batchDeletePlansApi = (data) => request.post("/execution/plans/batch-delete/", data);
export const batchUpdatePlansApi = (data) => request.post("/execution/plans/batch-update/", data);
export const batchCopyPlansApi = (data) => request.post("/execution/plans/batch-copy/", data);

export const getReportsApi = (params) => request.get("/execution/reports/", { params });
export const createReportApi = (data) => request.post("/execution/reports/", data);
export const updateReportApi = (id, data) => request.patch(`/execution/reports/${id}/`, data);
export const deleteReportApi = (id) => request.delete(`/execution/reports/${id}/`);
export const getReportDetailApi = (id) => request.get(`/execution/reports/${id}/`);
export const batchDeleteReportsApi = (data) =>
  request.post("/execution/reports/batch-delete/", data);
export const batchUpdateReportsApi = (data) =>
  request.post("/execution/reports/batch-update/", data);
export const batchCopyReportsApi = (data) =>
  request.post("/execution/reports/batch-copy/", data);

/** ApiScenario CRUD（后端 ViewSet：/api/execution/api-scenarios/） */
export const getApiScenariosApi = (params) =>
  request.get("/execution/api-scenarios/", { params });
export const getApiScenarioDetailApi = (id) =>
  request.get(`/execution/api-scenarios/${id}/`);

/** 生成场景草稿 / 可选落库：POST /api/execution/api-scenarios/generate/ */
export const generateApiScenarioApi = (data) =>
  request.post("/execution/api-scenarios/generate/", data);
