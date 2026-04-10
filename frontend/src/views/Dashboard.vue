<template>
  <div class="dashboard dashboard--cyber relative w-full min-h-full pb-2">
    <div class="dashboard__mesh pointer-events-none" aria-hidden="true" />
    <div class="dashboard__scan pointer-events-none" aria-hidden="true" />

    <div class="relative z-[1] flex flex-col gap-5">
      <!-- 统计卡片 -->
      <div class="stat-cards">
        <div
          v-for="card in statCards"
          :key="card.key"
          class="stat-card glass-panel glass-panel--interactive"
        >
          <div class="stat-card__value tech-metric">{{ card.valueDisplay }}</div>
          <div class="stat-card__label">{{ card.label }}</div>
          <div class="stat-card__sub">
            较昨日
            <span :class="card.deltaNum >= 0 ? 'stat-card__delta stat-card__delta--up' : 'stat-card__delta stat-card__delta--down'">
              {{ card.deltaText }}
            </span>
          </div>
          <div class="stat-card__bar-rail">
            <div class="stat-card__bar" :style="{ background: card.barBg }">
              <div
                class="stat-card__bar-fill"
                :style="{ width: card.barWidth, background: card.barColor }"
              />
            </div>
          </div>
        </div>
      </div>

      <div class="dashboard-middle">
        <div class="chart-card glass-panel glass-panel--chart flex-[2] min-w-0">
          <div class="chart-card__header">
            <span class="chart-card__title">测试执行情况</span>
            <div class="chart-tabs">
              <button
                type="button"
                class="chart-tab"
                :class="{ 'chart-tab--active': chartTab === 'week' }"
                @click="chartTab = 'week'"
              >
                周
              </button>
              <button
                type="button"
                class="chart-tab"
                :class="{ 'chart-tab--active': chartTab === 'month' }"
                @click="chartTab = 'month'"
              >
                月
              </button>
            </div>
          </div>
          <div ref="lineChartEl" class="chart-box" />
        </div>

        <div class="chart-card glass-panel glass-panel--chart flex-1 min-w-[260px]">
          <div class="chart-card__header">
            <span class="chart-card__title">AI测试分析</span>
            <span class="chart-card__sub-title">质量风险分析</span>
          </div>
          <div ref="pieChartEl" class="chart-box" />
          <div class="pie-legend">
            <span v-for="leg in pieLegend" :key="leg.name" class="pie-legend-item">
              <i :style="{ background: leg.color }" />
              {{ leg.name }}
            </span>
          </div>
        </div>
      </div>

      <div class="dashboard-bottom">
        <div class="chart-card glass-panel glass-panel--chart flex-[2] min-w-0">
          <div class="chart-card__header">
            <span class="chart-card__title">缺陷统计分析</span>
          </div>
          <div ref="barChartEl" class="chart-box chart-box--bar" />
        </div>

        <div class="chart-card glass-panel activity-card flex-[1.2] min-w-[280px]">
          <div class="chart-card__header">
            <span class="chart-card__title">最近测试任务</span>
            <span class="chart-card__meta">
              {{ streamConnected ? "实时通道已连接" : "实时通道重连中" }} · 更新于 {{ lastUpdatedText }}
            </span>
          </div>
          <div class="activity-list">
            <div v-for="item in activities" :key="item.id" class="activity-item">
              <el-tag :type="item.tagType" size="small" class="activity-tag">{{ item.tag }}</el-tag>
              <span class="activity-text">{{ item.text }}</span>
              <span class="activity-time">{{ item.time }}</span>
            </div>
            <div v-if="!activities.length" class="activity-empty">
              暂无最近任务数据（数据来自真实任务/缺陷/计划记录）
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch, onBeforeUnmount, computed } from "vue";
import * as echarts from "echarts";
import { ElMessage } from "element-plus";
import { getDashboardSummaryApi, getDashboardStreamUrl } from "@/api/dashboard";
import { useRealtimePolling } from "@/composables/useRealtimePolling";
import { useSseRefreshTrigger } from "@/composables/useSseRefreshTrigger";

/** Cyberpunk 仪表盘调色：霓虹青、电蓝、亮紫、霓虹绿 */
const CYBER = {
  neonCyan: "#00f5ff",
  electricBlue: "#3b8cff",
  brightPurple: "#c026fc",
  neonGreen: "#39ff14",
};

