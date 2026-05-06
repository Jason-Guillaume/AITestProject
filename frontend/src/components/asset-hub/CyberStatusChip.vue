<script setup lang="ts">
import { computed } from 'vue'
import type { CyberStatusVariant } from './cyberStatusTypes'

const props = defineProps<{
  variant: CyberStatusVariant
  label: string
}>()

const dotClass = computed(() => {
  const v = props.variant
  const base = 'asset-hub-status-chip__dot'
  if (v === 'sync-pending') return [base, `${base}--orange-breath`]
  if (v === 'sync-ready' || v === 'run-on') return [base, `${base}--cyan-solid`]
  if (v === 'exec-success') return [base, `${base}--green-solid`]
  if (v === 'exec-failed') return [base, `${base}--red-solid`]
  if (v === 'exec-unknown' || v === 'run-off') return [base, `${base}--slate-solid`]
  return [base, `${base}--slate-solid`]
})
</script>

<template>
  <span class="asset-hub-status-chip" :class="`asset-hub-status-chip--${variant}`">
    <span :class="dotClass" aria-hidden="true" />
    <span class="asset-hub-status-chip__text">{{ label }}</span>
  </span>
</template>

<style scoped>
.asset-hub-status-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 11px;
  border-radius: 999px;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-sizing: border-box;
  vertical-align: middle;
}

.asset-hub-status-chip__text {
  font-family: ui-monospace, 'JetBrains Mono', 'Monaco', 'Consolas', monospace;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  line-height: 1.2;
  color: rgba(226, 232, 240, 0.92);
}

/* 边框：按语义着色（无填充块） */
.asset-hub-status-chip--sync-pending {
  border-color: rgba(255, 152, 0, 0.42);
  box-shadow: 0 0 0 1px rgba(255, 152, 0, 0.06);
}

.asset-hub-status-chip--sync-ready {
  border-color: rgba(0, 243, 255, 0.38);
  box-shadow: 0 0 0 1px rgba(0, 243, 255, 0.05);
}

.asset-hub-status-chip--exec-success {
  border-color: rgba(52, 211, 153, 0.38);
}

.asset-hub-status-chip--exec-failed {
  border-color: rgba(248, 113, 113, 0.42);
}

.asset-hub-status-chip--exec-unknown {
  border-color: rgba(148, 163, 184, 0.35);
}

.asset-hub-status-chip--run-on {
  border-color: rgba(0, 243, 255, 0.36);
}

.asset-hub-status-chip--run-off {
  border-color: rgba(148, 163, 184, 0.32);
}

.asset-hub-status-chip__dot {
  flex: none;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  transform: translateZ(0);
}

/* 待初始化：橙色呼吸灯 */
.asset-hub-status-chip__dot--orange-breath {
  background: radial-gradient(circle at 35% 35%, #ffe082, #ff9800 55%, #e65100);
  animation: asset-hub-dot-orange-breath 1.85s ease-in-out infinite;
}

/* 已就绪 / 启用：赛博青常亮 */
.asset-hub-status-chip__dot--cyan-solid {
  background: radial-gradient(circle at 35% 35%, #e0f7fa, #00e5ff 58%, #00838f);
  box-shadow:
    0 0 6px rgba(0, 229, 255, 0.95),
    0 0 14px rgba(0, 243, 255, 0.45);
}

.asset-hub-status-chip__dot--green-solid {
  background: radial-gradient(circle at 35% 35%, #d1fae5, #34d399 60%, #047857);
  box-shadow: 0 0 8px rgba(52, 211, 153, 0.55);
}

.asset-hub-status-chip__dot--red-solid {
  background: radial-gradient(circle at 35% 35%, #fecaca, #f87171 58%, #b91c1c);
  box-shadow: 0 0 8px rgba(248, 113, 113, 0.5);
}

.asset-hub-status-chip__dot--slate-solid {
  background: radial-gradient(circle at 35% 35%, #e2e8f0, #94a3b8 65%, #475569);
  box-shadow: 0 0 6px rgba(148, 163, 184, 0.35);
}

@keyframes asset-hub-dot-orange-breath {
  0%,
  100% {
    box-shadow:
      0 0 4px 1px rgba(255, 152, 0, 0.55),
      0 0 10px rgba(255, 183, 77, 0.35);
  }
  50% {
    box-shadow:
      0 0 12px 3px rgba(255, 193, 7, 0.85),
      0 0 26px rgba(255, 152, 0, 0.5);
  }
}
</style>
