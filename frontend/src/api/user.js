import request from "@/utils/request";

/** GET /api/user/me/ 同步当前用户 is_system_admin 等 */
export function getCurrentUserApi() {
  return request.get("/user/me/");
}

export function changePasswordApi(payload) {
  // 后端：POST /api/user/change-password/
  return request.post("/user/change-password/", payload);
}

/** 个人中心：资料 GET/PATCH（PATCH 可 FormData 带头像） */
export function getUserProfileApi() {
  return request.get("/user/me/profile/");
}

export function patchUserProfileApi(data) {
  return request.patch("/user/me/profile/", data);
}

/** 待审批的敏感变更状态 */
export function getSensitiveChangeStatusApi() {
  return request.get("/user/me/change-requests-status/");
}

/** 提交用户名/密码变更申请 */
export function submitSensitiveChangeApi(payload) {
  return request.post("/user/me/sensitive-change/", payload);
}

/** 管理员：站内系统消息收件箱 */
export function getSystemMessagesApi(params) {
  return request.get("/user/system-messages/", { params });
}

/** 将单条站内信标记为已读 */
export function markSystemMessageReadApi(id) {
  return request.patch(`/user/system-messages/${id}/read/`);
}

/** 管理员：敏感变更申请列表（如 status=pending） */
export function getAdminChangeRequestsApi(params) {
  return request.get("/user/admin/change-requests/", { params });
}

/** POST /api/change-requests/:id/approve/ */
export function approveChangeRequestApi(id) {
  return request.post(`/change-requests/${id}/approve/`);
}

/** POST /api/change-requests/:id/reject/ */
export function rejectChangeRequestApi(id) {
  return request.post(`/change-requests/${id}/reject/`);
}

