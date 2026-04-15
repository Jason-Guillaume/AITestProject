<template>
  <div class="server-logs-page">
    <div class="server-logs-page__side">
      <div class="server-logs-page__side-head">
        <span>SSH 主机</span>
        <div class="server-logs-page__side-actions">
          <el-button type="primary" size="small" @click="openCreate">新增</el-button>
          <el-button size="small" :disabled="checkedIds.length !== 1" @click="openEditChecked">编辑</el-button>
          <el-button type="danger" plain size="small" :disabled="checkedIds.length === 0" @click="removeChecked">
            删除
          </el-button>
        </div>
      </div>
      <el-scrollbar class="server-logs-page__list">
        <div
          v-for="row in hosts"
          :key="row.id"
          class="server-logs-page__host"
          :class="{ 'is-active': selected?.id === row.id }"
          @click="selectHost(row)"
        >
          <div class="server-logs-page__host-top">
            <el-checkbox
              class="server-logs-page__host-check"
              :model-value="checkedIds.includes(row.id)"
              @click.stop
              @change="(v) => toggleChecked(row.id, v)"
            />
            <div class="server-logs-page__host-name">{{ row.name }}</div>
          </div>
          <div class="server-logs-page__host-meta">
            {{ row.host }}:{{ row.port }}
            <span v-if="row.organization_name" class="server-logs-page__org-tag">{{ row.organization_name }}</span>
          </div>
        </div>
        <el-empty v-if="!loading && !hosts.length" description="暂无主机" />
      </el-scrollbar>
    </div>

    <div class="server-logs-page__main">
      <template v-if="selected">
        <el-alert
          v-if="streaming && activeHost && activeHost.id !== selected.id"
          type="warning"
          show-icon
          class="server-logs-page__switch-alert"
          :title="`当前正在实时连接：${activeHost.name || activeHost.host}；已选中：${selected.name || selected.host}。点击“连接实时日志”将提示是否切换连接。`"
        />
        <div class="server-logs-page__controls">
          <el-input
            v-model="logPath"
            class="server-logs-page__path-input"
            placeholder="远程日志文件路径"
            clearable
          />
          <el-button v-if="!streaming" type="primary" @click="startStream">
            连接实时日志
          </el-button>
          <el-button v-else type="danger" plain @click="stopStream">断开</el-button>
          <el-button class="server-logs-page__ghost" @click="openEdit">编辑主机</el-button>
        </div>
        <LogTerminal :server-id="currentHost?.id" :log-path="logPath || currentHost?.default_log_path" :streaming="streaming" />
        <div class="server-logs-page__search">
          <el-input
            v-model="searchQ"
            placeholder="Elasticsearch 关键字（按当前主机 server_id 检索）"
            clearable
            class="server-logs-page__search-input"
            @keyup.enter="runSearch"
          />
          <el-button :loading="searchLoading" @click="runSearch">历史检索</el-button>
          <el-button :loading="trendLoading" @click="loadTrend">错误趋势</el-button>
        </div>
        <el-alert
          v-if="searchHint"
          :title="searchHint"
          type="info"
          show-icon
          class="server-logs-page__search-alert"
        />
        <div v-if="trendPoints.length" class="server-logs-page__trend">
          <div class="server-logs-page__trend-title">关键字趋势（默认 ERROR，最近 60 分钟）</div>
          <div ref="trendChartEl" class="server-logs-page__trend-chart" />
        </div>
        <el-alert
          v-else-if="trendHint"
          :title="trendHint"
          type="info"
          show-icon
          class="server-logs-page__search-alert"
        />
        <pre v-if="searchLines.length" class="server-logs-page__search-pre">{{ searchLines.join("\n") }}</pre>

        <el-collapse v-model="auditCollapse" class="server-logs-page__audit">
          <el-collapse-item title="操作审计" name="audit">
            <div class="server-logs-page__audit-bar">
              <el-button size="small" :loading="auditLoading" @click="loadAudit(1)">刷新审计</el-button>
              <span class="server-logs-page__audit-meta">共 {{ auditTotal }} 条</span>
            </div>
            <el-table :data="auditRows" size="small" stripe class="server-logs-page__audit-table" max-height="280">
              <el-table-column prop="created_at" label="时间" width="168" />
              <el-table-column prop="action_display" label="动作" width="120" />
              <el-table-column prop="user_display" label="用户" min-width="100" show-overflow-tooltip />
              <el-table-column prop="client_ip" label="IP" width="120" />
              <el-table-column label="详情" min-width="160">
                <template #default="{ row }">
                  <span class="server-logs-page__audit-meta">{{ auditMetaBrief(row.meta) }}</span>
                </template>
              </el-table-column>
            </el-table>
            <el-pagination
              v-if="auditTotal > auditPageSize"
              class="server-logs-page__audit-pager"
              layout="prev, pager, next"
              :total="auditTotal"
              :page-size="auditPageSize"
              :current-page="auditPage"
              @current-change="loadAudit"
            />
          </el-collapse-item>
        </el-collapse>
      </template>
      <el-empty v-else description="请选择或新增一台主机" />
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑 SSH 主机' : '新增 SSH 主机'"
      width="560px"
      destroy-on-close
      class="server-logs-dialog"
    >
      <el-form :model="form" label-width="108px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" maxlength="128" show-word-limit />
        </el-form-item>
        <el-form-item label="地址" required>
          <el-input v-model="form.host" placeholder="IP 或域名" />
        </el-form-item>
        <el-form-item label="端口">
          <el-input-number v-model="form.port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" autocomplete="off" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password autocomplete="new-password" />
        </el-form-item>
        <el-form-item label="私钥 PEM">
          <el-input
            v-model="form.private_key"
            type="textarea"
            :rows="4"
            placeholder="可选；与密码二选一或同时用于双因素环境"
          />
        </el-form-item>
        <el-form-item label="系统类型">
          <el-radio-group v-model="form.server_type">
            <el-radio label="linux">Linux</el-radio>
            <el-radio label="windows">Windows</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="默认路径">
          <el-input v-model="form.default_log_path" placeholder="/var/log/messages" />
        </el-form-item>
        <el-form-item label="共享组织">
          <el-select
            v-model="form.organization"
            clearable
            filterable
            placeholder="不选则仅自己可见；选择后组织创建人与成员均可使用"
            class="server-logs-page__org-select"
          >
            <el-option
              v-for="o in orgOptions"
              :key="o.id"
              :label="o.org_name"
              :value="o.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button v-if="editingId" type="danger" plain @click="removeHost">删除</el-button>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveHost">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import LogTerminal from "./LogTerminal.vue";
