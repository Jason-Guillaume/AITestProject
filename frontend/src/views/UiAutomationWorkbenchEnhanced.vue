<template>
  <div class="ui-automation-workbench">
    <!-- Header -->
    <div class="workbench-header">
      <h1 class="header-title">
        UI自动化脚本工作台
      </h1>
      <p class="header-subtitle">
        支持AI生成、在线编辑、文件上传和POM工程导入
      </p>
    </div>

    <div class="workbench-content">
      <!-- 左侧控制区 -->
      <div class="control-panel">
        <!-- 脚本来源切换 -->
        <div class="source-selector">
          <div class="section-title">
            脚本来源
          </div>
          <el-radio-group
            v-model="scriptSource"
            class="source-radio-group"
          >
            <el-radio-button
              label="online"
              class="source-radio-btn"
            >
              <span class="radio-icon">✏️</span>
              <span class="radio-text">在线编辑</span>
            </el-radio-button>
            <el-radio-button
              label="ai"
              class="source-radio-btn"
            >
              <span class="radio-icon">🤖</span>
              <span class="radio-text">AI 生成</span>
            </el-radio-button>
            <el-radio-button
              label="linear"
              class="source-radio-btn"
            >
              <span class="radio-icon">📄</span>
              <span class="radio-text">单文件上传</span>
            </el-radio-button>
            <el-radio-button
              label="pom"
              class="source-radio-btn"
            >
              <span class="radio-icon">📦</span>
              <span class="radio-text">POM工程</span>
            </el-radio-button>
          </el-radio-group>
        </div>

        <!-- 在线编辑配置 -->
        <div
          v-if="scriptSource === 'online'"
          class="config-section"
        >
          <div class="section-title">
            在线脚本编辑
          </div>

          <div class="form-item">
            <label class="form-label">脚本名称</label>
            <el-input
              v-model="onlineConfig.name"
              placeholder="例如：登录测试脚本"
              class="cyber-input"
            />
          </div>

          <div class="form-item">
            <label class="form-label">脚本语言</label>
            <el-select
              v-model="onlineConfig.language"
              class="cyber-input"
            >
              <el-option
                label="Python"
                value="PYTHON"
              />
              <el-option
                label="Java"
                value="JAVA"
              />
            </el-select>
          </div>

          <div class="form-item">
            <label class="form-label">测试框架</label>
            <el-select
              v-model="onlineConfig.framework"
              class="cyber-input"
            >
              <el-option
                label="自动检测"
                value="AUTO"
              />
              <el-option-group
                v-if="onlineConfig.language === 'PYTHON'"
                label="Python框架"
              >
                <el-option
                  label="Pytest"
                  value="PYTEST"
                />
                <el-option
                  label="Unittest"
                  value="UNITTEST"
                />
                <el-option
                  label="Nose"
                  value="NOSE"
                />
                <el-option
                  label="Robot Framework"
                  value="ROBOT"
                />
                <el-option
                  label="Behave"
                  value="BEHAVE"
                />
              </el-option-group>
              <el-option-group
                v-if="onlineConfig.language === 'JAVA'"
                label="Java框架"
              >
                <el-option
                  label="JUnit 4"
                  value="JUNIT4"
                />
                <el-option
                  label="JUnit 5"
                  value="JUNIT5"
                />
                <el-option
                  label="TestNG"
                  value="TESTNG"
                />
                <el-option
                  label="Cucumber"
                  value="CUCUMBER"
                />
                <el-option
                  label="Spock"
                  value="SPOCK"
                />
              </el-option-group>
            </el-select>
          </div>

          <div class="form-item">
            <label class="form-label">入口点</label>
            <el-input
              v-model="onlineConfig.entryPoint"
              placeholder="test_script.py"
              class="cyber-input"
            />
          </div>

          <el-button
            type="primary"
            :loading="uploading"
            :disabled="!canSaveOnline"
            class="action-btn"
            @click="handleSaveOnline"
          >
            <span v-if="uploading">保存中...</span>
            <span v-else>保存并创建</span>
          </el-button>
        </div>

        <!-- AI 生成配置 -->
        <div
          v-if="scriptSource === 'ai'"
          class="config-section"
        >
          <div class="section-title">
            AI 生成配置
          </div>

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
            class="action-btn"
            @click="handleGenerateAI"
          >
            <span v-if="generating">生成中...</span>
            <span v-else>生成脚本</span>
          </el-button>
        </div>

        <!-- 单文件上传 -->
        <div
          v-if="scriptSource === 'linear'"
          class="config-section"
        >
          <div class="section-title">
            单文件上传
          </div>

          <div class="form-item">
            <label class="form-label">脚本名称</label>
            <el-input
              v-model="linearConfig.name"
              placeholder="例如：登录测试脚本"
              class="cyber-input"
            />
          </div>

          <div class="form-item">
            <label class="form-label">脚本语言</label>
            <el-select
              v-model="linearConfig.language"
              class="cyber-input"
            >
              <el-option
                label="Python"
                value="PYTHON"
              />
              <el-option
                label="Java"
                value="JAVA"
              />
            </el-select>
          </div>

          <div class="form-item">
            <label class="form-label">上传文件</label>
            <el-upload
              class="cyber-upload"
              drag
              :auto-upload="false"
              :limit="1"
              :accept="linearConfig.language === 'PYTHON' ? '.py' : '.java'"
              :on-change="handleLinearFileChange"
              :on-remove="handleLinearFileRemove"
              :file-list="linearConfig.file ? [{ name: linearConfig.file.name }] : []"
            >
              <div class="upload-content">
                <el-icon class="upload-icon">
                  <UploadFilled />
                </el-icon>
                <div class="upload-text">
                  拖拽文件到此处
                </div>
                <div class="upload-hint">
                  或点击选择文件
                </div>
              </div>
            </el-upload>
          </div>

          <el-button
            type="primary"
            :loading="uploading"
            :disabled="!canUploadLinear"
            class="action-btn"
            @click="handleUploadLinear"
          >
            <span v-if="uploading">上传中...</span>
            <span v-else>上传脚本</span>
          </el-button>
        </div>

        <!-- POM工程导入 -->
        <div
          v-if="scriptSource === 'pom'"
          class="config-section"
        >
          <div class="section-title">
            POM工程导入
          </div>

          <div class="form-item">
            <label class="form-label">脚本名称</label>
            <el-input
              v-model="pomConfig.name"
              placeholder="例如：POM测试套件"
              class="cyber-input"
            />
          </div>

          <div class="form-item">
            <label class="form-label">脚本语言</label>
            <el-select
              v-model="pomConfig.language"
              class="cyber-input"
            >
              <el-option
                label="Python"
                value="PYTHON"
              />
              <el-option
                label="Java"
                value="JAVA"
              />
            </el-select>
          </div>

          <div class="form-item">
            <label class="form-label">导入方式</label>
            <el-radio-group v-model="pomConfig.importType">
              <el-radio label="zip">
                ZIP 文件
              </el-radio>
              <el-radio label="git">
                Git 仓库
              </el-radio>
            </el-radio-group>
          </div>

          <div
            v-if="pomConfig.importType === 'zip'"
            class="form-item"
          >
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
                <el-icon class="upload-icon">
                  <UploadFilled />
                </el-icon>
                <div class="upload-text">
                  拖拽 .zip 文件到此处
                </div>
                <div class="upload-hint">
                  最大50MB
                </div>
              </div>
            </el-upload>
          </div>

          <div
            v-if="pomConfig.importType === 'git'"
            class="form-item"
          >
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
              placeholder="例如：tests/test_login.py 或 src/test/java"
              class="cyber-input"
            />
          </div>

          <el-button
            type="primary"
            :loading="uploading"
            :disabled="!canUploadPom"
            class="action-btn"
            @click="handleUploadPom"
          >
            <span v-if="uploading">导入中...</span>
            <span v-else>导入工程</span>
          </el-button>
        </div>
      </div>

      <!-- 右侧编辑/预览区 -->
      <div class="preview-panel">
        <div class="panel-header">
          <h3 class="panel-title">
            {{ scriptSource === 'online' ? '代码编辑器' : '生成结果' }}
          </h3>
          <div
            v-if="scriptSource === 'online'"
            class="panel-actions"
          >
            <el-button
              size="small"
              @click="handleFormatCode"
            >
              格式化
            </el-button>
            <el-button
              size="small"
              type="primary"
              @click="handleRunScript"
            >
              运行测试
            </el-button>
          </div>
        </div>

        <!-- 在线代码编辑器 -->
        <div
          v-if="scriptSource === 'online'"
          class="code-editor-container"
        >
          <textarea
            v-model="onlineConfig.content"
            class="code-editor"
            placeholder="在此编写测试脚本..."
            spellcheck="false"
          />
        </div>

        <!-- 其他模式的空状态 -->
        <div
          v-else
          class="empty-state"
        >
          <div class="empty-icon">
            🤖
          </div>
          <p class="empty-text">
            填写左侧配置后开始
          </p>
        </div>
      </div>
    </div>

    <!-- 脚本列表对话框 -->
    <el-dialog
      v-model="showScriptList"
      title="已保存的脚本"
      width="80%"
      class="script-list-dialog"
    >
      <el-table
        :data="scriptList"
        style="width: 100%"
      >
        <el-table-column
          prop="id"
          label="ID"
          width="80"
        />
        <el-table-column
          prop="name"
          label="名称"
          width="200"
        />
        <el-table-column
          prop="language"
          label="语言"
          width="100"
        />
        <el-table-column
          prop="framework"
          label="框架"
          width="120"
        />
        <el-table-column
          prop="script_type"
          label="类型"
          width="100"
        />
        <el-table-column
          label="操作"
          width="300"
        >
          <template #default="scope">
            <el-button
              size="small"
              @click="handleEditScript(scope.row)"
            >
              编辑
            </el-button>
            <el-button
              size="small"
              type="primary"
              @click="handleExecuteScript(scope.row)"
            >
              执行
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="handleDeleteScript(scope.row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { UploadFilled } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import request from '@/utils/request';

