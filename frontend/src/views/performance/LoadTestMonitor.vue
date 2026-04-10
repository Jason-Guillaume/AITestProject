<template>
  <div class="cyber-page admin-list-page load-monitor-page">
    <el-card class="admin-list-card" shadow="never">
      <template #header>
        <span class="card-title">业务链路 k6 压测与实时监控</span>
        <span class="card-sub muted">WebSocket 推送 QPS / P95 / 错误率，ECharts 动态折线</span>
      </template>

      <el-form :model="form" label-width="120px" class="start-form">
        <el-form-item label="API 用例 ID" required>
          <el-input
            v-model="form.caseIdsText"
            type="textarea"
            :rows="2"
            placeholder="逗号或换行分隔，按顺序组成业务链路，例如：101,102,103"
          />
        </el-form-item>
        <el-form-item label="目标 Base URL">
          <el-input v-model="form.target_base_url" clearable placeholder="相对路径用例必填，如 https://api.example.com" />
        </el-form-item>
        <el-form-item label="vus">
          <el-input-number v-model="form.vus" :min="1" :max="500" />
        </el-form-item>
        <el-form-item label="持续时间">
          <el-input v-model="form.duration" placeholder="30s / 5m / 1h" style="width: 160px" />
        </el-form-item>
        <el-form-item label="AI 生成脚本">
          <el-switch v-model="form.use_ai" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="starting" @click="onStart">启动压测</el-button>
          <el-button :disabled="!wsConnected" @click="disconnectWs">断开实时通道</el-button>
        </el-form-item>
      </el-form>

      <el-alert v-if="runId" type="info" show-icon :closable="false" class="mb-3">
        run_id：<code>{{ runId }}</code>；状态：<strong>{{ sessionStatus }}</strong>
        <span v-if="wsConnected" class="ws-ok"> · WebSocket 已连接</span>
      </el-alert>

      <div class="charts-row">
        <div ref="chartQpsRef" class="chart-box" />
        <div ref="chartP95Ref" class="chart-box" />
      </div>

      <el-collapse v-if="lastFinal">
        <el-collapse-item title="最终 summary（k6 --summary-export）" name="1">
          <pre class="json-pre">{{ JSON.stringify(lastFinal, null, 2) }}</pre>
        </el-collapse-item>
      </el-collapse>
    </el-card>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, reactive, ref, shallowRef } from "vue";
import * as echarts from "echarts";
import { ElMessage } from "element-plus";
import { createK6Session } from "@/api/perfK6";
import { useCurrentEnvironment } from "@/composables/useCurrentEnvironment";

const { baseUrl, loadEnvironments } = useCurrentEnvironment();

const form = reactive({
  caseIdsText: "",
  target_base_url: "",
  vus: 5,
  duration: "30s",
  use_ai: true,
});

function applyBaseUrlFromCurrentEnv() {
  const b = (baseUrl.value || "").trim();
  if (!b) return;
  const cur = (form.target_base_url || "").trim();
  if (!cur) {
    form.target_base_url = b;
  }
}

const starting = ref(false);
const runId = ref("");
const sessionStatus = ref("");
const wsConnected = ref(false);
const lastFinal = shallowRef(null);

let ws = null;

const chartQpsRef = ref(null);
const chartP95Ref = ref(null);
let chartQps = null;
let chartP95 = null;

function parseCaseIds(text) {
  return String(text || "")
    .split(/[\s,，;；]+/)
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => parseInt(s, 10))
    .filter((n) => !Number.isNaN(n));
}

function buildWsUrl(token, id) {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const host = window.location.host;
  return `${proto}://${host}/ws/k6/${id}/?token=${encodeURIComponent(token || "")}`;
}

function initCharts() {
  if (chartQpsRef.value && !chartQps) {
    chartQps = echarts.init(chartQpsRef.value);
    chartQps.setOption({
      backgroundColor: "transparent",
      title: { text: "QPS（实时）", textStyle: { color: "#cbd5e1", fontSize: 14 } },
      grid: { left: 48, right: 16, top: 40, bottom: 32 },
      xAxis: { type: "category", data: [], axisLabel: { color: "#94a3b8" } },
      yAxis: { type: "value", axisLabel: { color: "#94a3b8" }, splitLine: { lineStyle: { color: "#334155" } } },
      series: [
        {
          name: "QPS",
          type: "line",
          smooth: true,
          showSymbol: false,
          areaStyle: { opacity: 0.15, color: "#38bdf8" },
          lineStyle: { color: "#38bdf8", width: 2 },
          data: [],
        },
      ],
    });
  }
  if (chartP95Ref.value && !chartP95) {
    chartP95 = echarts.init(chartP95Ref.value);
    chartP95.setOption({
      backgroundColor: "transparent",
      title: { text: "P95 / 错误率（实时）", textStyle: { color: "#cbd5e1", fontSize: 14 } },
      grid: { left: 56, right: 48, top: 40, bottom: 32 },
      legend: { textStyle: { color: "#94a3b8" }, top: 24 },
      xAxis: { type: "category", data: [], axisLabel: { color: "#94a3b8" } },
      yAxis: [
        {
          type: "value",
          name: "ms",
          axisLabel: { color: "#94a3b8" },
          splitLine: { lineStyle: { color: "#334155" } },
        },
        {
          type: "value",
          name: "%",
          max: 100,
          axisLabel: { color: "#94a3b8", formatter: "{value}%" },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: "P95 ms",
          type: "line",
          yAxisIndex: 0,
          smooth: true,
          showSymbol: false,
          areaStyle: { opacity: 0.12, color: "#a78bfa" },
          lineStyle: { color: "#a78bfa", width: 2 },
          data: [],
        },
        {
          name: "错误率",
          type: "line",
          yAxisIndex: 1,
          smooth: true,
          showSymbol: false,
          lineStyle: { color: "#f87171", width: 1, type: "dashed" },
          data: [],
        },
      ],
    });
  }
}