const THEME = {
  ...CYBER,
  cyanSoft: "#67e8f9",
  /** 坐标轴标签：浅灰 */
  axis: "#a8b5c4",
  /** 分隔线：极淡白虚线 */
  splitFaint: "rgba(255, 255, 255, 0.05)",
  /** 折线系列 2：亮紫 */
  defectLine: CYBER.brightPurple,
  pie: {
    安全: CYBER.neonCyan,
    合规: CYBER.neonGreen,
    性能: CYBER.electricBlue,
    功能: CYBER.brightPurple,
  },
};

const pieLegend = computed(() =>
  Object.entries(THEME.pie).map(([name, color]) => ({ name, color })),
);

const chartTab = ref("week");
const lineChartEl = ref(null);
const pieChartEl = ref(null);
const barChartEl = ref(null);

const dashboardData = ref(null);
const statCards = ref([]);
const activities = ref([]);
const streamConnected = ref(false);
const lastUpdatedAt = ref(null);
const lastUpdatedText = computed(() => {
  if (!lastUpdatedAt.value) return "--:--:--";
  return new Date(lastUpdatedAt.value).toLocaleTimeString("zh-CN", { hour12: false });
});

let lineChart = null;
let pieChart = null;
let barChart = null;

function formatDelta(deltaNum) {
  const n = Number(deltaNum || 0);
  return n >= 0 ? `↑ ${n}` : `↓ ${Math.abs(n)}`;
}

function axisLabelStyle() {
  return { color: THEME.axis, fontSize: 11 };
}

function renderLineChart() {
  if (!lineChartEl.value || !dashboardData.value) return;
  const payload = dashboardData.value.lineChart?.[chartTab.value];
  if (!payload) return;

  if (lineChart) lineChart.dispose();
  lineChart = echarts.init(lineChartEl.value);

  lineChart.setOption({
    backgroundColor: "transparent",
    grid: { top: 32, bottom: 28, left: 44, right: 16 },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(15, 23, 42, 0.94)",
      borderColor: "rgba(34, 211, 238, 0.25)",
      textStyle: { color: "#e2e8f0", fontSize: 12 },
    },
    legend: {
      data: ["测试执行数量", "缺陷数量"],
      top: 0,
      right: 0,
      textStyle: { color: THEME.axis, fontSize: 12 },
    },
    xAxis: {
      type: "category",
      data: payload.x || [],
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: axisLabelStyle(),
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: axisLabelStyle(),
      splitLine: {
        lineStyle: {
          color: THEME.splitFaint,
          type: "dashed",
          width: 1,
        },
      },
    },
    series: [
      {
        name: "测试执行数量",
        type: "line",
        smooth: true,
        symbol: "circle",
        symbolSize: 4,
        showSymbol: false,
        data: payload.executed || [],
        lineStyle: {
          color: THEME.electricBlue,
          width: 1.35,
          shadowBlur: 16,
          shadowColor: "rgba(59, 140, 255, 0.55)",
          shadowOffsetY: 0,
        },
        itemStyle: { color: THEME.electricBlue, borderColor: "#0a0e14", borderWidth: 1 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(59, 140, 255, 0.22)" },
            { offset: 0.4, color: "rgba(0, 245, 255, 0.08)" },
            { offset: 1, color: "rgba(10, 14, 20, 0)" },
          ]),
        },
      },
      {
        name: "缺陷数量",
        type: "line",
        smooth: true,
        symbol: "circle",
        symbolSize: 4,
        showSymbol: false,
        data: payload.defects || [],
        lineStyle: {
          color: THEME.brightPurple,
          width: 1.35,
          shadowBlur: 16,
          shadowColor: "rgba(192, 38, 252, 0.5)",
          shadowOffsetY: 0,
        },
        itemStyle: { color: THEME.brightPurple, borderColor: "#0a0e14", borderWidth: 1 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(192, 38, 252, 0.2)" },
            { offset: 0.55, color: "rgba(192, 38, 252, 0.06)" },
            { offset: 1, color: "rgba(10, 14, 20, 0)" },
          ]),
        },
      },
    ],
  });
}

