<template>
  <div class="page-wrap cyber-page sys-admin-page audit-events-page">
    <el-card class="sys-page-head" shadow="never">
      <div class="sys-page-head__row">
        <div>
          <h2 class="sys-page-head__title">{{ pageTitle }}</h2>
          <p class="sys-page-head__sub">{{ pageSub }}</p>
        </div>
        <div class="sys-page-head__actions">
          <el-button size="default" :loading="loading" @click="reload">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
          <el-button
            v-if="isSysMode"
            size="default"
            type="primary"
            :disabled="exporting"
            :loading="exporting"
            @click="exportCsv"
          >
            导出 CSV
          </el-button>
        </div>
      </div>
    </el-card>

    <el-card class="sys-filter-card" shadow="never">
      <div class="sys-toolbar">
        <div class="sys-toolbar__left">
          <el-date-picker
            v-if="isSysMode"
            v-model="filters.date_range"
            type="daterange"
            unlink-panels
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 260px"
            @change="handleFilterChange"
          />
          <el-input v-model="filters.action" clearable placeholder="action" style="width: 160px" @change="handleFilterChange" />
          <el-input v-model="filters.object_app" clearable placeholder="object_app" style="width: 160px" @change="handleFilterChange" />
          <el-input v-model="filters.object_model" clearable placeholder="object_model" style="width: 200px" @change="handleFilterChange" />
          <el-input v-model="filters.object_id" clearable placeholder="object_id" style="width: 200px" @change="handleFilterChange" />
        </div>
        <div class="sys-toolbar__right">
          <el-button size="default" @click="resetFilters">重置</el-button>
        </div>
      </div>
    </el-card>

    <el-card class="sys-table-card" shadow="never">
      <el-table :data="rows" v-loading="loading" class="admin-data-table sys-enterprise-table" border>
        <template #empty>
          <el-empty description="暂无审计事件" :image-size="78" />
        </template>
        <el-table-column prop="id" label="ID" width="90" align="center" />
        <el-table-column prop="create_time" label="时间" width="180" show-overflow-tooltip />
        <el-table-column prop="action" label="动作" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="info" effect="plain">{{ row.action }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="object_app" label="App" width="120" show-overflow-tooltip />
        <el-table-column prop="object_model" label="Model" width="160" show-overflow-tooltip />
        <el-table-column prop="object_id" label="Object ID" width="120" show-overflow-tooltip />
        <el-table-column prop="object_repr" label="对象" min-width="220" show-overflow-tooltip />
        <el-table-column v-if="isSysMode" prop="creator_id" label="操作人ID" width="110" align="center" />
        <el-table-column prop="request_path" label="路径" min-width="220" show-overflow-tooltip />
        <el-table-column prop="ip" label="IP" width="140" show-overflow-tooltip />
        <el-table-column v-if="isSysMode" prop="user_agent" label="UA" min-width="220" show-overflow-tooltip />
        <el-table-column label="extra" min-width="120" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="openJson('extra', row.extra)">查看</el-button>
          </template>
        </el-table-column>
        <el-table-column v-if="isSysMode" label="before" min-width="120" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="openJson('before', row.before)">查看</el-button>
          </template>
        </el-table-column>
        <el-table-column v-if="isSysMode" label="after" min-width="120" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="openJson('after', row.after)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager-row">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next, jumper"
          :page-sizes="[20, 50, 100, 200]"
          :total="total"
          v-model:current-page="page"
          v-model:page-size="pageSize"
          @current-change="load"
          @size-change="onPageSizeChange"
        />
      </div>
    </el-card>

    <el-dialog v-model="jsonDialog.visible" :title="jsonDialog.title" width="860px" destroy-on-close>
      <pre class="json-pre">{{ jsonDialog.text }}</pre>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import { downloadSysAuditExportCsv, getMyAuditEventsApi, getSysAuditEventsApi } from "@/api/audit";

const route = useRoute();
const isSysMode = computed(() => route.path === "/system/audit");

const pageTitle = computed(() => (isSysMode.value ? "系统审计" : "我的审计"));
const pageSub = computed(() =>
  isSysMode.value
    ? "查询全站敏感操作审计事件，并支持按筛选条件导出 CSV（仅系统管理员）。"
    : "查询你本人触发/产生的审计事件（只读）。"
);

const loading = ref(false);
const exporting = ref(false);

const page = ref(1);
const pageSize = ref(50);
const total = ref(0);
const rows = ref([]);

const filters = ref({
  date_range: [],
  action: "",
  object_app: "",
  object_model: "",
  object_id: "",
});

const jsonDialog = ref({ visible: false, title: "", text: "" });

function nonEmptyParams() {
  const f = filters.value;
  const p = {};
  if (String(f.action || "").trim()) p.action = String(f.action || "").trim();
  if (String(f.object_app || "").trim()) p.object_app = String(f.object_app || "").trim();
  if (String(f.object_model || "").trim()) p.object_model = String(f.object_model || "").trim();
  if (String(f.object_id || "").trim()) p.object_id = String(f.object_id || "").trim();
  if (isSysMode.value && Array.isArray(f.date_range) && f.date_range.length === 2) {
    const [s, e] = f.date_range;
    if (s) p.start_date = s;
    if (e) p.end_date = e;
  }
  return p;
}

function safeJson(v) {
  if (v == null) return "";
  if (typeof v === "string") return v;
  try {
    return JSON.stringify(v, null, 2);
  } catch {
    return String(v);
  }
}

function openJson(title, v) {
  jsonDialog.value = { visible: true, title, text: safeJson(v) || "（空）" };
}

async function load() {
  loading.value = true;
  try {
    const params = {
      page: page.value,
      page_size: pageSize.value,
      ...nonEmptyParams(),
    };
    const api = isSysMode.value ? getSysAuditEventsApi : getMyAuditEventsApi;
    const { data } = await api(params);
    if (data?.code !== 200) {
      rows.value = [];
      total.value = 0;
      ElMessage.error(data?.msg || "加载失败");
      return;
    }
    const payload = data?.data || {};
    rows.value = Array.isArray(payload.items) ? payload.items : [];
    total.value = Number(payload.total || 0) || 0;
  } catch (e) {
    rows.value = [];
    total.value = 0;
    ElMessage.error(e?.response?.data?.detail || e?.response?.data?.msg || "加载失败");
  } finally {
    loading.value = false;
  }
}

function reload() {
  page.value = 1;
  load();
}

function handleFilterChange() {
  page.value = 1;
  load();
}

function onPageSizeChange() {
  page.value = 1;
  load();
}

function resetFilters() {
  filters.value = { date_range: [], action: "", object_app: "", object_model: "", object_id: "" };
  page.value = 1;
  load();
}

async function exportCsv() {
  if (!isSysMode.value) return;
  exporting.value = true;
  try {
    const params = {
      limit: 200000,
      ...nonEmptyParams(),
    };
    await downloadSysAuditExportCsv(params);
  } catch (e) {
    ElMessage.error(e?.message || e?.response?.data?.detail || "导出失败");
  } finally {
    exporting.value = false;
  }
}

onMounted(() => {
  load();
});
</script>

<style scoped>
.pager-row {
  display: flex;
  justify-content: flex-end;
  padding: 12px 2px 0;
}

.json-pre {
  margin: 0;
  max-height: 520px;
  overflow: auto;
  font-size: 12px;
  line-height: 1.45;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
