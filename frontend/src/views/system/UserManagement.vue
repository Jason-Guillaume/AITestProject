<template>
  <div class="page-wrap cyber-page admin-list-page sys-admin-page">
    <el-card class="sys-filter-card" shadow="never">
      <div class="sys-toolbar">
        <el-input
          v-model="keyword"
          placeholder="搜索用户名 / 真实姓名"
          clearable
          size="default"
          class="sys-toolbar__search"
          @keyup.enter="load"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <div class="sys-toolbar__actions">
          <el-button size="default" @click="downloadImportTemplate">
            下载导入模板
          </el-button>
          <el-button size="default" @click="onBatchImport">
            批量导入
          </el-button>
          <el-button size="default" @click="onExport">
            导出
          </el-button>
          <el-button type="primary" size="default" @click="onAddUser">新增用户</el-button>
        </div>
      </div>
    </el-card>
    <input
      ref="importFileRef"
      type="file"
      accept=".csv,text/csv"
      class="import-file-input"
      @change="onImportFileChange"
    />

    <el-card class="sys-table-card" shadow="never">
      <el-table
        :data="rows"
        v-loading="loading"
        class="admin-data-table sys-enterprise-table"
        row-key="id"
      >
        <template #empty>
          <el-empty description="暂无用户数据" :image-size="88" />
        </template>
        <el-table-column label="头像" width="80" align="center" class-name="col-avatar">
          <template #default="{ row }">
            <div class="avatar-cell">
              <el-avatar
                shape="circle"
                :size="32"
                :src="avatarSrc(row)"
                :class="['user-avatar-ent', avatarToneClass(row)]"
              >
                {{ usernameInitial(row) }}
              </el-avatar>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="id" label="ID" min-width="88" width="88" align="left" />
        <el-table-column prop="username" label="用户名" min-width="140" align="left" show-overflow-tooltip />
        <el-table-column prop="real_name" label="真实姓名" min-width="140" align="left" show-overflow-tooltip />
        <el-table-column label="系统管理员" min-width="120" width="120" align="center">
          <template #default="{ row }">
            <el-switch
              :model-value="!!row.is_system_admin"
              :loading="adminToggleId === row.id"
              inline-prompt
              active-text="是"
              inactive-text="否"
              @change="(v) => toggleSystemAdmin(row, v)"
            />
          </template>
        </el-table-column>
        <el-table-column label="账号状态" min-width="120" width="120" align="center">
          <template #default="{ row }">
            <div class="status-cell">
              <el-badge
                is-dot
                :type="row.is_active ? 'success' : 'info'"
                class="status-cell__badge"
              >
                <span class="status-cell__label">{{ row.is_active ? "正常" : "禁用" }}</span>
              </el-badge>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="176" width="176" align="center" class-name="col-datetime">
          <template #default="{ row }">
            <span>{{ formatDate(row.create_time) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="168" width="168" fixed="right" align="center">
          <template #default="{ row }">
            <TableActionGroup :row="row" :actions="userTableActions(row)" @action="handleUserTableAction" />
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="createDialogVisible"
      title="新增用户"
      width="460px"
      destroy-on-close
      class="cyber-dialog-dark"
    >
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="92px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model.trim="createForm.username" placeholder="请输入用户名" autocomplete="off" />
        </el-form-item>
        <el-form-item label="真实姓名" prop="real_name">
          <el-input v-model.trim="createForm.real_name" placeholder="请输入真实姓名" autocomplete="off" />
        </el-form-item>
        <el-form-item label="初始密码" prop="password">
          <el-input
            v-model="createForm.password"
            placeholder="请输入初始密码"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item label="账号状态">
          <el-switch v-model="createForm.is_active" inline-prompt active-text="启用" inactive-text="禁用" />
        </el-form-item>
        <el-form-item label="系统管理员">
          <el-switch
            v-model="createForm.is_system_admin"
            inline-prompt
            active-text="是"
            inactive-text="否"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreateUser">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="importResultVisible"
      title="导入结果明细"
      width="760px"
      destroy-on-close
      class="cyber-dialog-dark"
    >
      <div class="import-summary">
        <el-tag type="success" effect="plain">成功 {{ importSummary.ok }} 条</el-tag>
        <el-tag type="danger" effect="plain">失败 {{ importSummary.failed }} 条</el-tag>
      </div>
      <el-table :data="importFailures" size="small" max-height="360" border>
        <el-table-column prop="lineNo" label="行号" width="90" align="center" />
        <el-table-column prop="username" label="用户名" min-width="180" show-overflow-tooltip />
        <el-table-column prop="reason" label="失败原因" min-width="360" show-overflow-tooltip />
      </el-table>
      <template #footer>
        <el-button :disabled="!importFailures.length" @click="exportImportFailuresCsv">导出失败明细</el-button>
        <el-button type="primary" @click="importResultVisible = false">我知道了</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Delete, Search, SwitchButton } from "@element-plus/icons-vue";
import TableActionGroup from "@/components/common/TableActionGroup.vue";
import { createUserApi, deleteUserApi, getUsersApi, updateUserApi } from "@/api/system";

const loading = ref(false);
const rows = ref([]);
const keyword = ref("");
const adminToggleId = ref(null);
const createDialogVisible = ref(false);
const createFormRef = ref(null);
const creating = ref(false);
const createForm = reactive({
  username: "",
  real_name: "",
  password: "",
  is_active: true,
  is_system_admin: false,
});
const createRules = {
  username: [
    { required: true, message: "请输入用户名", trigger: "blur" },
    { min: 2, max: 150, message: "用户名长度需在 2-150 字符", trigger: "blur" },
  ],
  real_name: [{ required: true, message: "请输入真实姓名", trigger: "blur" }],
  password: [
    { required: true, message: "请输入初始密码", trigger: "blur" },
    { min: 6, max: 128, message: "密码长度需在 6-128 字符", trigger: "blur" },
  ],
};

function userTableActions(row) {
  return [
    {
      key: "toggle",
      tooltip: row.is_active ? "禁用账号" : "启用账号",
      icon: SwitchButton,
      type: "primary",
    },
    { key: "delete", tooltip: "删除用户", icon: Delete, type: "danger" },
  ];
}

function handleUserTableAction(action, row) {
  if (action === "toggle") toggleActive(row);
  else if (action === "delete") delRow(row);
}
const importFileRef = ref(null);
const importResultVisible = ref(false);
const importFailures = ref([]);
const importSummary = reactive({
  ok: 0,
  failed: 0,
});

function formatDate(dt) {
  return dt ? String(dt).slice(0, 16).replace("T", " ") : "-";
}

/** 头像地址：兼容 snake_case / camelCase */
function avatarSrc(row) {
  const raw = row?.avatar_url ?? row?.avatarUrl;
  const s = raw != null ? String(raw).trim() : "";
  return s ? s : undefined;
}

/** 无图时仅展示用户名的首字符（拉丁字母大写，其它字符原样） */
function usernameInitial(row) {
  const u = String(row?.username ?? "").trim();
  if (!u) return "?";
  const ch = u.charAt(0);
  return /^[a-z]$/i.test(ch) ? ch.toUpperCase() : ch;
}

/** 按用户名稳定映射色调，避免整列单色 */
function avatarToneClass(row) {
  const s = String(row?.username ?? "—");
  let h = 0;
  for (let i = 0; i < s.length; i += 1) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return `user-avatar-ent--tone-${h % 6}`;
}

async function load() {
  loading.value = true;
  try {
    const { data } = await getUsersApi();
    const list = Array.isArray(data?.results)
      ? data.results
      : Array.isArray(data)
        ? data
        : data?.data || [];

    if (!keyword.value) {
      rows.value = list;
    } else {
      const kw = keyword.value.toLowerCase();
      rows.value = list.filter((u) => {
        return (
          String(u.username || "").toLowerCase().includes(kw) ||
          String(u.real_name || "").toLowerCase().includes(kw)
        );
      });
    }
  } catch (e) {
    ElMessage.error("获取用户失败");
    // eslint-disable-next-line no-console
    console.error(e);
  } finally {
    loading.value = false;
  }
}

async function toggleActive(row) {
  try {
    await updateUserApi(row.id, { is_active: !row.is_active });
    ElMessage.success("状态已更新");
    await load();
  } catch (e) {
    ElMessage.error("更新失败");
    // eslint-disable-next-line no-console
    console.error(e);
  }
}

async function toggleSystemAdmin(row, isAdmin) {
  adminToggleId.value = row.id;
  try {
    await updateUserApi(row.id, { is_system_admin: !!isAdmin });
    ElMessage.success("权限已更新");
    const selfId = localStorage.getItem("user_id");
    if (selfId && String(row.id) === String(selfId)) {
      localStorage.setItem("is_system_admin", isAdmin ? "1" : "0");
      window.dispatchEvent(new Event("app:permissions"));
    }
    await load();
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || e?.response?.data?.msg || "更新失败");
    // eslint-disable-next-line no-console
    console.error(e);
  } finally {
    adminToggleId.value = null;
  }
}

