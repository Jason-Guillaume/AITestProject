<script setup lang="ts">
defineProps<{
  executeLoading: boolean
}>()

const browserType = defineModel<string>('browserType', { required: true })
const isHeadless = defineModel<boolean>('isHeadless', { required: true })
const parallelCount = defineModel<number>('parallelCount', { required: true })
</script>

<template>
  <div class="params-drawer__body">
    <p class="params-drawer__hint">Web 运行器参数；与 Inspector 解耦，保持主栏极简。</p>
    <div class="params-drawer__row params-drawer__row--top">
      <span class="params-drawer__label">Browser Type</span>
      <el-select v-model="browserType" size="small" class="params-drawer__select" :disabled="executeLoading">
        <el-option label="Chrome" value="chrome" />
        <el-option label="Edge" value="edge" />
        <el-option label="Firefox" value="firefox" />
      </el-select>
    </div>
    <div class="params-drawer__row params-drawer__row--top params-drawer__row--switch">
      <span class="params-drawer__label">Headless</span>
      <el-switch
        v-model="isHeadless"
        inline-prompt
        active-text="无头"
        inactive-text="有头"
        class="headless-switch--cyber"
        :disabled="executeLoading"
      />
    </div>
    <div class="params-drawer__row params-drawer__row--top">
      <span class="params-drawer__label">并行度 (parallel)</span>
      <el-input-number v-model="parallelCount" :min="1" :max="50" size="small" controls-position="right" />
    </div>
  </div>
</template>
