import request from "@/utils/request";

/**
 * POST /api/ai/verify-connection/
 * 固定智谱 base + glm-4.7-flash，仅需 api_key（表单「测试连接」推荐用此接口）
 */
export const verifyAiConnectionApi = (data) =>
  request.post("/ai/verify-connection/", data);

/** POST /api/ai/test-connection/：可传 model、api_base_url，灵活测试 */
export const testAiConnectionApi = (data) =>
  request.post("/ai/test-connection/", data);

/** POST /api/ai/phase1-preview/：仅 Phase1 预览（用于生成前确认 AI 理解） */
export const previewAiPhase1Api = (data) =>
  request.post("/ai/phase1-preview/", data);

/**
 * POST /api/ai/generate-cases/：按需求描述生成测试用例（JSON，非流式）。
 * 成功时 body 含 success、cases、message；若 RAG 判定已有用例全覆盖则为 all_covered: true、cases: []。
 */
export const generateAiCasesApi = (data) =>
  request.post("/ai/generate-cases/", data);

/** 非流式响应是否表示「模块内已有用例已覆盖需求」、无需新用例 */
export function isAiGenerateAllCoveredResponse(body) {
  const d = body?.data !== undefined ? body.data : body;
  return d?.success === true && d?.all_covered === true;
}

/**
 * 调用非流式生成并归一化结果（便于在任意页面复用）。
 * @returns {Promise<{ allCovered: boolean, cases: any[], message?: string, model?: string, error?: string }>}
 */
export async function generateAiCasesNormalized(data) {
  const res = await generateAiCasesApi(data);
  const d = res?.data ?? {};
  if (isAiGenerateAllCoveredResponse(res)) {
    return {
      allCovered: true,
      cases: [],
      message: d.message,
      model: d.model,
    };
  }
  if (d.success === false) {
    return {
      allCovered: false,
      cases: [],
      error: d.error || d.message || "生成失败",
    };
  }
  return {
    allCovered: false,
    cases: Array.isArray(d.cases) ? d.cases : [],
    message: d.message,
    model: d.model,
  };
}

/** 流式生成请使用原生 fetch + SSE：POST /api/ai/generate-cases-stream/（见 TestCase.vue） */
export async function streamGenerateAiCases(payload, options = {}) {
  const {
    signal,
    maxBufferedChars = 800000,
    onEvent,
  } = options;
  const token = localStorage.getItem("token");
  const response = await fetch("/api/ai/generate-cases-stream/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Token ${token}` } : {}),
    },
    body: JSON.stringify(payload || {}),
    signal,
  });
  if (!response.ok) {
    let detail = "";
    try {
      detail = await response.text();
    } catch (_) {
      detail = "";
    }
    throw new Error(`流式生成失败(${response.status})${detail ? `: ${detail}` : ""}`);
  }
  if (!response.body) {
    throw new Error("浏览器不支持流式读取");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let pending = "";
  let bufferedChars = 0;

  const emit = (evt) => {
    if (typeof onEvent === "function") onEvent(evt);
  };

  const parseChunk = (chunk) => {
    pending += chunk;
    const blocks = pending.split("\n\n");
    pending = blocks.pop() || "";
    for (const block of blocks) {
      if (!block.trim()) continue;
      const lines = block.split("\n");
      const dataLines = [];
      for (const line of lines) {
        if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
      }
      if (!dataLines.length) continue;
      const dataText = dataLines.join("\n");
      let evt;
      try {
        evt = JSON.parse(dataText);
      } catch (_) {
        emit({ type: "malformed", raw: dataText });
        continue;
      }
      if (evt?.type === "delta" && typeof evt?.text === "string") {
        bufferedChars += evt.text.length;
        if (bufferedChars > maxBufferedChars) {
          throw new Error("AI 流式内容过长，已中止以保护页面性能");
        }
      }
      emit(evt);
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    parseChunk(decoder.decode(value, { stream: true }));
  }
  const tail = decoder.decode();
  if (tail) parseChunk(tail);
}

// 知识库（RAG）
export const searchKnowledgeApi = (data) =>
  request.post("/assistant/knowledge/search/", data);

export const getKnowledgeCategoriesApi = () =>
  request.get("/assistant/knowledge/categories/");

export const listKnowledgeArticlesApi = (params) =>
  request.get("/assistant/knowledge-articles/", { params });

export const createKnowledgeArticleApi = (data) =>
  request.post("/assistant/knowledge-articles/", data);

export const uploadKnowledgeDocumentApi = (formData) =>
  request.post("/assistant/knowledge/documents/upload/", formData);

export const ingestKnowledgeDocumentApi = (payload) =>
  request.post("/assistant/knowledge/documents/ingest/", payload);

export const listKnowledgeDocumentsApi = (params) =>
  request.get("/assistant/knowledge/documents/", { params });

export const getKnowledgeDocumentStatusApi = (id) =>
  request.get(`/assistant/knowledge/documents/${id}/status/`);

export const previewKnowledgeDocumentChunksApi = (id, params) =>
  request.get(`/assistant/knowledge/documents/${id}/chunks-preview/`, { params });

export const previewKnowledgeArticleChunksApi = (id, params) =>
  request.get(`/assistant/knowledge/articles/${id}/chunks-preview/`, { params });

export const probeKnowledgeDocumentDeleteApi = (id = 0) =>
  request({
    url: `/assistant/knowledge/documents/${id}/`,
    method: "delete",
  });

export const retryKnowledgeDocumentApi = (id) =>
  request.post(`/assistant/knowledge/documents/${id}/retry/`);

export const deleteKnowledgeDocumentApi = (id) =>
  request.delete(`/assistant/knowledge/documents/${id}/`);

export const getKnowledgeRuntimeStatusApi = () =>
  request.get("/assistant/knowledge/runtime-status/");

export const extractKnowledgeTextApi = (formData) =>
  request.post("/assistant/knowledge/extract-text/", formData);

export const autoFillKnowledgeFormApi = (formData) =>
  request.post("/assistant/knowledge/autofill-from-file/", formData);

export const updateKnowledgeArticleApi = (id, data) =>
  request.patch(`/assistant/knowledge-articles/${id}/`, data);

export const deleteKnowledgeArticleApi = (id) =>
  request.delete(`/assistant/knowledge-articles/${id}/`);
