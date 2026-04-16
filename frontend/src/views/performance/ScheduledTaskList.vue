<template>
  <div class="cyber-page admin-list-page scheduled-task-list-page">
    <el-card class="admin-list-card" shadow="never">
      <div class="admin-toolbar-row">
        <div class="admin-toolbar-row__left">
          <el-button type="primary" @click="router.push('/performance/scheduled-task')">新建定时任务</el-button>
          <el-button
            type="danger"
            plain
            :disabled="selectedIds.length === 0"
            :loading="batchDeleting"
            @click="batchDeleteSelected"
          >
            批量删除（{{ selectedIds.length }}）
          </el-button>
          <el-button
            type="warning"
            plain
            :disabled="selectedIds.length === 0"
            @click="openBatchUpdateStatus"
          >
            批量修改状态
          </el-button>
          <el-button
            type="success"
            plain
            :disabled="selectedIds.length === 0"
            :loading="batchCopying"
            @click="batchCopySelected"
          >
            批量复制
          </el-button>
        </div>
        <div class="admin-toolbar-row__right">
          <el-input
            v-model="filters.keyword"
            clearable
            placeholder="按任务名称关键字"
            class="search-input"
            @keyup.enter="onSearch"
          >
            <template #suffix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="rows"
        border
        stripe
        class="admin-data-table"
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="44" fixed="left" />
        <el-table-column prop="id" label="ID" width="90" align="center" />
        <el-table-column prop="name" label="任务名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="cron_expression" label="Cron" min-width="160" show-overflow-tooltip />
        <el-table-column label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" effect="dark">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="environment" label="环境" width="110" align="center" />
        <el-table-column prop="create_time" label="创建时间" width="184" align="center">
          <template #default="{ row }">{{ formatDate(row.create_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/performance/scheduled-task/${row.id}`)">详情</el-button>
            <el-button link type="danger" @click="delOne(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="pagination.page"
          :page-size="pagination.pageSize"
          :total="pagination.total"
          layout="total, prev, pager, next, jumper"
          @current-change="fetchList"
        />
      </div>
    </el-card>

    <el-dialog v-model="batchUpdateVisible" title="批量修改任务状态" width="420px" class="cyber-dialog-dark" destroy-on-close>
      <el-alert type="warning" :closable="false" show-icon title="将对已选任务应用同一状态更新；若某些记录无权限，会被跳过。" class="mb-3" />
      <el-form label-width="110px">
        <el-form-item label="目标状态">
          <el-select v-model="batchStatus" placeholder="请选择" class="w-full">
            <el-option label="启用" value="active" />
            <el-option label="暂停" value="paused" />
            <el-option label="禁用" value="disabled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchUpdateVisible = false">取消</el-button>
        <el-button type="primary" :loading="batchUpdating" :disabled="selectedIds.length === 0 || !batchStatus" @click="submitBatchUpdateStatus">
          应用到 {{ selectedIds.length }} 条
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { Search } from "@element-plus/icons-vue";
import {
  batchDeleteScheduledTasks,
  batchCopyScheduledTasks,
  batchUpdateScheduledTasks,
  deleteScheduledTask,
  getScheduledTasks,
} from "@/api/scheduledTask";

const router = useRouter();
const loading = ref(false);
const rows = ref([]);
const selectedIds = ref([]);
const batchDeleting = ref(false);
const batchUpdateVisible = ref(false);
const batchUpdating = ref(false);
const batchStatus = ref("");
const batchCopying = ref(false);

const filters = ref({ keyword: "" });
const pagination = ref({ page: 1, pageSize: 10, total: 0 });

function statusText(status) {
  return { active: "启用", paused: "暂停", disabled: "禁用" }[status] || status;
}

function statusTagType(status) {
  return { active: "success", paused: "warning", disabled: "info" }[status] || "info";
}

function formatDate(dt) {
  return dt ? String(dt).slice(0, 16).replace("T", " ") : "-";
}

function onSelectionChange(rowsSel) {
  selectedIds.value = (rowsSel || []).map((r) => r?.id).filter((id) => id != null);
}