const scriptSource = ref('online');

const onlineConfig = ref({
  name: '',
  language: 'PYTHON',
  framework: 'AUTO',
  entryPoint: 'test_script.py',
  content: ''
});

const aiConfig = ref({
  targetUrl: '',
  scenarioSteps: ''
});

const linearConfig = ref({
  name: '',
  language: 'PYTHON',
  file: null
});

const pomConfig = ref({
  name: '',
  language: 'PYTHON',
  importType: 'zip',
  gitRepoUrl: '',
  entryPoint: '',
  file: null
});

const generating = ref(false);
const uploading = ref(false);
const showScriptList = ref(false);
const scriptList = ref([]);

const canSaveOnline = computed(() => {
  return onlineConfig.value.name && onlineConfig.value.content && onlineConfig.value.entryPoint;
});

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

const handleSaveOnline = async () => {
  if (!canSaveOnline.value) {
    ElMessage.warning('请填写完整信息');
    return;
  }

  uploading.value = true;
  const formData = new FormData();
  formData.append('name', onlineConfig.value.name);
  formData.append('script_type', 'ONLINE');
  formData.append('language', onlineConfig.value.language);
  formData.append('framework', onlineConfig.value.framework);
  formData.append('entry_point', onlineConfig.value.entryPoint);
  formData.append('online_content', onlineConfig.value.content);

  try {
    const response = await request.post('/assistant/ui-scripts/', formData);
    ElMessage.success('在线脚本保存成功');
    onlineConfig.value.name = '';
    onlineConfig.value.content = '';
  } catch (error) {
    const errorMsg = error.response?.data?.detail || '保存失败';
    ElMessage.error(errorMsg);
  } finally {
    uploading.value = false;
  }
};

