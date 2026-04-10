import request from "@/utils/request";

export const getPlansApi = (params) => request.get("/execution/plans/", { params });
export const createPlanApi = (data) => request.post("/execution/plans/", data);
export const updatePlanApi = (id, data) => request.patch(`/execution/plans/${id}/`, data);
export const deletePlanApi = (id) => request.delete(`/execution/plans/${id}/`);
export const getPlanDetailApi = (id) => request.get(`/execution/plans/${id}/`);

export const getReportsApi = (params) => request.get("/execution/reports/", { params });
export const createReportApi = (data) => request.post("/execution/reports/", data);
export const updateReportApi = (id, data) => request.patch(`/execution/reports/${id}/`, data);
export const deleteReportApi = (id) => request.delete(`/execution/reports/${id}/`);
export const getReportDetailApi = (id) => request.get(`/execution/reports/${id}/`);
