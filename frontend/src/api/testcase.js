import request from "@/utils/request";

export const getApproachsApi = (params) => request.get("/testcase/approaches/", { params });
export const createApproachApi = (data) => request.post("/testcase/approaches/", data);
export const updateApproachApi = (id, data) => request.patch(`/testcase/approaches/${id}/`, data);
export const deleteApproachApi = (id) => request.delete(`/testcase/approaches/${id}/`);

// 方案图片
export const getApproachImagesApi = (id) =>
  request.get(`/testcase/approaches/${id}/images/`);

// files: File[]，字段名建议为 images（multipart）
export const uploadApproachImagesApi = (id, formData) =>
  request.post(`/testcase/approaches/${id}/images/upload/`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

export const deleteApproachImageApi = (approachId, imageId) =>
  request.delete(`/testcase/approaches/${approachId}/images/${imageId}/`);

export const getDesignsApi = (params) => request.get("/testcase/designs/", { params });
export const createDesignApi = (data) => request.post("/testcase/designs/", data);
export const updateDesignApi = (id, data) => request.patch(`/testcase/designs/${id}/`, data);
export const deleteDesignApi = (id) => request.delete(`/testcase/designs/${id}/`);
export const getDesignDetailApi = (id) => request.get(`/testcase/designs/${id}/`);

export const getModulesApi = (params) => request.get("/testcase/modules/", { params });
export const createModuleApi = (data) => request.post("/testcase/modules/", data);
export const updateModuleApi = (id, data) => request.patch(`/testcase/modules/${id}/`, data);
export const deleteModuleApi = (id) => request.delete(`/testcase/modules/${id}/`);

export const getCasesApi = (params) => request.get("/testcase/cases/", { params });
/** 回收站：与 getCasesApi 相同资源，必须带 recycle=1（或 is_deleted=true） */
export const getRecycleCasesApi = (params) =>
  request.get("/testcase/cases/", { params: { ...params, recycle: "1" } });
export const createCaseApi = (data) => request.post("/testcase/cases/", data);
export const updateCaseApi = (id, data) => request.patch(`/testcase/cases/${id}/`, data);
export const deleteCaseApi = (id) => request.delete(`/testcase/cases/${id}/`);
export const restoreCaseApi = (id) => request.post(`/testcase/cases/${id}/restore/`);
export const hardDeleteCaseApi = (id) => request.delete(`/testcase/cases/${id}/hard-delete/`);
/** 批量逻辑删除，body: { ids: number[] }；可选 config.params.project 与列表页一致，便于后端按项目收敛 */
export const batchDeleteCasesApi = (data, config) =>
  request.post("/testcase/cases/batch-delete/", data, config);
/** 批量记录执行（exec_count+1），body: { ids: number[] } */
export const batchExecuteCasesApi = (data) => request.post("/testcase/cases/batch-execute/", data);
/** 执行单条 API 用例（真实 HTTP + 落库 ApiTestLog） */
export const executeApiCaseApi = (id) => request.post(`/testcase/cases/${id}/execute-api/`);
/** 执行 API 用例（覆盖参数，落库 ExecutionLog） */
export const runApiCaseApi = (id, data) =>
  request.post(`/testcase/cases/${id}/run-api/`, data ?? {});
/** 预览 API 用例执行前最终请求（不发请求） */
export const previewRunApiCaseApi = (id, data) =>
  request.post(`/testcase/cases/${id}/preview-run-api/`, data ?? {});
/** AI 根据字段结构填充测试数据 */
export const aiFillTestDataApi = (data) => request.post("/testcase/ai-fill-test-data/", data);
export const getCaseDetailApi = (id) => request.get(`/testcase/cases/${id}/`);
/** 单用例执行日志分页列表 */
export const getCaseExecutionLogsApi = (id, params) =>
  request.get(`/testcase/cases/${id}/execution-logs/`, { params });
/** 单用例快照版本分页列表 */
export const getCaseVersionsApi = (id, params) =>
  request.get(`/testcase/cases/${id}/versions/`, { params });
/** 用例版本回溯，body: { version_id: number } */
export const rollbackCaseVersionApi = (id, data) =>
  request.post(`/testcase/cases/${id}/rollback-version/`, data);

export const createCaseStepApi = (data) => request.post("/testcase/steps/", data);

/** AI 批量导入用例（事务 + 逐条结果） */
export const aiImportCasesApi = (data) => request.post("/testcase/cases/ai-import/", data);

/** 批量预检：预览 API 用例最终请求（不发请求） */
export const batchPreviewRunApiCaseApi = (data) =>
  request.post("/testcase/cases/batch-preview-run-api/", data);

/** AI 导入前批量预检（草稿 items，不要求已落库） */
export const aiImportPrecheckApi = (data) =>
  request.post("/testcase/cases/ai-import-precheck/", data);