import {
  listServerLogHosts,
  createServerLogHost,
  updateServerLogHost,
  deleteServerLogHost,
  searchServerLogs,
  getServerLogErrorTrend,
  listServerLogAuditEvents,
  listLogServerOrganizationChoices,
} from "@/api/serverLogs";
import * as echarts from "echarts";

const hosts = ref([]);
const loading = ref(false);
const selected = ref(null);
const activeHost = ref(null); // 当前正在“实时连接”的主机（用于避免切换选择时自动断开）
const logPath = ref("");
const streaming = ref(false);
const checkedIds = ref([]);

const dialogVisible = ref(false);
const editingId = ref(null);
const saving = ref(false);
const orgOptions = ref([]);
const form = ref({
  name: "",
  host: "",
  port: 22,
  username: "",
  password: "",
  private_key: "",
  server_type: "linux",
  default_log_path: "/var/log/messages",
  organization: null,
});

const auditCollapse = ref([]);
const auditRows = ref([]);
const auditTotal = ref(0);
const auditPage = ref(1);
const auditPageSize = 15;
const auditLoading = ref(false);

const searchQ = ref("");
const searchLoading = ref(false);
const searchHint = ref("");
const searchLines = ref([]);

const trendLoading = ref(false);
const trendPoints = ref([]);
const trendHint = ref("");
const trendChartEl = ref(null);
let trendChart = null;

function normalizeList(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.results)) return payload.results;
  return [];
}

async function loadOrgOptions() {
  try {
    const { data } = await listLogServerOrganizationChoices();
    orgOptions.value = Array.isArray(data) ? data : [];
  } catch {
    orgOptions.value = [];
  }
}

function auditMetaBrief(meta) {
  if (!meta || typeof meta !== "object") return "";
  try {
    if (meta.path) return String(meta.path).slice(0, 120);
    if (meta.q) return `query: ${String(meta.q).slice(0, 80)}`;
    if (meta.success != null) return meta.success ? "AI 成功" : `失败: ${(meta.error || "").slice(0, 60)}`;
    return JSON.stringify(meta).slice(0, 120);
  } catch {
    return "";
  }
}

