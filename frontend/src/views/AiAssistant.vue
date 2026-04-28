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
          <ModelConfigForm />
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Plus, Delete } from '@element-plus/icons-vue'
import ModelConfigForm from '@/components/ModelConfigForm.vue'

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

function addRule() {
  rules.value.push('')
}

function removeRule(idx) {
  rules.value.splice(idx, 1)
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
