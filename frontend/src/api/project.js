import request from "@/utils/request";

export const getProjectsApi = (params) => request.get("/project/projects/", { params });
export const createProjectApi = (data) => request.post("/project/projects/", data);
export const updateProjectApi = (id, data) => request.patch(`/project/projects/${id}/`, data);
export const deleteProjectApi = (id) => request.delete(`/project/projects/${id}/`);

export const getTasksApi = (params) => request.get("/project/tasks/", { params });
export const createTaskApi = (data) => request.post("/project/tasks/", data);
export const updateTaskApi = (id, data) => request.patch(`/project/tasks/${id}/`, data);
export const deleteTaskApi = (id) => request.delete(`/project/tasks/${id}/`);

export const getReleasesApi = (params) => request.get("/project/releases/", { params });
export const createReleaseApi = (data) => request.post("/project/releases/", data);
export const updateReleaseApi = (id, data) => request.patch(`/project/releases/${id}/`, data);
export const deleteReleaseApi = (id) => request.delete(`/project/releases/${id}/`);
export const getReleaseDetailApi = (id) => request.get(`/project/releases/${id}/`);
