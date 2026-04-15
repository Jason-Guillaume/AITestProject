<template>
  <div class="page-wrap cyber-page sys-admin-page ai-usage-page">
    <el-card class="sys-page-head" shadow="never">
      <div class="sys-page-head__row">
        <div>
          <h2 class="sys-page-head__title">AI 用量与审计</h2>
          <p class="sys-page-head__sub">查看近 N 天调用汇总与最近审计事件（仅系统管理员）。</p>
        </div>
        <div class="sys-page-head__actions">
          <el-select v-model="days" size="default" style="width: 140px" @change="loadSummary">
            <el-option label="近 3 天" :value="3" />
            <el-option label="近 7 天" :value="7" />
            <el-option label="近 14 天" :value="14" />
            <el-option label="近 30 天" :value="30" />
          </el-select>
          <el-button size="default" :loading="loading" @click="reloadAll">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </div>
    </el-card>

    <div class="summary-grid" v-loading="summaryLoading">
      <el-card class="summary-card" shadow="never" v-for="row in summaryRows" :key="row.action">
        <div class="summary-card__title">{{ actionLabel(row.action) }}</div>
        <div class="summary-card__numbers">
          <div class="summary-metric">
            <div class="summary-metric__label">总计</div>
            <div class="summary-metric__value">{{ row.total }}</div>
          </div>
          <div class="summary-metric">
            <div class="summary-metric__label">成功</div>
            <div class="summary-metric__value ok">{{ row.success }}</div>
          </div>
          <div class="summary-metric">
            <div class="summary-metric__label">失败</div>
            <div class="summary-metric__value bad">{{ row.failed }}</div>
          </div>
        </div>
      </el-card>
      <el-empty v-if="!summaryRows.length && !summaryLoading" description="暂无汇总数据" :image-size="80" />
    </div>

    <el-card class="sys-table-card" shadow="never">
      <div class="chart-head">
        <div class="chart-head__title">调用趋势（按天）</div>
        <div class="chart-head__sub">展示各 action 的总调用量趋势。</div>
      </div>
      <div ref="trendChartEl" class="ai-usage-chart" v-loading="metricsLoading" />
    </el-card>

    <el-card class="sys-table-card" shadow="never">
      <div class="chart-head">
        <div class="chart-head__title">P95 耗时趋势（按天）</div>
        <div class="chart-head__sub">按 action 展示每天的 P95 耗时（ms）。</div>
      </div>
      <div ref="p95ChartEl" class="ai-usage-chart" v-loading="trendLoading" />
    </el-card>

    <el-card class="sys-table-card" shadow="never">
      <div class="chart-head">
        <div class="chart-head__title">耗时分布（P50 / P95）</div>
        <div class="chart-head__sub">按 action 统计近 N 天请求耗时分位数（基于最新样本抽样）。</div>
      </div>
      <el-table :data="latencyRows" v-loading="metricsLoading" class="admin-data-table sys-enterprise-table" border>
        <template #empty>
          <el-empty description="暂无耗时数据" :image-size="78" />
        </template>
        <el-table-column prop="action" label="动作" min-width="180">
          <template #default="{ row }">
            <el-tag size="small" type="info" effect="plain">{{ actionLabel(row.action) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total" label="样本量" width="90" align="center" />
        <el-table-column prop="avg_ms" label="均值(ms)" width="110" align="center" />
        <el-table-column prop="p50_ms" label="P50(ms)" width="110" align="center" />
        <el-table-column prop="p95_ms" label="P95(ms)" width="110" align="center" />
        <el-table-column prop="max_ms" label="最大(ms)" width="110" align="center" />
      </el-table>
    </el-card>

    <el-card class="sys-table-card" shadow="never">
      <div class="chart-head">
        <div class="chart-head__title">Top 失败原因</div>
        <div class="chart-head__sub">近 N 天失败事件的错误码/摘要 TopN。</div>
      </div>
      <el-table :data="topErrors" v-loading="errorsLoading" class="admin-data-table sys-enterprise-table" border>
        <template #empty>
          <el-empty description="暂无失败数据" :image-size="78" />
        </template>
        <el-table-column prop="action" label="动作" min-width="160">
          <template #default="{ row }">
            <el-tag size="small" type="info" effect="plain">{{ actionLabel(row.action) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="count" label="次数" width="90" align="center" />
        <el-table-column prop="max_latency_ms" label="最大耗时" width="110" align="center" />
        <el-table-column prop="error_code" label="错误码" min-width="160" show-overflow-tooltip />
        <el-table-column prop="error_message" label="错误摘要" min-width="260" show-overflow-tooltip />
      </el-table>
    </el-card>

    <el-card class="sys-filter-card" shadow="never">
      <div class="sys-toolbar">
        <div class="sys-toolbar__left">
          <el-date-picker
            v-model="filters.date_range"
            type="daterange"
            unlink-panels
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 260px"
            @change="loadEvents"
          />
          <el-select
            v-model="filters.actions"
            multiple
            collapse-tags
            collapse-tags-tooltip
            clearable
            placeholder="动作（可多选）"
            style="width: 260px"
            @change="loadEvents"
          >
            <el-option v-for="a in actionOptions" :key="a.value" :label="a.label" :value="a.value" />
          </el-select>
          <el-select v-model="filters.success" clearable placeholder="结果" style="width: 160px" @change="loadEvents">
            <el-option label="成功" value="true" />
            <el-option label="失败" value="false" />
          </el-select>
          <el-input
            v-model="filters.user_id"
            clearable
            placeholder="用户ID（可选）"
            style="width: 180px"
            @keyup.enter="loadEvents"
          />
          <el-input
            v-model="filters.error_code"
            clearable
            placeholder="错误码（可选）"
            style="width: 200px"
            @keyup.enter="loadEvents"
          />
          <el-select v-model="pageSize" style="width: 160px" @change="loadEvents">
            <el-option label="最近 50 条" :value="50" />
            <el-option label="最近 100 条" :value="100" />
            <el-option label="最近 200 条" :value="200" />
          </el-select>
        </div>
        <div class="sys-toolbar__right">
          <el-button size="default" :disabled="exporting" :loading="exporting" @click="exportCsv">
            导出 CSV
          </el-button>
          <el-button size="default" :loading="eventsLoading" @click="loadEvents">查询</el-button>
        </div>
      </div>
    </el-card>

    <el-card class="sys-table-card" shadow="never">
      <el-table :data="events" v-loading="eventsLoading" class="admin-data-table sys-enterprise-table" border>
        <template #empty>
          <el-empty description="暂无审计事件" :image-size="86" />
        </template>
        <el-table-column prop="created_at" label="时间" width="176" align="center">
          <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="action" label="动作" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <el-tag size="small" type="info" effect="plain">{{ actionLabel(row.action) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="success" label="结果" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.success ? 'success' : 'danger'" effect="plain">
              {{ row.success ? "成功" : "失败" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status_code" label="状态码" width="90" align="center" />
        <el-table-column prop="user_id" label="用户" width="90" align="center" />
        <el-table-column prop="model_used" label="模型" min-width="140" show-overflow-tooltip />
        <el-table-column prop="test_type" label="类型" width="120" align="center" />
        <el-table-column prop="module_id" label="模块" width="90" align="center">
          <template #default="{ row }">{{ row.module_id ?? "—" }}</template>
        </el-table-column>
        <el-table-column prop="latency_ms" label="耗时(ms)" width="110" align="center" />
        <el-table-column prop="cases_count" label="条数" width="80" align="center" />
        <el-table-column prop="error_code" label="错误码" min-width="140" show-overflow-tooltip />
        <el-table-column prop="error_message" label="错误摘要" min-width="220" show-overflow-tooltip />
        <el-table-column prop="endpoint" label="接口" min-width="200" show-overflow-tooltip />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import * as echarts from "echarts";
import {
  getAiUsageEventsApi,
  getAiUsageExportCsvUrl,
  getAiUsageLatencyTrendApi,
  getAiUsageMetricsApi,
  getAiUsageSummaryApi,
  getAiUsageTopErrorsApi,
} from "@/api/sysAiUsage";

const loading = ref(false);
const summaryLoading = ref(false);
const eventsLoading = ref(false);
const metricsLoading = ref(false);
const errorsLoading = ref(false);
const trendLoading = ref(false);
const exporting = ref(false);

const days = ref(7);
const pageSize = ref(50);

const filters = reactive({
  actions: [],
  success: "",
  user_id: "",
  error_code: "",
  date_range: [],
});

function actionParam() {
  const arr = Array.isArray(filters.actions) ? filters.actions.filter(Boolean) : [];
  return arr.length ? arr.join(",") : "";
}

function dateRangeParams() {
  const r = Array.isArray(filters.date_range) ? filters.date_range : [];
  if (r.length !== 2 || !r[0] || !r[1]) return {};
  const start = String(r[0]);
  const end = String(r[1]);
  // el-date-picker value-format 设为 YYYY-MM-DD 后，这里就是字符串
  return { start_date: start, end_date: end };
}

const events = ref([]);
const summary = ref({ by_action: {} });
const metrics = ref({ xAxis: [], trend: [], metrics: {} });
const topErrors = ref([]);
const p95Trend = ref({ xAxis: [], series: [] });

const trendChartEl = ref(null);
const p95ChartEl = ref(null);
let chart = null;
let p95Chart = null;

const actionOptions = [
  { value: "generate_cases", label: "生成用例（同步）" },
  { value: "generate_cases_stream", label: "生成用例（流式）" },
  { value: "phase1_preview", label: "Phase1 预览" },
  { value: "test_connection", label: "模型连通性测试" },
  { value: "verify_connection", label: "固定模型连通性校验" },
  { value: "knowledge_autofill", label: "知识库自动填表" },
];

function actionLabel(v) {
  return actionOptions.find((x) => x.value === v)?.label || v || "—";
}

function fmtTime(iso) {
  if (!iso) return "—";
  const s = String(iso).replace("T", " ");
  return s.length > 16 ? s.slice(0, 16) : s;
}

const summaryRows = computed(() => {
  const map = summary.value?.by_action || {};
  const rows = Object.entries(map).map(([action, m]) => ({
    action,
    total: Number(m?.total || 0),
    success: Number(m?.success || 0),
    failed: Number(m?.failed || 0),
  }));
  rows.sort((a, b) => b.total - a.total);
  return rows;
});

const latencyRows = computed(() => {
  const map = metrics.value?.metrics || {};
  const rows = Object.entries(map).map(([action, m]) => ({
    action,
    total: Number(m?.total || 0),
    avg_ms: Number(m?.avg_ms || 0),
    p50_ms: Number(m?.p50_ms || 0),
    p95_ms: Number(m?.p95_ms || 0),
    max_ms: Number(m?.max_ms || 0),
  }));
  rows.sort((a, b) => b.total - a.total);
  return rows;
});

function renderTrendChart() {
  if (!trendChartEl.value) return;
  const xAxis = Array.isArray(metrics.value?.xAxis) ? metrics.value.xAxis : [];
  const trend = Array.isArray(metrics.value?.trend) ? metrics.value.trend : [];
  if (!xAxis.length || !trend.length) return;
  if (chart) chart.dispose();
  chart = echarts.init(trendChartEl.value);
  const series = trend.map((t) => ({
    name: actionLabel(t.action),
    type: "line",
    smooth: true,
    showSymbol: false,
    data: Array.isArray(t.total) ? t.total : [],
  }));
  chart.setOption({
    tooltip: { trigger: "axis" },
    legend: { top: 8 },
    grid: { top: 44, left: 42, right: 18, bottom: 26 },
    xAxis: { type: "category", data: xAxis },
    yAxis: { type: "value" },
    series,
  });
}

function renderP95Chart() {
  if (!p95ChartEl.value) return;
  const xAxis = Array.isArray(p95Trend.value?.xAxis) ? p95Trend.value.xAxis : [];
  const seriesRows = Array.isArray(p95Trend.value?.series) ? p95Trend.value.series : [];
  if (!xAxis.length || !seriesRows.length) return;
  if (p95Chart) p95Chart.dispose();
  p95Chart = echarts.init(p95ChartEl.value);
  const series = seriesRows.map((s) => ({
    name: actionLabel(s.action),
    type: "line",
    smooth: true,
    showSymbol: false,
    data: Array.isArray(s.p95_ms) ? s.p95_ms : [],
  }));
  p95Chart.setOption({
    tooltip: { trigger: "axis" },
    legend: { top: 8 },
    grid: { top: 44, left: 42, right: 18, bottom: 26 },
    xAxis: { type: "category", data: xAxis },
    yAxis: { type: "value" },
    series,
  });
}

function resizeChart() {
  chart?.resize();
  p95Chart?.resize();
}

async function loadSummary() {
  summaryLoading.value = true;
  try {
    const { data } = await getAiUsageSummaryApi({ days: days.value });
    if (data?.success) summary.value = data;
    else summary.value = { by_action: {} };
  } catch (e) {
    summary.value = { by_action: {} };
    ElMessage.error(e?.response?.data?.detail || "加载汇总失败");
  } finally {
    summaryLoading.value = false;
  }
}

async function loadMetrics() {
  metricsLoading.value = true;
  try {
    const { data } = await getAiUsageMetricsApi({ days: days.value });
    metrics.value = data?.success ? data : { xAxis: [], trend: [], metrics: {} };
    await nextTick();
    renderTrendChart();
  } catch (e) {
    metrics.value = { xAxis: [], trend: [], metrics: {} };
    ElMessage.error(e?.response?.data?.detail || "加载趋势/耗时指标失败");
  } finally {
    metricsLoading.value = false;
  }
}

async function loadTopErrors() {
  errorsLoading.value = true;
  try {
    const params = {
      days: days.value,
      limit: 10,
      ...(actionParam() ? { action: actionParam() } : {}),
      ...dateRangeParams(),
    };
    const { data } = await getAiUsageTopErrorsApi(params);
    topErrors.value = data?.success && Array.isArray(data.results) ? data.results : [];
  } catch (e) {
    topErrors.value = [];
    ElMessage.error(e?.response?.data?.detail || "加载 Top 错误失败");
  } finally {
    errorsLoading.value = false;
  }
}

async function loadEvents() {
  eventsLoading.value = true;
  try {
    const params = {
      page_size: pageSize.value,
      ...(actionParam() ? { action: actionParam() } : {}),
      ...(filters.success ? { success: filters.success } : {}),
      ...(String(filters.user_id || "").trim() ? { user_id: String(filters.user_id || "").trim() } : {}),
      ...(String(filters.error_code || "").trim()
        ? { error_code: String(filters.error_code || "").trim() }
        : {}),
      ...dateRangeParams(),
    };
    const { data } = await getAiUsageEventsApi(params);
    if (data?.success) events.value = Array.isArray(data.results) ? data.results : [];
    else events.value = [];
  } catch (e) {
    events.value = [];
    ElMessage.error(e?.response?.data?.detail || "加载审计事件失败（需系统管理员权限）");
  } finally {
    eventsLoading.value = false;
  }
}

async function loadP95Trend() {
  trendLoading.value = true;
  try {
    const params = {
      days: days.value,
      max_samples: 500,
      ...(actionParam() ? { action: actionParam() } : {}),
      ...dateRangeParams(),
    };
    const { data } = await getAiUsageLatencyTrendApi(params);
    p95Trend.value = data?.success ? data : { xAxis: [], series: [] };
    await nextTick();
    renderP95Chart();
  } catch (e) {
    p95Trend.value = { xAxis: [], series: [] };
    ElMessage.error(e?.response?.data?.detail || "加载 P95 趋势失败");
  } finally {
    trendLoading.value = false;
  }
}

async function exportCsv() {
  exporting.value = true;
  try {
    const params = {
      ...(actionParam() ? { action: actionParam() } : {}),
      ...(filters.success ? { success: filters.success } : {}),
      ...(String(filters.user_id || "").trim()
        ? { user_id: String(filters.user_id || "").trim() }
        : {}),
      ...(String(filters.error_code || "").trim()
        ? { error_code: String(filters.error_code || "").trim() }
        : {}),
      ...dateRangeParams(),
      limit: 200000,
    };
    const url = getAiUsageExportCsvUrl(params);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ai-usage-events.csv`;
    a.click();
  } catch {
    ElMessage.error("导出失败");
  } finally {
    exporting.value = false;
  }
}

async function reloadAll() {
  loading.value = true;
  try {
    await Promise.all([loadSummary(), loadMetrics(), loadP95Trend(), loadTopErrors(), loadEvents()]);
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  reloadAll();
  window.addEventListener("resize", resizeChart);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", resizeChart);
  if (chart) chart.dispose();
  if (p95Chart) p95Chart.dispose();
});
</script>

<style scoped>
.sys-admin-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  box-sizing: border-box;
}

.sys-page-head,
.summary-card,
.sys-filter-card,
.sys-table-card {
  border-radius: 12px !important;
  border: 1px solid rgba(0, 255, 255, 0.12) !important;
  background: rgba(18, 26, 44, 0.92) !important;
  --el-card-bg-color: rgba(18, 26, 44, 0.92);
}

.sys-page-head :deep(.el-card__body) {
  padding: 16px 18px;
}

.sys-page-head__row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.sys-page-head__title {
  margin: 0 0 6px;
  font-size: 17px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.94);
}

.sys-page-head__sub {
  margin: 0;
  font-size: 12px;
  color: rgba(226, 232, 240, 0.65);
  line-height: 1.5;
}

.sys-page-head__actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

@media (max-width: 1100px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 760px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}

.summary-card :deep(.el-card__body) {
  padding: 14px 16px;
}

.summary-card__title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(226, 232, 240, 0.92);
  margin-bottom: 10px;
}

.summary-card__numbers {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.summary-metric__label {
  font-size: 11px;
  color: rgba(226, 232, 240, 0.55);
  margin-bottom: 4px;
}

.summary-metric__value {
  font-size: 16px;
  font-weight: 700;
  color: rgba(226, 232, 240, 0.92);
}
.summary-metric__value.ok {
  color: rgba(34, 197, 94, 0.95);
}
.summary-metric__value.bad {
  color: rgba(239, 68, 68, 0.95);
}

.sys-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.sys-toolbar__left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.ai-usage-chart {
  width: 100%;
  height: 360px;
}

.chart-head {
  margin-bottom: 10px;
}
.chart-head__title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(226, 232, 240, 0.92);
  margin-bottom: 4px;
}
.chart-head__sub {
  font-size: 12px;
  color: rgba(226, 232, 240, 0.6);
}
</style>

