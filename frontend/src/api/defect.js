import request from "@/utils/request";

export const getDefectsApi = (params) => request.get("/defect/defects/", { params });
export const createDefectApi = (data) => request.post("/defect/defects/", data);
export const updateDefectApi = (id, data) => request.patch(`/defect/defects/${id}/`, data);
export const deleteDefectApi = (id) => request.delete(`/defect/defects/${id}/`);
export const getDefectDetailApi = (id) => request.get(`/defect/defects/${id}/`);
