import request from '@/utils/request'

export function getKWLocators(projectId) {
  return request.get('/ai/kw-locators/', { params: { project: projectId } })
}

export function createKWLocator(data) {
  return request.post('/ai/kw-locators/', data)
}

export function updateKWLocator(id, data) {
  return request.patch(`/ai/kw-locators/${id}/`, data)
}

export function deleteKWLocator(id) {
  return request.delete(`/ai/kw-locators/${id}/`)
}

export function getKWTestCases(projectId) {
  return request.get('/ai/kw-test-cases/', { params: { project: projectId } })
}

export function getKWTestCaseDetail(id) {
  return request.get(`/ai/kw-test-cases/${id}/`)
}

export function createKWTestCase(data) {
  return request.post('/ai/kw-test-cases/', data)
}

export function updateKWTestCase(id, data) {
  return request.patch(`/ai/kw-test-cases/${id}/`, data)
}

export function deleteKWTestCase(id) {
  return request.delete(`/ai/kw-test-cases/${id}/`)
}

export function getKWActionSteps(testCaseId) {
  return request.get('/ai/kw-action-steps/', { params: { test_case: testCaseId } })
}

export function createKWActionStep(data) {
  return request.post('/ai/kw-action-steps/', data)
}

export function updateKWActionStep(id, data) {
  return request.patch(`/ai/kw-action-steps/${id}/`, data)
}

export function deleteKWActionStep(id) {
  return request.delete(`/ai/kw-action-steps/${id}/`)
}

export function batchUpdateKWActionSteps(steps) {
  return request.put('/ai/kw-action-steps/batch/', steps)
}

export function getKWTestCaseExecutorBlueprint(id) {
  return request.get(`/ai/kw-test-cases/${id}/executor_blueprint/`)
}

export function executeKWTestCase(id, params = {}) {
  return request.post(`/ai/kw-test-cases/${id}/execute/`, {
    browser: params.browser || 'chrome',
    headless: params.headless !== undefined ? params.headless : true,
  })
}

export function getKWExecutionStatus(executionId) {
  return request.get('/ai/kw-test-cases/execution-status/', {
    params: { execution_id: executionId },
  })
}

export function getKWExecutionLogs(executionId, start = 0, end = -1) {
  return request.get('/ai/kw-test-cases/execution-logs/', {
    params: { execution_id: executionId, start, end },
  })
}

export function getKWExecutionSteps(executionId) {
  return request.get('/ai/kw-test-cases/execution-steps/', {
    params: { execution_id: executionId },
  })
}

export function cancelKWExecution(executionId) {
  return request.post('/ai/kw-test-cases/cancel-execution/', {
    execution_id: executionId,
  })
}
