<template>
  <div class="message-manage cyber-page sys-admin-page">
    <el-card class="mm-top-card" shadow="never">
      <div class="mm-top">
        <div class="mm-top__text">
          <h1 class="mm-title">消息中心</h1>
          <p class="mm-sub">站内系统消息与敏感信息变更审批（用户名 / 密码）。</p>
        </div>
        <div class="mm-top__actions">
          <el-radio-group v-model="filterRead" size="default" class="mm-filter">
            <el-radio-button label="all">全部</el-radio-button>
            <el-radio-button label="unread">未读</el-radio-button>
            <el-radio-button label="read">已读</el-radio-button>
          </el-radio-group>
          <el-badge v-if="totalUnread" :value="totalUnread" class="mm-unread-pill" type="danger" />
          <el-button size="default" :disabled="!unreadIds.length" :loading="markAllLoading" @click="markAllAsRead">
            全部标为已读
          </el-button>
          <el-button size="default" :loading="loading" @click="loadAll">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </div>
    </el-card>

    <el-card class="mm-body-card" shadow="never">
      <div v-loading="loading" class="mm-master-detail">
        <aside class="mm-list-pane">
          <el-scrollbar max-height="calc(100vh - 220px)">
            <template v-if="filteredMessages.length">
              <button
                v-for="msg in filteredMessages"
                :key="msg.id"
                type="button"
                class="mm-list-item"
                :class="{ 'mm-list-item--active': selectedId === msg.id, 'mm-list-item--unread': !msg.is_read }"
                @click="onSelectMessage(msg)"
              >
                <span v-if="!msg.is_read" class="mm-unread-dot" aria-hidden="true" />
                <div class="mm-list-item__body">
                  <div class="mm-list-item__title-row">
                    <span class="mm-list-item__title">{{ msg.title }}</span>
                    <el-tag v-if="!msg.is_read" size="small" type="danger" effect="plain">未读</el-tag>
                  </div>
                  <time class="mm-list-item__time">{{ formatTime(msg.created_at) }}</time>
                </div>
              </button>
            </template>
            <div v-else class="mm-list-empty">
              <el-empty description="暂无消息" :image-size="72" />
            </div>
          </el-scrollbar>
        </aside>

        <main class="mm-detail-pane">
          <template v-if="selectedMessage">
            <div class="mm-detail__meta">
              <h2 class="mm-detail__title">{{ selectedMessage.title }}</h2>
              <div class="mm-detail__tags">
                <el-tag size="small" :type="selectedMessage.is_read ? 'info' : 'warning'">
                  {{ selectedMessage.is_read ? "已读" : "未读" }}
                </el-tag>
                <span class="mm-detail__time">{{ formatTime(selectedMessage.created_at) }}</span>
              </div>
            </div>
            <div class="mm-detail__content">{{ selectedMessage.content }}</div>

            <div v-if="showApprovalActions(selectedMessage)" class="mm-approval">
              <div class="mm-approval__label">审批申请</div>
              <p class="mm-approval__line">
                用户 <strong>{{ approvalDetail(selectedMessage)?.applicant_username || "—" }}</strong>
                请求修改 <strong>{{ requestTypeLabel(approvalDetail(selectedMessage)?.request_type) }}</strong>
              </p>
              <div class="mm-approval__actions">
                <el-button
                  type="primary"
                  plain
                  :loading="actingId === Number(selectedMessage.related_request)"
                  @click="onApprove(selectedMessage)"
                >
                  同意
                </el-button>
                <el-button
                  type="danger"
                  plain
                  :loading="actingId === Number(selectedMessage.related_request)"
                  @click="onReject(selectedMessage)"
                >
                  拒绝
                </el-button>
              </div>
            </div>

            <div
              v-else-if="selectedMessage.related_request && selectedMessage.is_read && wasApprovalMessage(selectedMessage)"
              class="mm-processed"
            >
              已处理
            </div>
          </template>
          <el-empty v-else description="请从左侧选择一条消息" :image-size="88" class="mm-detail-empty" />
        </main>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import {
  getSystemMessagesApi,
  getAdminChangeRequestsApi,
  approveChangeRequestApi,
  rejectChangeRequestApi,
  markSystemMessageReadApi,
} from "@/api/user";

const loading = ref(false);
const markAllLoading = ref(false);
const messages = ref([]);
const pendingById = ref(new Map());
const actingId = ref(null);
const filterRead = ref("all");
const selectedId = ref(null);

