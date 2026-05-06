import request from "@/utils/request";

function resolveCicdBaseURL() {
  const v = import.meta.env.VITE_CICD_API_BASE;
  if (v != null && String(v).trim() !== "") {
    return String(v).replace(/\/$/, "");
  }
  return "/cicd-api";
}

/** @param {Record<string, unknown>} [extra] */
function cicdRequestConfig(extra = {}) {
  return {
    baseURL: resolveCicdBaseURL(),
    timeout: 120000,
    ...extra,
  };
}

/**
 * 将 GET /pipelines 各类分页或包裹结构解析为流水线数组。
 * @param {unknown} payload
 * @returns {unknown[]}
 */
export function normalizePipelinesPayload(payload) {
  if (Array.isArray(payload)) return payload;
  if (!payload || typeof payload !== "object") return [];
  const o = payload;
  if (Array.isArray(o.results)) return o.results;
  if (Array.isArray(o.items)) return o.items;
  if (Array.isArray(o.pipelines)) return o.pipelines;
  if (Array.isArray(o.records)) return o.records;
  if (Array.isArray(o.list)) return o.list;
  if (Array.isArray(o.rows)) return o.rows;
  if (o.data != null) {
    if (Array.isArray(o.data)) return o.data;
    if (typeof o.data === "object" && o.data !== null) {
      const inner = o.data;
      if (Array.isArray(inner.results)) return inner.results;
      if (Array.isArray(inner.items)) return inner.items;
      if (Array.isArray(inner.data)) return inner.data;
    }
  }
  return [];
}

/** GET /health */
export function getHealth(config = {}) {
  return request.get("/health", cicdRequestConfig(config));
}

/**
 * GET /pipelines
 * `response.data` 已规范为流水线数组（兼容 results / items / data / pipelines 等）。
 */
export function getPipelines(params, config = {}) {
  return request
    .get("/pipelines", cicdRequestConfig({ params, ...config }))
    .then((res) => {
      const list = normalizePipelinesPayload(res.data);
      return { ...res, data: list };
    });
}

/** POST /pipelines/:id/run */
export function triggerBuild(id, data = {}, config = {}) {
  return request.post(`/pipelines/${id}/run`, data, cicdRequestConfig(config));
}

/** GET /runs/:runId */
export function getRunDetails(runId, config = {}) {
  return request.get(`/runs/${runId}`, cicdRequestConfig(config));
}