async function fetchList() {
  loading.value = true;
  try {
    const { data } = await getScheduledTasks({
      page: pagination.value.page,
      page_size: pagination.value.pageSize,
    });
    const list = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
    const kw = (filters.value.keyword || "").trim();
    rows.value = kw ? list.filter((x) => String(x?.name ?? "").includes(kw)) : list;
    pagination.value.total = Number(data?.count || list.length);
  } catch (err) {
    ElMessage.error(err?.response?.data?.msg || "加载定时任务失败");
    rows.value = [];
    pagination.value.total = 0;
  } finally {
    loading.value = false;
  }
}

async function onSearch() {
  pagination.value.page = 1;
  await fetchList();
}

async function delOne(row) {
  try {
    await ElMessageBox.confirm(`确定删除「${row?.name || row?.id}」？`, "警告", { type: "warning" });
  } catch {
    return;
  }
  try {
    await deleteScheduledTask(row.id);
    ElMessage.success("删除成功");
    fetchList();
  } catch (err) {
    ElMessage.error(err?.response?.data?.msg || "删除失败");
  }
}

async function batchDeleteSelected() {
  if (!selectedIds.value.length) return;
  try {
    await ElMessageBox.confirm(`确定批量删除 ${selectedIds.value.length} 条定时任务？`, "警告", { type: "warning" });
  } catch {
    return;
  }
  batchDeleting.value = true;
  try {
    const { data } = await batchDeleteScheduledTasks({ ids: selectedIds.value });
    const deleted = Number(data?.deleted ?? data?.data?.deleted ?? 0);
    const missing = Array.isArray(data?.missing_ids) ? data.missing_ids.length : 0;
    const errors = Array.isArray(data?.errors) ? data.errors.length : 0;
    if (errors) ElMessage.warning(`已删除 ${deleted} 条；缺失/无权限 ${missing} 条；失败 ${errors} 条`);
    else ElMessage.success(`已删除 ${deleted} 条；缺失/无权限 ${missing} 条`);
    selectedIds.value = [];
    fetchList();
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || "批量删除失败";
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
  if (!selectedIds.value.length || !batchStatus.value) return;
  try {
    await ElMessageBox.confirm(
      `确认将 ${selectedIds.value.length} 条任务状态批量更新为「${statusText(batchStatus.value)}」？`,
      "确认",
      { type: "warning" },
    );
  } catch {
    return;
  }
  batchUpdating.value = true;
  try {
    const { data } = await batchUpdateScheduledTasks({
      ids: selectedIds.value,
      patch: { status: batchStatus.value },
    });
    const d = data?.data && typeof data.data === "object" ? data.data : data;
    const updated = Number(d?.updated ?? 0);
    const missing = Array.isArray(d?.missing_ids) ? d.missing_ids.length : 0;
    const errors = Array.isArray(d?.errors) ? d.errors.length : 0;
    if (errors) ElMessage.warning(`已更新 ${updated} 条；缺失/无权限 ${missing} 条；失败 ${errors} 条`);
    else ElMessage.success(`已更新 ${updated} 条；缺失/无权限 ${missing} 条`);
    batchUpdateVisible.value = false;
    fetchList();
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || "批量更新失败";
    ElMessage.error(typeof msg === "string" ? msg : "批量更新失败");
  } finally {
    batchUpdating.value = false;
  }
}

async function batchCopySelected() {
  if (!selectedIds.value.length) return;
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
    const { data } = await batchCopyScheduledTasks({ ids: selectedIds.value, name_suffix: suffix });
    const d = data?.data && typeof data.data === "object" ? data.data : data;
    const created = Number(d?.created ?? 0);
    const missing = Array.isArray(d?.missing_ids) ? d.missing_ids.length : 0;
    const errors = Array.isArray(d?.errors) ? d.errors.length : 0;
    if (errors) ElMessage.warning(`已复制 ${created} 条；缺失/无权限 ${missing} 条；失败 ${errors} 条`);
    else ElMessage.success(`已复制 ${created} 条；缺失/无权限 ${missing} 条`);
    selectedIds.value = [];
    fetchList();
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || "批量复制失败";
    ElMessage.error(typeof msg === "string" ? msg : "批量复制失败");
  } finally {
    batchCopying.value = false;
  }
}

onMounted(fetchList);
</script>

<style scoped>
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  flex-shrink: 0;
  margin-top: 12px;
}
</style>