const filteredMessages = computed(() => {
  const list = messages.value;
  if (filterRead.value === "unread") return list.filter((m) => !m.is_read);
  if (filterRead.value === "read") return list.filter((m) => m.is_read);
  return list;
});

const totalUnread = computed(() => messages.value.filter((m) => !m.is_read).length);

const unreadIds = computed(() => messages.value.filter((m) => !m.is_read).map((m) => m.id));

const selectedMessage = computed(() => {
  if (selectedId.value == null) return null;
  return messages.value.find((m) => m.id === selectedId.value) || null;
});

watch(filteredMessages, (list) => {
  if (!list.length) {
    selectedId.value = null;
    return;
  }
  if (!list.some((m) => m.id === selectedId.value)) {
    selectedId.value = list[0].id;
  }
});

function formatTime(iso) {
  if (!iso) return "—";
  const s = String(iso).replace("T", " ");
  return s.length > 16 ? s.slice(0, 16) : s;
}

function requestTypeLabel(t) {
  if (t === "username") return "用户名";
  if (t === "password") return "密码";
  return t || "—";
}

function approvalDetail(msg) {
  const id = msg.related_request;
  if (id == null) return null;
  return pendingById.value.get(Number(id)) || null;
}

function showApprovalActions(msg) {
  if (!msg.related_request || msg.is_read) return false;
  const rid = Number(msg.related_request);
  const row = pendingById.value.get(rid);
  return row && row.status === "pending";
}

function wasApprovalMessage(msg) {
  return !!msg.related_request;
}

async function markOneRead(msg) {
  if (!msg || msg.is_read) return;
  try {
    await markSystemMessageReadApi(msg.id);
    msg.is_read = true;
  } catch (e) {
    ElMessage.error(e?.response?.data?.msg || "标记已读失败");
  }
}

function onSelectMessage(msg) {
  selectedId.value = msg.id;
  markOneRead(msg);
}

async function markAllAsRead() {
  const ids = unreadIds.value;
  if (!ids.length) return;
  try {
    await ElMessageBox.confirm(`将 ${ids.length} 条未读消息全部标为已读？`, "确认", { type: "info" });
  } catch {
    return;
  }
  markAllLoading.value = true;
  try {
    await Promise.all(ids.map((id) => markSystemMessageReadApi(id)));
    messages.value.forEach((m) => {
      if (!m.is_read) m.is_read = true;
    });
    ElMessage.success("已全部标为已读");
  } catch (e) {
    ElMessage.error(e?.response?.data?.msg || "部分消息标记失败，请刷新重试");
    await loadAll();
  } finally {
    markAllLoading.value = false;
  }
}

async function fetchMessages() {
  const { data: res } = await getSystemMessagesApi();
  const list = res?.data;
  messages.value = Array.isArray(list) ? list : [];
}

async function fetchPendingRequests() {
  const { data: res } = await getAdminChangeRequestsApi({ status: "pending" });
  const list = res?.data;
  const rows = Array.isArray(list) ? list : [];
  const map = new Map();
  for (const row of rows) map.set(Number(row.id), row);
  pendingById.value = map;
}

async function loadAll() {
  loading.value = true;
  try {
    await Promise.all([fetchMessages(), fetchPendingRequests()]);
    if (!selectedId.value && filteredMessages.value.length) {
      selectedId.value = filteredMessages.value[0].id;
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.msg || "加载失败");
  } finally {
    loading.value = false;
  }
}

async function onApprove(msg) {
  const rid = Number(msg.related_request);
  try {
    await ElMessageBox.confirm("确认同意该变更申请？", "审批", { type: "warning" });
  } catch {
    return;
  }
  actingId.value = rid;
  try {
    const { data: res } = await approveChangeRequestApi(rid);
    ElMessage.success(res?.msg || "已通过");
    await loadAll();
  } catch (e) {
    ElMessage.error(e?.response?.data?.msg || "操作失败");
  } finally {
    actingId.value = null;
  }
}

async function onReject(msg) {
  const rid = Number(msg.related_request);
  try {
    await ElMessageBox.confirm("确认拒绝该变更申请？", "审批", { type: "warning" });
  } catch {
    return;
  }
  actingId.value = rid;
  try {
    const { data: res } = await rejectChangeRequestApi(rid);
    ElMessage.success(res?.msg || "已拒绝");
    await loadAll();
  } catch (e) {
    ElMessage.error(e?.response?.data?.msg || "操作失败");
  } finally {
    actingId.value = null;
  }
}

onMounted(loadAll);
</script>

<style scoped>
.sys-admin-page {
  padding: 16px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}

