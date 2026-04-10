<template>
  <div class="cyber-page quality-page">
    <el-card class="admin-list-card" shadow="never">
      <div class="admin-toolbar-row">
        <div class="admin-toolbar-row__left">
          <span class="quality-title">测试质量分析（近30天）</span>
        </div>
        <div class="admin-toolbar-row__right">
          <el-button :loading="loading" @click="loadData">刷新</el-button>
        </div>
      </div>

      <el-row :gutter="12" class="metric-cards">
        <el-col :xs="24" :sm="8">
          <el-card shadow="never" class="metric-card">
            <div class="metric-card__label">最新通过率</div>
            <div class="metric-card__value">{{ latest.pass_rate }}%</div>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="8">
          <el-card shadow="never" class="metric-card">
            <div class="metric-card__label">最新缺陷密度</div>
            <div class="metric-card__value">{{ latest.defect_density }}</div>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="8">
          <el-card shadow="never" class="metric-card">
            <div class="metric-card__label">最新需求覆盖率</div>
            <div class="metric-card__value">{{ latest.requirement_coverage }}%</div>
          </el-card>
        </el-col>
      </el-row>

      <div ref="chartEl" class="quality-chart" v-loading="loading" />
    </el-card>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import * as echarts from "echarts";
import { ElMessage } from "element-plus";
import { getDashboardStreamUrl, getQualityDashboardApi } from "@/api/dashboard";
import { useRealtimePolling } from "@/composables/useRealtimePolling";
import { useSseRefreshTrigger } from "@/composables/useSseRefreshTrigger";

const loading = ref(false);
const payload = ref(null);
const chartEl = ref(null);
const streamConnected = ref(false);
let chart = null;

const latest = computed(() => payload.value?.latestMetrics || {
  pass_rate: 0,
  defect_density: 0,
  requirement_coverage: 0,
});

function renderChart() {
  if (!chartEl.value || !payload.value?.trendChart) return;
  const trend = payload.value.trendChart;
  if (chart) chart.dispose();
  chart = echarts.init(chartEl.value);
  chart.setOption({
    tooltip: { trigger: "axis" },
    legend: { top: 8 },
    grid: { top: 44, left: 42, right: 18, bottom: 26 },
    xAxis: { type: "category", data: trend.xAxis || [] },
    yAxis: { type: "value" },
    series: Array.isArray(trend.series) ? trend.series : [],
  });
}

function resizeChart() {
  chart?.resize();
}

async function loadData(showLoading = true) {
  if (showLoading) loading.value = true;
  try {
    const currentProject = localStorage.getItem("current_project_id");
    const params = {};
    if (currentProject) params.project_id = Number(currentProject);
    const { data } = await getQualityDashboardApi(params);
    payload.value = data || {};
    await nextTick();
    renderChart();
  } catch (error) {
    ElMessage.error(error?.response?.data?.msg || "加载质量分析失败");
  } finally {
    if (showLoading) loading.value = false;
  }
}

useRealtimePolling(() => loadData(false), {
  intervalMs: 5000,
  runOnMount: true,
  refreshEvents: ["app:current-project-changed", "app:current-environment-changed"],
  shouldSkip: () => streamConnected.value,
});

useSseRefreshTrigger(() => loadData(false), {
  buildUrl: () => {
    const projectId = localStorage.getItem("current_project_id");
    return getDashboardStreamUrl({ project_id: projectId || undefined });
  },
  reconnectMs: 3000,
  refreshEvents: ["app:current-project-changed", "app:current-environment-changed"],
  onConnectionChange: (connected) => {
    streamConnected.value = connected;
  },
});

onMounted(() => {
  window.addEventListener("resize", resizeChart);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", resizeChart);
  if (chart) chart.dispose();
});
</script>

<style scoped>
.quality-title {
  font-size: 16px;
  font-weight: 600;
}
.metric-cards {
  margin-bottom: 12px;
}
.metric-card {
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.metric-card__label {
  font-size: 12px;
  color: #94a3b8;
}
.metric-card__value {
  margin-top: 8px;
  font-size: 26px;
  font-weight: 700;
  color: #e2e8f0;
}
.quality-chart {
  width: 100%;
  height: 420px;
}
</style>
