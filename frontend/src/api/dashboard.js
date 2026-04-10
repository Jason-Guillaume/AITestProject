import request from "@/utils/request";

// 后端：GET /api/execution/dashboard/summary/
export function getDashboardSummaryApi() {
  return request.get("/execution/dashboard/summary/");
}

// 后端：GET /api/execution/dashboard/quality/
export function getQualityDashboardApi(params) {
  return request.get("/execution/dashboard/quality/", { params });
}

// SSE 推送流地址（用于触发前端刷新）
export function getDashboardStreamUrl(params = {}) {
  const search = new URLSearchParams();
  const token = localStorage.getItem("token");
  if (token) search.set("token", token);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") {
      search.set(k, String(v));
    }
  });
  const query = search.toString();
  return `/api/execution/dashboard/stream/${query ? `?${query}` : ""}`;
}

