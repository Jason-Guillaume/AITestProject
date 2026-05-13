<template>
  <div class="inspector-web-panel">
    <section class="inspector-block">
      <h4 class="inspector-block__h">
        Browser Config
      </h4>
      <el-select
        :model-value="browserType"
        size="small"
        class="inspector-web-panel__select"
        :disabled="executeLoading"
        @update:model-value="emit('update:browserType', $event)"
      >
        <el-option
          label="Chrome"
          value="chrome"
        />
        <el-option
          label="Edge"
          value="edge"
        />
        <el-option
          label="Firefox"
          value="firefox"
        />
      </el-select>
    </section>
    <section class="inspector-block">
      <h4 class="inspector-block__h">
        Headless
      </h4>
      <div class="inspector-web-panel__row">
        <span class="inspector-web-panel__hint">Telemetry 浏览器进程形态</span>
        <el-switch
          :model-value="isHeadless"
          inline-prompt
          active-text="无头"
          inactive-text="有头"
          class="headless-switch--cyber"
          :disabled="executeLoading"
          @change="(v: string | number | boolean) => emit('update:isHeadless', Boolean(v))"
        />
      </div>
    </section>
    <el-divider class="inspector-divider" />
    <section class="inspector-block inspector-block--element-tools">
      <h4 class="inspector-block__h">
        元素校验工具
      </h4>
      <p class="inspector-block__desc">
        选择器探测（对接 DOM / POM 前为占位）。
      </p>
      <el-input
        :model-value="elementProbeSelector"
        size="small"
        clearable
        placeholder="CSS / XPath / data-testid"
        class="inspector-element-input"
        @update:model-value="emit('update:elementProbeSelector', $event)"
      />
      <el-button
        type="primary"
        size="small"
        class="inspector-element-btn"
        :disabled="!elementProbeSelector.trim()"
        @click="emit('element-validate')"
      >
        校验
      </el-button>
    </section>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  isHeadless: boolean
  browserType: string
  executeLoading: boolean
  elementProbeSelector: string
}>()

const emit = defineEmits<{
  'update:isHeadless': [v: boolean]
  'update:browserType': [v: string]
  'update:elementProbeSelector': [v: string]
  'element-validate': []
}>()
</script>

<style scoped>
.inspector-web-panel__select {
  width: 100%;
}

.inspector-web-panel__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.inspector-web-panel__hint {
  font-size: 11px;
  color: rgba(148, 163, 184, 0.88);
}

.inspector-block__h {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 600;
  color: rgba(203, 213, 225, 0.92);
}

.inspector-block__desc {
  margin: 0 0 8px;
  font-size: 11px;
  line-height: 1.45;
  color: rgba(148, 163, 184, 0.88);
}

.inspector-block {
  margin-bottom: 12px;
}

.inspector-element-input {
  margin-bottom: 8px;
}

.inspector-element-btn {
  width: 100%;
  --el-button-bg-color: rgba(0, 240, 255, 0.12);
  --el-button-border-color: rgba(0, 240, 255, 0.35);
}

.inspector-divider {
  margin: 12px 0 !important;
  border-color: rgba(255, 255, 255, 0.08) !important;
}

.headless-switch--cyber :deep(.el-switch:not(.is-checked) .el-switch__core) {
  border-color: rgba(167, 139, 250, 0.42);
  background: rgba(30, 27, 48, 0.88);
}

.headless-switch--cyber :deep(.el-switch.is-checked .el-switch__core) {
  background-color: #00f0ff;
  border-color: #00f0ff;
  box-shadow: 0 0 8px rgba(0, 240, 255, 0.45);
}
</style>
