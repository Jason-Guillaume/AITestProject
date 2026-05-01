<template>
  <div class="ai-agent-page">
    <div class="agent-header">
      <div class="agent-icon">⚡</div>
      <div class="agent-info">
        <h1 class="agent-title">AI 接口自动化脚本助手</h1>
        <p class="agent-subtitle">基于接口用例自动生成Python/Java自动化测试脚本</p>
      </div>
    </div>

    <div class="agent-content">
      <el-card class="feature-card" shadow="never">
        <h3>功能特性</h3>
        <ul>
          <li>💻 脚本自动生成</li>
          <li>✅ 断言智能添加</li>
          <li>📊 数据驱动支持</li>
          <li>🔄 场景编排优化</li>
        </ul>
      </el-card>

      <el-card class="work-area" shadow="never">
        <h3>工作区</h3>
        <el-empty description="功能开发中，敬请期待..." />
      </el-card>
    </div>
  </div>
</template>

<script setup>
// Agent logic will be implemented here
</script>

<style scoped>
.ai-agent-page {
  padding: 32px;
  min-height: 100vh;
  background: linear-gradient(180deg, #0a0e1a 0%, #1a1f2e 100%);
}

.agent-header {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 32px;
}

.agent-icon {
  width: 80px;
  height: 80px;
  font-size: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #30cfd0 0%, #330867 100%);
  border-radius: 20px;
  box-shadow: 0 8px 24px rgba(48, 207, 208, 0.3);
}

.agent-info {
  flex: 1;
}

.agent-title {
  font-size: 32px;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0 0 8px 0;
}

.agent-subtitle {
  font-size: 16px;
  color: rgba(148, 163, 184, 0.9);
  margin: 0;
}

.agent-content {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 24px;
}

.feature-card,
.work-area {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(100, 255, 218, 0.12);
  border-radius: 16px;
}

.feature-card h3,
.work-area h3 {
  color: #e2e8f0;
  margin: 0 0 16px 0;
}

.feature-card ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.feature-card li {
  color: rgba(148, 163, 184, 0.9);
  padding: 8px 0;
  font-size: 14px;
}

@media (max-width: 1024px) {
  .agent-content {
    grid-template-columns: 1fr;
  }
}
</style>
