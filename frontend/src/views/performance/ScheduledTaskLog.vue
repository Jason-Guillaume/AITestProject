<template>
  <div class="cyber-page admin-list-page scheduled-task-log-page">
    <el-card class="admin-list-card" shadow="never">
      <div class="admin-toolbar-row">
        <div class="admin-toolbar-row__left">
          <el-select
            v-model="filters.scheduled_task"
            clearable
            filterable
            placeholder="按任务筛选"
            style="width: 260px"
          >
            <el-option
              v-for="item in taskOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
          <el-select
            v-model="filters.status"
            clearable
            placeholder="按状态筛选"
            style="width: 160px"
          >
            <el-option label="执行中" value="running" />
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failed" />
            <el-option label="部分成功" value="partial" />
          </el-select>
          <el-input
            v-model="filters.message"
            clearable
            placeholder="按失败原因/摘要关键字"
            style="width: 220px"
            @keyup.enter="onSearch"
          />
          <el-button type="primary" :loading="loading" @click="onSearch">查询</el-button>
          <el-button :disabled="loading" @click="onReset">重置</el-button>
          <el-button type="success" plain :disabled="rows.length === 0" @click="exportCurrentRowsJson">
            导出当前页 JSON
          </el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe class="admin-data-table">
        <el-table-column prop="id" label="日志ID" width="90" align="center" />
        <el-table-column prop="scheduled_task" label="任务ID" width="100" align="center" />
        <el-table-column prop="trigger_time" label="触发时间" min-width="170" />
        <el-table-column prop="start_time" label="开始时间" min-width="170" />
        <el-table-column prop="end_time" label="结束时间" min-width="170" />
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" effect="dark">
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="执行摘要" min-width="220" show-overflow-tooltip />
        <el-table-column label="明细" width="100" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="pagination.page"
          :page-size="pagination.pageSize"
          :total="pagination.total"
          layout="total, prev, pager, next, jumper"
          @current-change="fetchLogs"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="detailDialogVisible"
      title="执行明细"
      width="720px"
      class="cyber-dialog-dark"
      destroy-on-close
    >
      <pre class="detail-json-pre">{{ detailJsonText }}</pre>
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { getScheduledTaskLogs, getScheduledTasks } from "@/api/scheduledTask";

const loading = ref(false);
const rows = ref([]);
const taskOptions = ref([]);
const detailDialogVisible = ref(false);
const detailJsonText = ref("{}");
const filters = ref({
  scheduled_task: null,
  status: "",
  message: "",
});
const pagination = ref({
  page: 1,
  pageSize: 10,
  total: 0,
});

function statusText(status) {
  return {
    running: "执行中",
    success: "成功",
    failed: "失败",
    partial: "部分成功",
  }[status] || status;
}

function statusTagType(status) {
  return {
    running: "warning",
    success: "success",
    failed: "danger",
    partial: "info",
  }[status] || "info";
}

async function fetchTaskOptions() {
  try {
    const { data } = await getScheduledTasks({ page_size: 200 });
    taskOptions.value = Array.isArray(data?.results)
      ? data.results
      : Array.isArray(data)
        ? data
        : [];
  } catch {
    taskOptions.value = [];
  }
}

async function fetchLogs() {
  loading.value = true;
  try {
    const params = {
      page: pagination.value.page,
      page_size: pagination.value.pageSize,
    };
    if (filters.value.scheduled_task) {
      params.scheduled_task = filters.value.scheduled_task;
    }
    if (filters.value.status) {
      params.status = filters.value.status;
    }
    if (filters.value.message) {
      params.message = filters.value.message;
    }
    const { data } = await getScheduledTaskLogs(params);
    rows.value = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
    pagination.value.total = Number(data?.count || rows.value.length);
  } catch (error) {
    ElMessage.error(error?.response?.data?.msg || "加载调度日志失败");
  } finally {
    loading.value = false;
  }
}

async function onSearch() {
  pagination.value.page = 1;
  await fetchLogs();
}

async function onReset() {
  filters.value.scheduled_task = null;
  filters.value.status = "";
  filters.value.message = "";
  pagination.value.page = 1;
  await fetchLogs();
}

function openDetail(row) {
  try {
    detailJsonText.value = JSON.stringify(row?.detail || {}, null, 2);
  } catch {
    detailJsonText.value = String(row?.detail || "{}");
  }
  detailDialogVisible.value = true;
}

function exportCurrentRowsJson() {
  const payload = {
    exported_at: new Date().toISOString(),
    filters: { ...filters.value },
    count: rows.value.length,
    rows: rows.value,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const ts = new Date().toISOString().replace(/[:.]/g, "-");
  a.href = url;
  a.download = `scheduled-task-logs-${ts}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

onMounted(async () => {
  await fetchTaskOptions();
  await fetchLogs();
});
</script>

<style scoped>
.scheduled-task-log-page {
  min-height: 100%;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.detail-json-pre {
  margin: 0;
  max-height: 420px;
  overflow: auto;
  padding: 12px;
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.24);
  color: rgba(226, 232, 240, 0.94);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  line-height: 1.55;
}
</style>