function renderPieChart() {
  if (!pieChartEl.value || !dashboardData.value) return;
  const items = dashboardData.value.pieChart?.items || [];
  if (pieChart) pieChart.dispose();
  pieChart = echarts.init(pieChartEl.value);

  pieChart.setOption({
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      formatter: "{b}: {d}%",
      backgroundColor: "rgba(15, 23, 42, 0.94)",
      borderColor: "rgba(34, 211, 238, 0.25)",
      textStyle: { color: "#e2e8f0" },
    },
    series: [
      {
        type: "pie",
        radius: ["52%", "78%"],
        center: ["50%", "50%"],
        label: { show: false },
        emphasis: {
          scale: true,
          scaleSize: 4,
          itemStyle: {
            shadowBlur: 20,
            shadowColor: "rgba(34, 211, 238, 0.35)",
          },
        },
        data: items.map((it) => {
          const c = THEME.pie[it.name] || THEME.neonCyan;
          return {
            value: it.value,
            name: it.name,
            itemStyle: {
              color: c,
              shadowBlur: 14,
              shadowColor: "rgba(0, 245, 255, 0.25)",
            },
          };
        }),
      },
    ],
  });
}

function renderBarChart() {
  if (!barChartEl.value || !dashboardData.value) return;
  const payload = dashboardData.value.barChart || { x: [], values: [] };
  if (barChart) barChart.dispose();
  barChart = echarts.init(barChartEl.value);

  barChart.setOption({
    backgroundColor: "transparent",
    grid: { top: 12, bottom: 28, left: 44, right: 16 },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(15, 23, 42, 0.94)",
      borderColor: "rgba(34, 211, 238, 0.25)",
      textStyle: { color: "#e2e8f0" },
    },
    xAxis: {
      type: "category",
      data: payload.x || [],
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: axisLabelStyle(),
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: axisLabelStyle(),
      splitLine: {
        lineStyle: {
          color: THEME.splitFaint,
          type: "dashed",
          width: 1,
        },
      },
    },
    series: [
      {
        type: "bar",
        data: payload.values || [],
        barMaxWidth: 26,
        itemStyle: {
          borderRadius: [6, 6, 2, 2],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: THEME.neonCyan },
            { offset: 0.45, color: THEME.electricBlue },
            { offset: 1, color: THEME.brightPurple },
          ]),
          shadowBlur: 14,
          shadowColor: "rgba(0, 245, 255, 0.35)",
          shadowOffsetY: 2,
        },
      },
    ],
  });
}

function resizeCharts() {
  lineChart?.resize();
  pieChart?.resize();
  barChart?.resize();
}

async function loadDashboardData(showError = false) {
  try {
    const res = await getDashboardSummaryApi();
    dashboardData.value = res?.data || res;

    const sc = dashboardData.value?.statCards || {};
    statCards.value = [
      {
        key: "totalCases",
        valueDisplay: sc.totalCases?.value ?? 0,
        label: sc.totalCases?.label ?? "测试用例总数",
        deltaNum: sc.totalCases?.delta ?? 0,
        deltaText: formatDelta(sc.totalCases?.delta ?? 0),
        barBg: "rgba(8, 12, 22, 0.78)",
        barColor: "linear-gradient(90deg, #00d8ff, #22d3ee, #38bdf8)",
        barWidth: sc.totalCases?.barWidth ?? "70%",
      },
      {
        key: "todayExecuted",
        valueDisplay: sc.todayExecuted?.value ?? 0,
        label: sc.todayExecuted?.label ?? "今日执行用例",
        deltaNum: sc.todayExecuted?.delta ?? 0,
        deltaText: formatDelta(sc.todayExecuted?.delta ?? 0),
        barBg: "rgba(8, 12, 22, 0.78)",
        barColor: "linear-gradient(90deg, #5eead4, #00d8ff, #06b6d4)",
        barWidth: sc.todayExecuted?.barWidth ?? "55%",
      },
      {
        key: "unresolvedDefects",
        valueDisplay: sc.unresolvedDefects?.value ?? 0,
        label: sc.unresolvedDefects?.label ?? "未解决缺陷",
        deltaNum: sc.unresolvedDefects?.delta ?? 0,
        deltaText: formatDelta(sc.unresolvedDefects?.delta ?? 0),
        barBg: "rgba(8, 12, 22, 0.78)",
        barColor: "linear-gradient(90deg, #fde047, #fb923c, #f97316)",
        barWidth: sc.unresolvedDefects?.barWidth ?? "30%",
      },
      {
        key: "passRate",
        valueDisplay: sc.passRate?.value ?? "0%",
        label: sc.passRate?.label ?? "用例通过率",
        deltaNum: sc.passRate?.delta ?? 0,
        deltaText: formatDelta(sc.passRate?.delta ?? 0),
        barBg: "rgba(8, 12, 22, 0.78)",
        barColor: "linear-gradient(90deg, #4ade80, #34d399, #10b981)",
        barWidth: sc.passRate?.barWidth ?? "0%",
      },
    ];

    activities.value = dashboardData.value?.activities || [];
    lastUpdatedAt.value = Date.now();
    await nextTick();
    renderLineChart();
    renderPieChart();
    renderBarChart();
  } catch (err) {
    if (showError) ElMessage.error("获取首页统计数据失败");
    console.error(err);
  }
}