function pushTick(payload) {
  const t = new Date().toLocaleTimeString();
  const qps = payload.qps;
  const p95 = payload.p95_ms;
  const er = payload.error_rate;

  if (chartQps && qps != null) {
    const opt = chartQps.getOption();
    const xd = opt.xAxis[0].data || [];
    const sd = opt.series[0].data || [];
    xd.push(t);
    sd.push(qps);
    const max = 300;
    while (xd.length > max) {
      xd.shift();
      sd.shift();
    }
    chartQps.setOption({ xAxis: [{ data: xd }], series: [{ data: sd }] });
  }

  if (chartP95 && (p95 != null || er != null)) {
    const opt = chartP95.getOption();
    const xd = opt.xAxis[0].data || [];
    const sd0 = opt.series[0].data || [];
    const sd1 = opt.series[1].data || [];
    xd.push(t);
    sd0.push(p95 != null ? Number(p95.toFixed(2)) : null);
    sd1.push(er != null ? Number((er * 100).toFixed(3)) : null);
    const max = 300;
    while (xd.length > max) {
      xd.shift();
      sd0.shift();
      sd1.shift();
    }
    chartP95.setOption({
      xAxis: [{ data: xd }],
      series: [{ data: sd0 }, { data: sd1 }],
    });
  }
}

function handleWsMessage(ev) {
  let data;
  try {
    data = JSON.parse(ev.data);
  } catch {
    return;
  }
  if (data.type === "tick") {
    pushTick(data);
    if (data.qps != null) sessionStatus.value = "running";
  } else if (data.type === "final") {
    lastFinal.value = data;
    sessionStatus.value = data.exit_code === 0 ? "completed" : "failed";
    ElMessage[data.exit_code === 0 ? "success" : "warning"](
      data.exit_code === 0 ? "压测已完成" : `k6 退出码 ${data.exit_code}`
    );
  } else if (data.type === "error") {
    ElMessage.error(data.message || "错误");
    sessionStatus.value = "failed";
  } else if (data.type === "status") {
    if (data.phase === "subscribed") wsConnected.value = true;
    if (data.phase) sessionStatus.value = data.phase;
  }
}

function disconnectWs() {
  if (ws) {
    ws.close();
    ws = null;
  }
  wsConnected.value = false;
}

async function onStart() {
  const ids = parseCaseIds(form.caseIdsText);
  if (!ids.length) {
    ElMessage.warning("请填写至少一个 API 用例 ID");
    return;
  }
  starting.value = true;
  disconnectWs();
  lastFinal.value = null;
  tsQps.value = [];
  tsP95.value = [];
  try {
    initCharts();
    if (chartQps) {
      chartQps.setOption({ xAxis: [{ data: [] }], series: [{ data: [] }] });
    }
    if (chartP95) {
      chartP95.setOption({ xAxis: [{ data: [] }], series: [{ data: [] }, { data: [] }] });
    }

    const { data } = await createK6Session({
      test_case_ids: ids,
      vus: form.vus,
      duration: form.duration.trim(),
      use_ai: form.use_ai,
      target_base_url: form.target_base_url.trim(),
    });
    runId.value = data.run_id;
    sessionStatus.value = data.status || "pending";

    const token = localStorage.getItem("token");
    ws = new WebSocket(buildWsUrl(token, data.run_id));
    ws.onopen = () => {
      wsConnected.value = true;
    };
    ws.onmessage = handleWsMessage;
    ws.onerror = () => {
      ElMessage.error("WebSocket 连接异常");
      wsConnected.value = false;
    };
    ws.onclose = () => {
      wsConnected.value = false;
    };
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || e?.response?.data?.msg || "启动失败");
  } finally {
    starting.value = false;
  }
}

function onCurrentEnvChanged() {
  applyBaseUrlFromCurrentEnv();
}

onMounted(async () => {
  initCharts();
  await loadEnvironments();
  applyBaseUrlFromCurrentEnv();
  window.addEventListener("app:current-environment-changed", onCurrentEnvChanged);
  window.addEventListener("resize", () => {
    chartQps?.resize();
    chartP95?.resize();
  });
});

onBeforeUnmount(() => {
  window.removeEventListener("app:current-environment-changed", onCurrentEnvChanged);
  disconnectWs();
  chartQps?.dispose();
  chartP95?.dispose();
  chartQps = null;
  chartP95 = null;
});
</script>

<style scoped>
.load-monitor-page {
  min-height: 100%;
}
.card-title {
  font-weight: 600;
  color: #e2e8f0;
}
.card-sub {
  display: block;
  font-size: 12px;
  margin-top: 4px;
}
.muted {
  color: #94a3b8;
}
.start-form {
  max-width: 720px;
}
.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 16px;
}
.chart-box {
  height: 280px;
  min-width: 0;
  background: rgba(15, 23, 42, 0.5);
  border-radius: 8px;
  border: 1px solid #334155;
}
.json-pre {
  max-height: 360px;
  overflow: auto;
  font-size: 12px;
  background: #0f172a;
  color: #e2e8f0;
  padding: 12px;
  border-radius: 6px;
}
.mb-3 {
  margin-bottom: 12px;
}
.ws-ok {
  color: #4ade80;
}
@media (max-width: 900px) {
  .charts-row {
    grid-template-columns: 1fr;
  }
}
</style>
