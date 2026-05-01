<template>
  <div class="ui-automation-workbench">
    <!-- Header -->
    <div class="workbench-header">
      <h1 class="header-title">UI自动化脚本工作台</h1>
      <p class="header-subtitle">支持AI生成、单文件上传和ZIP/Git导入三种方式</p>
    </div>

    <div class="workbench-content">
      <!-- 左侧控制区 -->
      <div class="control-panel">
        <!-- 脚本来源切换 -->
        <div class="source-selector">
          <div class="section-title">脚本来源</div>
          <el-radio-group v-model="scriptSource" class="source-radio-group">
            <el-radio-button label="ai" class="source-radio-btn">
              <span class="radio-icon">🤖</span>
              <span class="radio-text">AI 生成</span>
            </el-radio-button>
            <el-radio-button label="linear" class="source-radio-btn">
              <span class="radio-icon">📄</span>
              <span class="radio-text">单文件上传(线性)</span>
            </el-radio-button>
            <el-radio-button label="pom" class="source-radio-btn">
              <span class="radio-icon">📦</span>
              <span class="radio-text">ZIP/Git导入(POM)</span>
            </el-radio-button>
          </el-radio-group>
        </div>

        <!-- AI 生成配置 -->
        <div v-if="scriptSource === 'ai'" class="config-section">
          <div class="section-title">AI 生成配置</div>

          <div class="form-item">
            <label class="form-label">目标 URL</label>
            <el-input
              v-model="aiConfig.targetUrl"
              placeholder="https://example.com"
              class="cyber-input"
            />
          </div>

          <div class="form-item">
            <label class="form-label">场景描述</label>
            <el-input
              v-model="aiConfig.scenarioSteps"
              type="textarea"
              :rows="8"
              placeholder="描述测试场景"
              class="cyber-textarea"
            />
          </div>

          <el-button
            type="primary"
            :loading="generating"
            :disabled="!canGenerateAI"
            @click="handleGenerateAI"
            class="action-btn"
          >
            <span v-if="generating">生成中...</span>
            <span v-else>生成脚本</span>
          </el-button>
        </div>

        <!-- 单文件上传 -->
        <div v-if="scriptSource === 'linear'" class="config-section">
          <div class="section-title">单文件上传</div>

          <div class="form-item">
            <label class="form-label">脚本名称</label>
            <el-input
              v-model="linearConfig.name"
              placeholder="例如：登录测试脚本"
              class="cyber-input"
            />
          </div>

          <div class="form-item">
            <label class="form-label">上传 Python 文件</label>
            <el-upload
              class="cyber-upload"
              drag
              :auto-upload="false"
              :limit="1"
              accept=".py"
              :on-change="handleLinearFileChange"
              :on-remove="handleLinearFileRemove"
              :file-list="linearConfig.file ? [{ name: linearConfig.file.name }] : []"
            >
              <div class="upload-content">
                <el-icon class="upload-icon"><UploadFilled /></el-icon>
                <div class="upload-text">拖拽 .py 文件到此处</div>
                <div class="upload-hint">或点击选择文件</div>
              </div>
            </el-upload>
          </div>

          <el-button
            type="primary"
            :loading="uploading"
            :disabled="!canUploadLinear"
            @click="handleUploadLinear"
            class="action-btn"
          >
            <span v-if="uploading">上传中...</span>
            <span v-else>上传脚本</span>
          </el-button>
        </div>

        <!-- ZIP/Git 导入 -->
        <div v-if="scriptSource === 'pom'" class="config-section">
          <div class="section-title">ZIP/Git 导入</div>

          <div class="form-item">
            <label class="form-label">脚本名称</label>
            <el-input
              v-model="pomConfig.name"
              placeholder="例如：POM测试套件"
              class="cyber-input"
            />
          </div>

          <div class="form-item">
            <label class="form-label">导入方式</label>
            <el-radio-group v-model="pomConfig.importType">
              <el-radio label="zip">ZIP 文件</el-radio>
              <el-radio label="git">Git 仓库</el-radio>
            </el-radio-group>
          </div>

          <div v-if="pomConfig.importType === 'zip'" class="form-item">
            <label class="form-label">上传 ZIP 文件</label>
            <el-upload
              class="cyber-upload"
              drag
              :auto-upload="false"
              :limit="1"
              accept=".zip"
              :on-change="handlePomFileChange"
              :on-remove="handlePomFileRemove"
              :file-list="pomConfig.file ? [{ name: pomConfig.file.name }] : []"
            >
              <div class="upload-content">
                <el-icon class="upload-icon"><UploadFilled /></el-icon>
                <div class="upload-text">拖拽 .zip 文件到此处</div>
                <div class="upload-hint">最大50MB</div>
              </div>
            </el-upload>
          </div>

          <div v-if="pomConfig.importType === 'git'" class="form-item">
            <label class="form-label">Git 仓库 URL</label>
            <el-input
              v-model="pomConfig.gitRepoUrl"
              placeholder="https://github.com/username/repo.git"
              class="cyber-input"
            />
          </div>

          <div class="form-item">
            <label class="form-label">执行入口点</label>
            <el-input
              v-model="pomConfig.entryPoint"
              placeholder="例如：tests/test_login.py"
              class="cyber-input"
            />
          </div>

          <el-button
            type="primary"
            :loading="uploading"
            :disabled="!canUploadPom"
            @click="handleUploadPom"
            class="action-btn"
          >
            <span v-if="uploading">导入中...</span>
            <span v-else>导入脚本</span>
          </el-button>
        </div>
      </div>

      <!-- 右侧预览区 -->
      <div class="preview-panel">
        <div class="panel-header">
          <h3 class="panel-title">生成结果</h3>
        </div>

        <div class="empty-state">
          <div class="empty-icon">🤖</div>
          <p class="empty-text">填写左侧配置后开始</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { UploadFilled } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import request from '@/utils/request';

