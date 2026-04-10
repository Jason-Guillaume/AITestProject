import request from '@/utils/request'

/** GET /api/sys/ai-config/ */
export const getAiModelConfigApi = () => request.get('/sys/ai-config/')

/** PUT /api/sys/ai-config/ — 系统管理员；更新时 api_key 可留空以保留原 Key */
export const saveAiModelConfigApi = (data) => request.put('/sys/ai-config/', data)

/** POST /api/sys/ai-config/disconnect/ */
export const disconnectAiModelConfigApi = () => request.post('/sys/ai-config/disconnect/')

/** POST /api/sys/ai-config/reconnect/ — 在保留 Key 的前提下恢复 is_connected */
export const reconnectAiModelConfigApi = () => request.post('/sys/ai-config/reconnect/')

/** DELETE /api/sys/ai-config/ */
export const deleteAiModelConfigApi = () => request.delete('/sys/ai-config/')
