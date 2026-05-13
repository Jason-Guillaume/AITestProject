<template>
  <div class="mc">
    <div
      v-if="isLoading"
      class="mc__loading"
    >
      <div class="mc__loading-spinner" />
      <p class="mc__loading-text">
        加载配置中...
      </p>
    </div>

    <div
      v-else
      class="mc__form"
    >
      <div class="mc__header">
        <h2 class="mc__title">
          AI 模型配置
        </h2>
        <p class="mc__subtitle">
          配置 OpenAI 兼容的 API 端点，用于 AI 驱动的测试功能
        </p>
      </div>

      <div class="mc__core">
        <div class="mc__field">
          <div class="mc__label-row">
            <label class="mc__label">API Provider</label>
            <span class="mc__badge">只读</span>
          </div>
          <div class="mc__input-wrap">
            <input
              v-model="formData.provider"
              type="text"
              class="mc__input mc__input--readonly"
              readonly
              placeholder="OpenAI Compatible"
            >
          </div>
          <span class="mc__hint">支持任何 OpenAI 兼容的 API 端点</span>
        </div>

        <div class="mc__field">
          <div class="mc__label-row">
            <label class="mc__label">Base URL</label>
            <el-tooltip
              content="API 请求的基础地址。留空则使用默认 OpenAI 端点"
              placement="top"
              :show-after="300"
            >
              <span class="mc__help">?</span>
            </el-tooltip>
          </div>
          <div class="mc__input-wrap">
            <input
              v-model="formData.baseUrl"
              type="text"
              class="mc__input"
              placeholder="https://api.openai.com/v1"
              :disabled="!isEditMode"
            >
          </div>
        </div>

        <div class="mc__field">
          <div class="mc__label-row">
            <label class="mc__label">API Key</label>
            <el-tooltip
              content="用于验证身份的密钥，安全存储且仅用于本平台发起 API 请求"
              placement="top"
              :show-after="300"
            >
              <span class="mc__help">?</span>
            </el-tooltip>
          </div>
          <div class="mc__input-wrap mc__input-wrap--with-action">
            <input
              v-model="formData.apiKey"
              :type="showApiKey ? 'text' : 'password'"
              class="mc__input"
              :placeholder="isEditMode && isSaved ? '输入新的 API Key 以更新' : 'sk-...'"
              :disabled="!isEditMode"
            >
            <button
              type="button"
              class="mc__input-action"
              :title="showApiKey ? '隐藏' : '显示'"
              @click="showApiKey = !showApiKey"
            >
              <svg
                v-if="showApiKey"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
              >
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                <line
                  x1="1"
                  y1="1"
                  x2="23"
                  y2="23"
                />
              </svg>
              <svg
                v-else
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
              >
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                <circle
                  cx="12"
                  cy="12"
                  r="3"
                />
              </svg>
            </button>
          </div>
          <span
            v-if="isEditMode && isSaved"
            class="mc__hint"
          >更新配置时需重新输入 API Key</span>
        </div>

        <div class="mc__field">
          <div class="mc__label-row">
            <label class="mc__label">Model ID</label>
            <el-tooltip
              content="要调用的模型标识符，如 gpt-4o、glm-4-flash、claude-3-opus"
              placement="top"
              :show-after="300"
            >
              <span class="mc__help">?</span>
            </el-tooltip>
          </div>
          <div class="mc__input-wrap">
            <input
              v-model="formData.modelId"
              type="text"
              class="mc__input"
              placeholder="gpt-4o / glm-4-flash / claude-3-opus"
              :disabled="!isEditMode"
            >
          </div>
        </div>
      </div>

      <div class="mc__advanced">
        <button
          type="button"
          class="mc__advanced-toggle"
          @click="showAdvanced = !showAdvanced"
        >
          <svg
            class="mc__advanced-chevron"
            :class="{ 'mc__advanced-chevron--open': showAdvanced }"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
          >
            <polyline points="9 18 15 12 9 6" />
          </svg>
          <span>⚙️ 高级选项 (Advanced Settings)</span>
          <span class="mc__advanced-count">{{ advancedCount }}</span>
        </button>

        <transition name="mc-slide">
          <div
            v-if="showAdvanced"
            class="mc__advanced-body"
          >
            <div class="mc__field">
              <div class="mc__label-row">
                <label class="mc__label">Context Length</label>
                <el-tooltip
                  content="模型单次请求可处理的最大 token 数。值越大能处理越长文本，但费用更高"
                  placement="top"
                  :show-after="300"
                >
                  <span class="mc__help">?</span>
                </el-tooltip>
              </div>
              <div class="mc__input-wrap">
                <input
                  v-model.number="formData.contextLength"
                  type="number"
                  class="mc__input"
                  placeholder="4096"
                  min="1"
                  :disabled="!isEditMode"
                >
              </div>
              <span class="mc__hint">默认 4096，增大可处理更长上下文</span>
            </div>

            <div class="mc__field">
              <div class="mc__label-row">
                <label class="mc__label">Custom Headers</label>
                <el-tooltip
                  content="附加到每次 API 请求的自定义 HTTP 头，如鉴权或代理所需字段"
                  placement="top"
                  :show-after="300"
                >
                  <span class="mc__help">?</span>
                </el-tooltip>
              </div>
              <div class="mc__headers">
                <div
                  v-for="(header, index) in formData.customHeaders"
                  :key="index"
                  class="mc__header-row"
                >
                  <div class="mc__input-wrap">
                    <input
                      v-model="header.key"
                      type="text"
                      class="mc__input"
                      placeholder="Header Name"
                      :disabled="!isEditMode"
                    >
                  </div>
                  <div class="mc__input-wrap">
                    <input
                      v-model="header.value"
                      type="text"
                      class="mc__input"
                      placeholder="Header Value"
                      :disabled="!isEditMode"
                    >
                  </div>
                  <button
                    v-if="isEditMode"
                    type="button"
                    class="mc__header-remove"
                    title="删除"
                    @click="removeHeader(index)"
                  >
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                    >
                      <line
                        x1="18"
                        y1="6"
                        x2="6"
                        y2="18"
                      /><line
                        x1="6"
                        y1="6"
                        x2="18"
                        y2="18"
                      />
                    </svg>
                  </button>
                </div>
              </div>
              <button
                v-if="isEditMode"
                type="button"
                class="mc__header-add"
                @click="addHeader"
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                >
                  <line
                    x1="12"
                    y1="5"
                    x2="12"
                    y2="19"
                  /><line
                    x1="5"
                    y1="12"
                    x2="19"
                    y2="12"
                  />
                </svg>
                添加 Header
              </button>
            </div>
          </div>
        </transition>
      </div>

      <div class="mc__actions">
        <button
          v-if="!isEditMode"
          type="button"
          class="mc__btn mc__btn--outline"
          @click="enableEditMode"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
          >
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
          </svg>
          更改配置
        </button>

        <template v-if="isEditMode">
          <button
            type="button"
            class="mc__btn mc__btn--primary"
            :disabled="isSaving || isTesting"
            @click="handleSave"
          >
            <span
              v-if="isSaving"
              class="mc__btn-spinner"
            />
            {{ isSaving ? '保存中...' : '保存配置' }}
          </button>
          <button
            type="button"
            class="mc__btn mc__btn--ghost"
            :disabled="isSaving || isTesting"
            @click="handleTest"
          >
            <span
              v-if="isTesting"
              class="mc__btn-spinner"
            />
            {{ isTesting ? '连接中...' : '测试连接' }}
          </button>
          <button
            v-if="isSaved"
            type="button"
            class="mc__btn mc__btn--cancel"
            :disabled="isSaving || isTesting"
            @click="cancelEdit"
          >
            取消
          </button>
        </template>
      </div>

      <div
        v-if="testResult || testError"
        class="mc__result"
      >
        <div
          v-if="testResult"
          class="mc__result-box mc__result-box--success"
        >
          <div class="mc__result-head">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
            >
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />
            </svg>
            <span>{{ testResult.message }}</span>
          </div>
          <div class="mc__result-body">
            <div class="mc__result-item">
              <span class="mc__result-label">Model</span><span class="mc__result-value">{{ testResult.model }}</span>
            </div>
            <div class="mc__result-item">
              <span class="mc__result-label">Response</span><span class="mc__result-value">{{ testResult.response }}</span>
            </div>
            <div
              v-if="testResult.usage"
              class="mc__result-item"
            >
              <span class="mc__result-label">Usage</span>
              <span class="mc__result-value">{{ testResult.usage.prompt_tokens }} prompt + {{ testResult.usage.completion_tokens }} completion = {{ testResult.usage.total_tokens }} tokens</span>
            </div>
          </div>
        </div>

        <div
          v-if="testError"
          class="mc__result-box mc__result-box--error"
        >
          <div class="mc__result-head">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
            >
              <circle
                cx="12"
                cy="12"
                r="10"
              /><line
                x1="15"
                y1="9"
                x2="9"
                y2="15"
              /><line
                x1="9"
                y1="9"
                x2="15"
                y2="15"
              />
            </svg>
            <span>{{ testError.message }}</span>
          </div>
          <div class="mc__result-body">
            <div class="mc__result-item">
              <span class="mc__result-label">Details</span><span class="mc__result-value mc__result-value--error">{{ testError.details }}</span>
            </div>
            <div
              v-if="testError.fullError"
              class="mc__result-item"
            >
              <span class="mc__result-label">Technical Info</span>
              <pre class="mc__result-code">{{ JSON.stringify(testError.fullError, null, 2) }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { getAiModelConfigApi, saveAiModelConfigApi } from '@/api/sysAiConfig'

const formData = reactive({
  provider: 'OpenAI Compatible',
  baseUrl: '',
  apiKey: '',
  modelId: '',
  contextLength: null,
  customHeaders: []
})

const showApiKey = ref(false)
const showAdvanced = ref(false)
const isSaving = ref(false)
const isTesting = ref(false)
const testResult = ref(null)
const testError = ref(null)
const isEditMode = ref(true)
const isSaved = ref(false)
const isLoading = ref(true)

const advancedCount = computed(() => {
  let n = 0
  if (formData.contextLength) n++
  if (formData.customHeaders.length) n += formData.customHeaders.length
  return n
})

const addHeader = () => {
  formData.customHeaders.push({ key: '', value: '' })
}

const removeHeader = (index) => {
  formData.customHeaders.splice(index, 1)
}

const handleSave = async () => {
  if (!formData.modelId.trim()) {
    ElMessage.warning('请输入 Model ID')
    return
  }
  if (isSaved.value && !formData.apiKey.trim()) {
    ElMessage.warning('请输入 API Key 以更新配置')
    return
  }
  if (!isSaved.value && !formData.apiKey.trim()) {
    ElMessage.warning('请输入 API Key')
    return
  }

  isSaving.value = true
  try {
    const payload = {
      model_type: formData.modelId.trim(),
      base_url: formData.baseUrl.trim() || '',
      is_connected: true
    }
    if (formData.apiKey.trim()) {
      payload.api_key = formData.apiKey.trim()
    }
    const { data } = await saveAiModelConfigApi(payload)
    if (data && data.code === 200) {
      isSaved.value = true
      isEditMode.value = false
      formData.apiKey = '********'
      ElMessage.success(data.msg || '配置保存成功')
    } else {
      throw new Error(data?.msg || '保存失败')
    }
  } catch (error) {
    console.error('Save failed:', error)
    ElMessage.error(error.response?.data?.msg || error.message || '保存配置失败')
  } finally {
    isSaving.value = false
  }
}

const enableEditMode = () => {
  isEditMode.value = true
  if (formData.apiKey === '********') {
    formData.apiKey = ''
  }
}

const cancelEdit = () => {
  if (isSaved.value) {
    isEditMode.value = false
    formData.apiKey = '********'
    ElMessage.info('已取消更改')
  }
}

const handleTest = async () => {
  if (!formData.apiKey.trim()) {
    ElMessage.warning('请输入 API Key')
    return
  }
  if (!formData.modelId.trim()) {
    ElMessage.warning('请输入 Model ID')
    return
  }

  testResult.value = null
  testError.value = null
  isTesting.value = true

  try {
    let apiUrl = formData.baseUrl.trim() || 'https://api.iamhc.cn/v1'
    if (apiUrl.endsWith('/')) {
      apiUrl = apiUrl.slice(0, -1)
    }

    const useProxy = apiUrl.includes('api.iamhc.cn')
    const requestUrl = useProxy
      ? '/ai-api/v1/chat/completions'
      : `${apiUrl}/chat/completions`

    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${formData.apiKey.trim()}`
    }
    formData.customHeaders.forEach(header => {
      if (header.key && header.value) {
        headers[header.key] = header.value
      }
    })

    const payload = {
      model: formData.modelId.trim(),
      messages: [{ role: 'user', content: 'Hello! Please respond with a simple greeting to confirm the connection.' }],
      max_tokens: 50,
      temperature: 0.7
    }

    const response = await axios.post(requestUrl, payload, { headers, timeout: 30000 })

    if (response.data && response.data.choices && response.data.choices.length > 0) {
      testResult.value = {
        success: true,
        message: '连接成功！',
        response: response.data.choices[0].message.content,
        model: response.data.model || formData.modelId,
        usage: response.data.usage
      }
    } else {
      throw new Error('Invalid response format from API')
    }
  } catch (error) {
    console.error('Connection test failed:', error)
    let errorMessage = '连接测试失败'
    let errorDetails = ''

    if (error.response) {
      const status = error.response.status
      const data = error.response.data
      switch (status) {
        case 401: errorMessage = '401 未授权'; errorDetails = 'API Key 无效，请检查凭证'; break
        case 403: errorMessage = '403 禁止访问'; errorDetails = '权限不足，API Key 可能没有访问权限'; break
        case 404: errorMessage = '404 未找到'; errorDetails = 'API 端点不存在，请检查 Base URL'; break
        case 429: errorMessage = '429 请求过多'; errorDetails = '触发速率限制，请稍后重试'; break
        case 500: errorMessage = '500 服务器错误'; errorDetails = 'API 服务器内部错误'; break
        default: errorMessage = `${status} 错误`; errorDetails = data?.error?.message || data?.message || '未知错误'
      }
    } else if (error.request) {
      errorMessage = '网络超时'
      errorDetails = '服务器无响应，请检查 Base URL 和网络连接'
    } else {
      errorMessage = '请求错误'
      errorDetails = error.message || '发送请求失败'
    }

    testError.value = {
      success: false,
      message: errorMessage,
      details: errorDetails,
      fullError: error.response?.data || error.message
    }
  } finally {
    isTesting.value = false
  }
}

const loadConfig = async () => {
  isLoading.value = true
  try {
    const { data } = await getAiModelConfigApi()
    if (data && data.code === 200 && data.data) {
      const config = data.data
      formData.baseUrl = config.base_url || ''
      formData.apiKey = '********'
      formData.modelId = config.model_type || ''
      isSaved.value = true
      isEditMode.value = false
    } else {
      isEditMode.value = true
      isSaved.value = false
    }
  } catch (error) {
    console.error('Failed to load config:', error)
    isEditMode.value = true
    isSaved.value = false
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped lang="scss">
.mc {
  max-width: 640px;
  margin: 0 auto;
  color: #e2e8f0;
}

.mc__loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 20px;
  gap: 16px;
}

.mc__loading-spinner {
  width: 32px;
  height: 32px;
  border: 2px solid rgba(255, 255, 255, 0.08);
  border-top-color: #00d8ff;
  border-radius: 50%;
  animation: mc-spin 0.8s linear infinite;
}

@keyframes mc-spin {
  to { transform: rotate(360deg); }
}

.mc__loading-text {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}

.mc__form {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.mc__header {
  margin-bottom: 32px;
}

.mc__title {
  font-size: 20px;
  font-weight: 700;
  color: #f8fafc;
  margin: 0 0 6px;
  letter-spacing: -0.02em;
}

.mc__subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 0;
  line-height: 1.5;
}

.mc__core {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.mc__field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.mc__label-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.mc__label {
  font-size: 13px;
  font-weight: 500;
  color: #94a3b8;
}

.mc__badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.06);
  color: #64748b;
  font-weight: 500;
}

.mc__help {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.06);
  color: #64748b;
  font-size: 10px;
  font-weight: 700;
  cursor: help;
  flex-shrink: 0;
  transition: background 0.2s ease, color 0.2s ease;

  &:hover {
    background: rgba(0, 216, 255, 0.15);
    color: #22d3ee;
  }
}

.mc__input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.mc__input-wrap--with-action {
  .mc__input {
    padding-right: 40px;
  }
}

.mc__input {
  width: 100%;
  padding: 8px 0;
  font-size: 14px;
  font-family: 'Bahnschrift', 'DIN Alternate', 'Roboto Mono', ui-monospace, 'SF Mono', 'Cascadia Code', monospace;
  font-variant-numeric: tabular-nums;
  color: #e2e8f0;
  background: transparent;
  border: none;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 0;
  outline: none;
  transition: border-color 0.25s ease, box-shadow 0.25s ease;

  &::placeholder {
    color: #475569;
    font-family: inherit;
  }

  &:focus {
    border-bottom-color: #00d8ff;
    box-shadow: 0 1px 0 0 #00d8ff, 0 2px 12px rgba(0, 216, 255, 0.15);
  }

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
}

.mc__input--readonly {
  opacity: 0.5;
  cursor: default;
}

.mc__input-action {
  position: absolute;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: #64748b;
  cursor: pointer;
  transition: color 0.2s ease, background 0.2s ease;

  svg {
    width: 16px;
    height: 16px;
  }

  &:hover {
    color: #94a3b8;
    background: rgba(255, 255, 255, 0.04);
  }
}

.mc__hint {
  font-size: 11px;
  color: #475569;
  line-height: 1.4;
}

.mc__advanced {
  margin-top: 28px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding-top: 4px;
}

.mc__advanced-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 12px 0;
  font-size: 13px;
  font-weight: 500;
  color: #64748b;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: color 0.2s ease;

  &:hover {
    color: #94a3b8;
  }
}

.mc__advanced-chevron {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  transition: transform 0.25s ease;
}

.mc__advanced-chevron--open {
  transform: rotate(90deg);
}

.mc__advanced-count {
  margin-left: auto;
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  color: #64748b;
  font-weight: 500;
}

.mc__advanced-body {
  padding-top: 4px;
  padding-bottom: 8px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.mc-slide-enter-active {
  transition: all 0.25s ease;
}

.mc-slide-leave-active {
  transition: all 0.2s ease;
}

.mc-slide-enter-from {
  opacity: 0;
  transform: translateY(-8px);
}

.mc-slide-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.mc__headers {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 8px;
}

.mc__header-row {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 8px;
  align-items: flex-end;
}

.mc__header-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: #64748b;
  cursor: pointer;
  transition: color 0.2s ease, background 0.2s ease;
  margin-bottom: 2px;

  svg {
    width: 14px;
    height: 14px;
  }

  &:hover {
    color: #fb7185;
    background: rgba(251, 113, 133, 0.08);
  }
}

.mc__header-add {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  padding: 8px 0;
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  background: transparent;
  border: none;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.1);
  border-radius: 0;
  cursor: pointer;
  transition: color 0.2s ease, border-color 0.2s ease;

  svg {
    width: 14px;
    height: 14px;
  }

  &:hover {
    color: #22d3ee;
    border-bottom-color: rgba(0, 216, 255, 0.3);
  }
}

.mc__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.mc__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 20px;
  font-size: 13px;
  font-weight: 600;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;

  svg {
    width: 14px;
    height: 14px;
    flex-shrink: 0;
  }

  &:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
}

.mc__btn--primary {
  background: #00d8ff;
  color: #fff;

  &:hover:not(:disabled) {
    background: #22d3ee;
    box-shadow: 0 0 20px rgba(0, 216, 255, 0.3);
  }

  &:active:not(:disabled) {
    transform: scale(0.97);
  }
}

.mc__btn--ghost {
  background: transparent;
  color: #94a3b8;
  border: 1px solid rgba(255, 255, 255, 0.1);

  &:hover:not(:disabled) {
    color: #e2e8f0;
    border-color: rgba(255, 255, 255, 0.2);
    background: rgba(255, 255, 255, 0.04);
  }
}

.mc__btn--outline {
  background: transparent;
  color: #22d3ee;
  border: 1px solid rgba(0, 216, 255, 0.3);

  &:hover:not(:disabled) {
    background: rgba(0, 216, 255, 0.08);
    border-color: rgba(0, 216, 255, 0.5);
  }
}

.mc__btn--cancel {
  background: transparent;
  color: #64748b;
  border: 1px solid rgba(255, 255, 255, 0.08);

  &:hover:not(:disabled) {
    color: #94a3b8;
    border-color: rgba(255, 255, 255, 0.16);
  }
}

.mc__btn-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255, 255, 255, 0.25);
  border-top-color: #fff;
  border-radius: 50%;
  animation: mc-spin 0.6s linear infinite;
  flex-shrink: 0;
}

.mc__result {
  margin-top: 24px;
}

.mc__result-box {
  border-radius: 10px;
  padding: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.02);
}

.mc__result-box--success {
  border-color: rgba(52, 211, 153, 0.2);
  background: rgba(52, 211, 153, 0.04);
}

.mc__result-box--error {
  border-color: rgba(251, 113, 133, 0.2);
  background: rgba(251, 113, 133, 0.04);
}

.mc__result-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;

  svg {
    width: 18px;
    height: 18px;
    flex-shrink: 0;
  }

  .mc__result-box--success & svg {
    color: #34d399;
  }

  .mc__result-box--error & svg {
    color: #fb7185;
  }
}

.mc__result-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mc__result-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.mc__result-label {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.mc__result-value {
  font-size: 13px;
  color: #cbd5e1;
  font-family: 'Bahnschrift', 'DIN Alternate', 'Roboto Mono', ui-monospace, monospace;
  line-height: 1.5;
}

.mc__result-value--error {
  color: #fca5a5;
  font-family: inherit;
}

.mc__result-code {
  font-size: 11px;
  color: #94a3b8;
  font-family: 'Bahnschrift', 'DIN Alternate', 'Roboto Mono', ui-monospace, monospace;
  line-height: 1.5;
  padding: 10px;
  background: rgba(0, 0, 0, 0.25);
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  overflow-x: auto;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}

@media (max-width: 768px) {
  .mc__header-row {
    grid-template-columns: 1fr;
  }

  .mc__actions {
    flex-wrap: wrap;
  }

  .mc__btn {
    flex: 1;
    min-width: 0;
  }
}
</style>
