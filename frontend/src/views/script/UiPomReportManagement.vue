<template>
  <div class="pom-report-page">
    <div class="page-header">
      <h1 class="title">
        UI / POM 测试报告
      </h1>
      <p class="subtitle">
        Web UI 脚本每次执行结束后，系统会在工作空间内扫描 HTML 报告并归档到此；支持预览与下载。
      </p>
    </div>

    <el-card
      shadow="never"
      class="filter-card"
    >
      <el-form
        :inline="true"
        @submit.prevent="loadReports"
      >
        <el-form-item label="关键词">
          <el-input
            v-model="filters.search"
            clearable
            placeholder="标题或路径"
            style="width: 220px"
            @clear="loadReports"
          />
        </el-form-item>
        <el-form-item label="脚本 ID">
          <el-input
            v-model="filters.script_id"
            clearable
            placeholder="可选"
            style="width: 140px"
            @clear="loadReports"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            @click="loadReports"
          >
            查询
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card
      shadow="never"
      class="table-card"
    >
      <el-table
        v-loading="loading"
        :data="rows"
        stripe
        empty-text="暂无报告"
      >
        <el-table-column
          prop="title"
          label="标题"
          min-width="220"
          show-overflow-tooltip
        />
        <el-table-column
          prop="script_name"
          label="脚本"
          width="160"
          show-overflow-tooltip
        />
        <el-table-column
          prop="execution_id_str"
          label="执行标识"
          width="180"
          show-overflow-tooltip
        />
        <el-table-column
          prop="execution_status"
          label="执行状态"
          width="100"
        />
        <el-table-column
          prop="source_relative_path"
          label="来源路径"
          min-width="200"
          show-overflow-tooltip
        />
        <el-table-column
          label="大小"
          width="100"
        >
          <template #default="{ row }">
            {{ formatSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="created_at"
          label="归档时间"
          width="180"
        />
        <el-table-column
          label="操作"
          width="200"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button
              type="primary"
              link
              @click="openPreview(row)"
            >
              预览
            </el-button>
            <el-button
              type="primary"
              link
              @click="downloadReport(row)"
            >
              下载
            </el-button>
            <el-button
              type="danger"
              link
              @click="removeReport(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="previewVisible"
      title="报告预览"
      width="90%"
      top="4vh"
      destroy-on-close
      @closed="revokePreview"
    >
      <iframe
        v-if="previewUrl"
        class="preview-frame"
        :src="previewUrl"
        title="preview"
      />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import request from "@/utils/request";

interface PomReportRow {
  id: number;
  title: string;
  script: number;
  script_name: string;
  execution: number;
  execution_id_str: string;
  execution_status: string;
  source_relative_path: string;
  file_size: number;
  file_url: string | null;
  created_at: string;
}

const loading = ref(false);
const rows = ref<PomReportRow[]>([]);
const filters = reactive({
  search: "",
  script_id: "",
});

const previewVisible = ref(false);
const previewUrl = ref<string | null>(null);

function formatSize(n: number | null | undefined) {
  if (n == null || n <= 0) return "-";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(2)} MB`;
}

async function loadReports() {
  loading.value = true;
  try {
    const params: Record<string, string> = {};
    if (filters.search.trim()) params.search = filters.search.trim();
    if (filters.script_id.trim()) params.script_id = filters.script_id.trim();
    const { data } = await request.get("/assistant/ui-pom-reports/", { params });
    rows.value = Array.isArray(data) ? data : data?.results || [];
  } catch (e: unknown) {
    console.error(e);
    ElMessage.error("加载报告列表失败");
    rows.value = [];
  } finally {
    loading.value = false;
  }
}

let previewObjectUrl: string | null = null;

async function openPreview(row: PomReportRow) {
  try {
    const res = await request.get(`/assistant/ui-pom-reports/${row.id}/preview/`, {
      responseType: "blob",
    });
    if (previewObjectUrl) {
      URL.revokeObjectURL(previewObjectUrl);
      previewObjectUrl = null;
    }
    previewObjectUrl = URL.createObjectURL(res.data);
    previewUrl.value = previewObjectUrl;
    previewVisible.value = true;
  } catch {
    ElMessage.error("预览失败");
  }
}

function revokePreview() {
  if (previewObjectUrl) {
    URL.revokeObjectURL(previewObjectUrl);
    previewObjectUrl = null;
  }
  previewUrl.value = null;
}

async function downloadReport(row: PomReportRow) {
  try {
    const res = await request.get(`/assistant/ui-pom-reports/${row.id}/download/`, {
      responseType: "blob",
    });
    const blob = res.data as Blob;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${row.title.replace(/[/\\?%*:|"<>]/g, "_")}.html`;
    a.click();
    URL.revokeObjectURL(url);
    ElMessage.success("已开始下载");
  } catch {
    ElMessage.error("下载失败");
  }
}

async function removeReport(row: PomReportRow) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.title}」？`, "删除报告", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    });
    await request.delete(`/assistant/ui-pom-reports/${row.id}/`);
    ElMessage.success("已删除");
    await loadReports();
  } catch (e: unknown) {
    if (e !== "cancel") ElMessage.error("删除失败");
  }
}

onMounted(() => {
  loadReports();
});
</script>

<style scoped>
.pom-report-page {
  padding: 24px 28px 40px;
  max-width: 1400px;
  margin: 0 auto;
}
.page-header {
  margin-bottom: 20px;
}
.title {
  font-size: 22px;
  font-weight: 600;
  margin: 0 0 8px;
  color: var(--el-text-color-primary);
}
.subtitle {
  margin: 0;
  font-size: 14px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
}
.filter-card,
.table-card {
  margin-bottom: 16px;
}
.preview-frame {
  width: 100%;
  height: 78vh;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
}
</style>
