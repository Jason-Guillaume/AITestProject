/**
 * UI元素库API
 */
import request from '@/utils/request';

/**
 * 获取模块树形结构
 */
export function getUIModulesTree(projectId) {
  return request.get('/ai/ui-modules/tree/', { params: { project_id: projectId } });
}

/**
 * 获取所有模块（扁平列表）
 */
export function getAllUIModules(projectId) {
  return request.get('/ai/ui-modules/', { params: { project_id: projectId } });
}

/**
 * 创建模块
 */
export function createUIModule(data) {
  return request.post('/ai/ui-modules/', data);
}

/**
 * 更新模块
 */
export function updateUIModule(id, data) {
  return request.put(`/ai/ui-modules/${id}/`, data);
}

/**
 * 删除模块
 */
export function deleteUIModule(id) {
  return request.delete(`/ai/ui-modules/${id}/`);
}

/**
 * 获取页面列表
 */
export function getUIPages(moduleId) {
  return request.get('/ai/ui-pages/', { params: { module_id: moduleId } });
}

/**
 * 创建页面
 */
export function createUIPage(data) {
  return request.post('/ai/ui-pages/', data);
}

/**
 * 更新页面
 */
export function updateUIPage(id, data) {
  return request.put(`/ai/ui-pages/${id}/`, data);
}

/**
 * 删除页面
 */
export function deleteUIPage(id) {
  return request.delete(`/ai/ui-pages/${id}/`);
}

/**
 * 获取页面元素列表
 */
export function getUIPageElements(pageId, search = '') {
  return request.get('/ai/ui-elements/', { params: { page_id: pageId, search } });
}

/**
 * 根据元素名称查找元素
 */
export function getUIElementByName(name, pageId = null) {
  return request.get('/ai/ui-elements/by_name/', { params: { name, page_id: pageId } });
}

/**
 * 创建页面元素
 */
export function createUIPageElement(data) {
  return request.post('/ai/ui-elements/', data);
}

/**
 * 更新页面元素
 */
export function updateUIPageElement(id, data) {
  return request.put(`/ai/ui-elements/${id}/`, data);
}

/**
 * 删除页面元素
 */
export function deleteUIPageElement(id) {
  return request.delete(`/ai/ui-elements/${id}/`);
}

/**
 * 获取测试用例列表
 */
export function getUITestCases(moduleId) {
  return request.get('/ai/ui-test-cases/', { params: { module_id: moduleId } });
}

/**
 * 创建测试用例
 */
export function createUITestCase(data) {
  return request.post('/ai/ui-test-cases/', data);
}

/**
 * 更新测试用例
 */
export function updateUITestCase(id, data) {
  return request.put(`/ai/ui-test-cases/${id}/`, data);
}

/**
 * 删除测试用例
 */
export function deleteUITestCase(id) {
  return request.delete(`/ai/ui-test-cases/${id}/`);
}

/**
 * 获取操作步骤列表
 */
export function getUIActionSteps(testCaseId) {
  return request.get('/ai/ui-action-steps/', { params: { test_case_id: testCaseId } });
}

/**
 * 创建操作步骤
 */
export function createUIActionStep(data) {
  return request.post('/ai/ui-action-steps/', data);
}

/**
 * 更新操作步骤
 */
export function updateUIActionStep(id, data) {
  return request.put(`/ai/ui-action-steps/${id}/`, data);
}

/**
 * 删除操作步骤
 */
export function deleteUIActionStep(id) {
  return request.delete(`/ai/ui-action-steps/${id}/`);
}