async function loadAudit(page = 1) {
  auditLoading.value = true;
  auditPage.value = page;
  try {
    const { data } = await listServerLogAuditEvents({ page, page_size: auditPageSize });
    if (Array.isArray(data?.results)) {
      auditRows.value = data.results;
      auditTotal.value = Number(data.count) || 0;
    } else if (Array.isArray(data)) {
      auditRows.value = data;
      auditTotal.value = data.length;
    } else {
      auditRows.value = normalizeList(data);
      auditTotal.value = Number(data?.count) || auditRows.value.length;
    }
  } catch {
    auditRows.value = [];
    auditTotal.value = 0;
  } finally {
    auditLoading.value = false;
  }
}

async function loadHosts() {
  loading.value = true;
  try {
    const { data } = await listServerLogHosts({ page_size: 200 });
    hosts.value = normalizeList(data);
    if (selected.value) {
      const m = hosts.value.find((h) => h.id === selected.value.id);
      selected.value = m || null;
    }
    // 维护多选：过滤掉已不存在的 id
    const existing = new Set(hosts.value.map((h) => h.id));
    checkedIds.value = checkedIds.value.filter((id) => existing.has(id));
  } catch {
    hosts.value = [];
    checkedIds.value = [];
  } finally {
    loading.value = false;
  }
}

function selectHost(row) {
  selected.value = row;
  // 未处于实时连接时，切换主机直接切换当前显示与输入框
  if (!streaming.value || !activeHost.value) {
    activeHost.value = row;
    logPath.value = row.default_log_path || "/var/log/messages";
  }
  searchHint.value = "";
  searchLines.value = [];
}

const currentHost = computed(() => {
  if (streaming.value && activeHost.value) return activeHost.value;
  return selected.value;
});

function toggleChecked(id, v) {
  const next = new Set(checkedIds.value);
  if (v) next.add(id);
  else next.delete(id);
  checkedIds.value = Array.from(next);
}

function openCreate() {
  editingId.value = null;
  loadOrgOptions();
  form.value = {
    name: "",
    host: "",
    port: 22,
    username: "",
    password: "",
    private_key: "",
    server_type: "linux",
    default_log_path: "/var/log/messages",
    organization: null,
  };
  dialogVisible.value = true;
}

function openEdit() {
  if (!selected.value) return;
  loadOrgOptions();
  editingId.value = selected.value.id;
  form.value = {
    name: selected.value.name,
    host: selected.value.host,
    port: selected.value.port,
    username: selected.value.username,
    password: "",
    private_key: "",
    server_type: selected.value.server_type || "linux",
    default_log_path: selected.value.default_log_path || "/var/log/messages",
    organization: selected.value.organization ?? null,
  };
  dialogVisible.value = true;
}

function openEditChecked() {
  if (checkedIds.value.length !== 1) return;
  const id = checkedIds.value[0];
  const row = hosts.value.find((h) => h.id === id);
  if (!row) return;
  // 复用现有编辑逻辑：将其设置为当前选中主机
  selected.value = row;
  openEdit();
}

async function saveHost() {
  saving.value = true;
  try {
    const body = { ...form.value };
    if (!body.password) delete body.password;
    if (!(body.private_key || "").trim()) delete body.private_key;
    if (editingId.value) {
      await updateServerLogHost(editingId.value, body);
      ElMessage.success("已保存");
    } else {
      await createServerLogHost(body);
      ElMessage.success("已创建");
    }
    dialogVisible.value = false;
    await loadHosts();
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || e?.message || "保存失败");
  } finally {
    saving.value = false;
  }
}

async function removeHost() {
  if (!editingId.value) return;
  try {
    await ElMessageBox.confirm("确定删除该主机配置？", "提示", { type: "warning" });
  } catch {
    return;
  }
  try {
    await deleteServerLogHost(editingId.value);
    ElMessage.success("已删除");
    dialogVisible.value = false;
    if (selected.value?.id === editingId.value) {
      selected.value = null;
    }
    if (activeHost.value?.id === editingId.value) {
      activeHost.value = null;
      stopStream();
    }
    editingId.value = null;
    await loadHosts();
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || e?.message || "删除失败");
  }
}

