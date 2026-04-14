<template>
  <div class="log-auto-ticket">
    <p class="log-auto-ticket__hint">
      根据当前选中的日志片段，结合 Elasticsearch 时间窗口上下文，由 Celery 异步生成「缺陷单草稿」JSON。可勾选「同步创建缺陷」在 AI
      成功后自动落库；若未勾选或自动创建失败，可在任务完成后使用「从草稿创建缺陷」补建。
    </p>
    <div class="log-auto-ticket__form">
      <el-checkbox v-model="createDefect" size="small">同步创建缺陷单</el-checkbox>
      <template v-if="createDefect || showManualDefectCreate">
        <el-select
          v-model="handlerId"
          class="log-auto-ticket__sel"
          placeholder="处理人（默认：本人）"
          clearable
          filterable
          size="small"
        >
          <el-option
            v-for="u in userOptions"
            :key="u.id"
            :label="userLabel(u)"
            :value="u.id"
          />
        </el-select>
        <el-select
          v-model="releaseId"
          class="log-auto-ticket__sel"
          placeholder="关联版本（可选）"
          clearable
          filterable
          size="small"
        >
          <el-option
            v-for="r in releaseOptions"
            :key="r.id"
            :label="releaseLabel(r)"
            :value="r.id"
          />
        </el-select>
        <el-select
          v-model="moduleId"
          class="log-auto-ticket__sel"
          placeholder="所属模块（可选）"
          clearable
          filterable
          size="small"
        >
          <el-option
            v-for="m in moduleOptions"
            :key="m.id"
            :label="m.name || `#${m.id}`"
            :value="m.id"
          />
        </el-select>
      </template>
    </div>
    <el-button
      type="primary"
      :disabled="!canRun"
      :loading="busy || polling"
      class="log-auto-ticket__btn"
      @click="runDraft"
    >
      生成工单草稿
    </el-button>
    <el-alert
      v-if="localError"
      type="error"
      :closable="false"
      show-icon
      class="log-auto-ticket__alert"
      :title="localError"
    />
    <div v-if="job && (polling || isTerminal)" class="log-auto-ticket__status">
      <el-tag :type="statusTagType" size="small">{{ statusLabel }}</el-tag>
      <span v-if="job.celery_task_id" class="log-auto-ticket__tid">task {{ job.celery_task_id.slice(0, 12) }}…</span>
    </div>
    <el-alert
      v-if="defectCreateBanner === 'ok'"
      type="success"
      :closable="false"
      show-icon
      class="log-auto-ticket__alert"
    >
      <span>已创建缺陷：</span>
      <el-link type="primary" class="log-auto-ticket__link" @click.prevent="goDefect(createdDefectId)">
        {{ createdDefectLabel }}
      </el-link>
    </el-alert>
    <el-alert
      v-else-if="defectCreateBanner === 'fail'"
      type="warning"
      :closable="false"
      show-icon
      class="log-auto-ticket__alert"
      :title="`缺陷未创建：${defectCreateError || '未知错误'}`"
    />
    <div v-if="draft" class="log-auto-ticket__result">
      <div class="log-auto-ticket__head">
        <h4 class="log-auto-ticket__title">{{ draft.title }}</h4>
        <div class="log-auto-ticket__tags">
          <el-tag size="small">严重：{{ severityLabel(draft.severity) }}</el-tag>
          <el-tag size="small" type="warning">优先级：{{ priorityLabel(draft.priority) }}</el-tag>
        </div>
      </div>
      <div class="log-auto-ticket__md" v-html="summaryHtml" />
      <div v-if="steps.length" class="log-auto-ticket__steps">
        <div class="log-auto-ticket__steps-title">复现 / 验证步骤</div>
        <ol>
          <li v-for="(s, i) in steps" :key="i">{{ s }}</li>
        </ol>
      </div>
      <p v-if="draft.environment_notes" class="log-auto-ticket__env">
        <strong>环境说明：</strong>{{ draft.environment_notes }}
      </p>
      <div v-if="showManualDefectCreate" class="log-auto-ticket__manual">
        <el-button
          type="success"
          size="small"
          plain
          :loading="manualDefectBusy"
          @click="submitCreateDefectFromDraft"
        >
          从草稿创建缺陷
        </el-button>
        <p class="log-auto-ticket__manual-hint">
          可选用上方处理人 / 版本 / 模块；未选择时沿用任务入队时的记录（无记录则处理人为本人）。
        </p>
      </div>
      <el-button size="small" class="log-auto-ticket__copy" @click="copyJson">复制 JSON</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import MarkdownIt from "markdown-it";