const handleGenerateAI = async () => {
  generating.value = true;
  try {
    const response = await request.post('/assistant/ui-automation/generate/', {
      url: aiConfig.value.targetUrl,
      steps: aiConfig.value.scenarioSteps
    });

    if (response.data.success) {
      // 将生成的代码填充到在线编辑器
      scriptSource.value = 'online';
      onlineConfig.value.content = response.data.code;
      onlineConfig.value.name = `AI生成_${Date.now()}`;
      ElMessage.success('脚本生成成功，已填充到编辑器');
    }
  } catch (error) {
    ElMessage.error('生成失败');
  } finally {
    generating.value = false;
  }
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
  formData.append('language', linearConfig.value.language);
  formData.append('file_path', linearConfig.value.file);

  try {
    await request.post('/assistant/ui-scripts/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    ElMessage.success('脚本上传成功');
    linearConfig.value.name = '';
    linearConfig.value.file = null;
  } catch (error) {
    const errorMsg = error.response?.data?.detail || '上传失败';
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
  formData.append('language', pomConfig.value.language);
  formData.append('entry_point', pomConfig.value.entryPoint);

  if (pomConfig.value.importType === 'zip') {
    formData.append('file_path', pomConfig.value.file);
  } else {
    formData.append('git_repo_url', pomConfig.value.gitRepoUrl);
  }

  try {
    await request.post('/assistant/ui-scripts/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    ElMessage.success('POM工程导入成功');
    pomConfig.value.name = '';
    pomConfig.value.gitRepoUrl = '';
    pomConfig.value.entryPoint = '';
    pomConfig.value.file = null;
  } catch (error) {
    const errorMsg = error.response?.data?.detail || '导入失败';
    ElMessage.error(errorMsg);
  } finally {
    uploading.value = false;
  }
};

const handleFormatCode = () => {
  ElMessage.info('代码格式化功能开发中');
};

const handleRunScript = () => {
  ElMessage.info('请先保存脚本，然后在脚本列表中执行');
};

onMounted(() => {
  // 初始化时可以加载脚本列表
});
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
  background: linear-gradient(135deg, #00d8ff 0%, #0ea5e9 50%, #06b6d4 100%);
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
  max-width: 1800px;
  margin: 0 auto;
}

.control-panel {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(100, 255, 218, 0.12);
  border-radius: 12px;
  padding: 24px;
  max-height: calc(100vh - 200px);
  overflow-y: auto;
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

.cyber-input :deep(.el-input__wrapper),
.cyber-input :deep(.el-select__wrapper) {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(100, 255, 218, 0.2);
  border-radius: 6px;
}

.cyber-input :deep(.el-input__inner),
.cyber-input :deep(.el-select__input) {
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
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 200px);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

.code-editor-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.code-editor {
  flex: 1;
  width: 100%;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(100, 255, 218, 0.2);
  border-radius: 8px;
  padding: 16px;
  color: #e2e8f0;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.6;
  resize: none;
  outline: none;
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
