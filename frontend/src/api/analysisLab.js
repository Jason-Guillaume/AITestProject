import request from "@/utils/request";

/** GET /api/reports/:id/details/ — UIScriptExecution 深度报告聚合（可传 { signal } 取消） */
export const getAnalysisLabReportDetailsApi = (id, config = {}) =>
  request.get(`/reports/${id}/details/`, config);

/** POST /api/ai/ui-execution-diagnose/ */
export const postUiExecutionDiagnoseApi = (data, config = {}) =>
  request.post("/ai/ui-execution-diagnose/", data, config);