import { getReleasesApi } from "@/api/project";
import { getModulesApi } from "@/api/testcase";
import { getUsersApi } from "@/api/system";
import {
  createDefectFromServerLogAutoTicketJob,
  enqueueServerLogAutoTicket,
  getServerLogAutoTicketJob,
} from "@/api/serverLogs";

const props = defineProps({
  serverId: { type: [Number, String], default: null },
  /** 与「AI 诊断」一致的锚点文本（通常为选中行） */
  anchorText: { type: String, default: "" },
});

const router = useRouter();
const md = new MarkdownIt({ html: false, linkify: true, breaks: true });
const busy = ref(false);
const polling = ref(false);
const localError = ref("");
const job = ref(null);
const draft = ref(null);
let pollTimer = null;
let attempts = 0;
const maxAttempts = 90;

const createDefect = ref(false);
const handlerId = ref(null);
const releaseId = ref(null);
const moduleId = ref(null);
const userOptions = ref([]);
const releaseOptions = ref([]);
const moduleOptions = ref([]);
const manualDefectBusy = ref(false);

function normalizeListPayload(payload) {
  if (!payload) return [];
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload.results)) return payload.results;
  return [];
}

function userLabel(u) {
  const n = (u?.real_name || "").trim();
  const un = (u?.username || "").trim();
  return n ? `${n}（${un || u.id}）` : un || `用户 #${u?.id}`;
}

function releaseLabel(r) {
  const v = (r?.version_no || "").trim();
  const n = (r?.release_name || "").trim();
  return [v, n].filter(Boolean).join(" · ") || `#${r?.id}`;
}

const defectCreateBanner = computed(() => {
  const dc = job.value?.meta?.defect_create;
  if (!dc || dc.skipped) return "";
  if (dc.success === true) return "ok";
  if (dc.success === false) return "fail";
  return "";
});

/** 任务已成功且有草稿，但尚未写入缺陷库（含未勾选同步、同步失败、或旧任务无 meta） */
const showManualDefectCreate = computed(() => {
  if (job.value?.status !== "success" || !draft.value) return false;
  if (job.value?.created_defect?.id) return false;
  if (job.value?.meta?.defect_create?.success === true) return false;
  return true;
});

const defectCreateError = computed(() => job.value?.meta?.defect_create?.error || "");

const createdDefectId = computed(() => job.value?.created_defect?.id || job.value?.meta?.defect_create?.defect_id);

const createdDefectLabel = computed(() => {
  const c = job.value?.created_defect;
  if (c?.defect_no) return `${c.defect_no} ${c.defect_name || ""}`.trim();
  const no = job.value?.meta?.defect_create?.defect_no;
  return no ? String(no) : "打开详情";
});

function goDefect(id) {
  if (!id) return;
  router.push(`/defect/detail/${id}`);
}

async function loadSelectOptions() {
  try {
    const pidRaw = localStorage.getItem("current_project_id");
    const projectParam =
      pidRaw != null && pidRaw !== "" && !Number.isNaN(Number(pidRaw)) ? { project: Number(pidRaw) } : {};
    const [uRes, rRes, mRes] = await Promise.all([
      getUsersApi({ page_size: 500 }),
      getReleasesApi({ page_size: 500 }),
      getModulesApi({ page_size: 500, ...projectParam }),
    ]);
    userOptions.value = normalizeListPayload(uRes.data);
    releaseOptions.value = normalizeListPayload(rRes.data);
    moduleOptions.value = normalizeListPayload(mRes.data);
  } catch {
    userOptions.value = [];
    releaseOptions.value = [];
    moduleOptions.value = [];
  }
}