async function delRow(row) {
  try {
    await ElMessageBox.confirm(`确认删除用户「${row.username}」吗？`, "提示", { type: "warning" });
  } catch {
    return;
  }
  try {
    await deleteUserApi(row.id);
    ElMessage.success("删除成功");
    await load();
  } catch (e) {
    ElMessage.error("删除失败");
    // eslint-disable-next-line no-console
    console.error(e);
  }
}

function onBatchImport() {
  importFileRef.value?.click();
}

function escapeCsv(v) {
  const s = v == null ? "" : String(v);
  if (/[",\r\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

function parseCsvLine(line) {
  const out = [];
  let cur = "";
  let inQuote = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuote && line[i + 1] === '"') {
        cur += '"';
        i += 1;
      } else {
        inQuote = !inQuote;
      }
    } else if (ch === "," && !inQuote) {
      out.push(cur);
      cur = "";
    } else {
      cur += ch;
    }
  }
  out.push(cur);
  return out;
}

function csvToUsers(text) {
  const lines = String(text || "")
    .replace(/^\uFEFF/, "")
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);
  if (lines.length < 2) return [];
  const headers = parseCsvLine(lines[0]).map((h) => h.trim().toLowerCase());
  const idx = {
    username: headers.indexOf("username"),
    real_name: headers.indexOf("real_name"),
    password: headers.indexOf("password"),
    is_active: headers.indexOf("is_active"),
    is_system_admin: headers.indexOf("is_system_admin"),
  };
  if (idx.username < 0 || idx.real_name < 0 || idx.password < 0) {
    throw new Error("CSV 必须包含表头：username,real_name,password");
  }
  const toBool = (v, fallback) => {
    const s = String(v ?? "").trim().toLowerCase();
    if (!s) return fallback;
    return ["1", "true", "yes", "y", "是"].includes(s);
  };
  return lines.slice(1).map((line, i) => {
    const cols = parseCsvLine(line);
    return {
      lineNo: i + 2,
      username: (cols[idx.username] || "").trim(),
      real_name: (cols[idx.real_name] || "").trim(),
      password: cols[idx.password] || "",
      is_active: toBool(cols[idx.is_active], true),
      is_system_admin: toBool(cols[idx.is_system_admin], false),
    };
  });
}

