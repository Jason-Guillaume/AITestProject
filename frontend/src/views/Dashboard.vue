<template>
  <div class="dashboard cyber-page">
    <div class="dashboard__header">
      <div class="dashboard__header-left">
        <h1 class="dashboard__title">
          工作台
        </h1>
        <span class="dashboard__subtitle">项目数据概览与快捷操作</span>
      </div>
      <div class="dashboard__header-right">
        <button
          type="button"
          class="btn-cyber-primary"
          @click="handleNewTest"
        >
          <svg
            viewBox="0 0 24 24"
            width="16"
            height="16"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
          >
            <line
              x1="12"
              y1="5"
              x2="12"
              y2="19"
            /><line
              x1="5"
              y1="12"
              x2="19"
              y2="12"
            />
          </svg>
          新建测试
        </button>
        <button
          type="button"
          class="btn-cyber-ghost"
          @click="loadDashboardData(false)"
        >
          <svg
            viewBox="0 0 24 24"
            width="14"
            height="14"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
          >
            <polyline points="23 4 23 10 17 10" /><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
          </svg>
          刷新
        </button>
      </div>
    </div>

    <div class="bento">
      <div
        v-for="card in statCards"
        :key="card.key"
        class="bento__cell bento__cell--stat cyber-glass cyber-glass--interactive"
      >
        <div class="stat-value">
          {{ card.valueDisplay }}
        </div>
        <div class="stat-label">
          {{ card.label }}
        </div>
        <div class="stat-delta">
          较昨日
          <span :class="card.deltaNum >= 0 ? 'stat-delta--up' : 'stat-delta--down'">
            {{ card.deltaText }}
          </span>
        </div>
        <div class="stat-bar">
          <div
            class="stat-bar__fill"
            :style="{ width: card.barWidth }"
          />
        </div>
      </div>

      <div class="bento__cell bento__cell--line-chart cyber-glass cyber-glass--interactive">
        <div class="cell-header">
          <span class="cell-title">测试执行情况</span>
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
        <div
          ref="lineChartEl"
          class="chart-box"
        />
      </div>

      <div class="bento__cell bento__cell--pie-chart cyber-glass cyber-glass--interactive">
        <div class="cell-header">
          <span class="cell-title">AI 测试分析</span>
          <span class="cell-subtitle">质量风险分析</span>
        </div>
        <div
          ref="pieChartEl"
          class="chart-box chart-box--pie"
        />
        <div class="pie-legend">
          <span
            v-for="leg in pieLegend"
            :key="leg.name"
            class="pie-legend-item"
          >
            <i :style="{ background: leg.color }" />
            {{ leg.name }}
          </span>
        </div>
      </div>

      <div class="bento__cell bento__cell--activity cyber-glass cyber-glass--interactive">
        <div class="cell-header">
          <span class="cell-title">最近测试任务</span>
          <span class="cell-meta">
            {{ streamConnected ? "实时已连接" : "重连中" }} · {{ lastUpdatedText }}
          </span>
        </div>
        <div class="activity-list">
          <div
            v-for="item in activities"
            :key="item.id"
            class="activity-item"
          >
            <el-tag
              :type="item.tagType"
              size="small"
              class="activity-tag"
            >
              {{ item.tag }}
            </el-tag>
            <span class="activity-text">{{ item.text }}</span>
            <span class="activity-time">{{ item.time }}</span>
          </div>
          <div
            v-if="!activities.length"
            class="activity-empty"
          >
            暂无最近任务数据
          </div>
        </div>
      </div>

      <div class="bento__cell bento__cell--bar-chart cyber-glass cyber-glass--interactive">
        <div class="cell-header">
          <span class="cell-title">缺陷统计分析</span>
        </div>
        <div
          ref="barChartEl"
          class="chart-box"
        />
      </div>

      <div class="bento__cell bento__cell--quick-actions cyber-glass cyber-glass--interactive">
        <div class="cell-header">
          <span class="cell-title">快捷操作</span>
        </div>
        <div class="quick-actions">
          <button
            type="button"
            class="quick-action-btn"
            @click="$router.push('/test-case/functional')"
          >
            <svg
              viewBox="0 0 24 24"
              width="18"
              height="18"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line
                x1="16"
                y1="13"
                x2="8"
                y2="13"
              /><line
                x1="16"
                y1="17"
                x2="8"
                y2="17"
              />
            </svg>
            功能用例
          </button>
          <button
            type="button"
            class="quick-action-btn"
            @click="$router.push('/test-case/api')"
          >
            <svg
              viewBox="0 0 24 24"
              width="18"
              height="18"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
            </svg>
            接口用例
          </button>
          <button
            type="button"
            class="quick-action-btn"
            @click="$router.push('/test-plan')"
          >
            <svg
              viewBox="0 0 24 24"
              width="18"
              height="18"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <rect
                x="3"
                y="4"
                width="18"
                height="18"
                rx="2"
                ry="2"
              /><line
                x1="16"
                y1="2"
                x2="16"
                y2="6"
              /><line
                x1="8"
                y1="2"
                x2="8"
                y2="6"
              /><line
                x1="3"
                y1="10"
                x2="21"
                y2="10"
              />
            </svg>
            测试计划
          </button>
          <button
            type="button"
            class="quick-action-btn"
            @click="$router.push('/agent-hub')"
          >
            <svg
              viewBox="0 0 24 24"
              width="18"
              height="18"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M12 2a3 3 0 0 0-3 3v1a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" /><path d="M19 10H5a2 2 0 0 0-2 2v1a7 7 0 0 0 14 0v-1a2 2 0 0 0-2-2z" /><circle
                cx="12"
                cy="5"
                r="3"
              />
            </svg>
            AI 智能体
          </button>
          <button
            type="button"
            class="quick-action-btn"
            @click="$router.push('/defect/list')"
          >
            <svg
              viewBox="0 0 24 24"
              width="18"
              height="18"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line
                x1="12"
                y1="9"
                x2="12"
                y2="13"
              /><line
                x1="12"
                y1="17"
                x2="12.01"
                y2="17"
              />
            </svg>
            缺陷管理
          </button>
          <button
            type="button"
            class="quick-action-btn"
            @click="$router.push('/test-report')"
          >
            <svg
              viewBox="0 0 24 24"
              width="18"
              height="18"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <line
                x1="18"
                y1="20"
                x2="18"
                y2="10"
              /><line
                x1="12"
                y1="20"
                x2="12"
                y2="4"
              /><line
                x1="6"
                y1="20"
                x2="6"
                y2="14"
              />
            </svg>
            测试报告
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch, onBeforeUnmount, computed } from "vue";
import { useRouter } from "vue-router";
import * as echarts from "echarts";
import { ElMessage } from "element-plus";
import { getDashboardSummaryApi, getDashboardStreamUrl } from "@/api/dashboard";
import { useRealtimePolling } from "@/composables/useRealtimePolling";
import { useSseRefreshTrigger } from "@/composables/useSseRefreshTrigger";

