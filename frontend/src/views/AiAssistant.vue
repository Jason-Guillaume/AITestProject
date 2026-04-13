<template>
  <div class="page-wrap cyber-page">
    <el-tabs v-model="activeTab" class="ai-tabs">
      <el-tab-pane label="用例规范审查" name="review">
        <div class="tab-content">
          <div class="section-card cyber-glass">
            <h3 class="section-title">用例规范</h3>
            <el-input
              v-model="specTemplate"
              type="textarea"
              :rows="8"
              placeholder="在此输入用例规范模板..."
              class="spec-input"
            />
          </div>
          <div class="section-card cyber-glass" style="margin-top:16px">
            <div class="section-header">
              <h3 class="section-title">用例规范规则</h3>
            </div>
            <div class="rules-list">
              <div class="rule-item" v-for="(rule, idx) in rules" :key="idx">
                <span class="rule-label">规则{{ zh[idx] }}</span>
                <el-input v-model="rules[idx]" placeholder="请输入规则内容" class="rule-input" />
                <el-button circle size="small" type="danger" plain @click="removeRule(idx)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
            <el-button type="primary" plain class="add-rule-btn" @click="addRule">
              <el-icon><Plus /></el-icon> 新增规则
            </el-button>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="用例逻辑评审" name="logic">
        <div class="tab-content empty-tip">
          <el-empty description="用例逻辑评审功能开发中" />
        </div>
      </el-tab-pane>

      <el-tab-pane label="模型接入" name="model">
        <div class="tab-content">
          <div class="section-card cyber-glass">
            <h3 class="section-title">AI 模型配置</h3>
            <p v-if="!isSystemAdmin" class="section-hint">
              配置由系统管理员维护；你可查看当前接入状态。如需「AI 生成用例」等能力，请等待管理员完成配置并保持已连接。
            </p>

            <div v-loading="configLoading" class="model-config-body">
              <div v-if="currentConfig" class="current-model-card">
                <div class="card-row card-head">
                  <span class="model-label">当前模型</span>
                  <span class="model-name">{{ normalizedConfig.model_display_name || normalizedConfig.model_type || '未识别模型' }}</span>
                </div>
                <div class="card-row status-row">
                  <span
                    class="status-dot"
                    :class="currentConfig.is_connected ? 'status-on' : 'status-off'"
                  />
                  <span class="status-text">{{
                    currentConfig.is_connected ? '已连接' : '已断开'
                  }}</span>
                  <span
                    v-if="normalizedConfig.base_url"
                    class="base-url-hint"
                    :title="normalizedConfig.base_url"
                  >
                    Base：{{ normalizedConfig.base_url }}
                  </span>
                </div>
                <div v-if="isSystemAdmin" class="card-actions">
                  <el-button
                    v-if="currentConfig.is_connected"
                    type="warning"
                    plain
                    :loading="configMutating"
                    @click="onDisconnect"
                  >
                    断开连接
                  </el-button>
                  <el-button
                    v-else
                    type="primary"
                    plain
                    :loading="configMutating"
                    @click="onReconnect"
                  >
                    重新连接
                  </el-button>
                  <el-button type="danger" plain :loading="configMutating" @click="onDeleteConfig">
                    删除
                  </el-button>
                </div>
              </div>

              <template v-else>
                <el-alert
                  v-if="!isSystemAdmin"
                  type="info"
                  show-icon
                  :closable="false"
                  title="当前尚未配置平台级 AI 模型"
                  description="请联系系统管理员在「智能助手 → 模型接入」保存 API Key。"
                  class="config-alert"
                />
                <el-form
                  v-else
                  :model="modelForm"
                  label-width="120px"
                  style="max-width:600px;margin-top:12px"
                >
                  <el-form-item label="模型类型">
                    <el-select
                      v-model="modelForm.type"
                      placeholder="请选择或输入模型（支持自定义）"
                      filterable
                      allow-create
                      default-first-option
                      style="width:100%"
                    >
                      <el-option-group label="智谱 AI (GLM)">
                        <el-option label="GLM-4.7-Flash" value="glm-4.7-flash" />
                        <el-option label="GLM-4" value="glm-4" />
                        <el-option label="GLM-4-Flash" value="glm-4-flash" />
                        <el-option label="GLM-4-Plus" value="glm-4-plus" />
                      </el-option-group>
                      <el-option-group label="讯飞 MaaS">
                        <el-option label="Astron Coding (astron-code-latest)" value="astron-code-latest" />
                      </el-option-group>
                      <el-option-group label="其他（需填写 API 地址）">
                        <el-option label="文心大模型 5.0" value="wenxin" />
                        <el-option label="GPT-4o" value="gpt-4o" />
                        <el-option label="Claude 3.5" value="claude-3-5-sonnet" />
                        <el-option label="通义千问" value="qwen-turbo" />
                      </el-option-group>
                    </el-select>
                  </el-form-item>
                  <el-form-item label="API Key">
                    <el-input v-model="modelForm.apiKey" show-password placeholder="请输入 API Key" />
                  </el-form-item>
                  <el-form-item label="API 地址">
                    <el-input
                      v-model="modelForm.baseUrl"
                      :placeholder="isIflytekMaaSSelected ? IFLYTEK_MAAS_OPENAI_BASE : '可选，自定义接入地址'"
                    />
                    <div v-if="isIflytekMaaSSelected" class="config-hint">
                      建议使用根路径：{{ IFLYTEK_MAAS_OPENAI_BASE }}（系统会自动拼接 /chat/completions）。
                    </div>
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" :loading="configMutating" @click="saveModel">保存配置</el-button>
                    <el-button :loading="llmTesting" :disabled="llmTesting" style="margin-left:8px" @click="testModel">
                      测试连接
                    </el-button>
                  </el-form-item>
                </el-form>
              </template>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import { verifyAiConnectionApi, testAiConnectionApi } from '@/api/assistant'
