<template>
  <div class="cyber-page admin-list-page env-management-page">
    <div class="env-content-shell">
      <div class="env-stat-row">
        <div v-for="card in statCards" :key="card.key" class="env-stat-card">
          <div class="env-stat-card__head">
            <span class="env-stat-card__icon">
              <el-icon><component :is="card.icon" /></el-icon>
            </span>
            <span class="env-stat-card__label">{{ card.label }}</span>
          </div>
          <div class="env-stat-card__value tech-metric">{{ card.value }}</div>
          <div class="env-stat-card__sub">{{ card.sub }}</div>
          <div class="env-stat-card__bar">
            <span class="env-stat-card__bar-fill" :style="{ width: card.barWidth, background: card.barColor }" />
          </div>
        </div>
      </div>

      <el-card class="admin-list-card env-cyber-card" shadow="never">
        <div class="admin-toolbar-row env-toolbar-row">
          <div class="admin-toolbar-row__left env-toolbar-left">
            <el-button type="primary" class="env-primary-btn" @click="openCreateDialog">新增环境</el-button>
          </div>
        </div>

        <el-table :data="envList" border stripe class="admin-data-table env-data-table" v-loading="loading">
          <el-table-column prop="name" label="环境名称" min-width="140" />
          <el-table-column prop="env_type" label="环境类型" width="120" />
          <el-table-column prop="base_url" label="Base URL" min-width="220" show-overflow-tooltip />
          <el-table-column
            prop="health_check_path"
            label="健康检查路径"
            min-width="140"
            show-overflow-tooltip
          >
            <template #default="{ row }">
              <span>{{ row.health_check_path || "—" }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="描述" min-width="160" show-overflow-tooltip />
          <el-table-column label="操作" width="240" align="center">
            <template #default="{ row }">
              <TableActionGroup :row="row" :actions="envTableActions(row)" @action="handleEnvTableAction" />
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑环境' : '新增环境'"
      width="680px"
      class="cyber-dialog-dark"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
        <el-form-item label="环境名称" prop="name">
          <el-input v-model="form.name" placeholder="例如：测试环境-A" />
        </el-form-item>
        <el-form-item label="环境类型" prop="env_type">
          <el-select v-model="form.env_type" class="w-full">
            <el-option label="开发环境" value="dev" />
            <el-option label="测试环境" value="test" />
            <el-option label="预发环境" value="staging" />
            <el-option label="生产镜像" value="prod" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="Base URL" prop="base_url">
          <el-input v-model="form.base_url" placeholder="https://api.example.com" />
        </el-form-item>
        <el-form-item label="健康检查路径">
          <el-input
            v-model="form.health_check_path"
            clearable
            placeholder="可选，如 health、api/health；留空则探测 Base URL 根路径"
          />
        </el-form-item>
        <el-form-item label="DB 配置">
          <el-input
            v-model="dbConfigText"
            type="textarea"
            :rows="5"
            placeholder='{"host":"127.0.0.1","port":3306,"user":"root","password":"***"}'
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { Clock, Connection, DataAnalysis, Delete, Edit, Opportunity, SwitchButton } from "@element-plus/icons-vue";
import { ElMessageBox, ElNotification } from "element-plus";
import TableActionGroup from "@/components/common/TableActionGroup.vue";
import {
  createEnvironment,
  deleteEnvironment,
  getEnvironments,
  updateEnvironment,
  validateEnvironment,
} from "@/api/environment";

const loading = ref(false);
const saving = ref(false);
const dialogVisible = ref(false);
const isEdit = ref(false);
const editingId = ref(null);
const envList = ref([]);
const validatingIds = ref(new Set());
const formRef = ref();
const form = ref({
  name: "",
  env_type: "test",
  base_url: "",
  health_check_path: "",
  db_config: {},
  description: "",
});
const dbConfigText = ref("{}");

const rules = {
  name: [{ required: true, message: "请输入环境名称", trigger: "blur" }],
  env_type: [{ required: true, message: "请选择环境类型", trigger: "change" }],
};

const totalEnvironments = computed(() => envList.value.length);

const activeNodes = computed(() =>
  envList.value.filter((item) => {
    const status = String(item?.status || item?.node_status || "").toLowerCase();
    return Boolean(item?.is_active || item?.enabled || status === "active" || status === "online");
  }).length,
);

const healthyRate = computed(() => {
  const total = envList.value.length;
  if (!total) return 0;
  const healthy = envList.value.filter((item) => {
    const text = String(
      item?.health_status || item?.status || item?.connectivity || item?.validation_status || "",
    ).toLowerCase();
    return (
      item?.healthy === true ||
      item?.is_healthy === true ||
      text === "healthy" ||
      text === "ok" ||
      text === "online" ||
      text === "pass"
    );
  }).length;
  return Math.round((healthy / total) * 100);
});

const lastCheckInText = computed(() => {
  const times = envList.value
    .map((item) => item?.last_check_at || item?.last_check_in || item?.updated_at || item?.created_at)
    .filter(Boolean)
    .map((v) => new Date(v))
    .filter((d) => !Number.isNaN(d.getTime()))
    .sort((a, b) => b.getTime() - a.getTime());
  if (!times.length) return "未记录";
  const d = times[0];
  const mm = `${d.getMonth() + 1}`.padStart(2, "0");
  const dd = `${d.getDate()}`.padStart(2, "0");
  const hh = `${d.getHours()}`.padStart(2, "0");
  const mi = `${d.getMinutes()}`.padStart(2, "0");
  return `${mm}-${dd} ${hh}:${mi}`;
});

const statCards = computed(() => [
  {
    key: "total",
    label: "Total Environments",
    value: String(totalEnvironments.value),
    sub: "注册环境总数",
    barWidth: `${Math.min(100, Math.max(18, totalEnvironments.value * 14))}%`,
    barColor: "linear-gradient(90deg, #00d8ff, #3b8cff)",
    icon: DataAnalysis,
  },
  {
    key: "active",
    label: "Active Nodes",
    value: String(activeNodes.value),
    sub: `${totalEnvironments.value ? Math.round((activeNodes.value / totalEnvironments.value) * 100) : 0}% 在线占比`,
    barWidth: `${totalEnvironments.value ? Math.max(12, Math.round((activeNodes.value / totalEnvironments.value) * 100)) : 12}%`,
    barColor: "linear-gradient(90deg, #00f5ff, #00d8ff, #a855f7)",
    icon: SwitchButton,
  },
  {
    key: "healthy",
    label: "Healthy Status",
    value: `${healthyRate.value}%`,
    sub: "连通性健康率",
    barWidth: `${Math.max(10, healthyRate.value)}%`,
    barColor: "linear-gradient(90deg, #22d3ee, #818cf8, #c026fc)",
    icon: Opportunity,
  },
  {
    key: "lastCheck",
    label: "Last Check-in",
    value: lastCheckInText.value,
    sub: "最近一次环境状态写入",
    barWidth: "72%",
    barColor: "linear-gradient(90deg, #67e8f9, #a78bfa)",
    icon: Clock,
  },
]);

function notifySuccess(title, message, duration = 3200) {
  ElNotification.success({ title, message, duration });
}

function notifyError(title, message, duration = 4200) {
  ElNotification.error({ title, message, duration });
}

function isRowValidating(id) {
  return validatingIds.value.has(id);
}

function startValidating(id) {
  validatingIds.value = new Set(validatingIds.value).add(id);
}

function stopValidating(id) {
  const next = new Set(validatingIds.value);
  next.delete(id);
  validatingIds.value = next;
}

function envTableActions(row) {
  return [
    { key: "edit", tooltip: "编辑环境", icon: Edit, type: "primary" },
    {
      key: "validate",
      tooltip: "连通性校验",
      icon: Connection,
      type: "success",
      loading: isRowValidating(row.id),
    },
    { key: "delete", tooltip: "删除环境", icon: Delete, type: "danger" },
  ];
}

function handleEnvTableAction(action, row) {
  if (action === "edit") openEditDialog(row);
  else if (action === "validate") onValidate(row);
  else if (action === "delete") onDelete(row);
}

function resetForm() {
  form.value = {
    name: "",
    env_type: "test",
    base_url: "",
    health_check_path: "",
    db_config: {},
    description: "",
  };
  dbConfigText.value = "{}";
  editingId.value = null;
}

async function fetchEnvironments() {
  loading.value = true;
  try {
    const { data } = await getEnvironments({ page_size: 200 });
    envList.value = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
  } catch (error) {
    notifyError("加载失败", error?.response?.data?.msg || "加载环境列表失败");
  } finally {
    loading.value = false;
  }
}

function openCreateDialog() {
  isEdit.value = false;
  resetForm();
  dialogVisible.value = true;
}

function openEditDialog(row) {
  isEdit.value = true;
  editingId.value = row.id;
  form.value = {
    name: row.name || "",
    env_type: row.env_type || "test",
    base_url: row.base_url || "",
    health_check_path: row.health_check_path || "",
    db_config: row.db_config || {},
    description: row.description || "",
  };
  dbConfigText.value = JSON.stringify(row.db_config || {}, null, 2);
  dialogVisible.value = true;
}

async function onSubmit() {
  await formRef.value.validate();
  saving.value = true;
  try {
    let dbConfig = {};
    try {
      dbConfig = JSON.parse(dbConfigText.value || "{}");
    } catch {
      notifyError("保存失败", "DB 配置 JSON 格式不正确");
      return;
    }
    const payload = { ...form.value, db_config: dbConfig };
    if (isEdit.value && editingId.value) {
      await updateEnvironment(editingId.value, payload);
      notifySuccess("保存成功", "环境已更新");
    } else {
      await createEnvironment(payload);
      notifySuccess("创建成功", "环境已创建");
    }
    dialogVisible.value = false;
    await fetchEnvironments();
    window.dispatchEvent(new Event("app:environments-updated"));
  } catch (error) {
    notifyError("保存失败", error?.response?.data?.msg || "保存环境失败");
  } finally {
    saving.value = false;
  }
}

async function onDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除环境「${row.name}」吗？`, "删除确认", {
      type: "warning",
    });
    await deleteEnvironment(row.id);
    notifySuccess("删除成功", "环境已删除");
    await fetchEnvironments();
    window.dispatchEvent(new Event("app:environments-updated"));
  } catch (error) {
    if (error !== "cancel" && error !== "close") {
      notifyError("删除失败", error?.response?.data?.msg || "删除失败");
    }
  }
}

function formatValidateSummary(data) {
  if (!data) return "";
  const lines = [];
  const http = data.http;
  if (http) {
    if (http.url) {
      lines.push(`探测地址：${http.url}`);
    }
    if (http.ok) {
      lines.push(`HTTP：可达（状态码 ${http.status_code ?? "—"}）`);
    } else if (http.error) {
      lines.push(`HTTP：不可达 — ${http.error}`);
    }
  }
  const db = data.db;
  if (db && (db.host || db.port || db.error)) {
    if (db.ok) {
      lines.push(`数据库 TCP：${db.host}:${db.port} 可达`);
    } else {
      lines.push(`数据库：未通过 — ${db.error || "未知原因"}`);
    }
  }
  return lines.length ? lines.join("\n") : JSON.stringify(data);
}

async function onValidate(row) {
  if (!row?.id || isRowValidating(row.id)) return;
  startValidating(row.id);
  try {
    const { data } = await validateEnvironment(row.id, { timeout: 5 });
    if (data?.ok) {
      const detail = formatValidateSummary(data);
      notifySuccess("连通性校验通过", detail || "HTTP / 已配置项检查均正常", 4500);
    } else {
      const detail = formatValidateSummary(data);
      ElNotification.warning({
        title: "连通性未完全通过",
        message: detail,
        duration: 8000,
      });
    }
  } catch (error) {
    notifyError("校验失败", error?.response?.data?.msg || "环境校验失败");
  } finally {
    stopValidating(row.id);
  }
}

onMounted(fetchEnvironments);
</script>

<style scoped>
.env-management-page {
  min-height: 100%;
  padding-inline: 8px;
}

.env-content-shell {
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
}

.env-stat-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 14px;
}

.env-stat-card {
  border-radius: 14px;
  border: 1px solid rgba(34, 211, 238, 0.2);
  background: rgba(15, 23, 42, 0.5);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  padding: 14px 16px;
  transition:
    transform 0.25s ease,
    box-shadow 0.25s ease,
    border-color 0.25s ease;
}

.env-stat-card:hover {
  transform: translateY(-2px);
  border-color: rgba(34, 211, 238, 0.42);
  box-shadow:
    0 10px 30px rgba(2, 6, 23, 0.42),
    0 0 22px rgba(56, 189, 248, 0.16);
}

.env-stat-card__head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.env-stat-card__icon {
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: #67e8f9;
  background: linear-gradient(135deg, rgba(0, 216, 255, 0.16), rgba(168, 85, 247, 0.18));
  box-shadow: 0 0 16px rgba(34, 211, 238, 0.2);
}

.env-stat-card__label {
  font-size: 12px;
  color: #94a3b8;
  letter-spacing: 0.02em;
}

.tech-metric {
  margin-top: 8px;
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
  font-size: 28px;
  font-weight: 800;
  line-height: 1.12;
  letter-spacing: 0.03em;
  background: linear-gradient(105deg, #a5f3fc 0%, #00d8ff 32%, #22d3ee 56%, #a78bfa 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
  filter:
    drop-shadow(0 0 1px rgba(0, 216, 255, 0.9))
    drop-shadow(0 0 10px rgba(0, 216, 255, 0.42))
    drop-shadow(0 0 20px rgba(168, 85, 247, 0.2));
}

.env-stat-card__sub {
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
}

.env-stat-card__bar {
  margin-top: 10px;
  height: 6px;
  border-radius: 999px;
  overflow: hidden;
  border: 1px solid rgba(0, 216, 255, 0.2);
  background: rgba(8, 12, 22, 0.78);
}

.env-stat-card__bar-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  transition: width 0.45s ease;
  box-shadow:
    0 0 10px rgba(0, 216, 255, 0.45),
    0 0 14px rgba(168, 85, 247, 0.22);
}

.env-cyber-card {
  border-radius: 16px;
  border: 1px solid rgba(34, 211, 238, 0.2);
  background: rgba(15, 23, 42, 0.58);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow:
    0 14px 40px rgba(2, 6, 23, 0.45),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.env-toolbar-row {
  margin-bottom: 12px;
}

.env-toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}


:deep(.env-primary-btn.el-button--primary) {
  border-color: rgba(34, 211, 238, 0.42);
  color: #e0f2fe;
  background: linear-gradient(120deg, #00d8ff 0%, #3b82f6 52%, #a855f7 100%);
  box-shadow:
    0 0 0 1px rgba(34, 211, 238, 0.18),
    0 0 18px rgba(56, 189, 248, 0.25),
    0 0 26px rgba(168, 85, 247, 0.2);
}

:deep(.env-primary-btn.el-button--primary:hover) {
  filter: brightness(1.08);
  border-color: rgba(34, 211, 238, 0.58);
}

:deep(.env-data-table.el-table) {
  --el-table-border-color: rgba(148, 163, 184, 0.18);
  --el-table-row-hover-bg-color: rgba(34, 211, 238, 0.08);
  --el-table-header-bg-color: rgba(20, 29, 52, 0.92);
  --el-table-tr-bg-color: rgba(15, 23, 42, 0.45);
  --el-table-bg-color: transparent;
  border-radius: 12px;
  overflow: hidden;
}

:deep(.env-data-table .el-table__header-wrapper th.el-table__cell) {
  color: #dbeafe;
  background: linear-gradient(120deg, rgba(0, 216, 255, 0.18), rgba(168, 85, 247, 0.18));
}

@media (max-width: 1200px) {
  .env-stat-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 680px) {
  .env-stat-row {
    grid-template-columns: 1fr;
  }
}
</style>