onMounted(() => {
  loadSelectOptions();
});

const canRun = computed(() => {
  const sid = props.serverId != null && props.serverId !== "";
  const text = String(props.anchorText || "").trim();
  return sid && text.length > 0;
});

const isTerminal = computed(() => {
  const s = job.value?.status;
  return s === "success" || s === "failed";
});

const statusLabel = computed(() => {
  const m = {
    pending: "排队中",
    processing: "分析中",
    success: "已完成",
    failed: "失败",
  };
  return m[job.value?.status] || job.value?.status || "";
});

const statusTagType = computed(() => {
  const s = job.value?.status;
  if (s === "success") return "success";
  if (s === "failed") return "danger";
  if (s === "processing") return "warning";
  return "info";
});

const summaryHtml = computed(() => {
  const raw = draft.value?.summary_markdown || "";
  if (!raw) return "";
  return md.render(raw);
});

const steps = computed(() => {
  const s = draft.value?.reproduction_steps;
  return Array.isArray(s) ? s.filter(Boolean) : [];
});

function severityLabel(v) {
  const m = { 1: "致命", 2: "严重", 3: "一般", 4: "建议" };
  return m[Number(v)] || String(v ?? "");
}

function priorityLabel(v) {
  const m = { 1: "高", 2: "中", 3: "低" };
  return m[Number(v)] || String(v ?? "");
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function pollOnce() {
  if (!job.value?.id) return;
  attempts += 1;
  if (attempts > maxAttempts) {
    stopPoll();
    polling.value = false;
    localError.value = localError.value || "等待结果超时，请稍后在审计记录中查看任务是否已完成。";
    return;
  }
  try {
    const { data } = await getServerLogAutoTicketJob(job.value.id);
    job.value = data;
    if (data?.status === "success" && data?.draft) {
      draft.value = data.draft;
      stopPoll();
      polling.value = false;
    } else if (data?.status === "failed") {
      draft.value = null;
      localError.value = data?.error_message || "任务失败";
      stopPoll();
      polling.value = false;
    }
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || "轮询失败";
    localError.value = String(msg);
    stopPoll();
    polling.value = false;
  }
}

async function runDraft() {
  localError.value = "";
  draft.value = null;
  job.value = null;
  attempts = 0;
  stopPoll();
  polling.value = false;
  if (!canRun.value) {
    ElMessage.warning("请先选中日志文本并确保已选择主机");
    return;
  }
  busy.value = true;
  try {
    const payload = {
      server_id: Number(props.serverId),
      anchor_text: String(props.anchorText || "").trim(),
      window_seconds: 300,
      es_limit: 200,
      create_defect: createDefect.value,
    };
    if (createDefect.value && handlerId.value) payload.defect_handler = handlerId.value;
    if (createDefect.value && releaseId.value) payload.defect_release_version = releaseId.value;
    if (createDefect.value && moduleId.value) payload.defect_module = moduleId.value;

    const { data, status } = await enqueueServerLogAutoTicket(payload);
    if (status === 202 && data?.success && data?.job_id) {
      job.value = { id: data.job_id, status: "pending", celery_task_id: data.task_id || "" };
      busy.value = false;
      polling.value = true;
      await pollOnce();
      if (job.value && job.value.status !== "success" && job.value.status !== "failed") {
        pollTimer = setInterval(pollOnce, 1500);
      } else {
        polling.value = false;
      }
      return;
    }
    localError.value = data?.error || "入队失败";
  } catch (e) {
    const body = e?.response?.data;
    if (body?.job && (e?.response?.status === 503 || e?.response?.status === 502)) {
      job.value = body.job;
    }
    localError.value = body?.error || body?.detail || e?.message || "请求失败";
  } finally {
    busy.value = false;
  }
}

async function copyJson() {
  if (!draft.value) return;
  const text = JSON.stringify(draft.value, null, 2);
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success("已复制 JSON");
  } catch {
    ElMessage.error("复制失败");
  }
}