function validateImportUsers(users) {
  const failed = [];
  const valid = [];
  const seen = new Set();
  for (const u of users) {
    const reasons = [];
    if (!u.username) reasons.push("用户名为空");
    if (!u.real_name) reasons.push("真实姓名为空");
    if (!u.password) reasons.push("密码为空");
    if (u.username && (u.username.length < 2 || u.username.length > 150)) {
      reasons.push("用户名长度需在 2-150 字符");
    }
    if (u.password && (u.password.length < 6 || u.password.length > 128)) {
      reasons.push("密码长度需在 6-128 字符");
    }
    const key = String(u.username || "").toLowerCase();
    if (key && seen.has(key)) reasons.push("CSV 内用户名重复");
    if (key) seen.add(key);
    if (reasons.length) {
      failed.push({
        lineNo: u.lineNo,
        username: u.username || "-",
        reason: reasons.join("；"),
      });
    } else {
      valid.push(u);
    }
  }
  return { valid, failed };
}

async function onImportFileChange(evt) {
  const file = evt?.target?.files?.[0];
  if (!file) return;
  try {
    const text = await file.text();
    const parsedUsers = csvToUsers(text);
    if (!parsedUsers.length) {
      ElMessage.warning("CSV 无有效数据行");
      return;
    }
    const precheck = validateImportUsers(parsedUsers);
    let ok = 0;
    const failed = [...precheck.failed];
    for (const u of precheck.valid) {
      try {
        await createUserApi({
          username: u.username,
          real_name: u.real_name,
          password: u.password,
          is_active: u.is_active,
          is_system_admin: u.is_system_admin,
        });
        ok += 1;
      } catch (e) {
        failed.push({
          lineNo: u.lineNo,
          username: u.username || "-",
          reason: e?.response?.data?.detail || e?.response?.data?.msg || "创建失败",
        });
      }
    }
    await load();
    importSummary.ok = ok;
    importSummary.failed = failed.length;
    importFailures.value = failed;
    if (!failed.length) {
      ElMessage.success(`导入完成，共 ${ok} 条`);
    } else {
      ElMessage.warning(`导入完成：成功 ${ok} 条，失败 ${failed.length} 条`);
      importResultVisible.value = true;
    }
  } catch (e) {
    ElMessage.error(e?.message || "CSV 解析失败");
  } finally {
    if (evt?.target) evt.target.value = "";
  }
}

