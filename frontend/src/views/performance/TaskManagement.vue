<template>
  <div class="h-screen w-full flex bg-gray-100">
    <aside class="w-64 bg-slate-900 text-slate-200 flex flex-col">
      <div class="h-16 flex items-center px-6 border-b border-slate-800">
        <div class="text-lg font-semibold tracking-wide text-white">AI测试平台</div>
      </div>

      <el-menu
        :default-active="activeMenu"
        class="flex-1 border-none bg-slate-900 text-slate-200"
        background-color="#0f172a"
        text-color="#cbd5e1"
        active-text-color="#60a5fa"
      >
        <el-menu-item index="home">首页</el-menu-item>
        <el-menu-item index="tools">测试工具</el-menu-item>
        <el-menu-item index="api-auto">接口自动化</el-menu-item>
        <el-menu-item index="web-auto">Web自动化</el-menu-item>
        <el-menu-item index="app-auto">App自动化</el-menu-item>
        <el-sub-menu index="perf">
          <template #title>性能测试</template>
          <el-menu-item index="perf-task-management">任务管理</el-menu-item>
        </el-sub-menu>
        <el-menu-item index="mock-service">Mock服务</el-menu-item>
        <el-menu-item index="openclaw">OpenClaw AI助手</el-menu-item>
        <el-menu-item index="settings">配置中心</el-menu-item>
      </el-menu>
    </aside>

    <div class="flex-1 flex flex-col overflow-hidden">
      <header class="h-16 bg-white border-b border-gray-200 px-6 flex items-center justify-between">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item>性能测试</el-breadcrumb-item>
          <el-breadcrumb-item>任务管理</el-breadcrumb-item>
        </el-breadcrumb>

        <el-dropdown>
          <div class="flex items-center gap-2 cursor-pointer">
            <el-avatar :size="32">U</el-avatar>
            <span class="text-sm text-gray-700">管理员</span>
            <el-icon><arrow-down /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item>个人中心</el-dropdown-item>
              <el-dropdown-item>修改密码</el-dropdown-item>
              <el-dropdown-item divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </header>

      <main class="flex-1 overflow-auto p-6">
        <div class="bg-white rounded-lg border border-gray-200 p-4">
          <el-form :inline="true" :model="searchForm" class="mb-4">
            <el-form-item label="任务名称">
              <el-input v-model="searchForm.name" clearable placeholder="请输入任务名称" class="!w-52" />
            </el-form-item>
            <el-form-item label="任务状态">
              <el-select v-model="searchForm.status" clearable placeholder="请选择状态" class="!w-44">
                <el-option label="全部" value="" />
                <el-option label="运行中" value="running" />
                <el-option label="已完成" value="completed" />
                <el-option label="失败" value="failed" />
                <el-option label="待执行" value="pending" />
              </el-select>
            </el-form-item>
            <el-form-item label="执行人">
              <el-input v-model="searchForm.executor" clearable placeholder="请输入执行人" class="!w-44" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="loading" @click="handleSearch">查询</el-button>
              <el-button :disabled="loading" @click="handleReset">重置</el-button>
            </el-form-item>
          </el-form>

          <div class="mb-4 perf-task-toolbar">
            <el-button type="primary" @click="openCreateDialog">新建任务</el-button>
            <el-button
              type="danger"
              plain
              :disabled="selectedTaskIds.length === 0"
              :loading="batchDeleting"
              @click="batchDeleteSelected"
            >
              批量删除（{{ selectedTaskIds.length }}）
            </el-button>
            <el-button
              type="warning"
              plain
              :disabled="selectedTaskIds.length === 0"
              @click="openBatchUpdateStatus"
            >
              批量修改状态
            </el-button>
            <el-button
              type="success"
              plain
              :disabled="selectedTaskIds.length === 0"
              :loading="batchCopying"
              @click="batchCopySelected"
            >
              批量复制
            </el-button>
            <el-button @click="toEnvironmentManagement">环境管理</el-button>
            <CurrentEnvironmentSelect :show-label="true" compact />
            <el-button type="warning" plain @click="toLoadTestMonitor">k6 压测看板</el-button>
            <el-button type="warning" plain @click="toK6Sessions">k6 会话列表</el-button>
            <el-button type="success" plain @click="toScheduledTaskCreate">新建定时任务</el-button>
            <el-button type="success" plain @click="toScheduledTaskList">定时任务列表</el-button>
            <el-button type="info" plain @click="toScheduledTaskLogs">调度日志</el-button>
          </div>

          <el-table
            v-loading="loading"
            :data="tableData"
            stripe
            border
            class="w-full perf-task-table"
            @selection-change="onSelectionChange"
          >
            <el-table-column type="selection" width="44" fixed="left" />
            <el-table-column prop="task_id" label="任务ID" width="120" align="left" show-overflow-tooltip />
            <el-table-column prop="task_name" label="任务名称" min-width="180" align="left" show-overflow-tooltip />
            <el-table-column prop="scenario" label="测试场景" min-width="180" align="center">
              <template #default="{ row }">
                {{ scenarioLabel(row.scenario) }}
              </template>
            </el-table-column>
            <el-table-column prop="concurrency" label="并发数" width="96" align="center" />
            <el-table-column prop="duration" label="持续时间" width="112" align="center" />
            <el-table-column label="状态" width="120" align="center">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)" effect="light">{{ statusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="executor" label="执行人" width="108" align="center" show-overflow-tooltip />
            <el-table-column prop="created_at" label="创建时间" width="184" align="center" />
            <el-table-column label="操作" width="200" fixed="right" align="center">
              <template #default="{ row }">
                <TableActionGroup :row="row" :actions="taskTableActions" @action="handleTaskTableAction" />
              </template>
            </el-table-column>
          </el-table>

          <div class="mt-4 flex justify-end">
            <el-pagination
              v-model:current-page="pagination.page"
              v-model:page-size="pagination.pageSize"
              :total="pagination.total"
              :page-sizes="[5, 10, 20, 50]"
              layout="total, sizes, prev, pager, next, jumper"
              @current-change="fetchTasks"
              @size-change="handleSizeChange"
            />
          </div>
        </div>
      </main>
    </div>

    <el-dialog v-model="createDialogVisible" title="新建性能任务" width="520px" destroy-on-close>
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="90px">
        <el-form-item label="任务名称" prop="task_name">
          <el-input v-model="createForm.task_name" placeholder="请输入任务名称" />
        </el-form-item>
        <el-form-item label="测试场景" prop="scenario">
          <el-select v-model="createForm.scenario" placeholder="请选择场景" class="w-full">
            <el-option label="JMeter" value="jmeter" />
            <el-option label="Locust" value="locust" />
          </el-select>
        </el-form-item>
        <el-form-item label="并发数" prop="concurrency">
          <el-input-number v-model="createForm.concurrency" :min="1" :max="100000" class="!w-full" />
        </el-form-item>
        <el-form-item label="持续时间" prop="duration">
          <el-input v-model="createForm.duration" placeholder="例如: 30s / 10m / 2h" />
        </el-form-item>
        <el-form-item label="执行人" prop="executor">
          <el-input v-model="createForm.executor" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="submitCreate">确定</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailDrawerVisible" title="任务详情" size="420px">
      <el-descriptions :column="1" border v-if="detailTask">
        <el-descriptions-item label="任务ID">{{ detailTask.task_id }}</el-descriptions-item>
        <el-descriptions-item label="任务名称">{{ detailTask.task_name }}</el-descriptions-item>
        <el-descriptions-item label="测试场景">{{ scenarioLabel(detailTask.scenario) }}</el-descriptions-item>
        <el-descriptions-item label="并发数">{{ detailTask.concurrency }}</el-descriptions-item>
        <el-descriptions-item label="持续时间">{{ detailTask.duration }}</el-descriptions-item>
        <el-descriptions-item label="执行人">{{ detailTask.executor || "-" }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusTagType(detailTask.status)" effect="light">
            {{ statusText(detailTask.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ detailTask.created_at || "-" }}</el-descriptions-item>
      </el-descriptions>
    </el-drawer>

    <el-dialog v-model="batchUpdateVisible" title="批量修改任务状态" width="420px" destroy-on-close>
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        title="将对已选任务应用同一状态更新；若某些记录无权限，会被跳过。"
        class="mb-3"
      />
      <el-form label-width="110px">
        <el-form-item label="目标状态">
          <el-select v-model="batchStatus" placeholder="请选择" class="w-full">
            <el-option label="待执行" value="pending" />
            <el-option label="运行中" value="running" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchUpdateVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="batchUpdating"
          :disabled="selectedTaskIds.length === 0 || !batchStatus"
          @click="submitBatchUpdateStatus"
        >
          应用到 {{ selectedTaskIds.length }} 条
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ArrowDown, Delete, VideoPlay, View } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import CurrentEnvironmentSelect from "@/components/CurrentEnvironmentSelect.vue";
import TableActionGroup from "@/components/common/TableActionGroup.vue";
import {
  batchDeletePerfTasks,
  batchCopyPerfTasks,
  batchUpdatePerfTasks,
  createPerfTask,
  deletePerfTask,
  getPerfTasks,
  runPerfTask,
} from "@/api/perfTask";

const activeMenu = ref("perf-task-management");
const router = useRouter();
const loading = ref(false);
const createLoading = ref(false);
const createDialogVisible = ref(false);
const createFormRef = ref();
const detailDrawerVisible = ref(false);
const detailTask = ref(null);

const searchForm = ref({ name: "", status: "", executor: "" });
const pagination = ref({ page: 1, pageSize: 5, total: 0 });
const tableData = ref([]);
const selectedTaskIds = ref([]);
const batchDeleting = ref(false);
const batchUpdateVisible = ref(false);
const batchUpdating = ref(false);
const batchStatus = ref("");
const batchCopying = ref(false);

const createForm = ref({
  task_name: "",
  scenario: "jmeter",
  concurrency: 100,
  duration: "10m",
  status: "pending",
  executor: "",
});

const createRules = {
  task_name: [{ required: true, message: "请输入任务名称", trigger: "blur" }],
  scenario: [{ required: true, message: "请选择测试场景", trigger: "change" }],
  concurrency: [{ required: true, type: "number", message: "请输入并发数", trigger: "change" }],
  duration: [
    { required: true, message: "请输入持续时间", trigger: "blur" },
    {
      pattern: /^\d+[smh]$/,
      message: "持续时间格式应为 30s/10m/2h",
      trigger: "blur",
    },
  ],
};

const taskTableActions = [
  { key: "view", tooltip: "查看任务", icon: View, type: "primary" },
  { key: "run", tooltip: "执行任务", icon: VideoPlay, type: "success" },
  { key: "delete", tooltip: "删除任务", icon: Delete, type: "danger" },
];

function handleTaskTableAction(action, row) {
  if (action === "view") handleView(row);
  else if (action === "run") handleRun(row);
  else if (action === "delete") handleDelete(row);
}

async function fetchTasks() {
  loading.value = true;
  try {
    const params = {
      page: pagination.value.page,
      page_size: pagination.value.pageSize,
      name: searchForm.value.name || undefined,
      status: searchForm.value.status || undefined,
      executor: searchForm.value.executor || undefined,
    };
    const { data } = await getPerfTasks(params);
    tableData.value = Array.isArray(data.results) ? data.results : [];
    pagination.value.total = Number(data.count || 0);
  } catch (error) {
    const st = error?.response?.status;
    // 401 由 request 拦截器处理；5xx 已提示「服务异常」，避免双条红字造成「整页崩坏」观感
    if (st === 401) return;
    if (st != null && st >= 500) {
      /* 仅控制台记录，便于排查后端 */
    } else {
      ElMessage.error(
        error?.response?.data?.detail || error?.response?.data?.msg || "获取任务列表失败"
      );
    }
    // eslint-disable-next-line no-console
    console.error(error);
  } finally {
    loading.value = false;
  }
}

async function handleSearch() {
  pagination.value.page = 1;
  await fetchTasks();
}

async function handleReset() {
  searchForm.value = { name: "", status: "", executor: "" };
  pagination.value.page = 1;
  await fetchTasks();
}

async function handleSizeChange(size) {
  pagination.value.pageSize = size;
  pagination.value.page = 1;
  await fetchTasks();
}

function handleView(row) {
  detailTask.value = row;
  detailDrawerVisible.value = true;
}

async function handleRun(row) {
  try {
    await runPerfTask(row.task_id);
    ElMessage.success(`已触发执行：${row.task_id}`);
    await fetchTasks();
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || `执行失败：${row.task_id}`);
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除任务 ${row.task_id} 吗？`, "提示", { type: "warning" });
    await deletePerfTask(row.task_id);
    ElMessage.success("删除成功");
    if (tableData.value.length === 1 && pagination.value.page > 1) {
      pagination.value.page -= 1;
    }
    await fetchTasks();
  } catch (error) {
    if (error !== "cancel" && error !== "close") {
      ElMessage.error("删除失败");
    }
  }
}

function openCreateDialog() {
  createDialogVisible.value = true;
}

async function submitCreate() {
  if (!createFormRef.value) return;
  await createFormRef.value.validate(async (valid) => {
    if (!valid) return;
    createLoading.value = true;
    try {
      await createPerfTask(createForm.value);
      ElMessage.success("任务创建成功");
      createDialogVisible.value = false;
      createForm.value = {
        task_name: "",
        scenario: "jmeter",
        concurrency: 100,
        duration: "10m",
        status: "pending",
        executor: "",
      };
      pagination.value.page = 1;
      await fetchTasks();
    } catch (error) {
      ElMessage.error(error?.response?.data?.detail || "创建失败");
    } finally {
      createLoading.value = false;
    }
  });
}

function statusText(status) {
  return {
    pending: "待执行",
    running: "运行中",
    completed: "已完成",
    failed: "失败",
  }[status] || "未知";
}

function statusTagType(status) {
  return {
    pending: "info",
    running: "primary",
    completed: "success",
    failed: "danger",
  }[status] || "info";
}

function scenarioLabel(scenario) {
  return {
    jmeter: "JMeter",
    locust: "Locust",
  }[scenario] || scenario;
}

function onSelectionChange(rows) {
  selectedTaskIds.value = (rows || [])
    .map((r) => r?.task_id)
    .filter((id) => typeof id === "string" && id.trim());
}

async function batchDeleteSelected() {
  if (!selectedTaskIds.value.length) return;
  try {
    await ElMessageBox.confirm(
      `确定批量删除 ${selectedTaskIds.value.length} 条性能任务？`,
      "警告",
      { type: "warning" },
    );
  } catch {
    return;
  }
  batchDeleting.value = true;
  try {
    const { data } = await batchDeletePerfTasks({ task_ids: selectedTaskIds.value });
    const deleted = Number(data?.deleted ?? data?.data?.deleted ?? 0);
    const skipped = Number(data?.skipped ?? data?.data?.skipped ?? 0);
    ElMessage.success(`删除成功：${deleted}，跳过：${skipped}`);
    selectedTaskIds.value = [];
    fetchTasks();
  } catch (err) {
    const msg =
      err?.response?.data?.msg ||
      err?.response?.data?.detail ||
      err?.message ||
      "批量删除失败";
    ElMessage.error(typeof msg === "string" ? msg : "批量删除失败");
  } finally {
    batchDeleting.value = false;
  }
}

function openBatchUpdateStatus() {
  batchStatus.value = "";
  batchUpdateVisible.value = true;
}

async function submitBatchUpdateStatus() {
  if (!selectedTaskIds.value.length || !batchStatus.value) return;
  try {
    await ElMessageBox.confirm(
      `确认将 ${selectedTaskIds.value.length} 条任务状态批量更新为「${statusText(batchStatus.value)}」？`,
      "确认",
      { type: "warning" },
    );
  } catch {
    return;
  }
  batchUpdating.value = true;
  try {
    const { data } = await batchUpdatePerfTasks({
      task_ids: selectedTaskIds.value,
      patch: { status: batchStatus.value },
    });
    const d = data?.data && typeof data.data === "object" ? data.data : data;
    const updated = Number(d?.updated ?? 0);
    const missing = Array.isArray(d?.missing_task_ids) ? d.missing_task_ids.length : 0;
    const errors = Array.isArray(d?.errors) ? d.errors.length : 0;
    if (errors) ElMessage.warning(`已更新 ${updated} 条；缺失/无权限 ${missing} 条；失败 ${errors} 条`);
    else ElMessage.success(`已更新 ${updated} 条；缺失/无权限 ${missing} 条`);
    batchUpdateVisible.value = false;
    fetchTasks();
  } catch (err) {
    const msg =
      err?.response?.data?.msg ||
      err?.response?.data?.detail ||
      err?.message ||
      "批量更新失败";
    ElMessage.error(typeof msg === "string" ? msg : "批量更新失败");
  } finally {
    batchUpdating.value = false;
  }
}

async function batchCopySelected() {
  if (!selectedTaskIds.value.length) return;
  let suffix = "（复制）";
  try {
    const r = await ElMessageBox.prompt("请输入复制后名称后缀（可留空）", "批量复制", {
      inputValue: suffix,
      confirmButtonText: "复制",
      cancelButtonText: "取消",
    });
    suffix = String(r?.value ?? "").trim() || "（复制）";
  } catch {
    return;
  }
  batchCopying.value = true;
  try {
    const { data } = await batchCopyPerfTasks({
      task_ids: selectedTaskIds.value,
      name_suffix: suffix,
    });
    const d = data?.data && typeof data.data === "object" ? data.data : data;
    const created = Number(d?.created ?? 0);
    const missing = Array.isArray(d?.missing_task_ids) ? d.missing_task_ids.length : 0;
    const errors = Array.isArray(d?.errors) ? d.errors.length : 0;
    if (errors) ElMessage.warning(`已复制 ${created} 条；缺失/无权限 ${missing} 条；失败 ${errors} 条`);
    else ElMessage.success(`已复制 ${created} 条；缺失/无权限 ${missing} 条`);
    selectedTaskIds.value = [];
    fetchTasks();
  } catch (err) {
    const msg =
      err?.response?.data?.msg ||
      err?.response?.data?.detail ||
      err?.message ||
      "批量复制失败";
    ElMessage.error(typeof msg === "string" ? msg : "批量复制失败");
  } finally {
    batchCopying.value = false;
  }
}

function toEnvironmentManagement() {
  router.push("/performance/environments");
}

function toLoadTestMonitor() {
  router.push("/performance/load-monitor");
}

function toK6Sessions() {
  router.push("/performance/k6-sessions");
}

function toScheduledTaskCreate() {
  router.push("/performance/scheduled-task");
}

function toScheduledTaskList() {
  router.push("/performance/scheduled-tasks");
}

function toScheduledTaskLogs() {
  router.push("/performance/scheduled-task-logs");
}

onMounted(fetchTasks);
</script>

<style scoped>
.perf-task-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 12px;
}

:deep(.perf-task-table td.el-table__cell),
:deep(.perf-task-table th.el-table__cell) {
  vertical-align: middle;
}

:deep(.el-menu) {
  border-right: none;
}

:deep(.el-sub-menu__title),
:deep(.el-menu-item) {
  color: #cbd5e1 !important;
}

:deep(.el-menu-item.is-active) {
  background-color: #1e293b !important;
  color: #60a5fa !important;
}
</style>