useRealtimePolling(() => loadDashboardData(false), {
  intervalMs: 5000,
  runOnMount: true,
  refreshEvents: ["app:current-project-changed", "app:current-environment-changed"],
  shouldSkip: () => streamConnected.value,
});

useSseRefreshTrigger(() => loadDashboardData(false), {
  buildUrl: () => getDashboardStreamUrl(),
  reconnectMs: 3000,
  refreshEvents: ["app:current-project-changed", "app:current-environment-changed"],
  onConnectionChange: (connected) => {
    streamConnected.value = connected;
  },
});

onMounted(() => {
  window.addEventListener("resize", resizeCharts);
});

watch(chartTab, async () => {
  await nextTick();
  renderLineChart();
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", resizeCharts);
  if (lineChart) lineChart.dispose();
  if (pieChart) pieChart.dispose();
  if (barChart) barChart.dispose();
});
</script>

<style scoped lang="scss">
/* Dark Tech-Noir 玻璃：半透明深 slate + 霓虹描边 */
.glass-panel {
  background: rgba(15, 23, 42, 0.55);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border: 1px solid rgba(34, 211, 238, 0.14);
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.35),
    0 0 0 1px rgba(0, 0, 0, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  border-radius: 14px;
  transition:
    transform 0.3s ease,
    box-shadow 0.3s ease,
    border-color 0.3s ease;
}