function onExport() {
  const headers = ["id", "username", "real_name", "is_active", "is_system_admin", "create_time"];
  const rowsCsv = rows.value.map((u) => {
    return [
      u.id,
      u.username,
      u.real_name,
      !!u.is_active,
      !!u.is_system_admin,
      u.create_time || "",
    ]
      .map(escapeCsv)
      .join(",");
  });
  const content = [headers.join(","), ...rowsCsv].join("\r\n");
  const blob = new Blob([`\uFEFF${content}`], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `users-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(link.href);
  ElMessage.success("导出完成");
}

function downloadImportTemplate() {
  const headers = ["username", "real_name", "password", "is_active", "is_system_admin"];
  const samples = [
    ["zhangsan", "张三", "Test@123456", "true", "false"],
    ["lisi", "李四", "Test@123456", "true", "true"],
  ];
  const content = [headers.join(","), ...samples.map((r) => r.map(escapeCsv).join(","))].join("\r\n");
  const blob = new Blob([`\uFEFF${content}`], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "users-import-template.csv";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(link.href);
  ElMessage.success("模板已下载");
}

function exportImportFailuresCsv() {
  if (!importFailures.value.length) return;
  const headers = ["line_no", "username", "reason"];
  const rowsCsv = importFailures.value.map((it) => {
    return [it.lineNo, it.username, it.reason].map(escapeCsv).join(",");
  });
  const content = [headers.join(","), ...rowsCsv].join("\r\n");
  const blob = new Blob([`\uFEFF${content}`], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `users-import-failures-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(link.href);
  ElMessage.success("失败明细已导出");
}

function onAddUser() {
  createForm.username = "";
  createForm.real_name = "";
  createForm.password = "";
  createForm.is_active = true;
  createForm.is_system_admin = false;
  createDialogVisible.value = true;
}

async function submitCreateUser() {
  if (!createFormRef.value) return;
  await createFormRef.value.validate(async (valid) => {
    if (!valid) return;
    creating.value = true;
    try {
      await createUserApi({
        username: createForm.username,
        real_name: createForm.real_name,
        password: createForm.password,
        is_active: !!createForm.is_active,
        is_system_admin: !!createForm.is_system_admin,
      });
      ElMessage.success("用户创建成功");
      createDialogVisible.value = false;
      await load();
    } catch (e) {
      ElMessage.error(e?.response?.data?.detail || e?.response?.data?.msg || "创建失败");
      // eslint-disable-next-line no-console
      console.error(e);
    } finally {
      creating.value = false;
    }
  });
}

onMounted(load);
</script>

<style scoped>
.sys-admin-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  box-sizing: border-box;
  min-height: 0;
}

.sys-filter-card,
.sys-table-card {
  border-radius: 12px !important;
  border: 1px solid rgba(0, 255, 255, 0.12) !important;
  background: rgba(18, 26, 44, 0.92) !important;
  --el-card-bg-color: rgba(18, 26, 44, 0.92);
}

.sys-filter-card :deep(.el-card__body),
.sys-table-card :deep(.el-card__body) {
  padding: 16px 18px;
}

.sys-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
}

.sys-toolbar__search {
  width: 280px;
  flex-shrink: 0;
}

.sys-toolbar__actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.import-file-input {
  display: none;
}

.import-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

/* 头像列：单元格与 flex 内容区双重居中 */
.sys-enterprise-table :deep(th.col-avatar .cell),
.sys-enterprise-table :deep(td.col-avatar .cell) {
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
}

.avatar-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 32px;
}

.user-avatar-ent {
  flex-shrink: 0;
  font-size: 14px;
  font-weight: 600;
  color: #fff !important;
  user-select: none;
}

.user-avatar-ent :deep(img) {
  object-fit: cover;
}

.user-avatar-ent--tone-0 {
  background: linear-gradient(145deg, #2563eb, #1d4ed8) !important;
}
.user-avatar-ent--tone-1 {
  background: linear-gradient(145deg, #059669, #047857) !important;
}
.user-avatar-ent--tone-2 {
  background: linear-gradient(145deg, #7c3aed, #6d28d9) !important;
}
.user-avatar-ent--tone-3 {
  background: linear-gradient(145deg, #c2410c, #9a3412) !important;
}
.user-avatar-ent--tone-4 {
  background: linear-gradient(145deg, #0e7490, #155e75) !important;
}
.user-avatar-ent--tone-5 {
  background: linear-gradient(145deg, #4f46e5, #4338ca) !important;
}

.status-cell {
  display: flex;
  justify-content: center;
  align-items: center;
}

.status-cell__badge :deep(.el-badge__content.is-dot) {
  top: 4px;
  right: -2px;
}

.status-cell__label {
  padding: 2px 10px 2px 6px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.88);
}

.sys-enterprise-table :deep(.el-table__cell) {
  padding-top: 12px !important;
  padding-bottom: 12px !important;
}

.sys-enterprise-table :deep(.el-table__header .el-table__cell) {
  white-space: nowrap;
}
</style>
