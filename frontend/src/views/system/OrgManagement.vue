<template>
  <div class="page-wrap cyber-page admin-list-page sys-admin-page">
    <el-card class="sys-filter-card" shadow="never">
      <div class="sys-toolbar">
        <div class="sys-toolbar__left">
          <el-button type="primary" size="default" @click="openCreateDialog">新增组织</el-button>
          <el-input
            v-model="keyword"
            placeholder="搜索组织名称"
            clearable
            size="default"
            class="sys-toolbar__search"
            @keyup.enter="load"
          />
        </div>
        <span class="sys-toolbar__meta">共 {{ flatOrgs.length }} 条（树形展示）</span>
      </div>
    </el-card>

    <el-card class="sys-table-card" shadow="never">
      <el-table
        :data="treeData"
        v-loading="loading"
        class="admin-data-table sys-enterprise-table org-tree-table"
        row-key="id"
        :tree-props="{ children: 'children', hasChildren: 'hasChildren' }"
        default-expand-all
        border
      >
        <template #empty>
          <el-empty description="暂无组织数据" :image-size="88" />
        </template>
        <el-table-column prop="org_name" label="组织名称" min-width="200" align="left" show-overflow-tooltip />
        <el-table-column prop="description" label="描述" min-width="200" align="left" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.description || "—" }}</span>
          </template>
        </el-table-column>
        <el-table-column label="负责人" min-width="120" width="120" align="center" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.leader_name || "—" }}</span>
          </template>
        </el-table-column>
        <el-table-column label="编制人数" min-width="100" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="info" effect="plain">{{ row.headcount ?? 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="176" width="176" align="center" class-name="col-datetime">
          <template #default="{ row }">
            <span>{{ formatDate(row.create_time) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="168" width="168" fixed="right" align="center">
          <template #default="{ row }">
            <TableActionGroup :row="row" :actions="orgTableActions" @action="handleOrgTableAction" />
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editing ? '编辑组织' : '新增组织'"
      width="560px"
      destroy-on-close
      class="cyber-dialog-dark"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="上级组织" prop="parent_id">
          <el-tree-select
            v-model="form.parent_id"
            :data="parentTreeOptions"
            check-strictly
            :render-after-expand="false"
            clearable
            placeholder="不选则为顶级"
            class="w-full"
            :props="{ label: 'org_name', value: 'id', children: 'children' }"
          />
        </el-form-item>
        <el-form-item label="组织名称" prop="org_name">
          <el-input v-model="form.org_name" placeholder="请输入组织名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" placeholder="可选描述" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="负责人" prop="leader_name">
          <el-input v-model="form.leader_name" placeholder="前端展示用，可对接人事字段" />
        </el-form-item>
        <el-form-item label="编制人数" prop="headcount">
          <el-input-number v-model="form.headcount" :min="0" :max="99999" controls-position="right" class="w-full-num" />
        </el-form-item>
        <el-form-item label="组织成员" prop="member_ids">
          <el-select
            v-model="form.member_ids"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            placeholder="选择可共享本组织资源的用户（如服务器日志主机）"
            class="w-full"
          >
            <el-option
              v-for="u in userOptions"
              :key="u.id"
              :label="u.real_name || u.username"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Delete, Edit } from "@element-plus/icons-vue";
import TableActionGroup from "@/components/common/TableActionGroup.vue";
import { createOrgApi, deleteOrgApi, getOrgsApi, getUsersApi, updateOrgApi } from "@/api/system";

const OVERLAY_KEY = "sys_org_tree_overlay_v1";

const loading = ref(false);
const flatOrgs = ref([]);
const treeData = ref([]);
const keyword = ref("");

const dialogVisible = ref(false);
const editing = ref(null);
const saving = ref(false);
const formRef = ref(null);
const userOptions = ref([]);

const form = reactive({
  parent_id: null,
  org_name: "",
  description: "",
  leader_name: "",
  headcount: 0,
  member_ids: [],
});

const orgTableActions = [
  { key: "edit", tooltip: "编辑组织", icon: Edit, type: "primary" },
  { key: "delete", tooltip: "删除组织", icon: Delete, type: "danger" },
];

function handleOrgTableAction(action, row) {
  if (action === "edit") openEditDialog(row);
  else if (action === "delete") delRow(row);
}

const rules = {
  org_name: [{ required: true, message: "请输入组织名称", trigger: "blur" }],
};

function readOverlay() {
  try {
    return JSON.parse(localStorage.getItem(OVERLAY_KEY) || "{}");
  } catch {
    return {};
  }
}

function writeOverlay(map) {
  localStorage.setItem(OVERLAY_KEY, JSON.stringify(map));
}

function getOverlayFor(id) {
  const all = readOverlay();
  return all[String(id)] || {};
}

function setOverlayFor(id, patch) {
  const all = readOverlay();
  all[String(id)] = { ...getOverlayFor(id), ...patch };
  writeOverlay(all);
}

function removeOverlayFor(id) {
  const all = readOverlay();
  delete all[String(id)];
  writeOverlay(all);
}

function formatDate(dt) {
  return dt ? String(dt).slice(0, 16).replace("T", " ") : "-";
}

function mergeRow(org) {
  const ex = getOverlayFor(org.id);
  const members = Array.isArray(org.members) ? org.members : [];
  return {
    ...org,
    parent_id: ex.parent_id != null ? ex.parent_id : null,
    leader_name: ex.leader_name ?? "—",
    headcount: typeof ex.headcount === "number" ? ex.headcount : 0,
    members,
  };
}

function buildTree(flat) {
  const nodes = {};
  for (const raw of flat) {
    const m = mergeRow(raw);
    nodes[m.id] = { ...m, children: [] };
  }
  const roots = [];
  for (const m of Object.values(nodes)) {
    const pid = m.parent_id;
    if (pid != null && nodes[pid]) nodes[pid].children.push(m);
    else roots.push(m);
  }
  const prune = (list) =>
    list.map((n) => {
      const ch = n.children?.length ? prune(n.children) : [];
      const next = { ...n };
      if (ch.length) {
        next.children = ch;
        next.hasChildren = true;
      } else {
        delete next.children;
        next.hasChildren = false;
      }
      return next;
    });
  return prune(roots);
}

function stripSelfSubtree(nodes, exId) {
  if (exId == null) return nodes || [];
  return (nodes || [])
    .map((n) => {
      if (n.id === exId) return null;
      const ch = stripSelfSubtree(n.children || [], exId).filter(Boolean);
      return { ...n, children: ch.length ? ch : undefined };
    })
    .filter(Boolean);
}

const parentTreeOptions = computed(() => stripSelfSubtree(treeData.value, editing.value?.id));

async function loadUserOptions() {
  try {
    const { data } = await getUsersApi({ page: 1, page_size: 500 });
    const list = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
    userOptions.value = list;
  } catch {
    userOptions.value = [];
  }
}

function openCreateDialog() {
  editing.value = null;
  loadUserOptions();
  Object.assign(form, {
    parent_id: null,
    org_name: "",
    description: "",
    leader_name: "",
    headcount: 0,
    member_ids: [],
  });
  dialogVisible.value = true;
}

function openEditDialog(row) {
  editing.value = row;
  loadUserOptions();
  const ex = getOverlayFor(row.id);
  const m = mergeRow(row);
  Object.assign(form, {
    parent_id: ex.parent_id ?? row.parent_id ?? null,
    org_name: row.org_name || "",
    description: row.description || "",
    leader_name: ex.leader_name === "—" ? "" : ex.leader_name || "",
    headcount: typeof ex.headcount === "number" ? ex.headcount : row.headcount ?? 0,
    member_ids: Array.isArray(m.members) ? [...m.members] : [],
  });
  dialogVisible.value = true;
}

function wouldCycle(childId, newParentId) {
  if (newParentId == null || childId == null) return false;
  const cid = Number(childId);
  let p = Number(newParentId);
  const seen = new Set();
  while (p) {
    if (p === cid) return true;
    if (seen.has(p)) break;
    seen.add(p);
    const o = getOverlayFor(p);
    p = o.parent_id != null ? Number(o.parent_id) : null;
  }
  return false;
}

async function load() {
  loading.value = true;
  try {
    const params = { page: 1, page_size: 500 };
    const kw = keyword.value.trim();
    if (kw) params.name = kw;
    const { data } = await getOrgsApi(params);
    const list = Array.isArray(data?.results)
      ? data.results
      : Array.isArray(data)
        ? data
        : [];
    flatOrgs.value = list;
    treeData.value = buildTree(flatOrgs.value);
  } catch (e) {
    ElMessage.error("获取组织列表失败");
    // eslint-disable-next-line no-console
    console.error(e);
  } finally {
    loading.value = false;
  }
}

async function delRow(row) {
  try {
    await ElMessageBox.confirm(`确定删除组织「${row.org_name}」吗？`, "提示", { type: "warning" });
  } catch {
    return;
  }
  try {
    await deleteOrgApi(row.id);
    removeOverlayFor(row.id);
    const all = readOverlay();
    for (const k of Object.keys(all)) {
      if (Number(all[k].parent_id) === Number(row.id)) {
        all[k] = { ...all[k], parent_id: null };
      }
    }
    writeOverlay(all);
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
    const apiPayload = {
      org_name: form.org_name,
      description: form.description || "",
      members: Array.isArray(form.member_ids) ? form.member_ids : [],
    };
    const meta = {
      parent_id: form.parent_id ?? null,
      leader_name: (form.leader_name || "").trim() || "—",
      headcount: Number(form.headcount) || 0,
    };
    try {
      let targetId = editing.value?.id;
      if (editing.value && wouldCycle(editing.value.id, meta.parent_id)) {
        ElMessage.warning("不能将上级设为自己或下属部门");
        saving.value = false;
        return;
      }
      if (editing.value) {
        await updateOrgApi(editing.value.id, apiPayload);
        ElMessage.success("更新成功");
      } else {
        const res = await createOrgApi(apiPayload);
        const body = res?.data;
        targetId = body?.id ?? body?.data?.id ?? body?.results?.[0]?.id;
        ElMessage.success("创建成功");
      }
      if (targetId != null) setOverlayFor(targetId, meta);
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

.sys-toolbar__left {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.sys-toolbar__search {
  width: 260px;
}

.sys-toolbar__meta {
  font-size: 12px;
  color: rgba(226, 232, 240, 0.55);
}

.w-full {
  width: 100%;
}

.w-full-num {
  width: 100%;
}

.sys-enterprise-table :deep(.el-table__cell) {
  padding-top: 12px !important;
  padding-bottom: 12px !important;
}

.sys-enterprise-table :deep(.el-table__header .el-table__cell) {
  white-space: nowrap;
}

.org-tree-table :deep(.el-table__placeholder) {
  display: none;
}
</style>
