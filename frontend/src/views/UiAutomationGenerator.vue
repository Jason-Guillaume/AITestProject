<template>
  <div class="page-wrap cyber-page ui-automation-page">
    <el-card class="sys-page-head" shadow="never">
      <div class="sys-page-head__row">
        <div>
          <h2 class="sys-page-head__title">AI 脚本生成工作区</h2>
          <p class="sys-page-head__sub">
            输入目标URL和测试场景描述，AI将自动生成基于Unittest框架的UI自动化测试脚本
          </p>
        </div>
      </div>
    </el-card>

    <div class="split-layout">
      <!-- 左侧：输入区域 -->
      <el-card class="input-pane" shadow="never">
        <div class="pane-header">
          <h3 class="pane-title">输入配置</h3>
        </div>

        <div class="form-section">
          <div class="form-label">目标 URL</div>
          <el-input
            v-model="targetUrl"
            placeholder="https://example.com"
            clearable
            class="input-field"
          />
        </div>

        <div class="form-section">
          <div class="form-label">场景步骤描述</div>
          <el-input
            v-model="scenarioSteps"
            type="textarea"
            :autosize="{ minRows: 12, maxRows: 20 }"
            placeholder="描述用户操作流程，例如：&#10;1. 打开登录页面&#10;2. 输入用户名和密码&#10;3. 点击登录按钮&#10;4. 验证登录成功..."
            class="textarea-field"
          />
        </div>

        <div class="action-section">
          <el-button
            type="primary"
            :loading="loading"
            :disabled="!canGenerate"
            @click="handleGenerate"
            class="generate-btn"
          >
            <span v-if="loading">生成中...</span>
            <span v-else>生成脚本</span>
          </el-button>
        </div>
      </el-card>

      <!-- 右侧：输出区域 -->
      <el-card class="output-pane" shadow="never">
        <div class="pane-header">
          <h3 class="pane-title">生成结果</h3>
          <el-button
            v-if="generatedCode"
            size="small"
            @click="handleCopyCode"
            class="copy-btn"
          >
            {{ copyButtonText }}
          </el-button>
        </div>

        <div v-if="errorMessage" class="error-message">
          <el-alert type="error" :closable="false" show-icon>
            <template #title>{{ errorMessage }}</template>
          </el-alert>
        </div>

        <div v-if="!generatedCode && !errorMessage && !loading" class="empty-state">
          <div class="empty-icon">📝</div>
          <p class="empty-text">填写左侧信息后点击"生成脚本"开始</p>
        </div>

        <div v-if="loading" class="loading-state">
          <el-icon class="is-loading"><Loading /></el-icon>
          <p class="loading-text">AI 正在生成测试脚本...</p>
        </div>

        <pre v-if="generatedCode" class="code-output">{{ generatedCode }}</pre>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { ElMessage } from 'element-plus';
import { Loading } from '@element-plus/icons-vue';
import { generateUiAutomationScriptApi } from '@/api/assistant';

const targetUrl = ref('');
const scenarioSteps = ref('');
const generatedCode = ref('');
const loading = ref(false);
const errorMessage = ref('');
const copyButtonText = ref('复制代码');

const canGenerate = computed(() => {
  return targetUrl.value.trim() !== '' && scenarioSteps.value.trim() !== '';
});

const handleGenerate = async () => {
  if (!canGenerate.value) {
    ElMessage.warning('请填写目标URL和场景步骤');
    return;
  }

  loading.value = true;
  errorMessage.value = '';
  generatedCode.value = '';

  try {
    const response = await generateUiAutomationScriptApi({
      url: targetUrl.value.trim(),
      steps: scenarioSteps.value.trim()
    });

    if (response.data.success) {
      generatedCode.value = response.data.code;
      ElMessage.success(response.data.message || '脚本生成成功');
    } else {
      errorMessage.value = response.data.error || '生成失败';
      ElMessage.error(errorMessage.value);
    }
  } catch (error) {
    errorMessage.value = error.response?.data?.error || error.message || '网络请求失败';
    ElMessage.error('生成失败：' + errorMessage.value);
  } finally {
    loading.value = false;
  }
};