import {
  getAiModelConfigApi,
  saveAiModelConfigApi,
  disconnectAiModelConfigApi,
  reconnectAiModelConfigApi,
  deleteAiModelConfigApi,
} from '@/api/sysAiConfig'

const activeTab = ref('review')
const zh = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']

const specTemplate = ref(
`1. 用例名称：[核心功能+操作目的]，如"用户通过手机号验证码登录"
2. 执行者：[角色名]，如"普通用户/管理员"
3. 前置条件：[执行前需满足]，如"用户已获取验证码"
4. 操作步骤：1.[具体操作1] 2.[操作2] 如"填写验证码并提交"
5. 预期结果：[明确结果]，如"页面跳转至个人中心，显示用户名"
6. 后置条件：[执行后状态]，如"登录状态有效期2小时"
7. 优先级：高/中/低`
)

const rules = ref([
  '检测用例中重复、错别字',
  '每个步骤仅描述 1 个独立操作，且需明确定位，禁止合并操作',
  '预期结果需包含各系统明确指向，禁止模糊描述',
  '每个步骤描述 1 个独立操作，需明确"操作对象 + 动作 + 参数"',
  '用例范围需覆盖"正常场景 + 边界场景 + 异常场景"',
])

const IFLYTEK_MAAS_MODEL_TYPE = 'iflytek-spark-maas-coding'
const IFLYTEK_MAAS_OPENAI_BASE =
  'https://maas-coding-api.cn-huabei-1.xf-yun.com/v2'

const modelForm = ref({ type: '', apiKey: '', baseUrl: '' })
const llmTesting = ref(false)
const configLoading = ref(false)
const configMutating = ref(false)
const currentConfig = ref(null)

const isSystemAdmin = computed(() => localStorage.getItem('is_system_admin') === '1')
const isIflytekMaaSSelected = computed(
  () => isIflytekModelType(modelForm.value.type),
)

function isIflytekModelType(modelType) {
  const t = String(modelType || '').trim().toLowerCase()
  if (!t) return false
  return t === IFLYTEK_MAAS_MODEL_TYPE || t.includes('iflytek') || t.includes('spark') || t.includes('astron')
}

