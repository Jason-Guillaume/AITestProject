import request from "@/utils/request";

/** GET /api/sys/ai-quota/policies/ */
export const listAiQuotaPoliciesApi = (params) =>
  request.get("/sys/ai-quota/policies/", { params });

/** POST /api/sys/ai-quota/policies/ */
export const createAiQuotaPolicyApi = (data) =>
  request.post("/sys/ai-quota/policies/", data);

/** GET /api/sys/ai-quota/policies/<id>/ */
export const getAiQuotaPolicyApi = (id) =>
  request.get(`/sys/ai-quota/policies/${id}/`);

/** PUT /api/sys/ai-quota/policies/<id>/ */
export const updateAiQuotaPolicyApi = (id, data) =>
  request.put(`/sys/ai-quota/policies/${id}/`, data);

/** DELETE /api/sys/ai-quota/policies/<id>/ */
export const deleteAiQuotaPolicyApi = (id) =>
  request.delete(`/sys/ai-quota/policies/${id}/`);