async function submitCreateDefectFromDraft() {
  if (!job.value?.id) return;
  manualDefectBusy.value = true;
  try {
    const payload = {};
    if (handlerId.value) payload.defect_handler = handlerId.value;
    if (releaseId.value) payload.defect_release_version = releaseId.value;
    if (moduleId.value) payload.defect_module = moduleId.value;
    const { data, status } = await createDefectFromServerLogAutoTicketJob(job.value.id, payload);
    if (data?.job) {
      job.value = data.job;
      if (data.job.draft) draft.value = data.job.draft;
    }
    if (data?.already_created) ElMessage.success("该任务已有关联缺陷");
    else if (status === 201 && data?.success) ElMessage.success("已创建缺陷");
  } catch (e) {
    const msg = e?.response?.data?.error || e?.response?.data?.detail || e?.message || "创建失败";
    ElMessage.error(typeof msg === "string" ? msg : "创建失败");
  } finally {
    manualDefectBusy.value = false;
  }
}

watch(
  () => props.anchorText,
  () => {
    stopPoll();
    polling.value = false;
    busy.value = false;
    if (!props.anchorText) {
      job.value = null;
      draft.value = null;
      localError.value = "";
    }
  }
);

onUnmounted(() => {
  stopPoll();
});
</script>

<style scoped lang="scss">
.log-auto-ticket {
  padding: 4px 0 12px;
  color: #d8f7ff;
  font-size: 14px;
}
.log-auto-ticket__hint {
  margin: 0 0 12px;
  line-height: 1.55;
  opacity: 0.88;
  font-size: 13px;
}
.log-auto-ticket__form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid rgba(0, 207, 236, 0.18);
  background: rgba(0, 40, 80, 0.25);
}
.log-auto-ticket__sel {
  width: 100%;
}
.log-auto-ticket__link {
  margin-left: 6px;
  vertical-align: baseline;
}
.log-auto-ticket__btn {
  margin-bottom: 12px;
}
.log-auto-ticket__alert {
  margin-bottom: 12px;
}
.log-auto-ticket__status {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.log-auto-ticket__tid {
  font-size: 12px;
  opacity: 0.65;
  font-family: ui-monospace, monospace;
}
.log-auto-ticket__result {
  border: 1px solid rgba(0, 207, 236, 0.25);
  border-radius: 8px;
  padding: 12px;
  background: rgba(0, 30, 60, 0.35);
}
.log-auto-ticket__head {
  margin-bottom: 10px;
}
.log-auto-ticket__title {
  margin: 0 0 8px;
  font-size: 16px;
  color: #5cf0ff;
}
.log-auto-ticket__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.log-auto-ticket__md {
  line-height: 1.65;
  margin-bottom: 12px;
  :deep(h1),
  :deep(h2),
  :deep(h3) {
    color: #7eebfd;
    margin: 0.5em 0 0.25em;
  }
  :deep(code) {
    background: rgba(0, 207, 236, 0.12);
    padding: 1px 6px;
    border-radius: 4px;
  }
}
.log-auto-ticket__steps-title {
  font-weight: 600;
  margin-bottom: 6px;
  color: #b6f7ff;
}
.log-auto-ticket__steps ol {
  margin: 0;
  padding-left: 1.2em;
}
.log-auto-ticket__env {
  font-size: 13px;
  opacity: 0.92;
  margin: 10px 0;
}
.log-auto-ticket__copy {
  margin-top: 4px;
}
.log-auto-ticket__manual {
  margin: 12px 0 8px;
  padding-top: 10px;
  border-top: 1px dashed rgba(0, 207, 236, 0.25);
}
.log-auto-ticket__manual-hint {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.5;
  opacity: 0.82;
}
</style>