const scriptSource = ref('ai');

const aiConfig = ref({
  targetUrl: '',
  scenarioSteps: ''
});

const linearConfig = ref({
  name: '',
  file: null
});

const pomConfig = ref({
  name: '',
  importType: 'zip',
  gitRepoUrl: '',
  entryPoint: '',
  file: null
});

const generating = ref(false);
const uploading = ref(false);

const canGenerateAI = computed(() => {
  return aiConfig.value.targetUrl && aiConfig.value.scenarioSteps;
});

const canUploadLinear = computed(() => {
  return linearConfig.value.name && linearConfig.value.file;
});

const canUploadPom = computed(() => {
  if (!pomConfig.value.name || !pomConfig.value.entryPoint) return false;
  if (pomConfig.value.importType === 'zip') {
    return !!pomConfig.value.file;
  } else {
    return !!pomConfig.value.gitRepoUrl;
  }
});

const handleGenerateAI = () => {
  console.log('Generate AI script');
};

const handleLinearFileChange = (file) => {
  linearConfig.value.file = file.raw;
};

const handleLinearFileRemove = () => {
  linearConfig.value.file = null;
};

const handlePomFileChange = (file) => {
  pomConfig.value.file = file.raw;
};

const handlePomFileRemove = () => {
  pomConfig.value.file = null;
};

