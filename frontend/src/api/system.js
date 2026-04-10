import request from "@/utils/request";

export const getOrgsApi = (params) => request.get("/user/orgs/", { params });
export const createOrgApi = (data) => request.post("/user/orgs/", data);
export const updateOrgApi = (id, data) => request.patch(`/user/orgs/${id}/`, data);
export const deleteOrgApi = (id) => request.delete(`/user/orgs/${id}/`);

export const getMessageSettingsApi = (params) =>
  request.get("/user/message-settings/", { params });
export const createMessageSettingApi = (data) =>
  request.post("/user/message-settings/", data);
export const updateMessageSettingApi = (id, data) =>
  request.patch(`/user/message-settings/${id}/`, data);

export const getRolesApi = () => request.get("/user/roles/");
export const createRoleApi = (data) => request.post("/user/roles/", data);
export const updateRoleApi = (id, data) => request.patch(`/user/roles/${id}/`, data);
export const deleteRoleApi = (id) => request.delete(`/user/roles/${id}/`);

export const getUsersApi = (params) => request.get("/user/users/", { params });
export const createUserApi = (data) => request.post("/user/users/", data);
export const updateUserApi = (id, data) => request.patch(`/user/users/${id}/`, data);
export const deleteUserApi = (id) => request.delete(`/user/users/${id}/`);

