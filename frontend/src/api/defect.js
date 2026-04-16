import request from "@/utils/request";

export const getDefectsApi = (params) => request.get("/defect/defects/", { params });
export const createDefectApi = (data) => request.post("/defect/defects/", data);
export const updateDefectApi = (id, data) => request.patch(`/defect/defects/${id}/`, data);
export const deleteDefectApi = (id) => request.delete(`/defect/defects/${id}/`);
export const getDefectDetailApi = (id) => request.get(`/defect/defects/${id}/`);

// 缺陷：回收站/恢复/彻底删除（统一批量语义）
export const getDefectsRecycleApi = (params) =>
  request.get("/defect/defects/recycle/", { params });
export const restoreDefectApi = (id) =>
  request.post(`/defect/defects/${id}/restore/`);
export const hardDeleteDefectApi = (id) =>
  request.post(`/defect/defects/${id}/hard-delete/`);
export const bulkSoftDeleteDefectsApi = (data) =>
  request.post("/defect/defects/bulk-soft-delete/", data);
export const bulkRestoreDefectsApi = (data) =>
  request.post("/defect/defects/bulk-restore/", data);
export const bulkHardDeleteDefectsApi = (data) =>
  request.post("/defect/defects/bulk-hard-delete/", data);
