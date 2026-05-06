<template>
  <div class="mobile-workspace-shell">
    <p class="mobile-workspace-shell__badge">Layout · Mobile</p>
    <el-empty description="设备会话、Node 编排与录制流将挂载于此区域" :image-size="64" />
    <p class="mobile-workspace-shell__hint">
      Telemetry 与 Run Output 仍使用下方共用面板；平台切换不销毁终端单例。
    </p>
  </div>
</template>

<style scoped>
.mobile-workspace-shell {
  flex: 1;
  min-height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 16px;
  border-radius: 10px;
  border: 1px dashed rgba(244, 114, 182, 0.35);
  background: rgba(244, 114, 182, 0.04);
}

.mobile-workspace-shell__badge {
  margin: 0;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(244, 114, 182, 0.85);
}

.mobile-workspace-shell__hint {
  margin: 0;
  max-width: 360px;
  font-size: 11px;
  line-height: 1.5;
  color: rgba(148, 163, 184, 0.85);
  text-align: center;
}
</style>
