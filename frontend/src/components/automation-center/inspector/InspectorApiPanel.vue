<template>
  <div class="inspector-api-panel">
    <section class="inspector-block">
      <h4 class="inspector-block__h">API · Telemetry</h4>
      <p class="inspector-block__desc">
        场景执行 Telemetry 由运行器输出；Artifacts（HAR、响应体）将汇总至 Analysis Lab。
      </p>
    </section>
  </div>
</template>

<script setup lang="ts"></script>

<style scoped>
.inspector-block__h {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 600;
  color: rgba(203, 213, 225, 0.92);
}

.inspector-block__desc {
  margin: 0;
  font-size: 11px;
  line-height: 1.5;
  color: rgba(148, 163, 184, 0.88);
}
</style>
