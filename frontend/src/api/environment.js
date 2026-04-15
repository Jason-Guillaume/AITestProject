import request from "@/utils/request";

export function getEnvironments(params) {
  return request.get("/environments/", { params });
}

export function createEnvironment(data) {
  return request.post("/environments/", data);
}

export function updateEnvironment(id, data) {
  return request.patch(`/environments/${id}/`, data);
}

export function deleteEnvironment(id) {
  return request.delete(`/environments/${id}/`);
}

export function validateEnvironment(id, data = {}) {
  return request.post(`/environments/${id}/validate/`, data);
}
