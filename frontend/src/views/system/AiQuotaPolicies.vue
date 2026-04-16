<template>
  <div class="ai-quota-page">
    <div class="panel-title">AI 配额策略</div>

    <div class="toolbar">
      <el-select v-model="filters.scope_type" placeholder="范围" clearable style="width: 140px">
        <el-option label="项目" value="project" />
        <el-option label="组织" value="org" />
        <el-option label="用户" value="user" />
      </el-select>
      <el-input v-model="filters.project_id" placeholder="project_id" clearable style="width: 140px" />
      <el-input v-model="filters.org_id" placeholder="org_id" clearable style="width: 120px" />
      <el-input v-model="filters.user_id" placeholder="user_id" clearable style="width: 120px" />
      <el-button type="primary" :loading="loading" @click="load">查询</el-button>
      <el-button :disabled="loading" @click="resetFilters">重置</el-button>
      <div class="spacer" />
      <el-button type="success" @click="openCreate">新建策略</el-button>
    </div>

    <el-table :data="items" v-loading="loading" size="small" class="admin-data-table" height="560">
      <el-table-column prop="id" label="ID" width="80" align="center" />
      <el-table-column prop="scope_type" label="范围" width="110" align="center">
        <template #default="{ row }">
          <el-tag size="small" effect="dark" v-if="row.scope_type === 'project'">项目</el-tag>
          <el-tag size="small" effect="dark" type="warning" v-else-if="row.scope_type === 'org'">组织</el-tag>
          <el-tag size="small" effect="dark" type="info" v-else>用户</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="project" label="project_id" width="110" align="center" />
      <el-table-column prop="org" label="org_id" width="100" align="center" />
      <el-table-column prop="user" label="user_id" width="100" align="center" />
      <el-table-column prop="daily_requests" label="每日上限" width="110" align="center" />
      <el-table-column prop="max_concurrency" label="最大并发" width="110" align="center" />
      <el-table-column prop="concurrency_ttl_seconds" label="TTL(秒)" width="100" align="center" />
      <el-table-column prop="is_enabled" label="启用" width="80" align="center">
        <template #default="{ row }">
          <el-tag size="small" type="success" v-if="row.is_enabled">是</el-tag>
          <el-tag size="small" type="info" v-else>否</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="allowed_actions" label="actions" min-width="200">
        <template #default="{ row }">
          <span class="actions-cell">{{ formatActions(row.allowed_actions) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="notes" label="备注" min-width="140" show-overflow-tooltip />
      <el-table-column label="操作" width="180" fixed="right" align="center">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog.visible" :title="dialog.title" width="640px" destroy-on-close>
      <el-form :model="dialog.form" label-width="120px">
        <el-form-item label="范围(scope_type)">
          <el-select v-model="dialog.form.scope_type" placeholder="请选择" style="width: 220px">
            <el-option label="项目(project)" value="project" />
            <el-option label="组织(org)" value="org" />
            <el-option label="用户(user)" value="user" />
          </el-select>
        </el-form-item>
        <el-form-item label="project_id">
          <el-input v-model="dialog.form.project" placeholder="可空" />
        </el-form-item>
        <el-form-item label="org_id">
          <el-input v-model="dialog.form.org" placeholder="可空" />
        </el-form-item>
        <el-form-item label="user_id">
          <el-input v-model="dialog.form.user" placeholder="可空" />
        </el-form-item>
        <el-form-item label="每日上限">
          <el-input-number v-model="dialog.form.daily_requests" :min="0" :max="999999" />
          <span class="hint">0 表示不限制</span>
        </el-form-item>
        <el-form-item label="最大并发">
          <el-input-number v-model="dialog.form.max_concurrency" :min="0" :max="1000" />
          <span class="hint">0 表示不限制</span>
        </el-form-item>
        <el-form-item label="并发 TTL(秒)">
          <el-input-number v-model="dialog.form.concurrency_ttl_seconds" :min="10" :max="3600" />
        </el-form-item>
        <el-form-item label="actions(逗号分隔)">
          <el-input
            v-model="dialog.form.allowed_actions_text"
            placeholder="为空=对所有 action 生效；例如：knowledge_ask,security_analyze"
          />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="dialog.form.is_enabled" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="dialog.form.notes" maxlength="255" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  createAiQuotaPolicyApi,
  deleteAiQuotaPolicyApi,
  listAiQuotaPoliciesApi,
  updateAiQuotaPolicyApi,
} from "@/api/sysAiQuota";

const loading = ref(false);
const items = ref([]);

const filters = reactive({
  scope_type: "",
  project_id: "",
  org_id: "",
  user_id: "",
});

function nonEmptyParams() {
  const p = {};
  if (filters.scope_type) p.scope_type = filters.scope_type;
  if (String(filters.project_id || "").trim()) p.project_id = String(filters.project_id).trim();
  if (String(filters.org_id || "").trim()) p.org_id = String(filters.org_id).trim();
  if (String(filters.user_id || "").trim()) p.user_id = String(filters.user_id).trim();
  return p;
}

function formatActions(arr) {
  if (!Array.isArray(arr) || arr.length === 0) return "（全部）";
  return arr.join(", ");
}

async function load() {
  loading.value = true;
  try {
    const { data } = await listAiQuotaPoliciesApi({ limit: 300, ...nonEmptyParams() });
    const payload = data && typeof data === "object" && "data" in data ? data.data : data;
    items.value = Array.isArray(payload) ? payload : [];
  } catch (e) {
    ElMessage.error(e?.message || "加载失败");
    items.value = [];
  } finally {
    loading.value = false;
  }
}

function resetFilters() {
  filters.scope_type = "";
  filters.project_id = "";
  filters.org_id = "";
  filters.user_id = "";
  load();
}

const dialog = reactive({
  visible: false,
  title: "",
  saving: false,
  editingId: null,
  form: {
    scope_type: "project",
    project: "",
    org: "",
    user: "",
    daily_requests: 0,
    max_concurrency: 2,
    concurrency_ttl_seconds: 180,
    allowed_actions_text: "",
    is_enabled: true,
    notes: "",
  },
});

function openCreate() {
  dialog.title = "新建 AI 配额策略";
  dialog.editingId = null;
  dialog.form = {
    scope_type: "project",
    project: "",
    org: "",
    user: "",
    daily_requests: 0,
    max_concurrency: 2,
    concurrency_ttl_seconds: 180,
    allowed_actions_text: "",
    is_enabled: true,
    notes: "",
  };
  dialog.visible = true;
}

function openEdit(row) {
  dialog.title = "编辑 AI 配额策略";
  dialog.editingId = row.id;
  dialog.form = {
    scope_type: row.scope_type || "project",
    project: row.project ?? "",
    org: row.org ?? "",
    user: row.user ?? "",
    daily_requests: Number(row.daily_requests ?? 0) || 0,
    max_concurrency: Number(row.max_concurrency ?? 0) || 0,
    concurrency_ttl_seconds: Number(row.concurrency_ttl_seconds ?? 180) || 180,
    allowed_actions_text: Array.isArray(row.allowed_actions) ? row.allowed_actions.join(",") : "",
    is_enabled: Boolean(row.is_enabled),
    notes: row.notes || "",
  };
  dialog.visible = true;
}

function parseActionsText(text) {
  const raw = String(text || "")
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
  return raw;
}

async function save() {
  dialog.saving = true;
  try {
    const payload = {
      scope_type: dialog.form.scope_type,
      project: dialog.form.project ? Number(dialog.form.project) : null,
      org: dialog.form.org ? Number(dialog.form.org) : null,
      user: dialog.form.user ? Number(dialog.form.user) : null,
      daily_requests: Number(dialog.form.daily_requests ?? 0) || 0,
      max_concurrency: Number(dialog.form.max_concurrency ?? 0) || 0,
      concurrency_ttl_seconds: Number(dialog.form.concurrency_ttl_seconds ?? 180) || 180,
      allowed_actions: parseActionsText(dialog.form.allowed_actions_text),
      is_enabled: Boolean(dialog.form.is_enabled),
      notes: dialog.form.notes || "",
    };

    if (dialog.editingId) {
      await updateAiQuotaPolicyApi(dialog.editingId, payload);
      ElMessage.success("已保存");
    } else {
      await createAiQuotaPolicyApi(payload);
      ElMessage.success("已创建");
    }
    dialog.visible = false;
    load();
  } catch (e) {
    ElMessage.error(e?.message || "保存失败");
  } finally {
    dialog.saving = false;
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确认删除策略 #${row.id}？`, "提示", { type: "warning" });
  } catch {
    return;
  }
  try {
    await deleteAiQuotaPolicyApi(row.id);
    ElMessage.success("已删除");
    load();
  } catch (e) {
    ElMessage.error(e?.message || "删除失败");
  }
}

load();
</script>

<style scoped>
.ai-quota-page {
  padding: 12px 6px;
}
.panel-title {
  font-weight: 600;
  margin: 4px 0 10px;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.spacer {
  flex: 1;
}
.hint {
  margin-left: 10px;
  font-size: 12px;
  opacity: 0.8;
}
.actions-cell {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 12px;
  opacity: 0.95;
}
</style>