const handleCopyCode = async () => {
  try {
    await navigator.clipboard.writeText(generatedCode.value);
    copyButtonText.value = '已复制';
    ElMessage.success('代码已复制到剪贴板');

    setTimeout(() => {
      copyButtonText.value = '复制代码';
    }, 2000);
  } catch (error) {
    ElMessage.error('复制失败，请手动复制');
  }
};
</script>

<style scoped lang="scss">
.ui-automation-page {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.sys-page-head {
  margin-bottom: 16px;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border: 1px solid rgba(59, 130, 246, 0.3);

  &__row {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  &__title {
    font-size: 24px;
    font-weight: 600;
    color: #60a5fa;
    margin: 0 0 8px 0;
    text-shadow: 0 0 10px rgba(96, 165, 250, 0.5);
  }

  &__sub {
    font-size: 14px;
    color: #94a3b8;
    margin: 0;
  }
}

.split-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.input-pane,
.output-pane {
  background: #0f172a;
  border: 1px solid rgba(59, 130, 246, 0.2);
  display: flex;
  flex-direction: column;
  height: 100%;

  :deep(.el-card__body) {
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: 20px;
  }
}

.pane-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.2);
}

.pane-title {
  font-size: 18px;
  font-weight: 600;
  color: #60a5fa;
  margin: 0;
}

.copy-btn {
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
  color: #60a5fa;

  &:hover {
    background: rgba(59, 130, 246, 0.2);
    border-color: #60a5fa;
  }
}

.form-section {
  margin-bottom: 20px;
}

.form-label {
  font-size: 14px;
  font-weight: 500;
  color: #94a3b8;
  margin-bottom: 8px;
}

.input-field,
.textarea-field {
  :deep(.el-input__wrapper) {
    background: #1e293b;
    border: 1px solid rgba(59, 130, 246, 0.2);
    box-shadow: none;

    &:hover {
      border-color: rgba(59, 130, 246, 0.4);
    }
  }

  :deep(.el-input__inner),
  :deep(.el-textarea__inner) {
    color: #e2e8f0;
    background: transparent;

    &::placeholder {
      color: #475569;
    }
  }

  :deep(.el-textarea__inner) {
    background: #1e293b;
    border: 1px solid rgba(59, 130, 246, 0.2);
    color: #e2e8f0;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 13px;
    line-height: 1.6;

    &:hover {
      border-color: rgba(59, 130, 246, 0.4);
    }

    &:focus {
      border-color: #60a5fa;
    }
  }
}

.action-section {
  margin-top: auto;
  padding-top: 20px;
}

.generate-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  font-weight: 600;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  border: none;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);

  &:hover {
    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
    box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
  }

  &:disabled {
    background: #334155;
    box-shadow: none;
  }
}

.empty-state,
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 400px;
  color: #64748b;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-text,
.loading-text {
  font-size: 14px;
  color: #64748b;
}

.loading-state {
  .el-icon {
    font-size: 48px;
    color: #60a5fa;
    margin-bottom: 16px;
  }
}

.error-message {
  margin-bottom: 16px;

  :deep(.el-alert) {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);

    .el-alert__title {
      color: #fca5a5;
    }
  }
}

.code-output {
  flex: 1;
  background: #1e293b;
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 6px;
  padding: 16px;
  margin: 0;
  overflow: auto;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #e2e8f0;
  white-space: pre-wrap;
  word-wrap: break-word;

  &::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }

  &::-webkit-scrollbar-track {
    background: #0f172a;
    border-radius: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(59, 130, 246, 0.3);
    border-radius: 4px;

    &:hover {
      background: rgba(59, 130, 246, 0.5);
    }
  }
}
</style>
