<template>
  <div class="cyber-page admin-list-page k6-session-list-page">
    <el-card class="admin-list-card" shadow="never">
      <div class="admin-toolbar-row">
        <div class="admin-toolbar-row__left">
          <el-button type="primary" @click="router.push('/performance/load-monitor')">去压测看板</el-button>
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
            type="success"
            plain
            :disabled="selectedIds.length === 0"
            :loading="batchCopying"
            @click="batchCopySelected"
          >
            批量复制并执行
          </el-button>
        </div>
        <div class="admin-toolbar-row__right">
          <el-input v-model="filters.run_id" clearable placeholder="按 run_id 关键字" style="width: 220px" @keyup.enter="onSearch" />
          <el-select v-model="filters.status" clearable placeholder="按状态" style="width: 160px" @change="onSearch">
            <el-option label="pending" value="pending" />
            <el-option label="generating" value="generating" />
            <el-option label="running" value="running" />
            <el-option label="completed" value="completed" />
            <el-option label="failed" value="failed" />
          </el-select>
          <el-select v-model="filters.ordering" placeholder="排序" style="width: 160px; margin-left: 10px" @change="onSearch">
            <el-option label="创建时间↓" value="-create_time" />
            <el-option label="创建时间↑" value="create_time" />
            <el-option label="状态↑" value="status" />
            <el-option label="状态↓" value="-status" />
          </el-select>
          <el-date-picker
            v-model="filters.createdRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 260px; margin-left: 10px"
            @change="onSearch"
          />
          <el-checkbox v-model="filters.created_by_me" @change="onSearch" style="margin-left: 10px">
            只看我创建的
          </el-checkbox>
        </div>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe class="admin-data-table" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="44" fixed="left" />
        <el-table-column prop="id" label="ID" width="90" align="center" />
        <el-table-column prop="run_id" label="run_id" min-width="220" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="120" align="center" />
        <el-table-column prop="vus" label="vus" width="90" align="center" />
        <el-table-column prop="duration" label="duration" width="110" align="center" />
        <el-table-column prop="use_ai" label="use_ai" width="90" align="center" />
        <el-table-column prop="create_time" label="创建时间" width="184" align="center">
          <template #default="{ row }">{{ formatDate(row.create_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/performance/load-monitor?run_id=${row.run_id}`)">查看</el-button>
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
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { batchCopyK6Sessions, batchDeleteK6Sessions, getK6Sessions } from "@/api/perfK6";

const router = useRouter();
const loading = ref(false);
const rows = ref([]);
const selectedIds = ref([]);
const batchDeleting = ref(false);
const batchCopying = ref(false);
const filters = ref({
  status: "",
  run_id: "",
  created_by_me: false,
  ordering: "-create_time",
  createdRange: [],
});
const pagination = ref({ page: 1, pageSize: 10, total: 0 });

function formatDate(dt) {
  return dt ? String(dt).slice(0, 16).replace("T", " ") : "-";
}

function onSelectionChange(sel) {
  selectedIds.value = (sel || []).map((r) => r?.id).filter((id) => id != null);
}

async function fetchList() {
  loading.value = true;
  try {
    const params = {
      page: pagination.value.page,
      page_size: pagination.value.pageSize,
    };
    const st = (filters.value.status || "").trim();
    if (st) params.status = st;
    const rid = (filters.value.run_id || "").trim();
    if (rid) params.run_id = rid;
    if (filters.value.created_by_me) params.created_by_me = "1";
    const ord = (filters.value.ordering || "").trim();
    if (ord) params.ordering = ord;
    if (Array.isArray(filters.value.createdRange) && filters.value.createdRange.length === 2) {
      const [s, e] = filters.value.createdRange;
      if (s) params.created_start = s;
      if (e) params.created_end = e;
    }
    const { data } = await getK6Sessions(params);
    const list = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
    rows.value = list;
    pagination.value.total = Number(data?.count || list.length);
  } catch (err) {
    ElMessage.error(err?.response?.data?.detail || "加载 k6 会话失败");
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

async function batchDeleteSelected() {
  if (!selectedIds.value.length) return;
  try {
    await ElMessageBox.confirm(`确定批量删除 ${selectedIds.value.length} 条 k6 会话？`, "警告", { type: "warning" });
  } catch {
    return;
  }
  batchDeleting.value = true;
  try {
    const { data } = await batchDeleteK6Sessions({ ids: selectedIds.value });
    const deleted = Number(data?.deleted ?? data?.data?.deleted ?? 0);
    const skipped = Number(data?.skipped ?? data?.data?.skipped ?? 0);
    ElMessage.success(`删除成功：${deleted}，跳过：${skipped}`);
    selectedIds.value = [];
    await fetchList();
  } catch (err) {
    ElMessage.error(err?.response?.data?.detail || "批量删除失败");
  } finally {
    batchDeleting.value = false;
  }
}

async function batchCopySelected() {
  if (!selectedIds.value.length) return;
  try {
    await ElMessageBox.confirm(
      `将复制并重新执行 ${selectedIds.value.length} 条 k6 会话（会重新入队执行）。确定继续？`,
      "确认",
      { type: "warning" },
    );
  } catch {
    return;
  }
  batchCopying.value = true;
  try {
    const { data } = await batchCopyK6Sessions({ ids: selectedIds.value });
    const created = Number(data?.created ?? data?.data?.created ?? 0);
    ElMessage.success(`已创建并入队：${created} 条`);
    selectedIds.value = [];
    await fetchList();
  } catch (err) {
    ElMessage.error(err?.response?.data?.detail || "批量复制失败");
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

