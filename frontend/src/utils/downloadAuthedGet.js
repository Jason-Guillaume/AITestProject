import axios from "axios";

function normalizeDetail(detail) {
  if (detail == null) return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((x) => {
        if (typeof x === "string") return x;
        if (x && typeof x === "object" && String(x.string || "").trim()) return String(x.string);
        return JSON.stringify(x);
      })
      .join("；");
  }
  if (typeof detail === "object") return JSON.stringify(detail);
  return String(detail);
}

/**
 * 从 Blob 中解析 DRF / 常见 JSON 错误体，或截取纯文本片段（如 HTML 错误页）。
 * @param {Blob} blob
 * @returns {Promise<string>}
 */
export async function messageFromBlob(blob) {
  if (!(blob instanceof Blob) || blob.size === 0) return "";
  try {
    const text = await blob.text();
    const t = text.trim();
    if (!t) return "";
    const first = t[0];
    if (first === "{" || first === "[") {
      try {
        const j = JSON.parse(t);
        if (typeof j === "string") return j;
        if (j.detail != null) return normalizeDetail(j.detail);
        if (j.msg != null) return String(j.msg);
        if (j.message != null) return String(j.message);
        if (j.error != null) return typeof j.error === "string" ? j.error : JSON.stringify(j.error);
        return t.slice(0, 800);
      } catch {
        return t.slice(0, 800);
      }
    }
    return t.slice(0, 800);
  } catch {
    return "";
  }
}

/**
 * 浏览器导航式下载无法携带 DRF Token，统一用 Axios 拉 blob 再触发保存。
 * 失败时尽量从响应 Blob 中解析 `detail`/`msg` 并 `throw new Error(…)`，便于 `ElMessage.error(e.message)`。
 *
 * @param {string} absPath 以 `/api/...` 开头的绝对路径（与 Vite 代理一致）
 * @param {{ params?: object, timeout?: number, defaultFilename?: string }} opts
 */
export async function downloadAuthedGet(absPath, opts = {}) {
  const { params, timeout = 120000, defaultFilename = "download" } = opts;
  const token = localStorage.getItem("token");

  let resp;
  try {
    resp = await axios.get(absPath, {
      params,
      responseType: "blob",
      timeout,
      headers: token ? { Authorization: `Token ${token}` } : {},
    });
  } catch (e) {
    const r = e?.response;
    if (r?.data instanceof Blob) {
      const msg = await messageFromBlob(r.data);
      throw new Error(msg || e.message || "下载失败");
    }
    throw e;
  }

  const ct = String(resp.headers["content-type"] || "").toLowerCase();
  if (ct.includes("application/json") || ct.includes("text/json")) {
    const msg = await messageFromBlob(resp.data);
    throw new Error(msg || "下载失败");
  }
  if (ct.includes("text/html") && resp.data instanceof Blob && resp.data.size < 65536) {
    const msg = await messageFromBlob(resp.data);
    if (msg) throw new Error(msg);
  }

  const dispo = String(resp.headers["content-disposition"] || "");
  const m = /filename="([^"]+)"/i.exec(dispo) || /filename=([^;]+)/i.exec(dispo);
  const filename = (m && m[1] ? m[1].trim() : defaultFilename).replaceAll('"', "").trim();

  const url = URL.createObjectURL(resp.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