const handleUploadLinear = async () => {
  if (!canUploadLinear.value) {
    ElMessage.warning('请填写脚本名称并上传文件');
    return;
  }

  uploading.value = true;
  const formData = new FormData();
  formData.append('name', linearConfig.value.name);
  formData.append('script_type', 'LINEAR');
  formData.append('file_path', linearConfig.value.file);

  try {
    const response = await request.post('/assistant/ui-scripts/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    ElMessage.success('脚本上传成功');
    linearConfig.value.name = '';
    linearConfig.value.file = null;
  } catch (error) {
    const errorMsg = error.response?.data?.file_path?.[0]
      || error.response?.data?.entry_point?.[0]
      || error.response?.data?.detail
      || '上传失败';
    ElMessage.error(errorMsg);
  } finally {
    uploading.value = false;
  }
};

const handleUploadPom = async () => {
  if (!canUploadPom.value) {
    ElMessage.warning('请填写完整信息');
    return;
  }

  uploading.value = true;
  const formData = new FormData();
  formData.append('name', pomConfig.value.name);
  formData.append('script_type', 'POM');
  formData.append('entry_point', pomConfig.value.entryPoint);

  if (pomConfig.value.importType === 'zip') {
    formData.append('file_path', pomConfig.value.file);
  } else {
    formData.append('git_repo_url', pomConfig.value.gitRepoUrl);
  }

  try {
    const response = await request.post('/assistant/ui-scripts/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    ElMessage.success('脚本导入成功');
    pomConfig.value.name = '';
    pomConfig.value.gitRepoUrl = '';
    pomConfig.value.entryPoint = '';
    pomConfig.value.file = null;
  } catch (error) {
    const errorMsg = error.response?.data?.file_path?.[0]
      || error.response?.data?.entry_point?.[0]
      || error.response?.data?.detail
      || '导入失败';
    ElMessage.error(errorMsg);
  } finally {
    uploading.value = false;
  }
};
</script>

<style scoped>
.ui-automation-workbench {
  min-height: 100vh;
  padding: 24px;
  background: linear-gradient(180deg, #0a0e1a 0%, #1a1f2e 100%);
}

.workbench-header {
  margin-bottom: 32px;
  text-align: center;
}

.header-title {
  font-size: 32px;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0 0 8px 0;
  background: linear-gradient(135deg, #00d8ff 0%, #0ea5e9 50%, #3b82f6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.header-subtitle {
  font-size: 14px;
  color: rgba(148, 163, 184, 0.8);
  margin: 0;
}

.workbench-content {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 24px;
  max-width: 1600px;
  margin: 0 auto;
}

.control-panel {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(100, 255, 218, 0.12);
  border-radius: 12px;
  padding: 24px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #00d8ff;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(100, 255, 218, 0.12);
}

.source-radio-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

.source-radio-btn {
  width: 100%;
}

:deep(.source-radio-btn .el-radio-button__inner) {
  width: 100%;
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(100, 255, 218, 0.2);
  border-radius: 8px;
  color: #94a3b8;
}

:deep(.source-radio-btn.is-active .el-radio-button__inner) {
  background: rgba(0, 216, 255, 0.1);
  border-color: #00d8ff;
  color: #00d8ff;
  box-shadow: 0 0 20px rgba(0, 216, 255, 0.3);
}

.radio-icon {
  font-size: 24px;
  margin-right: 12px;
}

.radio-text {
  font-size: 14px;
  font-weight: 500;
}

.config-section {
  margin-top: 24px;
}

.form-item {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-size: 13px;
  color: #94a3b8;
  margin-bottom: 8px;
}

.cyber-input :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(100, 255, 218, 0.2);
  border-radius: 6px;
}

.cyber-input :deep(.el-input__inner) {
  color: #e2e8f0;
}

.cyber-textarea :deep(.el-textarea__inner) {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(100, 255, 218, 0.2);
  border-radius: 6px;
  color: #e2e8f0;
}

.cyber-upload :deep(.el-upload-dragger) {
  background: rgba(255, 255, 255, 0.02);
  border: 2px dashed rgba(100, 255, 218, 0.3);
  border-radius: 8px;
  padding: 32px 16px;
}

.upload-content {
  text-align: center;
}

.upload-icon {
  font-size: 48px;
  color: #00d8ff;
  margin-bottom: 12px;
}

.upload-text {
  font-size: 14px;
  color: #e2e8f0;
  margin-bottom: 4px;
}

.upload-hint {
  font-size: 12px;
  color: #64748b;
}

.action-btn {
  width: 100%;
  height: 44px;
  background: linear-gradient(135deg, #00d8ff 0%, #0ea5e9 100%);
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #0a0e1a;
  margin-top: 8px;
}

.preview-panel {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(100, 255, 218, 0.12);
  border-radius: 12px;
  padding: 24px;
}

.panel-header {
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(100, 255, 218, 0.12);
}

.panel-title {
  font-size: 18px;
  font-weight: 600;
  color: #00d8ff;
  margin: 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-text {
  font-size: 14px;
  color: #64748b;
  margin: 0;
}
</style>
