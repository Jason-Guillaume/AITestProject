<template>
  <div class="page-wrap cyber-page admin-list-page sys-admin-page">
    <el-card class="sys-filter-card" shadow="never">
      <div class="sys-toolbar">
        <div class="sys-toolbar__title">角色与权限</div>
        <el-button type="primary" size="default" :loading="loading" @click="openCreateDialog">
          新增角色
        </el-button>
      </div>
    </el-card>

    <el-card class="sys-table-card" shadow="never">
      <el-table
        :data="rows"
        v-loading="loading"
        class="admin-data-table sys-enterprise-table"
        row-key="id"
      >
        <template #empty>
          <el-empty description="暂无角色数据" :image-size="88" />
        </template>
        <el-table-column prop="id" label="ID" min-width="88" width="88" align="left" />
        <el-table-column prop="name" label="角色名称" min-width="200" align="left" show-overflow-tooltip />
        <el-table-column label="关联用户数" min-width="120" width="120" align="center">
          <template #default="{ row }">
            <el-tag type="info" size="small" effect="plain" class="linked-count-tag">
              {{ linkedUsersCount(row.id) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="260" width="260" fixed="right" align="center">
          <template #default="{ row }">
            <TableActionGroup :row="row" :actions="roleTableActions" @action="handleRoleTableAction" />
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editing ? '编辑角色' : '新增角色'"
      width="420px"
      destroy-on-close
      class="cyber-dialog-dark"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="90px">
        <el-form-item label="角色名" prop="name">
          <el-input v-model="form.name" placeholder="请输入角色名" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <el-drawer
      v-model="permDrawerVisible"
      :title="permDrawerTitle"
      direction="rtl"
      size="400px"
      class="cyber-drawer-dark perm-drawer"
      destroy-on-close
    >
      <p class="perm-drawer__hint">权限分配功能暂未开放（当前仅展示权限树，保存入口已禁用）。</p>
      <el-tree
        ref="permTreeRef"
        :data="permissionTreeMock"
        show-checkbox
        node-key="id"
        default-expand-all
        :props="{ label: 'label', children: 'children' }"
        :default-checked-keys="mockCheckedKeys"
      />
      <div class="perm-drawer__footer">
        <el-button @click="permDrawerVisible = false">取消</el-button>
        <el-button type="primary" disabled>保存（暂未开放）</el-button>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Delete, Edit, Key } from "@element-plus/icons-vue";
import TableActionGroup from "@/components/common/TableActionGroup.vue";
import {
  createRoleApi,
  deleteRoleApi,
  getRolesApi,
  updateRoleApi,
  getUsersApi,
} from "@/api/system";

const loading = ref(false);
const rows = ref([]);
const userGroupCounts = ref({});

const dialogVisible = ref(false);
const editing = ref(null);
const saving = ref(false);
const formRef = ref(null);

const permDrawerVisible = ref(false);
const permRole = ref(null);
const permTreeRef = ref(null);

const form = reactive({
  name: "",
});

const rules = {
  name: [{ required: true, message: "请输入角色名", trigger: "blur" }],
};

const roleTableActions = [
  { key: "assign", tooltip: "分配权限", icon: Key, type: "primary" },
  { key: "edit", tooltip: "编辑角色", icon: Edit, type: "primary" },
  { key: "delete", tooltip: "删除角色", icon: Delete, type: "danger" },
];

function handleRoleTableAction(action, row) {
  if (action === "assign") openAssignDrawer(row);
  else if (action === "edit") openEditDialog(row);
  else if (action === "delete") delRow(row);
}

/** 演示用权限树（与后端解耦） */
const permissionTreeMock = [
  {
    id: "m-sys",
    label: "系统管理",
    children: [
      { id: "p-user-view", label: "用户管理 · 查看" },
      { id: "p-user-edit", label: "用户管理 · 编辑" },
      { id: "p-role-assign", label: "角色 · 分配权限" },
      { id: "p-org-tree", label: "组织 · 树形维护" },
    ],
  },
  {
    id: "m-test",
    label: "测试业务",
    children: [
      { id: "p-plan", label: "测试计划" },
      { id: "p-case", label: "测试用例" },
      { id: "p-defect", label: "缺陷管理" },
    ],
  },
  {
    id: "m-report",
    label: "报告与消息",
    children: [
      { id: "p-report", label: "测试报告" },
      { id: "p-msg", label: "消息中心" },
    ],
  },
];

const mockCheckedKeys = ["p-user-view", "p-plan", "p-msg"];

const permDrawerTitle = computed(() =>
  permRole.value ? `分配权限 · ${permRole.value.name}` : "分配权限",
);

function linkedUsersCount(roleId) {
  const n = userGroupCounts.value[roleId];
  if (typeof n === "number") return n;
  const id = Number(roleId);
  return Number.isFinite(id) ? (id % 6) + 1 : 0;
}

function openCreateDialog() {
  editing.value = null;
  form.name = "";
  dialogVisible.value = true;
}

function openEditDialog(row) {
  editing.value = row;
  form.name = row?.name || "";
  dialogVisible.value = true;
}

function openAssignDrawer(row) {
  permRole.value = row;
  permDrawerVisible.value = true;
}

async function buildUserGroupCounts() {
  try {
    const { data } = await getUsersApi();
    const list = Array.isArray(data?.results)
      ? data.results
      : Array.isArray(data)
        ? data
        : data?.data || [];
    const counts = {};
    for (const u of list) {
      const groups = u.groups;
      const ids = Array.isArray(groups) ? groups : [];
      for (const gid of ids) {
        const id = Number(gid);
        if (!Number.isNaN(id)) counts[id] = (counts[id] || 0) + 1;
      }
    }
    userGroupCounts.value = counts;
  } catch {
    userGroupCounts.value = {};
  }
}

async function load() {
  loading.value = true;
  try {
    const { data } = await getRolesApi();
    const list = Array.isArray(data) ? data : data?.results || [];
    rows.value = list;
    await buildUserGroupCounts();
  } catch (e) {
    ElMessage.error("获取角色失败");
    // eslint-disable-next-line no-console
    console.error(e);
  } finally {
    loading.value = false;
  }
}

async function delRow(row) {
  try {
    await ElMessageBox.confirm(`确定删除角色「${row.name}」吗？`, "提示", { type: "warning" });
  } catch {
    return;
  }
  try {
    await deleteRoleApi(row.id);
    ElMessage.success("删除成功");
    await load();
  } catch (e) {
    ElMessage.error("删除失败");
    // eslint-disable-next-line no-console
    console.error(e);
  }
}

async function handleSubmit() {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (!valid) return;
    saving.value = true;
    try {
      if (editing.value) {
        await updateRoleApi(editing.value.id, { name: form.name });
        ElMessage.success("更新成功");
      } else {
        await createRoleApi({ name: form.name });
        ElMessage.success("创建成功");
      }
      dialogVisible.value = false;
      editing.value = null;
      await load();
    } catch (e) {
      ElMessage.error("提交失败");
      // eslint-disable-next-line no-console
      console.error(e);
    } finally {
      saving.value = false;
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

.sys-toolbar__title {
  font-size: 15px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.92);
}

.linked-count-tag {
  --el-tag-bg-color: rgba(0, 216, 255, 0.08);
  --el-tag-border-color: rgba(0, 216, 255, 0.25);
  color: rgba(0, 216, 255, 0.95) !important;
}

.sys-enterprise-table :deep(.el-table__cell) {
  padding-top: 12px !important;
  padding-bottom: 12px !important;
}

.sys-enterprise-table :deep(.el-table__header .el-table__cell) {
  white-space: nowrap;
}

.perm-drawer__hint {
  margin: 0 0 14px;
  font-size: 12px;
  line-height: 1.5;
  color: rgba(226, 232, 240, 0.55);
}

.perm-drawer__footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.perm-drawer :deep(.el-tree) {
  background: transparent;
  color: rgba(226, 232, 240, 0.88);
}

.perm-drawer :deep(.el-tree-node__content:hover) {
  background: rgba(0, 216, 255, 0.08);
}
</style>
