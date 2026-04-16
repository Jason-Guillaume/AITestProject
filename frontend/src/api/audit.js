import request from "@/utils/request";
import { downloadAuthedGet } from "@/utils/downloadAuthedGet";

/** GET /api/sys/audit/events/ */
export const getSysAuditEventsApi = (params) =>
  request.get("/sys/audit/events/", { params });

/** GET /api/user/me/audit/events/ */
export const getMyAuditEventsApi = (params) =>
  request.get("/user/me/audit/events/", { params });

/**
 * 下载系统审计 CSV（需要 Token Header；不要用 window.open 裸链）。
 * GET /api/sys/audit/export.csv
 */
export async function downloadSysAuditExportCsv(params) {
  return downloadAuthedGet("/api/sys/audit/export.csv", {
    params,
    defaultFilename: "audit-events.csv",
  });
}
