<template>
  <div class="placeholder-page cyber-page cyber-glass">
    <el-result icon="info" title="帮助中心" sub-title="该模块正在开发中" />
  </div>
</template>

<script setup>
</script>

<style scoped>
.placeholder-page {
  border-radius: 10px;
  padding: 20px;
  min-height: 420px;
}

.placeholder-page :deep(.el-result__title) {
  color: #e2e8f0;
}

.placeholder-page :deep(.el-result__subtitle) {
  color: rgba(226, 232, 240, 0.65);
}
</style>