.mm-top-card,
.mm-body-card {
  border-radius: 12px !important;
  border: 1px solid rgba(0, 255, 255, 0.12) !important;
  background: rgba(18, 26, 44, 0.92) !important;
  --el-card-bg-color: rgba(18, 26, 44, 0.92);
}

.mm-top-card :deep(.el-card__body) {
  padding: 16px 18px;
}

.mm-body-card :deep(.el-card__body) {
  padding: 0;
}

.mm-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.mm-title {
  margin: 0 0 6px;
  font-size: 20px;
  font-weight: 700;
  color: #e2e8f0;
  text-shadow: 0 0 18px rgba(0, 216, 255, 0.22);
}

.mm-sub {
  margin: 0;
  font-size: 13px;
  color: rgba(226, 232, 240, 0.55);
  max-width: 560px;
  line-height: 1.5;
}

.mm-top__actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.mm-filter :deep(.el-radio-button__inner) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(10, 16, 29, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: rgba(226, 232, 240, 0.65);
  box-shadow: none;
}

.mm-filter :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: rgba(0, 216, 255, 0.15);
  border-color: rgba(0, 216, 255, 0.35);
  color: #00d8ff;
  box-shadow: 0 0 12px rgba(0, 216, 255, 0.15);
}

.mm-unread-pill :deep(.el-badge__content) {
  border: none;
  font-weight: 600;
}

.mm-master-detail {
  display: flex;
  min-height: 420px;
  position: relative;
}

.mm-list-pane {
  width: 320px;
  flex-shrink: 0;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(8, 12, 22, 0.35);
}

.mm-list-item {
  display: flex;
  gap: 10px;
  width: 100%;
  padding: 14px 16px;
  margin: 0;
  border: none;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: background 0.2s ease;
  font: inherit;
  color: inherit;
}

.mm-list-item:hover {
  background: rgba(0, 216, 255, 0.06);
}

.mm-list-item--active {
  background: rgba(0, 216, 255, 0.1);
  box-shadow: inset 3px 0 0 rgba(0, 216, 255, 0.75);
}

.mm-list-item--unread .mm-list-item__title {
  font-weight: 600;
  color: rgba(255, 255, 255, 0.95);
}

.mm-unread-dot {
  width: 8px;
  height: 8px;
  margin-top: 6px;
  border-radius: 50%;
  background: #f43f5e;
  box-shadow: 0 0 10px rgba(244, 63, 94, 0.65);
  flex-shrink: 0;
}

.mm-list-item__body {
  min-width: 0;
  flex: 1;
}

.mm-list-item__title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}

.mm-list-item__title {
  font-size: 13px;
  color: rgba(226, 232, 240, 0.88);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.mm-list-item__time {
  font-size: 11px;
  color: rgba(148, 163, 184, 0.85);
}

.mm-list-empty {
  padding: 40px 12px;
}

.mm-list-empty :deep(.el-empty__description) {
  color: rgba(226, 232, 240, 0.5);
}

.mm-detail-pane {
  flex: 1;
  min-width: 0;
  padding: 20px 24px 28px;
}

.mm-detail-empty {
  height: 100%;
  min-height: 320px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mm-detail-empty :deep(.el-empty__description) {
  color: rgba(226, 232, 240, 0.5);
}

.mm-detail__title {
  margin: 0 0 10px;
  font-size: 17px;
  font-weight: 600;
  color: #e2e8f0;
}

.mm-detail__tags {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.mm-detail__time {
  font-size: 12px;
  color: rgba(148, 163, 184, 0.9);
}

.mm-detail__content {
  font-size: 14px;
  line-height: 1.65;
  color: rgba(226, 232, 240, 0.85);
  white-space: pre-wrap;
  word-break: break-word;
}

.mm-approval {
  margin-top: 20px;
  padding: 16px;
  border-radius: 10px;
  border: 1px solid rgba(0, 255, 255, 0.15);
  background: rgba(10, 16, 29, 0.45);
}

.mm-approval__label {
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(0, 216, 255, 0.65);
  margin-bottom: 8px;
}

.mm-approval__line {
  margin: 0 0 12px;
  font-size: 13px;
  color: #e2e8f0;
}

.mm-approval__line strong {
  color: #5ee7ff;
  font-weight: 600;
}

.mm-approval__actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.mm-processed {
  margin-top: 16px;
  font-size: 12px;
  color: rgba(226, 232, 240, 0.45);
}

.message-manage :deep(.el-loading-mask) {
  background-color: rgba(10, 16, 29, 0.55);
}
</style>