function inferModelTypeFromBaseUrl(baseUrl) {
  const b = String(baseUrl || '').toLowerCase()
  if (!b) return ''
  if (b.includes('dashscope.aliyuncs.com') || b.includes('qwen')) return 'qwen-turbo'
  if (b.includes('bigmodel.cn') || b.includes('/paas/v4')) return 'glm-4.7-flash'
  if (b.includes('xf-yun.com') || b.includes('iflytek')) return 'astron-code-latest'
  return ''
}

function inferModelDisplayName(modelType) {
  const t = String(modelType || '').toLowerCase()
  if (!t) return ''
  if (t === 'qwen-turbo') return '通义千问'
  if (t === 'glm-4.7-flash') return 'GLM-4.7-Flash'
  if (t === 'glm-4') return 'GLM-4'
  if (t === 'glm-4-flash') return 'GLM-4-Flash'
  if (t === 'glm-4-plus') return 'GLM-4-Plus'
  if (t === IFLYTEK_MAAS_MODEL_TYPE) return 'iFLYTEK Spark MaaS Coding'
  if (t === 'astron-code-latest') return 'Astron Coding'
  return modelType
}

const normalizedConfig = computed(() => {
  const cfg = currentConfig.value || {}
  const base = String(cfg.base_url || '').trim()
  const rawType = String(cfg.model_type || '').trim()
  const inferredType = inferModelTypeFromBaseUrl(base)
  const modelType = rawType || inferredType
  const modelDisplayName =
    String(cfg.model_display_name || '').trim() || inferModelDisplayName(modelType)
  return {
    ...cfg,
    model_type: modelType,
    model_display_name: modelDisplayName,
    base_url: base,
  }
})

function syncModelFormFromConfig() {
  const cfg = normalizedConfig.value
  // 兼容旧配置：历史别名自动迁移到可直接调用的具体模型名
  modelForm.value.type = cfg.model_type === IFLYTEK_MAAS_MODEL_TYPE ? 'astron-code-latest' : (cfg.model_type || '')
  modelForm.value.baseUrl = cfg.base_url || ''
}

watch(
  () => modelForm.value.type,
  (type) => {
    if (isIflytekModelType(type) && !(modelForm.value.baseUrl || '').trim()) {
      modelForm.value.baseUrl = IFLYTEK_MAAS_OPENAI_BASE
    }
  },
  { immediate: true },
)

async function loadAiConfig() {
  configLoading.value = true
  try {
    const { data } = await getAiModelConfigApi()
    if (data?.code === 200 && data?.data) {
      currentConfig.value = data.data
      syncModelFormFromConfig()
    } else {
      currentConfig.value = null
      modelForm.value.type = ''
      modelForm.value.baseUrl = ''
    }
  } catch {
    currentConfig.value = null
    modelForm.value.type = ''
    modelForm.value.baseUrl = ''
  } finally {
    configLoading.value = false
  }
}

function addRule() {
  rules.value.push('')
}

function removeRule(idx) {
  rules.value.splice(idx, 1)
}

async function saveModel() {
  const key = (modelForm.value.apiKey || '').trim()
  if (!key) {
    ElMessage.warning('请填写 API Key')
    return
  }
  configMutating.value = true
  try {
    const { data } = await saveAiModelConfigApi({
      model_type: modelForm.value.type,
      api_key: key,
      base_url: (modelForm.value.baseUrl || '').trim(),
    })
    if (data?.code === 200) {
      ElMessage.success(data.msg || '模型配置已保存')
      currentConfig.value = data.data || null
      syncModelFormFromConfig()
      modelForm.value.apiKey = ''
    } else {
      ElMessage.error(data?.msg || '保存失败')
    }
  } catch (err) {
    const msg =
      err?.response?.data?.detail ||
      err?.response?.data?.msg ||
      err?.message ||
      '保存失败，请确认当前账号为系统管理员'
    ElMessage.error(typeof msg === 'string' ? msg : '保存失败')
  } finally {
    configMutating.value = false
  }
}

