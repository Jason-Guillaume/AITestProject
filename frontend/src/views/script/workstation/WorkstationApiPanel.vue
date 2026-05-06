<template>
  <div class="layout sw-cyber">
    <aside class="sw-cyber-panel col-tree">
      <div class="panel-head sw-glow-text">场景 / 集合</div>
      <el-tree
        :key="wb.apiTreeKey"
        class="tree"
        lazy
        :load="wb.loadApiTreeNode"
        :props="{ label: 'label', children: 'children', isLeaf: 'isLeaf' }"
        highlight-current
        @node-click="wb.onApiTreeClick"
      />
    </aside>
    <div class="col-main">
      <div class="sw-cyber-panel is-active editor-block">
        <p class="path sw-glow-text">{{ scenarioLabel }}</p>
        <div class="monaco-box">
          <Suspense v-if="showMonaco">
            <template #default>
              <MonacoEditor v-model="yamlModel" language="yaml" />
            </template>
            <template #fallback>
              <div class="monaco-ph">加载编辑器组件…</div>
            </template>
          </Suspense>
          <div v-else class="monaco-ph">准备编辑器…</div>
        </div>
      </div>
      <el-tabs v-model="wb.mainTab" class="tabs">
        <el-tab-pane label="断言与延迟" name="report">
          <div class="metrics sw-cyber-panel">
            <div class="metric"><span class="k">最近运行</span><span class="v sw-glow-text">{{ wb.apiLatest.runAt }}</span></div>
            <div class="metric"><span class="k">断言</span><span class="v sw-glow-text">{{ wb.apiLatest.checksPct }}%</span></div>
            <div class="metric"><span class="k">P95</span><span class="v sw-glow-text">{{ wb.apiLatest.p95 }}ms</span></div>
          </div>
          <div ref="chartMount" class="chart sw-cyber-panel" />
          <el-table :data="wb.apiReportRows" class="tbl" :border="false" size="small">
            <el-table-column prop="name" label="步骤" />
            <el-table-column prop="latency" label="ms" width="72" />
            <el-table-column prop="ok" label="OK" width="56" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="终端" name="terminal">
          <div class="term sw-cyber-panel">
            <div v-for="(line, i) in wb.mockTerminalLines" :key="i" class="line">{{ line }}</div>
            <div v-if="wb.mockTerminalLines.length === 0" class="idle">$ 等待「跑场景」</div>
          </div>
        </el-tab-pane>
      </el-tabs>
      <div class="sw-cyber-panel actions">
        <el-button class="ghost-btn accent" :icon="VideoPlay" @click="wb.runApiMock">跑场景</el-button>
      </div>
    </div>
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
const chartMount = ref<HTMLElement | null>(null)
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

const scenarioLabel = computed(() => `scenario_${unref(wb.selectedApiScriptKey)}.yaml`)

const yamlModel = computed({
  get: () => wb.apiScripts[unref(wb.selectedApiScriptKey)] ?? '',
  set: (v: string) => {
    const k = unref(wb.selectedApiScriptKey)
    wb.apiScripts[k] = v
  },
})

function renderChart() {
  if (!chartMount.value) return
  chart?.dispose()
  chart = echarts.init(chartMount.value)
  const s = wb.apiLatest.series?.length ? wb.apiLatest.series : [90, 110, 95]
  chart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 36, right: 8, top: 16, bottom: 24 },
    xAxis: { type: 'category', data: s.map((_, i) => `S${i + 1}`), axisLine: { lineStyle: { color: 'rgba(0,240,255,0.2)' } } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } } },
    series: [{ type: 'bar', data: s, itemStyle: { color: 'rgba(0,240,255,0.45)' }, barMaxWidth: 28 }],
  })
}

watch(
  () => [wb.mainTab, wb.apiLatest.series],
  () => {
    if (unref(wb.mainTab) === 'report') nextTick(renderChart)
  },
)

onMounted(() => {
  monacoDeferTimer = window.setTimeout(() => {
    showMonaco.value = true
    monacoDeferTimer = null
  }, 2000)
  wb.chartApiRef.value = chartMount.value
  nextTick(() => {
    requestAnimationFrame(() => nextTick(renderChart))
  })
})
</script>

<style scoped src="./panelCyber.css"></style>
<style scoped>
.layout {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 14px;
  min-height: 620px;
}
.col-tree {
  padding: 12px;
}
.panel-head {
  font-size: 11px;
  letter-spacing: 0.12em;
  color: rgba(255, 255, 255, 0.45);
  margin-bottom: 10px;
}
.tree {
  background: transparent !important;
  --el-tree-node-hover-bg-color: rgba(0, 240, 255, 0.06);
}
.col-main {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}
.editor-block {
  padding: 10px;
  flex: 1;
  min-height: 260px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.monaco-box {
  flex: 1;
  min-height: 200px;
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
.editor-block :deep(.monaco-editor-root) {
  flex: 1;
  min-height: 200px;
  border: none !important;
}
.path {
  font-size: 12px;
  font-family: ui-monospace, monospace;
}
.tabs :deep(.el-tabs__item.is-active) {
  color: #00f0ff;
  text-shadow: 0 0 8px rgba(0, 240, 255, 0.5);
}
.metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding: 12px;
  margin-bottom: 10px;
}
.metric .k {
  display: block;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
  margin-bottom: 4px;
}
.metric .v {
  font-family: ui-monospace, monospace;
  font-size: 20px;
}
.chart {
  height: 200px;
  margin-bottom: 10px;
}
.tbl {
  background: transparent !important;
  --el-table-bg-color: transparent;
  --el-table-border-color: transparent;
}
.term {
  padding: 12px;
  font-family: ui-monospace, monospace;
  font-size: 12px;
  color: #a5b4fc;
  min-height: 160px;
}
.idle {
  opacity: 0.5;
}
.actions {
  padding: 10px;
}
.ghost-btn {
  background: transparent !important;
  border: 1px solid rgba(0, 240, 255, 0.1) !important;
}
.ghost-btn:hover {
  border-color: rgba(0, 240, 255, 0.8) !important;
  box-shadow: 0 0 15px rgba(0, 240, 255, 0.2) !important;
}
.tip {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  margin: 0;
}
@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
