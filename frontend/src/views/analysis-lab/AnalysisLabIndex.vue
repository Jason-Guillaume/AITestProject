<template>
  <div class="analysis-lab analysis-lab--cyber">
    <header class="analysis-lab__hero glass-panel">
      <h1 class="analysis-lab__title">Analysis Lab</h1>
      <p class="analysis-lab__lead">
        多态报告视图 · Node Step Flow · Media Evidence · AI Diagnostics（与指挥中心 Telemetry / Artifacts 联动）
      </p>
    </header>
    <section class="analysis-lab__grid">
      <el-card class="analysis-lab__card" shadow="never">
        <template #header>入口</template>
        <p class="analysis-lab__hint">
          从自动化指挥中心一次 Telemetry 运行结束后，可使用
          <strong>[View Depth Report]</strong> 携带执行记录 ID 进入深度报告。
        </p>
        <el-button type="primary" plain @click="$router.push('/analysis-lab/reports/demo')">
          打开示例多态布局（demo）
        </el-button>
      </el-card>
    </section>
  </div>
</template>

<style scoped>
.analysis-lab--cyber {
  padding: 20px 24px;
  color: rgba(255, 255, 255, 0.9);
}

.glass-panel {
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(12, 18, 32, 0.42);
  backdrop-filter: blur(16px);
  padding: 18px 20px;
  margin-bottom: 16px;
}

.analysis-lab__title {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: #00f0ff;
  text-shadow: 0 0 14px rgba(0, 240, 255, 0.35);
}

.analysis-lab__lead {
  margin: 0;
  font-size: 13px;
  color: rgba(148, 163, 184, 0.95);
  line-height: 1.55;
}

.analysis-lab__card {
  --el-card-bg-color: rgba(0, 0, 0, 0.2);
  --el-card-border-color: rgba(0, 240, 255, 0.15);
  max-width: 520px;
  color: rgba(226, 232, 240, 0.92);
}

.analysis-lab__hint {
  margin: 0 0 14px;
  font-size: 13px;
  line-height: 1.5;
  color: rgba(203, 213, 225, 0.9);
}
</style>
