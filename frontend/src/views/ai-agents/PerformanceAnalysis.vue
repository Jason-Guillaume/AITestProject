<template>
  <div class="ai-agent-page">
    <div class="agent-header">
      <div class="agent-icon">📊</div>
      <div class="agent-info">
        <h1 class="agent-title">AI 性能数据分析助手</h1>
        <p class="agent-subtitle">分析性能测试结果数据，自动识别性能瓶颈和异常指标</p>
      </div>
    </div>

    <div class="agent-content">
      <el-card class="feature-card" shadow="never">
        <h3>功能特性</h3>
        <ul>
          <li>📈 性能数据分析</li>
          <li>🔍 瓶颈智能诊断</li>
          <li>📉 趋势预测分析</li>
          <li>💡 优化建议生成</li>
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
  background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
  border-radius: 20px;
  box-shadow: 0 8px 24px rgba(255, 236, 210, 0.3);
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
