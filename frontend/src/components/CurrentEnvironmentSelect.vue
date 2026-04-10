<template>
  <div class="current-env-select" :class="rootClass">
    <span v-if="showLabel && variant !== 'navbar'" class="current-env-select__label">执行环境</span>
    <el-tooltip
      :disabled="variant !== 'navbar'"
      :content="tooltipContent"
      placement="bottom"
      effect="dark"
      :show-after="280"
    >
      <div
        class="current-env-select__tooltip-anchor"
        :style="variant !== 'navbar' ? { display: 'contents' } : undefined"
        :title="variant === 'navbar' ? tooltipContent : undefined"
      >
        <el-select
          :model-value="environmentId"
          :placeholder="placeholder"
          clearable
          filterable
          :class="selectClass"
          popper-class="dark-tech-dropdown"
          :teleported="true"
          @update:model-value="setEnvironmentId"
        >
          <el-option
            v-for="e in environments"
            :key="e.id"
            :label="envOptionLabel(e)"
            :value="e.id"
          />
        </el-select>
      </div>
    </el-tooltip>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useCurrentEnvironment } from '@/composables/useCurrentEnvironment'
import type { TestEnvironmentOption } from '@/composables/useCurrentEnvironment'

const props = withDefaults(
  defineProps<{
    compact?: boolean
    showLabel?: boolean
    placeholder?: string
    /** default：独立工具栏；navbar：顶栏上下文条内嵌 */
    variant?: 'default' | 'navbar'
  }>(),
  {
    compact: false,
    showLabel: true,
    placeholder: '当前执行环境（相对路径用例将拼接 Base URL）',
    variant: 'default',
  },
)

const { environmentId, environments, loadEnvironments, setEnvironmentId } =
  useCurrentEnvironment()

const rootClass = computed(() => ({
  'current-env-select--compact': props.compact,
  'current-env-select--navbar': props.variant === 'navbar',
}))

const selectClass = computed(() => [
  'current-env-select__control',
  { 'current-env-select__control--navbar': props.variant === 'navbar' },
])

function envOptionLabel(e: TestEnvironmentOption) {
  const b = (e.base_url || '').trim()
  return b ? `${e.name} · ${b}` : e.name
}

const tooltipContent = computed(() => {
  if (environmentId.value == null) return props.placeholder
  const e = environments.value.find((x) => x.id === environmentId.value)
  return e ? envOptionLabel(e) : props.placeholder
})

onMounted(() => {
  loadEnvironments()
})
</script>

<style scoped>
.current-env-select {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  /* 与 MainLayout .tech-select-wrapper 一致：强制 EP 继承（独立页面无外层 wrapper 时仍生效） */
  --el-input-bg-color: rgba(255, 255, 255, 0.08);
  --el-input-text-color: #ffffff;
  --el-input-placeholder-color: #94a3b8;
  --el-input-border-color: rgba(0, 200, 255, 0.3);
  --el-input-hover-border-color: #00c8ff;
  --el-input-focus-border-color: #00c8ff;
  --el-select-input-color: #ffffff;
}

.current-env-select :deep(.el-input__wrapper) {
  min-height: 38px;
  padding: 4px 12px;
  border-radius: 8px;
  background-color: var(--el-input-bg-color) !important;
  box-shadow: 0 0 0 1px var(--el-input-border-color) inset !important;
  border: none !important;
  transition:
    background-color 0.2s ease,
    box-shadow 0.2s ease !important;
}

.current-env-select :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--el-input-hover-border-color) inset !important;
}

.current-env-select :deep(.el-input__wrapper.is-focus) {
  box-shadow:
    0 0 0 1px var(--el-input-focus-border-color) inset,
    0 0 14px rgba(0, 200, 255, 0.25) !important;
}

.current-env-select :deep(.el-input__inner) {
  color: var(--el-input-text-color) !important;
  -webkit-text-fill-color: var(--el-input-text-color) !important;
}

.current-env-select :deep(.el-select__input-wrapper),
.current-env-select :deep(.el-select__input) {
  color: var(--el-select-input-color) !important;
  -webkit-text-fill-color: var(--el-select-input-color) !important;
}

.current-env-select :deep(.el-select__selected-item) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
  font-weight: 500;
  font-size: 13px;
  color: var(--el-select-input-color) !important;
  -webkit-text-fill-color: var(--el-select-input-color) !important;
}

.current-env-select :deep(.el-select__placeholder),
.current-env-select :deep(.el-select__placeholder span) {
  color: var(--el-input-placeholder-color) !important;
  -webkit-text-fill-color: var(--el-input-placeholder-color) !important;
}

.current-env-select :deep(.el-select__caret) {
  width: 12px !important;
  opacity: 1 !important;
  color: var(--el-input-placeholder-color) !important;
}

.current-env-select :deep(.el-select__selection) {
  overflow: hidden;
}

.current-env-select__label {
  font-size: 12px;
  color: var(--layout-text-muted, #9ca3b8);
  white-space: nowrap;
}

.current-env-select__control {
  min-width: 220px;
  max-width: min(420px, 36vw);
}

.current-env-select--compact .current-env-select__control {
  min-width: 180px;
  max-width: min(360px, 70vw);
}

.current-env-select--compact .current-env-select__label {
  display: none;
}

/* ========== 顶栏 navbar 变体：与 MainLayout context-switcher 对齐 ========== */
.current-env-select--navbar {
  flex: 1 1 50%;
  min-width: 0;
  gap: 0;
  padding: 6px 10px;
  align-items: center;
}

.current-env-select__tooltip-anchor {
  min-width: 0;
  flex: 1 1 auto;
  display: block;
}

.current-env-select--navbar .current-env-select__control--navbar {
  width: 100%;
  min-width: 0;
  max-width: none;
}

.current-env-select--navbar :deep(.el-input__wrapper) {
  min-height: 38px;
}
</style>
