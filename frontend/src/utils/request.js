import axios from "axios";
import { ElMessage } from "element-plus";

let backendUnhealthyNotified = false;

function normalizeDetail(detail) {
  if (detail == null) return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((x) => {
        if (typeof x === "string") return x;
        if (x && typeof x === "object" && String(x.string || "").trim()) return String(x.string);
        try {
          return JSON.stringify(x);
        } catch {
          return String(x);
        }
      })
      .join("；");
  }
  if (typeof detail === "object") {
    try {
      return JSON.stringify(detail);
    } catch {
      return String(detail);
    }
  }
  return String(detail);
}

function notifyBackendHealth(status, message) {
  if (typeof window === "undefined") return;
  if (status === "healthy") {
    backendUnhealthyNotified = false;
    window.dispatchEvent(new CustomEvent("app:backend-healthy"));
    return;
  }
  if (backendUnhealthyNotified) return;
  backendUnhealthyNotified = true;
  window.dispatchEvent(
    new CustomEvent("app:backend-unhealthy", {
      detail: { message: message || "后端服务暂不可用" },
    })
  );
}

const pendingRequests = new Map();

function generateRequestKey(config) {
  const { method, url, params, data } = config || {};
  return [method, url, JSON.stringify(params), JSON.stringify(data)].join("&");
}

function addPendingRequest(config) {
  const key = generateRequestKey(config);
  if (pendingRequests.has(key)) {
    const cancel = pendingRequests.get(key);
    if (cancel) cancel();
  }
  config.cancelToken = config.cancelToken || new axios.CancelToken((cancel) => {
    pendingRequests.set(key, cancel);
  });
}

function removePendingRequest(config) {
  const key = generateRequestKey(config);
  if (pendingRequests.has(key)) {
    pendingRequests.delete(key);
  }
}

const request = axios.create({
  baseURL: "/api",
  timeout: 60000,
  withCredentials: true,
});

request.interceptors.request.use(
  (config) => {
    addPendingRequest(config);
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Token ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

request.interceptors.response.use(
  (response) => {
    removePendingRequest(response.config);
    notifyBackendHealth("healthy");
    return response;
  },
  (error) => {
    if (axios.isCancel(error)) {
      return Promise.reject(error);
    }
    removePendingRequest(error.config || {});
    // Axios 超时：error.response 可能为空，先单独处理以给出更明确的提示
    if (
      error?.code === "ECONNABORTED" ||
      String(error?.message || "").toLowerCase().includes("timeout")
    ) {
      const method = String(error?.config?.method || "GET").toUpperCase();
      const url = error?.config?.url || "";
      const msg = `请求超时（60s）：${method} ${url}`;
      ElMessage.error(msg);
      notifyBackendHealth("unhealthy", msg);
      return Promise.reject(error);
    }

    const status = error?.response?.status;
    const contentType = String(error?.response?.headers?.["content-type"] || "").toLowerCase();
    const rawData = error?.response?.data;
    let dataMsg =
      rawData?.message ||
      rawData?.msg ||
      rawData?.error ||
      (typeof rawData === "string" ? rawData : "");
    if (!dataMsg && rawData?.detail != null) {
      dataMsg = normalizeDetail(rawData.detail);
    }

    // 后端返回 HTML 错误页（常见于 Django debug/500），给出可读错误提示。
    if (status >= 500 && (contentType.includes("text/html") || /^<html/i.test(String(rawData || "")))) {
      const msg = "后端内部错误（500），请检查 Django 服务日志或重启后端";
      ElMessage.error(msg);
      notifyBackendHealth("unhealthy", msg);
      return Promise.reject(error);
    }

    // 代理层连不上后端（如 ECONNREFUSED）时，error.response 通常为空。
    if (!error?.response) {
      const msg = "后端未就绪或连接被拒绝，请确认后端服务正在运行";
      ElMessage.error(msg);
      notifyBackendHealth("unhealthy", msg);
      return Promise.reject(error);
    }

    if (status === 401) {
      ElMessage.error("登录已过期，请重新登录");
      localStorage.removeItem("token");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    } else if (status >= 500) {
      const msg = dataMsg || "服务异常，请稍后重试";
      ElMessage.error(msg);
      notifyBackendHealth("unhealthy", msg);
    }
    return Promise.reject(error);
  }
);

export default request;