const router = useRouter();

const BRAND = {
  primary: "#00d8ff",
  primarySoft: "#22d3ee",
  primaryDim: "rgba(0, 216, 255, 0.45)",
  glow: "rgba(0, 216, 255, 0.22)",
  violet: "#a78bfa",
  violetSoft: "#c084fc",
  green: "#34d399",
  amber: "#fbbf24",
  rose: "#fb7185",
  text: "#e2e8f0",
  textSecondary: "#94a3b8",
  textMuted: "#64748b",
  splitLine: "rgba(0, 216, 255, 0.08)",
  pie: {
    安全: "#a78bfa",
    合规: "#34d399",
    性能: "#22d3ee",
    功能: "#fb7185",
  },
};

const pieLegend = computed(() =>
  Object.entries(BRAND.pie).map(([name, color]) => ({ name, color })),
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
  return { color: BRAND.textMuted, fontSize: 11 };
}

function renderLineChart() {
  if (!lineChartEl.value || !dashboardData.value) return;
  const payload = dashboardData.value.lineChart?.[chartTab.value];
  if (!payload) return;

  if (lineChart) lineChart.dispose();
  lineChart = echarts.init(lineChartEl.value);

  lineChart.setOption({
    backgroundColor: "transparent",
    grid: { top: 36, bottom: 28, left: 44, right: 16 },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(10, 14, 22, 0.94)",
      borderColor: "rgba(0, 216, 255, 0.18)",
      borderWidth: 1,
      textStyle: { color: BRAND.text, fontSize: 12 },
    },
    legend: {
      data: ["测试执行数量", "缺陷数量"],
      top: 0,
      right: 0,
      textStyle: { color: BRAND.textSecondary, fontSize: 12 },
      itemWidth: 12,
      itemHeight: 2,
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
        lineStyle: { color: BRAND.splitLine, type: "dashed", width: 1 },
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
        lineStyle: { color: BRAND.primary, width: 2 },
        itemStyle: { color: BRAND.primary },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(0, 216, 255, 0.18)" },
            { offset: 1, color: "rgba(0, 216, 255, 0)" },
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
        lineStyle: { color: BRAND.violet, width: 2 },
        itemStyle: { color: BRAND.violet },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(167, 139, 250, 0.14)" },
            { offset: 1, color: "rgba(167, 139, 250, 0)" },
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
      backgroundColor: "rgba(10, 14, 22, 0.94)",
      borderColor: "rgba(0, 216, 255, 0.18)",
      borderWidth: 1,
      textStyle: { color: BRAND.text },
    },
    series: [
      {
        type: "pie",
        radius: ["52%", "78%"],
        center: ["50%", "50%"],
        label: { show: false },
        emphasis: { scale: true, scaleSize: 4 },
        data: items.map((it) => ({
          value: it.value,
          name: it.name,
          itemStyle: { color: BRAND.pie[it.name] || BRAND.primary },
        })),
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
      backgroundColor: "rgba(10, 14, 22, 0.94)",
      borderColor: "rgba(0, 216, 255, 0.18)",
      borderWidth: 1,
      textStyle: { color: BRAND.text },
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
        lineStyle: { color: BRAND.splitLine, type: "dashed", width: 1 },
      },
    },
    series: [
      {
        type: "bar",
        data: payload.values || [],
        barMaxWidth: 24,
        itemStyle: {
          borderRadius: [4, 4, 2, 2],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: BRAND.primarySoft },
            { offset: 1, color: BRAND.primary },
          ]),
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

function handleNewTest() {
  router.push("/test-case/functional");
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
        barWidth: sc.totalCases?.barWidth ?? "70%",
      },
      {
        key: "todayExecuted",
        valueDisplay: sc.todayExecuted?.value ?? 0,
        label: sc.todayExecuted?.label ?? "今日执行用例",
        deltaNum: sc.todayExecuted?.delta ?? 0,
        deltaText: formatDelta(sc.todayExecuted?.delta ?? 0),
        barWidth: sc.todayExecuted?.barWidth ?? "55%",
      },
      {
        key: "unresolvedDefects",
        valueDisplay: sc.unresolvedDefects?.value ?? 0,
        label: sc.unresolvedDefects?.label ?? "未解决缺陷",
        deltaNum: sc.unresolvedDefects?.delta ?? 0,
        deltaText: formatDelta(sc.unresolvedDefects?.delta ?? 0),
        barWidth: sc.unresolvedDefects?.barWidth ?? "30%",
      },
      {
        key: "passRate",
        valueDisplay: sc.passRate?.value ?? "0%",
        label: sc.passRate?.label ?? "用例通过率",
        deltaNum: sc.passRate?.delta ?? 0,
        deltaText: formatDelta(sc.passRate?.delta ?? 0),
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
  deferredInitialRunMs: 500,
  refreshEvents: ["app:current-project-changed", "app:current-environment-changed"],
  shouldSkip: () => streamConnected.value,
});

useSseRefreshTrigger(() => loadDashboardData(false), {
  buildUrl: () => getDashboardStreamUrl(),
  reconnectMs: 3000,
  connectDelayMs: 900,
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
.dashboard {
  position: relative;
  width: 100%;
  min-height: 100%;
  color: #e2e8f0;
  padding-bottom: 8px;
}

.dashboard__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.dashboard__header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.dashboard__title {
  font-size: 22px;
  font-weight: 700;
  color: #f8fafc;
  letter-spacing: -0.02em;
  margin: 0;
  line-height: 1.2;
  background: linear-gradient(105deg, #00d8ff 0%, #22d3ee 45%, #7dd3fc 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 0 10px rgba(0, 216, 255, 0.25));
}

.dashboard__subtitle {
  font-size: 13px;
  color: #64748b;
  font-weight: 400;
}

.dashboard__header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.btn-cyber-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  border: 1px solid rgba(0, 216, 255, 0.35);
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(0, 216, 255, 0.12), rgba(0, 216, 255, 0.04));
  color: #00d8ff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  letter-spacing: 0.02em;
  box-shadow:
    0 0 14px rgba(0, 216, 255, 0.15),
    inset 0 0 10px rgba(0, 216, 255, 0.05);
  transition: all 0.25s ease;

  &:hover {
    background: linear-gradient(135deg, rgba(0, 216, 255, 0.2), rgba(0, 216, 255, 0.08));
    border-color: rgba(0, 216, 255, 0.55);
    box-shadow:
      0 0 22px rgba(0, 216, 255, 0.28),
      inset 0 0 14px rgba(0, 216, 255, 0.08);
    color: #22d3ee;
  }

  &:active {
    transform: scale(0.97);
  }

  svg {
    flex-shrink: 0;
  }
}

.btn-cyber-ghost {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 7px 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  background: transparent;
  color: #94a3b8;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;

  &:hover {
    color: #00d8ff;
    border-color: rgba(0, 216, 255, 0.25);
    background: rgba(0, 216, 255, 0.04);
    box-shadow: 0 0 12px rgba(0, 216, 255, 0.1);
  }

  svg {
    flex-shrink: 0;
  }
}

.bento {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.bento__cell {
  border-radius: 12px;
  padding: 20px;
  transition: border-color 0.25s ease, box-shadow 0.25s ease, background 0.25s ease;
}

.bento__cell--stat {
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    border-radius: 12px 12px 0 0;
    opacity: 0.7;
  }

  &:nth-child(1)::before {
    background: linear-gradient(90deg, #00d8ff, #22d3ee);
    box-shadow: 0 0 12px rgba(0, 216, 255, 0.5);
  }
  &:nth-child(2)::before {
    background: linear-gradient(90deg, #06b6d4, #22d3ee);
    box-shadow: 0 0 12px rgba(34, 211, 238, 0.5);
  }
  &:nth-child(3)::before {
    background: linear-gradient(90deg, #d97706, #fbbf24);
    box-shadow: 0 0 12px rgba(251, 191, 36, 0.5);
  }
  &:nth-child(4)::before {
    background: linear-gradient(90deg, #059669, #34d399);
    box-shadow: 0 0 12px rgba(52, 211, 153, 0.5);
  }

  &:nth-child(1) .stat-value { color: #00d8ff; text-shadow: 0 0 16px rgba(0, 216, 255, 0.4); }
  &:nth-child(2) .stat-value { color: #22d3ee; text-shadow: 0 0 16px rgba(34, 211, 238, 0.4); }
  &:nth-child(3) .stat-value { color: #fbbf24; text-shadow: 0 0 16px rgba(251, 191, 36, 0.35); }
  &:nth-child(4) .stat-value { color: #34d399; text-shadow: 0 0 16px rgba(52, 211, 153, 0.35); }

  &:nth-child(1) .stat-bar__fill { background: linear-gradient(90deg, #00d8ff, #22d3ee); box-shadow: 0 0 8px rgba(0, 216, 255, 0.45); }
  &:nth-child(2) .stat-bar__fill { background: linear-gradient(90deg, #06b6d4, #22d3ee); box-shadow: 0 0 8px rgba(34, 211, 238, 0.45); }
  &:nth-child(3) .stat-bar__fill { background: linear-gradient(90deg, #d97706, #fbbf24); box-shadow: 0 0 8px rgba(251, 191, 36, 0.4); }
  &:nth-child(4) .stat-bar__fill { background: linear-gradient(90deg, #059669, #34d399); box-shadow: 0 0 8px rgba(52, 211, 153, 0.4); }
}

.bento__cell--line-chart {
  grid-column: span 2;
}

.bento__cell--pie-chart {
  grid-column: span 1;
}

.bento__cell--activity {
  grid-column: span 1;
}

.bento__cell--bar-chart {
  grid-column: span 3;
}

.bento__cell--quick-actions {
  grid-column: span 1;
}

.stat-value {
  font-family: "Bahnschrift", "DIN Alternate", "Roboto Mono", ui-monospace, "SF Mono", "Cascadia Code", monospace;
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1;
  font-size: 28px;
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.02em;
}

.stat-label {
  font-size: 13px;
  color: #94a3b8;
  margin-top: 6px;
  font-weight: 500;
}

.stat-delta {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
}

.stat-delta--up {
  color: #34d399;
  font-weight: 600;
}

.stat-delta--down {
  color: #fb7185;
  font-weight: 600;
}

.stat-bar {
  margin-top: 12px;
  height: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  overflow: hidden;
}

.stat-bar__fill {
  height: 100%;
  min-width: 0;
  border-radius: 999px;
  transition: width 0.55s ease;
}

.cell-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.cell-title {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
  letter-spacing: -0.01em;
}

.cell-subtitle {
  font-size: 12px;
  color: #64748b;
  font-weight: 400;
}

.cell-meta {
  font-size: 11px;
  color: #475569;
}

.chart-tabs {
  display: flex;
  gap: 4px;
}

.chart-tab {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 6px;
  cursor: pointer;
  color: #64748b;
  border: 1px solid transparent;
  background: transparent;
  transition: all 0.2s ease;

  &:hover {
    color: #94a3b8;
    background: rgba(0, 216, 255, 0.04);
  }
}

.chart-tab--active {
  color: #00d8ff;
  background: rgba(0, 216, 255, 0.1);
  border-color: rgba(0, 216, 255, 0.25);
  font-weight: 500;
  box-shadow: 0 0 10px rgba(0, 216, 255, 0.12);
}

.chart-box {
  height: 220px;
}

.chart-box--pie {
  height: 180px;
}

.pie-legend {
  display: flex;
  justify-content: center;
  gap: 14px 18px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.pie-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #94a3b8;
  font-weight: 400;
}

.pie-legend-item i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  box-shadow: 0 0 6px currentColor;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  max-height: 260px;
  padding-right: 2px;
}

.activity-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(0, 216, 255, 0.02);
  border: 1px solid rgba(0, 216, 255, 0.06);
  transition: background 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;

  &:hover {
    background: rgba(0, 216, 255, 0.06);
    border-color: rgba(0, 216, 255, 0.15);
    box-shadow: 0 0 8px rgba(0, 216, 255, 0.08);
  }
}

.activity-empty {
  font-size: 12px;
  color: #475569;
  padding: 12px;
  border-radius: 8px;
  border: 1px dashed rgba(0, 216, 255, 0.12);
  text-align: center;
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
  color: #475569;
  font-size: 11px;
}

.quick-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.quick-action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 14px 8px;
  border: 1px solid rgba(0, 216, 255, 0.1);
  border-radius: 10px;
  background: rgba(0, 216, 255, 0.02);
  color: #94a3b8;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;

  &:hover {
    color: #00d8ff;
    background: rgba(0, 216, 255, 0.08);
    border-color: rgba(0, 216, 255, 0.3);
    box-shadow:
      0 0 14px rgba(0, 216, 255, 0.15),
      inset 0 0 8px rgba(0, 216, 255, 0.04);
  }

  &:active {
    transform: scale(0.96);
  }

  svg {
    flex-shrink: 0;
  }
}

@media (max-width: 1200px) {
  .bento {
    grid-template-columns: repeat(2, 1fr);
  }

  .bento__cell--line-chart,
  .bento__cell--bar-chart {
    grid-column: span 2;
  }

  .bento__cell--pie-chart,
  .bento__cell--activity,
  .bento__cell--quick-actions {
    grid-column: span 1;
  }
}

@media (max-width: 768px) {
  .bento {
    grid-template-columns: 1fr;
  }

  .bento__cell--line-chart,
  .bento__cell--bar-chart,
  .bento__cell--pie-chart,
  .bento__cell--activity,
  .bento__cell--quick-actions {
    grid-column: span 1;
  }

  .quick-actions {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 560px) {
  .quick-actions {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