.glass-panel--interactive:hover {
  transform: translateY(-3px);
  box-shadow:
    0 12px 40px rgba(0, 0, 0, 0.4),
    0 0 32px rgba(34, 211, 238, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
  border-color: rgba(34, 211, 238, 0.35);
}

.glass-panel--chart:hover {
  transform: translateY(-2px);
  box-shadow:
    0 10px 36px rgba(0, 0, 0, 0.38),
    0 0 28px rgba(56, 189, 248, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  border-color: rgba(56, 189, 248, 0.22);
}

.dashboard {
  position: relative;
  box-sizing: border-box;
}

.dashboard--cyber {
  color: #e2e8f0;
}

.dashboard__mesh {
  position: absolute;
  inset: 0;
  opacity: 0.12;
  background-image:
    linear-gradient(rgba(34, 211, 238, 0.2) 1px, transparent 1px),
    linear-gradient(90deg, rgba(34, 211, 238, 0.2) 1px, transparent 1px);
  background-size: 28px 28px;
  z-index: 0;
}

.dashboard__scan {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background: linear-gradient(
    transparent 0%,
    rgba(34, 211, 238, 0.03) 48%,
    rgba(34, 211, 238, 0.06) 50%,
    rgba(34, 211, 238, 0.03) 52%,
    transparent 100%
  );
  background-size: 100% 220%;
  animation: dashboard-scan 8s linear infinite;
  opacity: 0.5;
}

@keyframes dashboard-scan {
  0% {
    background-position: 0 -100%;
  }
  100% {
    background-position: 0 100%;
  }
}

.stat-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

@media (max-width: 1200px) {
  .stat-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 560px) {
  .stat-cards {
    grid-template-columns: 1fr;
  }
}

.stat-card {
  padding: 22px 20px;
}

/* 主指标：DIN / 等宽数字 + 主色青霓虹光晕 */
.tech-metric {
  font-family:
    "Bahnschrift",
    "DIN Alternate",
    "DIN Condensed",
    "Roboto Mono",
    ui-monospace,
    "SF Mono",
    "Cascadia Code",
    Menlo,
    Monaco,
    Consolas,
    monospace;
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1;
  font-size: 32px;
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: 0.04em;
  background: linear-gradient(105deg, #a5f3fc 0%, #00d8ff 28%, #22d3ee 55%, #38bdf8 85%, #818cf8 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
  filter:
    drop-shadow(0 0 1px rgba(0, 216, 255, 0.9))
    drop-shadow(0 0 10px rgba(0, 216, 255, 0.45))
    drop-shadow(0 0 22px rgba(34, 211, 238, 0.28))
    drop-shadow(0 0 36px rgba(0, 216, 255, 0.12));
}

.stat-card__label {
  font-size: 13px;
  color: #94a3b8;
  margin-top: 8px;
  font-weight: 500;
}

.stat-card__sub {
  font-size: 12px;
  color: #64748b;
  margin-top: 6px;
}

.stat-card__delta--up {
  color: #4ade80;
  font-weight: 600;
}

.stat-card__delta--down {
  color: #f87171;
  font-weight: 600;
}

.stat-card__bar-rail {
  margin-top: 14px;
}

/* 轨道：深色半透明 + 内凹；填充仍由 card.barBg / card.barColor 绑定 */
.stat-card__bar {
  height: 7px;
  border-radius: 999px;
  overflow: hidden;
  border: 1px solid rgba(0, 216, 255, 0.18);
  box-shadow:
    inset 0 1px 4px rgba(0, 0, 0, 0.55),
    inset 0 0 0 1px rgba(0, 0, 0, 0.25);
}

.stat-card__bar-fill {
  height: 100%;
  min-width: 0;
  border-radius: 999px;
  transition: width 0.55s ease;
  box-shadow:
    0 0 10px rgba(0, 216, 255, 0.5),
    0 0 18px rgba(34, 211, 238, 0.25),
    inset 0 1px 0 rgba(255, 255, 255, 0.25);
}

.dashboard-middle,
.dashboard-bottom {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.chart-card {
  padding: 18px 18px 16px;
}

.chart-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  flex-wrap: wrap;
  gap: 8px;
}

.chart-card__title {
  font-size: 15px;
  font-weight: 700;
  color: #f1f5f9;
  letter-spacing: 0.02em;
}

.chart-card__sub-title {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 500;
}

.chart-tabs {
  display: flex;
  gap: 6px;
}

.chart-tab {
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 8px;
  cursor: pointer;
  color: #94a3b8;
  border: 1px solid rgba(51, 65, 85, 0.9);
  background: rgba(15, 23, 42, 0.5);
  transition: all 0.25s ease;
}

.chart-tab:hover {
  border-color: rgba(34, 211, 238, 0.35);
  color: #67e8f9;
  box-shadow: 0 0 16px rgba(34, 211, 238, 0.1);
}

.chart-tab--active {
  color: #e0f2fe;
  border-color: rgba(34, 211, 238, 0.45);
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.15), rgba(37, 99, 235, 0.12));
  box-shadow: 0 0 20px rgba(34, 211, 238, 0.15);
  font-weight: 600;
}

.chart-box {
  height: 220px;
}

.chart-box--bar {
  height: 188px;
}

.pie-legend {
  display: flex;
  justify-content: center;
  gap: 14px 18px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.pie-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #cbd5e1;
  font-weight: 500;
}

.pie-legend-item i {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
  box-shadow: 0 0 0 2px rgba(15, 23, 42, 0.9), 0 0 8px rgba(34, 211, 238, 0.2);
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  max-height: 248px;
  padding-right: 4px;
}

.chart-card__meta {
  font-size: 11px;
  color: #64748b;
}

.activity-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(30, 41, 59, 0.45);
  border: 1px solid rgba(51, 65, 85, 0.8);
  transition: background 0.25s ease, box-shadow 0.25s ease;
}

.activity-empty {
  font-size: 12px;
  color: #64748b;
  padding: 10px;
  border-radius: 10px;
  border: 1px dashed rgba(100, 116, 139, 0.5);
  background: rgba(30, 41, 59, 0.25);
}

.activity-item:hover {
  background: rgba(34, 211, 238, 0.06);
  box-shadow: 0 0 0 1px rgba(34, 211, 238, 0.2);
}

.activity-tag {
  flex-shrink: 0;
}

.activity-text {
  flex: 1;
  color: #cbd5e1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-time {
  flex-shrink: 0;
  color: #64748b;
  font-size: 11px;
}
</style>