async function removeChecked() {
  const ids = checkedIds.value.slice();
  if (!ids.length) return;
  const count = ids.length;
  try {
    await ElMessageBox.confirm(`确定删除已勾选的 ${count} 台主机配置？`, "提示", { type: "warning" });
  } catch {
    return;
  }
  let ok = 0;
  let fail = 0;
  for (const id of ids) {
    try {
      await deleteServerLogHost(id);
      ok += 1;
    } catch {
      fail += 1;
    }
  }
  checkedIds.value = [];
  if (selected.value && ids.includes(selected.value.id)) selected.value = null;
  if (activeHost.value && ids.includes(activeHost.value.id)) {
    activeHost.value = null;
    stopStream();
  }
  await loadHosts();
  if (fail === 0) ElMessage.success(`已删除 ${ok} 台`);
  else ElMessage.warning(`删除完成：成功 ${ok}，失败 ${fail}`);
}

function startStream() {
  if (!selected.value) return;
  // 未连接：直接开始
  if (!streaming.value || !activeHost.value) {
    activeHost.value = selected.value;
    logPath.value = selected.value.default_log_path || "/var/log/messages";
    streaming.value = true;
    return;
  }
  // 已连接且用户想连另一台：此时才提示是否切换
  if (activeHost.value?.id !== selected.value.id) {
    ElMessageBox.confirm(
      `当前正在实时连接「${activeHost.value?.name || activeHost.value?.host || activeHost.value?.id}」。\n` +
        `是否断开并切换连接到「${selected.value?.name || selected.value?.host || selected.value?.id}」？`,
      "切换实时连接",
      { type: "warning", confirmButtonText: "切换连接", cancelButtonText: "取消" }
    )
      .then(() => {
        // 先断开旧连接，再切换目标并连接
        streaming.value = false;
        activeHost.value = selected.value;
        logPath.value = selected.value.default_log_path || "/var/log/messages";
        // 下一帧再打开，确保子组件先收到 streaming=false 触发 disconnect
        requestAnimationFrame(() => {
          streaming.value = true;
        });
      })
      .catch(() => {});
    return;
  }
  // 已连接且同一台：保持
  streaming.value = true;
}

function stopStream() {
  streaming.value = false;
}

async function runSearch() {
  searchLoading.value = true;
  searchHint.value = "";
  searchLines.value = [];
  try {
    const keyword = String(searchQ.value || "").trim();
    const serverId = selected.value?.id;
    const { data } = await searchServerLogs({ server_id: serverId, keyword, limit: 80 });
    if (!data.enabled) {
      searchHint.value = data.message || "未启用历史检索";
      return;
    }
    if (data.message) searchHint.value = data.message;
    searchLines.value = (data.results || []).map((r) => {
      const ts = r.timestamp != null ? String(r.timestamp) : "";
      return `[${ts}] ${r.message || ""}`;
    });
  } catch (e) {
    searchHint.value = e?.response?.data?.message || e?.message || "检索失败";
  } finally {
    searchLoading.value = false;
  }
}

function renderTrend() {
  if (!trendChartEl.value) return;
  if (!trendChart) trendChart = echarts.init(trendChartEl.value);
  const xs = trendPoints.value.map((p) => String(p.ts || ""));
  const ys = trendPoints.value.map((p) => Number(p.count || 0));
  trendChart.setOption({
    grid: { left: 42, right: 16, top: 20, bottom: 26 },
    xAxis: { type: "category", data: xs, axisLabel: { color: "#7de3f6", hideOverlap: true } },
    yAxis: { type: "value", axisLabel: { color: "#7de3f6" } },
    series: [
      {
        type: "line",
        data: ys,
        smooth: true,
        showSymbol: false,
        lineStyle: { color: "#00cfec", width: 2 },
        areaStyle: { color: "rgba(0, 207, 236, 0.12)" },
      },
    ],
    tooltip: { trigger: "axis" },
  });
}

async function loadTrend() {
  if (!selected.value) return;
  trendLoading.value = true;
  trendHint.value = "";
  try {
    const { data } = await getServerLogErrorTrend({
      server_id: selected.value.id,
      keyword: "ERROR",
      minutes: 60,
      interval: "1m",
    });
    if (!data?.enabled) {
      trendPoints.value = [];
      trendHint.value = data?.message || "趋势暂不可用";
      return;
    }
    trendPoints.value = Array.isArray(data?.points) ? data.points : [];
    requestAnimationFrame(renderTrend);
  } catch {
    trendPoints.value = [];
    trendHint.value = "趋势加载失败";
  } finally {
    trendLoading.value = false;
  }
}

