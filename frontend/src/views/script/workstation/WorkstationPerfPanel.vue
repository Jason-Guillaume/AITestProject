<template>
  <div class="layout sw-cyber">
    <aside class="sw-cyber-panel col-form">
      <div class="panel-head sw-glow-text">
        运行参数
      </div>
      <el-form
        label-position="top"
        class="form"
      >
        <el-form-item label="脚本">
          <el-radio-group
            v-model="wb.selectedPerfScriptKey"
            size="small"
            class="script-pick"
          >
            <el-radio-button label="smoke">
              smoke.js
            </el-radio-button>
            <el-radio-button label="load">
              load.js
            </el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="虚拟用户数 (VUs)">
          <el-input-number
            v-model="wb.perfForm.vus"
            :min="1"
            :max="500"
            class="full"
          />
        </el-form-item>
        <el-form-item label="持续时间 (秒)">
          <el-input-number
            v-model="wb.perfForm.durationSec"
            :min="10"
            :max="3600"
            class="full"
          />
        </el-form-item>
        <el-form-item label="QPS 告警阈值">
          <el-input-number
            v-model="wb.perfForm.qpsThreshold"
            :min="1"
            :max="1000000"
            class="full"
          />
        </el-form-item>
      </el-form>
      <el-button
        class="ghost-btn accent full-w"
        :icon="VideoPlay"
        @click="wb.runPerfMock"
      >
        运行 k6（演示）
      </el-button>
    </aside>
    <div class="col-center">
      <div class="sw-cyber-panel is-active editor-wrap">
        <p class="path sw-glow-text">
          k6 脚本 · {{ perfScriptName }}.js
        </p>
        <div class="monaco-box">
          <Suspense v-if="showMonaco">
            <template #default>
              <MonacoEditor
                v-model="jsModel"
                language="javascript"
              />
            </template>
            <template #fallback>
              <div class="monaco-ph">
                加载编辑器组件…
              </div>
            </template>
          </Suspense>
          <div
            v-else
            class="monaco-ph"
          >
            准备编辑器…
          </div>
        </div>
      </div>
      <div class="sw-cyber-panel chart-zone">
        <el-empty
          description="实时压力曲线图（接入压测引擎后展示）"
          :image-size="120"
        />
      </div>
    </div>
    <aside class="sw-cyber-panel col-side">
      <div class="panel-head sw-glow-text">
        摘要
      </div>
      <div class="kv">
        <span class="k">最近运行</span><span class="v sw-glow-text">{{ wb.perfLatest.runAt }}</span>
      </div>
      <div class="kv">
        <span class="k">RPS</span><span class="v sw-glow-text">{{ wb.perfLatest.rps }}</span>
      </div>
      <div class="kv">
        <span class="k">P95</span><span class="v sw-glow-text">{{ wb.perfLatest.p95ms }}ms</span>
      </div>
      <div
        ref="sideChart"
        class="mini-chart sw-cyber-panel"
      />
      <el-table
        :data="wb.perfDetailRows"
        class="tbl"
        :border="false"
        size="small"
      >
        <el-table-column
          prop="metric"
          label="指标"
        />
        <el-table-column
          prop="value"
          label="值"
          width="100"
        />
      </el-table>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, ref, watch, onMounted, onBeforeUnmount, nextTick, unref } from 'vue'
import { VideoPlay } from '@element-plus/icons-vue'
import { defineAsyncComponent } from 'vue'
import * as echarts from 'echarts'
import { SCRIPT_WORKBENCH_INJECT } from './workbenchInject'

const MonacoEditor = defineAsyncComponent(() => import('@/components/MonacoEditor/index.vue'))

const wb = inject(SCRIPT_WORKBENCH_INJECT)!
const perfScriptName = computed(() => unref(wb.selectedPerfScriptKey))
const sideChart = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null

const showMonaco = ref(false)
let monacoDeferTimer: ReturnType<typeof setTimeout> | null = null

onBeforeUnmount(() => {
  if (monacoDeferTimer != null) {
    clearTimeout(monacoDeferTimer)
    monacoDeferTimer = null
  }
  chart?.dispose()
  chart = null
})

const jsModel = computed({
  get: () => wb.perfScripts[unref(wb.selectedPerfScriptKey)] ?? '',
  set: (v: string) => {
    wb.perfScripts[unref(wb.selectedPerfScriptKey)] = v
  },
})

function renderSide() {
  if (!sideChart.value) return
  chart?.dispose()
  chart = echarts.init(sideChart.value)
  const s = wb.perfLatest.series?.length ? wb.perfLatest.series : [0, 1, 1.5, 2, 1.8]
  chart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 28, right: 4, top: 8, bottom: 20 },
    xAxis: { type: 'category', show: false, data: s.map((_, i) => i) },
    yAxis: { type: 'value', show: false, splitLine: { show: false } },
    series: [{ type: 'line', data: s, smooth: true, lineStyle: { color: 'rgba(0,240,255,0.85)' }, areaStyle: { color: 'rgba(0,240,255,0.12)' } }],
  })
}

watch(
  () => wb.perfLatest.series,
  () => nextTick(renderSide),
  { deep: true },
)

onMounted(() => {
  monacoDeferTimer = window.setTimeout(() => {
    showMonaco.value = true
    monacoDeferTimer = null
  }, 2000)
  wb.chartPerfRef.value = sideChart.value
  nextTick(() => {
    requestAnimationFrame(() => nextTick(renderSide))
  })
})
</script>

<style scoped src="./panelCyber.css"></style>
<style scoped>
.layout {
  display: grid;
  grid-template-columns: 240px 1fr 260px;
  gap: 14px;
  min-height: 640px;
  align-items: stretch;
}
.col-form {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.panel-head {
  font-size: 11px;
  letter-spacing: 0.12em;
  color: rgba(255, 255, 255, 0.45);
}
.form :deep(.el-form-item__label) {
  color: rgba(255, 255, 255, 0.5) !important;
  font-size: 12px;
}
.full {
  width: 100%;
}
.full-w {
  width: 100%;
}
.ghost-btn {
  background: transparent !important;
  border: 1px solid rgba(0, 240, 255, 0.1) !important;
}
.ghost-btn:hover {
  border-color: rgba(0, 240, 255, 0.8) !important;
  box-shadow: 0 0 15px rgba(0, 240, 255, 0.2) !important;
}
.col-center {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}
.editor-wrap {
  flex: 1;
  min-height: 280px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.monaco-box {
  flex: 1;
  min-height: 220px;
  display: flex;
  flex-direction: column;
}
.monaco-ph {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.35);
  letter-spacing: 0.06em;
}
.editor-wrap :deep(.monaco-editor-root) {
  flex: 1;
  min-height: 220px;
  border: none !important;
}
.path {
  font-size: 12px;
  font-family: ui-monospace, monospace;
}
.chart-zone {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.chart-zone :deep(.el-empty__description) {
  color: rgba(0, 240, 255, 0.55);
  text-shadow: 0 0 8px rgba(0, 240, 255, 0.35);
}
.col-side {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.kv .k {
  display: block;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
}
.kv .v {
  font-family: ui-monospace, monospace;
  font-size: 18px;
}
.mini-chart {
  height: 140px;
  padding: 4px;
}
.tbl {
  background: transparent !important;
  --el-table-bg-color: transparent;
  --el-table-border-color: transparent;
}
@media (max-width: 1200px) {
  .layout {
    grid-template-columns: 220px 1fr;
    grid-template-rows: auto auto;
  }
  .col-side {
    grid-column: 1 / -1;
  }
}
@media (max-width: 768px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
