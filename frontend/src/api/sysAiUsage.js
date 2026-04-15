import request from "@/utils/request";

/** GET /api/sys/ai-usage/events/ */
export const getAiUsageEventsApi = (params) =>
  request.get("/sys/ai-usage/events/", { params });

/** GET /api/sys/ai-usage/summary/ */
export const getAiUsageSummaryApi = (params) =>
  request.get("/sys/ai-usage/summary/", { params });

/** GET /api/sys/ai-usage/metrics/ */
export const getAiUsageMetricsApi = (params) =>
  request.get("/sys/ai-usage/metrics/", { params });

/** GET /api/sys/ai-usage/top-errors/ */
export const getAiUsageTopErrorsApi = (params) =>
  request.get("/sys/ai-usage/top-errors/", { params });

/** GET /api/sys/ai-usage/latency-trend/ */
export const getAiUsageLatencyTrendApi = (params) =>
  request.get("/sys/ai-usage/latency-trend/", { params });

/** GET /api/sys/ai-usage/export.csv */
export const getAiUsageExportCsvUrl = (params) => {
  const q = new URLSearchParams(params || {});
  const qs = q.toString();
  return `/api/sys/ai-usage/export.csv${qs ? `?${qs}` : ""}`;
};

