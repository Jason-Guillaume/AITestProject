import request from "@/utils/request";

export const getPlansApi = (params) => request.get("/execution/plans/", { params });
export const createPlanApi = (data) => request.post("/execution/plans/", data);
export const updatePlanApi = (id, data) => request.patch(`/execution/plans/${id}/`, data);
export const deletePlanApi = (id) => request.delete(`/execution/plans/${id}/`);
export const getPlanDetailApi = (id) => request.get(`/execution/plans/${id}/`);
export const batchDeletePlansApi = (data) => request.post("/execution/plans/batch-delete/", data);
export const batchUpdatePlansApi = (data) => request.post("/execution/plans/batch-update/", data);
export const batchCopyPlansApi = (data) => request.post("/execution/plans/batch-copy/", data);

// 测试计划：回收站/恢复/彻底删除（统一批量语义）
export const getPlansRecycleApi = (params) =>
  request.get("/execution/plans/recycle/", { params });
export const restorePlanApi = (id) =>
  request.post(`/execution/plans/${id}/restore/`);
export const hardDeletePlanApi = (id) =>
  request.post(`/execution/plans/${id}/hard-delete/`);
export const bulkSoftDeletePlansApi = (data) =>
  request.post("/execution/plans/bulk-soft-delete/", data);
export const bulkRestorePlansApi = (data) =>
  request.post("/execution/plans/bulk-restore/", data);
export const bulkHardDeletePlansApi = (data) =>
  request.post("/execution/plans/bulk-hard-delete/", data);

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

// 测试报告：回收站/恢复/彻底删除（统一批量语义）
export const getReportsRecycleApi = (params) =>
  request.get("/execution/reports/recycle/", { params });
export const restoreReportApi = (id) =>
  request.post(`/execution/reports/${id}/restore/`);
export const hardDeleteReportApi = (id) =>
  request.post(`/execution/reports/${id}/hard-delete/`);
export const bulkSoftDeleteReportsApi = (data) =>
  request.post("/execution/reports/bulk-soft-delete/", data);
export const bulkRestoreReportsApi = (data) =>
  request.post("/execution/reports/bulk-restore/", data);
export const bulkHardDeleteReportsApi = (data) =>
  request.post("/execution/reports/bulk-hard-delete/", data);

/** 批量刷新测试报告统计字段（从关联计划同步）：POST /api/execution/reports/batch-refresh-from-plan/ */
export const batchRefreshReportsFromPlanApi = (data) =>
  request.post("/execution/reports/batch-refresh-from-plan/", data);

/** 批量执行测试报告（异步 Celery）：POST /api/execution/reports/batch-execute/ */
export const batchExecuteReportsApi = (data) =>
  request.post("/execution/reports/batch-execute/", data);

/** ApiScenario CRUD（后端 ViewSet：/api/execution/api-scenarios/） */
export const getApiScenariosApi = (params) =>
  request.get("/execution/api-scenarios/", { params });
export const getApiScenarioDetailApi = (id) =>
  request.get(`/execution/api-scenarios/${id}/`);

/** 生成场景草稿 / 可选落库：POST /api/execution/api-scenarios/generate/ */
export const generateApiScenarioApi = (data) =>
  request.post("/execution/api-scenarios/generate/", data);
