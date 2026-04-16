import request from "@/utils/request";
import { downloadAuthedGet } from "@/utils/downloadAuthedGet";

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

/**
 * 下载 AI 用量审计 CSV（需 Token Header；勿用 window.open / <a href> 裸链）。
 * GET /api/sys/ai-usage/export.csv
 */
export async function downloadAiUsageExportCsv(params) {
  return downloadAuthedGet("/api/sys/ai-usage/export.csv", {
    params,
    defaultFilename: "ai-usage-events.csv",
  });
}