async function onDisconnect() {
  configMutating.value = true
  try {
    const { data } = await disconnectAiModelConfigApi()
    if (data?.code === 200 && data?.data) {
      currentConfig.value = data.data
      syncModelFormFromConfig()
      ElMessage.success(data.msg || '已断开')
    } else {
      ElMessage.warning(data?.msg || '操作失败')
    }
  } catch (err) {
    ElMessage.error(err?.response?.data?.detail || '操作失败')
  } finally {
    configMutating.value = false
  }
}

async function onReconnect() {
  configMutating.value = true
  try {
    const { data } = await reconnectAiModelConfigApi()
    if (data?.code === 200 && data?.data) {
      currentConfig.value = data.data
      syncModelFormFromConfig()
      ElMessage.success(data.msg || '已重新连接')
    } else {
      ElMessage.warning(data?.msg || '操作失败')
    }
  } catch (err) {
    ElMessage.error(err?.response?.data?.detail || '操作失败')
  } finally {
    configMutating.value = false
  }
}

async function onDeleteConfig() {
  try {
    await ElMessageBox.confirm(
      '确定要删除当前 AI 模型配置吗？删除后 API Key 将从服务器移除，需重新填写保存。',
      '删除配置',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  configMutating.value = true
  try {
    const { data } = await deleteAiModelConfigApi()
    if (data?.code === 200) {
      ElMessage.success(data.msg || '已删除')
      currentConfig.value = null
      modelForm.value.type = ''
      modelForm.value.baseUrl = ''
    } else {
      ElMessage.warning(data?.msg || '删除失败')
    }
  } catch (err) {
    ElMessage.error(err?.response?.data?.detail || '删除失败')
  } finally {
    configMutating.value = false
  }
}

async function testModel() {
  const apiKey = (modelForm.value.apiKey || '').trim()
  if (!apiKey) {
    ElMessage.warning('请先填写 API Key')
    return
  }
  llmTesting.value = true
  try {
    const normalizedBaseUrl = (modelForm.value.baseUrl || '').trim()
    const useZhipuShortcut =
      modelForm.value.type === 'glm-4.7-flash' && !normalizedBaseUrl
    const { data } = useZhipuShortcut
      ? await verifyAiConnectionApi({ api_key: apiKey })
      : await testAiConnectionApi({
          api_key: apiKey,
          model: modelForm.value.type,
          api_base_url: normalizedBaseUrl || undefined,
        })
    if (data?.success) {
      const reply = data.reply
      ElMessage.success(
        reply ? `${data.message || '连接成功'}：${reply}` : data.message || '连接成功',
      )
    } else {
      ElMessage.error(data?.error || data?.message || '连接失败')
    }
  } catch (err) {
    const msg =
      err?.response?.data?.error ||
      err?.response?.data?.msg ||
      err?.response?.data?.detail ||
      err?.message ||
      '请求失败，请检查网络或登录状态'
    ElMessage.error(typeof msg === 'string' ? msg : '请求失败')
  } finally {
    llmTesting.value = false
  }
}

onMounted(() => {
  try {
    const tab = new URLSearchParams(window.location.search).get('tab')
    if (tab === 'model') {
      activeTab.value = 'model'
    }
  } catch {
    /* ignore invalid URL parsing */
  }
  loadAiConfig()
  window.addEventListener('focus', loadAiConfig)
  document.addEventListener('visibilitychange', handleVisibilityRefresh)
})

function handleVisibilityRefresh() {
  if (document.visibilityState === 'visible') loadAiConfig()
}

onUnmounted(() => {
  window.removeEventListener('focus', loadAiConfig)
  document.removeEventListener('visibilitychange', handleVisibilityRefresh)
})
</script>

<style scoped>
.page-wrap {
  background: transparent;
  border-radius: 10px;
  padding: 16px;
  min-height: 400px;
}

.ai-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.ai-tabs :deep(.el-tabs__item) {
  color: rgba(226, 232, 240, 0.65);
}

.ai-tabs :deep(.el-tabs__item.is-active) {
  color: #00d8ff;
}

.ai-tabs :deep(.el-tabs__active-bar) {
  background: #00d8ff;
  box-shadow: 0 0 10px rgba(0, 216, 255, 0.45);
}

.tab-content { padding: 16px 0; }

.section-card {
  border-radius: 10px;
}

.section-card.cyber-glass {
  transition:
    border-color 0.25s ease,
    box-shadow 0.25s ease;
}

.section-card.cyber-glass:hover {
  border-color: rgba(0, 255, 255, 0.25);
  box-shadow: 0 0 22px rgba(0, 216, 255, 0.1);
}

.section-header { display: flex; align-items: center; justify-content: space-between; }
.section-title { font-size: 14px; font-weight: 600; color: #e2e8f0; margin: 0 0 12px 0; }
.section-hint {
  font-size: 12px;
  color: rgba(226, 232, 240, 0.55);
  margin: 0 0 12px 0;
  line-height: 1.5;
}
.model-config-body { min-height: 80px; margin-top: 8px; }
.current-model-card {
  max-width: 560px;
  padding: 16px 18px;
  border-radius: 10px;
  border: 1px solid rgba(0, 255, 255, 0.12);
  background: rgba(8, 12, 22, 0.35);
}
.card-row { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.card-head { margin-bottom: 12px; }
.model-label { font-size: 12px; color: rgba(226, 232, 240, 0.5); margin-right: 8px; }
.model-name { font-size: 15px; font-weight: 600; color: #e2e8f0; }
.status-row { margin-bottom: 16px; }
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-dot.status-on {
  background: #22c55e;
  box-shadow: 0 0 8px rgba(34, 197, 94, 0.55);
}
.status-dot.status-off {
  background: rgba(226, 232, 240, 0.35);
}
.status-text { font-size: 13px; color: rgba(226, 232, 240, 0.85); }
.base-url-hint {
  font-size: 12px;
  color: rgba(226, 232, 240, 0.45);
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card-actions { display: flex; flex-wrap: wrap; gap: 10px; }
.config-alert { margin-top: 8px; max-width: 560px; }
.config-alert :deep(.el-alert__title) { color: #e2e8f0; }
.config-alert :deep(.el-alert__description) { color: rgba(226, 232, 240, 0.65); }
.config-hint {
  margin-top: 6px;
  font-size: 12px;
  color: rgba(226, 232, 240, 0.55);
  line-height: 1.45;
}

.spec-input :deep(.el-textarea__inner) {
  font-size: 13px;
  line-height: 1.8;
  background: rgba(8, 12, 22, 0.45);
  color: #e2e8f0;
  border: 1px solid rgba(0, 255, 255, 0.12);
  box-shadow: none;
}

.rules-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 12px; }
.rule-item { display: flex; align-items: center; gap: 10px; }
.rule-label { flex-shrink: 0; font-size: 13px; color: rgba(226, 232, 240, 0.65); min-width: 40px; }
.rule-input { flex: 1; }

.rule-input :deep(.el-input__wrapper) {
  background: rgba(10, 16, 28, 0.45);
  box-shadow: none;
  border: 1px solid rgba(0, 255, 255, 0.1);
}

.add-rule-btn {
  width: 100%;
  border-style: dashed;
  border-color: rgba(0, 255, 255, 0.25);
  color: rgba(226, 232, 240, 0.85);
  background: transparent;
}

.add-rule-btn:hover {
  border-color: rgba(0, 216, 255, 0.45);
  color: #00d8ff;
  background: rgba(0, 216, 255, 0.06);
}

.empty-tip { display: flex; justify-content: center; padding: 60px 0; }

.empty-tip :deep(.el-empty__description) {
  color: rgba(226, 232, 240, 0.55);
}

.page-wrap :deep(.el-form-item__label) {
  color: rgba(226, 232, 240, 0.78);
}

.page-wrap :deep(.el-input__wrapper),
.page-wrap :deep(.el-select .el-input__wrapper) {
  background: rgba(10, 16, 28, 0.45);
  box-shadow: none;
  border: 1px solid rgba(0, 255, 255, 0.1);
}
</style>