onMounted(() => {
  loadHosts();
  loadAudit(1);
});
</script>

<style scoped lang="scss">
.server-logs-page {
  display: flex;
  gap: 16px;
  height: calc(100vh - 140px);
  min-height: 520px;
}

.server-logs-page__side {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #0c1f3a, #0a1628);
  border: 1px solid rgba(0, 207, 236, 0.2);
  border-radius: 10px;
  box-shadow: 0 0 20px rgba(0, 80, 120, 0.2);
}

.server-logs-page__side-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 12px 8px;
  color: #9ee7f7;
  font-weight: 600;
  border-bottom: 1px solid rgba(0, 207, 236, 0.15);
}

.server-logs-page__side-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.server-logs-page__list {
  flex: 1;
  padding: 8px;
}

.server-logs-page__host {
  padding: 10px 10px;
  margin-bottom: 6px;
  border-radius: 8px;
  border: 1px solid transparent;
  cursor: pointer;
  color: #b8e8f5;
  background: rgba(0, 40, 70, 0.35);
  transition: border-color 0.15s, box-shadow 0.15s;
}

.server-logs-page__host-top {
  display: flex;
  align-items: center;
  gap: 8px;
}

.server-logs-page__host-check {
  flex-shrink: 0;
}

.server-logs-page__host:hover {
  border-color: rgba(0, 207, 236, 0.35);
}

.server-logs-page__host.is-active {
  border-color: rgba(0, 207, 236, 0.65);
  box-shadow: 0 0 14px rgba(0, 180, 220, 0.25);
}

.server-logs-page__host-name {
  font-weight: 600;
  color: #e6fbff;
}

.server-logs-page__host-meta {
  font-size: 12px;
  opacity: 0.75;
  margin-top: 4px;
}

.server-logs-page__org-tag {
  display: inline-block;
  margin-left: 6px;
  padding: 0 6px;
  border-radius: 4px;
  font-size: 11px;
  background: rgba(0, 207, 236, 0.15);
  color: #9ee7f7;
}

.server-logs-page__org-select {
  width: 100%;
}

.server-logs-page__audit {
  margin-top: 12px;
  border: 1px solid rgba(0, 207, 236, 0.2);
  border-radius: 8px;
  overflow: hidden;
}

.server-logs-page__audit-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.server-logs-page__audit-meta {
  font-size: 12px;
  opacity: 0.8;
  color: #b6d4e8;
}

.server-logs-page__audit-table {
  --el-table-bg-color: #071426;
  --el-table-tr-bg-color: #071426;
}

.server-logs-page__audit-pager {
  margin-top: 10px;
  justify-content: flex-end;
}

.server-logs-page__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.server-logs-page__controls {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.server-logs-page__path-input {
  flex: 1;
  min-width: 220px;
  max-width: 520px;
}

.server-logs-page__ghost {
  --el-button-bg-color: rgba(0, 207, 236, 0.08);
  --el-button-border-color: rgba(0, 207, 236, 0.35);
  --el-button-text-color: #b6f7ff;
}

.server-logs-page__search {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 4px;
}

.server-logs-page__search-input {
  flex: 1;
  max-width: 640px;
}

.server-logs-page__search-alert {
  margin-top: 4px;
}

.server-logs-page__search-pre {
  margin: 0;
  padding: 10px 12px;
  max-height: 200px;
  overflow: auto;
  background: #071426;
  border: 1px solid rgba(0, 207, 236, 0.2);
  border-radius: 8px;
  color: #7eebfd;
  font-size: 12px;
  line-height: 1.5;
}

.server-logs-page__switch-alert {
  margin-bottom: 6px;
}

.server-logs-page__trend {
  margin-top: 10px;
  padding: 10px 12px;
  border: 1px solid rgba(0, 207, 236, 0.18);
  border-radius: 10px;
  background: rgba(6, 18, 32, 0.42);
}
.server-logs-page__trend-title {
  color: #9ee7f7;
  font-weight: 600;
  margin-bottom: 8px;
}
.server-logs-page__trend-chart {
  height: 180px;
  width: 100%;
}
</style>

<style lang="scss">
.server-logs-dialog .el-dialog__body {
  padding-top: 8px;
}
</style>
