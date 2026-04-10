import request from "@/utils/request";

export function getEnvironments(params) {
  return request.get("/testcase/environments/", { params });
}

export function createEnvironment(data) {
  return request.post("/testcase/environments/", data);
}

export function updateEnvironment(id, data) {
  return request.patch(`/testcase/environments/${id}/`, data);
}

export function deleteEnvironment(id) {
  return request.delete(`/testcase/environments/${id}/`);
}

export function validateEnvironment(id, data = {}) {
  return request.post(`/testcase/environments/${id}/validate/`, data);
}
