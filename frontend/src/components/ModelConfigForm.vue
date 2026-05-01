<template>
  <div class="model-config-container">
    <!-- Header -->
    <div class="config-header">
      <h2 class="config-title">AI Model Configuration</h2>
      <p class="config-subtitle">Configure your OpenAI-compatible API endpoint for AI-powered testing features</p>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="loading-container">
      <div class="loading-spinner"></div>
      <p class="loading-text">Loading configuration...</p>
    </div>

    <!-- Configuration Form -->
    <div v-else class="config-form">
      <!-- API Provider -->
      <div class="form-group">
        <label class="form-label">API Provider</label>
        <input
          type="text"
          class="form-input"
          v-model="formData.provider"
          readonly
          placeholder="OpenAI Compatible"
        />
        <span class="form-helper">This configuration supports any OpenAI-compatible API endpoint</span>
      </div>

      <!-- Base URL -->
      <div class="form-group">
        <label class="form-label">Base URL</label>
        <input
          type="text"
          class="form-input"
          v-model="formData.baseUrl"
          placeholder="https://api.openai.com/v1"
          :disabled="!isEditMode"
          @focus="handleFocus"
          @blur="handleBlur"
        />
        <span class="form-helper">The base URL for API requests. Leave blank to use the default OpenAI endpoint.</span>
      </div>

      <!-- API Key -->
      <div class="form-group">
        <label class="form-label">API Key</label>
        <div class="input-with-icon">
          <input
            :type="showApiKey ? 'text' : 'password'"
            class="form-input"
            v-model="formData.apiKey"
            :placeholder="isEditMode && isSaved ? 'Enter new API Key to update' : 'sk-...'"
            :disabled="!isEditMode"
            @focus="handleFocus"
            @blur="handleBlur"
          />
          <button
            type="button"
            class="icon-button"
            @click="toggleApiKeyVisibility"
            :title="showApiKey ? 'Hide API Key' : 'Show API Key'"
          >
            <svg v-if="showApiKey" class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
              <line x1="1" y1="1" x2="23" y2="23"></line>
            </svg>
            <svg v-else class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
              <circle cx="12" cy="12" r="3"></circle>
            </svg>
          </button>
        </div>
        <span class="form-helper">
          {{ isEditMode && isSaved
            ? 'For security, you must enter the API Key again to update the configuration.'
            : 'This key is stored securely and only used to make API requests from this platform.' }}
        </span>
      </div>

      <!-- Model ID -->
      <div class="form-group">
        <label class="form-label">Model ID</label>
        <input
          type="text"
          class="form-input"
          v-model="formData.modelId"
          placeholder="e.g., glm-4.7-flash, gpt-4o, claude-3-opus"
          :disabled="!isEditMode"
          @focus="handleFocus"
          @blur="handleBlur"
        />
        <span class="form-helper">The exact model identifier to use for API requests.</span>
      </div>

      <!-- Advanced Configuration (Collapsible) -->
      <div class="advanced-section">
        <button
          type="button"
          class="advanced-toggle"
          @click="showAdvanced = !showAdvanced"
        >
          <svg
            class="toggle-icon"
            :class="{ 'rotate': showAdvanced }"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
          <span>Advanced Configuration</span>
        </button>

        <transition name="slide-fade">
          <div v-if="showAdvanced" class="advanced-content">
            <!-- Context Length -->
            <div class="form-group">
              <label class="form-label">Context Length</label>
              <input
                type="number"
                class="form-input"
                v-model.number="formData.contextLength"
                placeholder="4096"
                min="1"
                :disabled="!isEditMode"
                @focus="handleFocus"
                @blur="handleBlur"
              />
              <span class="form-helper">Maximum context window size in tokens.</span>
            </div>

            <!-- Custom Headers -->
            <div class="form-group">
              <label class="form-label">Custom Headers</label>
              <div class="headers-list">
                <div
                  v-for="(header, index) in formData.customHeaders"
                  :key="index"
                  class="header-row"
                >
                  <input
                    type="text"
                    class="form-input header-key"
                    v-model="header.key"
                    placeholder="Header Name"
                    :disabled="!isEditMode"
                    @focus="handleFocus"
                    @blur="handleBlur"
                  />
                  <input
                    type="text"
                    class="form-input header-value"
                    v-model="header.value"
                    placeholder="Header Value"
                    :disabled="!isEditMode"
                    @focus="handleFocus"
                    @blur="handleBlur"
                  />
                  <button
                    v-if="isEditMode"
                    type="button"
                    class="icon-button delete-btn"
                    @click="removeHeader(index)"
                    title="Remove Header"
                  >
                    <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <line x1="18" y1="6" x2="6" y2="18"></line>
                      <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                  </button>
                </div>
              </div>
              <button
                v-if="isEditMode"
                type="button"
                class="add-header-btn"
                @click="addHeader"
              >
                <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="12" y1="5" x2="12" y2="19"></line>
                  <line x1="5" y1="12" x2="19" y2="12"></line>
                </svg>
                <span>Add Custom Header</span>
              </button>
            </div>
          </div>
        </transition>
      </div>

      <!-- Action Buttons -->
      <div class="form-actions">
        <!-- 查看模式：显示更改配置按钮 -->
        <button
          v-if="!isEditMode"
          type="button"
          class="btn btn-edit"
          @click="enableEditMode"
        >
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
          </svg>
          <span>更改配置</span>
        </button>

        <!-- 编辑模式：显示保存和测试按钮 -->
        <template v-if="isEditMode">
          <button
            type="button"
            class="btn btn-primary"
            @click="handleSave"
            :disabled="isSaving || isTesting"
          >
            <span v-if="isSaving" class="btn-spinner"></span>
            <span>{{ isSaving ? 'Saving...' : '保存配置' }}</span>
          </button>
          <button
            type="button"
            class="btn btn-secondary"
            @click="handleTest"
            :disabled="isSaving || isTesting"
          >
            <span v-if="isTesting" class="btn-spinner"></span>
            <span>{{ isTesting ? 'Connecting...' : '测试连接' }}</span>
          </button>
          <button
            v-if="isSaved"
            type="button"
            class="btn btn-cancel"
            @click="cancelEdit"
            :disabled="isSaving || isTesting"
          >
            <span>取消</span>
          </button>
        </template>
      </div>

      <!-- Test Result Display -->
      <div v-if="testResult || testError" class="test-result-container">
        <!-- Success Result -->
        <div v-if="testResult" class="test-result success">
          <div class="result-header">
            <svg class="result-icon success-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
              <polyline points="22 4 12 14.01 9 11.01"></polyline>
            </svg>
            <h3 class="result-title">{{ testResult.message }}</h3>
          </div>
          <div class="result-body">
            <div class="result-item">
              <span class="result-label">Model:</span>
              <span class="result-value">{{ testResult.model }}</span>
            </div>
            <div class="result-item">
              <span class="result-label">Response:</span>
              <div class="result-response">{{ testResult.response }}</div>
            </div>
            <div v-if="testResult.usage" class="result-item">
              <span class="result-label">Usage:</span>
              <span class="result-value">
                {{ testResult.usage.prompt_tokens }} prompt +
                {{ testResult.usage.completion_tokens }} completion =
                {{ testResult.usage.total_tokens }} tokens
              </span>
            </div>
          </div>
        </div>

        <!-- Error Result -->
        <div v-if="testError" class="test-result error">
          <div class="result-header">
            <svg class="result-icon error-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="15" y1="9" x2="9" y2="15"></line>
              <line x1="9" y1="9" x2="15" y2="15"></line>
            </svg>
            <h3 class="result-title">{{ testError.message }}</h3>
          </div>
          <div class="result-body">
            <div class="result-item">
              <span class="result-label">Details:</span>
              <div class="result-error">{{ testError.details }}</div>
            </div>
            <div v-if="testError.fullError" class="result-item">
              <span class="result-label">Technical Info:</span>
              <pre class="result-code">{{ JSON.stringify(testError.fullError, null, 2) }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { getAiModelConfigApi, saveAiModelConfigApi } from '@/api/sysAiConfig'

// Form state
const formData = reactive({
  provider: 'OpenAI Compatible',
  baseUrl: '',
  apiKey: '',
  modelId: '',
  contextLength: null,
  customHeaders: []
})

// UI state
const showApiKey = ref(false)
const showAdvanced = ref(false)
const isSaving = ref(false)
const isTesting = ref(false)
const testResult = ref(null)
const testError = ref(null)
const isEditMode = ref(true)  // true = 编辑模式, false = 查看模式
const isSaved = ref(false)     // 是否已保存配置
const isLoading = ref(true)    // 是否正在加载配置

// Methods
const toggleApiKeyVisibility = () => {
  showApiKey.value = !showApiKey.value
}

const handleFocus = (e) => {
  e.target.parentElement.classList.add('focused')
}

const handleBlur = (e) => {
  e.target.parentElement.classList.remove('focused')
}

const addHeader = () => {
  formData.customHeaders.push({ key: '', value: '' })
}

const removeHeader = (index) => {
  formData.customHeaders.splice(index, 1)
}

const handleSave = async () => {
  // Validation
  if (!formData.modelId.trim()) {
    ElMessage.warning('Please enter a Model ID')
    return
  }

  // 如果是更新已有配置且 API Key 为空，提示用户
  if (isSaved.value && !formData.apiKey.trim()) {
    ElMessage.warning('Please enter the API Key to update the configuration')
    return
  }

  // 如果是新配置，必须提供 API Key
  if (!isSaved.value && !formData.apiKey.trim()) {
    ElMessage.warning('Please enter an API Key')
    return
  }

  isSaving.value = true
  try {
    // 调用后端 API 保存配置
    const payload = {
      model_type: formData.modelId.trim(),
      base_url: formData.baseUrl.trim() || '',
      is_connected: true
    }

    // 只有在用户输入了新的 API Key 时才发送
    if (formData.apiKey.trim()) {
      payload.api_key = formData.apiKey.trim()
    }

    const { data } = await saveAiModelConfigApi(payload)

    // data 包含后端返回的 { code, msg, data }
    if (data && data.code === 200) {
      // 保存成功后切换到查看模式
      isSaved.value = true
      isEditMode.value = false
      // 将 API Key 替换为占位符
      formData.apiKey = '********'
      ElMessage.success(data.msg || 'Configuration saved successfully')
    } else {
      throw new Error(data?.msg || 'Save failed')
    }
  } catch (error) {
    console.error('Save failed:', error)
    ElMessage.error(error.response?.data?.msg || error.message || 'Failed to save configuration')
  } finally {
    isSaving.value = false
  }
}

const enableEditMode = () => {
  isEditMode.value = true
  // 清空 API Key 占位符，让用户输入新的 Key
  if (formData.apiKey === '********') {
    formData.apiKey = ''
  }
}

const cancelEdit = () => {
  if (isSaved.value) {
    isEditMode.value = false
    // 恢复 API Key 占位符
    formData.apiKey = '********'
    ElMessage.info('Changes cancelled')
  }
}

const handleTest = async () => {
  // Validation
  if (!formData.apiKey.trim()) {
    ElMessage.warning('Please enter an API Key')
    return
  }
  if (!formData.modelId.trim()) {
    ElMessage.warning('Please enter a Model ID')
    return
  }

  // Reset previous results
  testResult.value = null
  testError.value = null
  isTesting.value = true

  try {
    // Determine the endpoint URL
    let apiUrl = formData.baseUrl.trim() || 'https://api.iamhc.cn/v1'

    // Remove trailing slash if present
    if (apiUrl.endsWith('/')) {
      apiUrl = apiUrl.slice(0, -1)
    }

    // Use proxy for CORS bypass
    // If baseUrl is the default (api.iamhc.cn), use the proxy
    const useProxy = apiUrl.includes('api.iamhc.cn')
    const requestUrl = useProxy
      ? '/ai-api/v1/chat/completions'
      : `${apiUrl}/chat/completions`

    // Prepare headers
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${formData.apiKey.trim()}`
    }

    // Add custom headers if any
    formData.customHeaders.forEach(header => {
      if (header.key && header.value) {
        headers[header.key] = header.value
      }
    })

    // Prepare request payload
    const payload = {
      model: formData.modelId.trim(),
      messages: [
        {
          role: 'user',
          content: 'Hello! Please respond with a simple greeting to confirm the connection.'
        }
      ],
      max_tokens: 50,
      temperature: 0.7
    }

    console.log('Testing connection to:', requestUrl)
    console.log('Using model:', formData.modelId)

    // Make the API request
    const response = await axios.post(requestUrl, payload, {
      headers,
      timeout: 30000 // 30 second timeout
    })

    // Extract the response
    if (response.data && response.data.choices && response.data.choices.length > 0) {
      const aiMessage = response.data.choices[0].message.content
      testResult.value = {
        success: true,
        message: 'Connection successful!',
        response: aiMessage,
        model: response.data.model || formData.modelId,
        usage: response.data.usage
      }
      console.log('Test successful:', testResult.value)
    } else {
      throw new Error('Invalid response format from API')
    }

  } catch (error) {
    console.error('Connection test failed:', error)

    // Parse error details
    let errorMessage = 'Connection test failed'
    let errorDetails = ''

    if (error.response) {
      // Server responded with error status
      const status = error.response.status
      const data = error.response.data

      switch (status) {
        case 401:
          errorMessage = '401 Unauthorized'
          errorDetails = 'Invalid API Key. Please check your credentials.'
          break
        case 403:
          errorMessage = '403 Forbidden'
          errorDetails = 'Access denied. Your API key may not have permission.'
          break
        case 404:
          errorMessage = '404 Not Found'
          errorDetails = 'API endpoint not found. Please check your Base URL.'
          break
        case 429:
          errorMessage = '429 Too Many Requests'
          errorDetails = 'Rate limit exceeded. Please try again later.'
          break
        case 500:
          errorMessage = '500 Internal Server Error'
          errorDetails = 'The API server encountered an error.'
          break
        default:
          errorMessage = `${status} Error`
          errorDetails = data?.error?.message || data?.message || 'Unknown error occurred'
      }
    } else if (error.request) {
      // Request made but no response received
      errorMessage = 'Network Timeout'
      errorDetails = 'No response from server. Check your Base URL and network connection.'
    } else {
      // Error in request setup
      errorMessage = 'Request Error'
      errorDetails = error.message || 'Failed to send request'
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

// 加载已保存的配置
const loadConfig = async () => {
  isLoading.value = true
  try {
    const { data } = await getAiModelConfigApi()
    // data 包含后端返回的 { code, msg, data }
    if (data && data.code === 200 && data.data) {
      const config = data.data
      formData.baseUrl = config.base_url || ''
      formData.apiKey = '********' // 不显示真实的 API Key
      formData.modelId = config.model_type || ''

      // 如果已有配置，切换到查看模式
      isSaved.value = true
      isEditMode.value = false
    } else {
      // 没有配置，保持编辑模式
      isEditMode.value = true
      isSaved.value = false
    }
  } catch (error) {
    console.error('Failed to load config:', error)
    // 加载失败，保持编辑模式
    isEditMode.value = true
    isSaved.value = false
  } finally {
    isLoading.value = false
  }
}

// 组件挂载时加载配置
onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.model-config-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px 0;
}

/* Header */
.config-header {
  margin-bottom: 32px;
}

.config-title {
  font-size: 24px;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0 0 8px 0;
  letter-spacing: -0.3px;
}

.config-subtitle {
  font-size: 14px;
  color: rgba(148, 163, 184, 0.85);
  margin: 0;
  line-height: 1.5;
}

/* Form */
.config-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 12px;
  font-weight: 600;
  color: #cbd5e1;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.form-input {
  width: 100%;
  padding: 10px 14px;
  font-size: 14px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  color: #e2e8f0;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(100, 116, 139, 0.3);
  border-radius: 6px;
  outline: none;
  transition: all 0.2s ease;
}

.form-input::placeholder {
  color: rgba(148, 163, 184, 0.4);
}

.form-input:focus {
  border-color: #06b6d4;
  box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.15);
  background: rgba(0, 0, 0, 0.35);
}

.form-input:read-only {
  cursor: not-allowed;
  opacity: 0.6;
}

.form-input:disabled {
  cursor: not-allowed;
  opacity: 0.6;
  background: rgba(0, 0, 0, 0.15);
}

.form-helper {
  font-size: 12px;
  color: rgba(148, 163, 184, 0.7);
  line-height: 1.4;
}

/* Input with Icon */
.input-with-icon {
  position: relative;
  display: flex;
  align-items: center;
}

.input-with-icon .form-input {
  padding-right: 44px;
}

.icon-button {
  position: absolute;
  right: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: rgba(148, 163, 184, 0.7);
  cursor: pointer;
  transition: all 0.2s ease;
}

.icon-button:hover {
  background: rgba(6, 182, 212, 0.1);
  color: #06b6d4;
}

.icon {
  width: 18px;
  height: 18px;
}

/* Advanced Section */
.advanced-section {
  margin-top: 8px;
}

.advanced-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 12px 0;
  font-size: 13px;
  font-weight: 600;
  color: #94a3b8;
  background: transparent;
  border: none;
  border-top: 1px solid rgba(100, 116, 139, 0.2);
  cursor: pointer;
  transition: color 0.2s ease;
}

.advanced-toggle:hover {
  color: #06b6d4;
}

.toggle-icon {
  width: 16px;
  height: 16px;
  transition: transform 0.3s ease;
}

.toggle-icon.rotate {
  transform: rotate(90deg);
}

.advanced-content {
  padding-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Slide Fade Transition */
.slide-fade-enter-active {
  transition: all 0.3s ease;
}

.slide-fade-leave-active {
  transition: all 0.2s ease;
}

.slide-fade-enter-from {
  transform: translateY(-10px);
  opacity: 0;
}

.slide-fade-leave-to {
  transform: translateY(-5px);
  opacity: 0;
}

/* Custom Headers */
.headers-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 12px;
}

.header-row {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 8px;
  align-items: center;
}

.header-key,
.header-value {
  margin: 0;
}

.delete-btn {
  position: static;
  width: 36px;
  height: 36px;
  color: rgba(239, 68, 68, 0.7);
}

.delete-btn:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.add-header-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 500;
  color: rgba(148, 163, 184, 0.85);
  background: transparent;
  border: 1px dashed rgba(100, 116, 139, 0.3);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.add-header-btn:hover {
  border-color: #06b6d4;
  color: #06b6d4;
  background: rgba(6, 182, 212, 0.05);
}

/* Action Buttons */
.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  padding-top: 24px;
  border-top: 1px solid rgba(100, 116, 139, 0.2);
}

.btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 11px 24px;
  font-size: 14px;
  font-weight: 600;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 120px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  color: #ffffff;
  background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
  box-shadow: 0 4px 12px rgba(14, 165, 233, 0.3);
}

.btn-primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
  box-shadow: 0 6px 20px rgba(14, 165, 233, 0.5);
  transform: translateY(-1px);
}

.btn-secondary {
  color: #06b6d4;
  background: transparent;
  border: 1px solid #06b6d4;
}

.btn-secondary:hover:not(:disabled) {
  background: rgba(6, 182, 212, 0.1);
  box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.1);
}

.btn-edit {
  color: #06b6d4;
  background: transparent;
  border: 1px solid #06b6d4;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-edit:hover:not(:disabled) {
  background: rgba(6, 182, 212, 0.1);
  box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.1);
}

.btn-edit .icon {
  width: 16px;
  height: 16px;
}

.btn-cancel {
  color: #94a3b8;
  background: transparent;
  border: 1px solid rgba(148, 163, 184, 0.3);
}

.btn-cancel:hover:not(:disabled) {
  background: rgba(148, 163, 184, 0.1);
  border-color: rgba(148, 163, 184, 0.5);
}

.btn-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Test Result Styles */
.test-result-container {
  margin-top: 24px;
}

.test-result {
  border-radius: 8px;
  padding: 20px;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.test-result.success {
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.test-result.error {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.result-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.result-icon {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
}

.success-icon {
  color: #22c55e;
}

.error-icon {
  color: #ef4444;
}

.result-title {
  font-size: 16px;
  font-weight: 600;
  color: #e2e8f0;
  margin: 0;
}

.result-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.result-label {
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.result-value {
  font-size: 14px;
  color: #e2e8f0;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}

.result-response {
  font-size: 14px;
  color: #e2e8f0;
  line-height: 1.6;
  padding: 12px;
  background: rgba(0, 0, 0, 0.25);
  border-radius: 6px;
  border: 1px solid rgba(100, 116, 139, 0.3);
}

.result-error {
  font-size: 14px;
  color: #fca5a5;
  line-height: 1.6;
  padding: 12px;
  background: rgba(0, 0, 0, 0.25);
  border-radius: 6px;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.result-code {
  font-size: 12px;
  color: #cbd5e1;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  line-height: 1.5;
  padding: 12px;
  background: rgba(0, 0, 0, 0.4);
  border-radius: 6px;
  border: 1px solid rgba(100, 116, 139, 0.3);
  overflow-x: auto;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}

/* Loading State */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 16px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(6, 182, 212, 0.2);
  border-top-color: #06b6d4;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.loading-text {
  font-size: 14px;
  color: #94a3b8;
  margin: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .model-config-container {
    padding: 16px;
  }

  .config-title {
    font-size: 20px;
  }

  .header-row {
    grid-template-columns: 1fr;
  }

  .delete-btn {
    justify-self: end;
  }

  .form-actions {
    flex-direction: column;
  }

  .btn {
    width: 100%;
  }

  .result-code {
    font-size: 11px;
  }
}
</style>
