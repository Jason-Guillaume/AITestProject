<template>
  <div class="cyber-page knowledge-page">
    <div class="knowledge-bg-mask"></div>
    <el-card class="admin-list-card cyber-card" shadow="never">
      <div class="knowledge-layout">
        <aside class="knowledge-sidenav">
          <div class="knowledge-sidenav__title">文档分类导航</div>
          <el-menu :default-active="activePurpose" class="cyber-menu" @select="onPurposeSelect">
            <el-menu-item v-for="item in purposeTabs" :key="item.value" :index="item.value">
              <span>{{ item.label }}</span>
              <span class="purpose-count-badge">{{ purposeCount(item.value) }}</span>
            </el-menu-item>
          </el-menu>
        </aside>

        <section class="knowledge-main">
          <div class="admin-toolbar-row knowledge-toolbar">
            <div class="admin-toolbar-row__left">
              <div class="title-stack">
                <h3 class="knowledge-title">知识中心 / Knowledge Hub</h3>
                <div class="title-subline">
                  <span class="capability-chip" :class="`capability-chip--${deleteCapability.status}`">
                    <span class="capability-chip__dot"></span>
                    <span>删除能力：{{ deleteCapability.label }}</span>
                  </span>
                </div>
              </div>
            </div>
            <div class="admin-toolbar-row__right">
              <el-button class="cyber-ghost-btn" @click="loadDocuments">刷新</el-button>
              <el-button class="cyber-ghost-btn" @click="retryPendingDocuments">批量重试待处理</el-button>
              <el-button class="holo-btn" @click="openIngestDrawer">导入/新增</el-button>
            </div>
          </div>

          <div class="runtime-summary">
            <el-tag size="small">待处理 {{ runtimeStatus.counters.pending || 0 }}</el-tag>
            <el-tag size="small" type="warning">处理中 {{ runtimeStatus.counters.processing || 0 }}</el-tag>
            <el-tag size="small" type="success">已完成 {{ runtimeStatus.counters.completed || 0 }}</el-tag>
            <el-tag size="small" type="danger">失败 {{ runtimeStatus.counters.failed || 0 }}</el-tag>
          </div>
          <el-alert
            v-if="pageErrorMessage"
            :title="pageErrorMessage"
            type="error"
            show-icon
            :closable="true"
            class="knowledge-error-banner"
            @close="pageErrorMessage = ''"
          />

          <el-table :data="filteredDocuments" border stripe v-loading="loading" class="knowledge-table">
            <el-table-column label="文件名" min-width="220" show-overflow-tooltip>
              <template #default="{ row }">{{ row.title || row.file_name || "-" }}</template>
            </el-table-column>
            <el-table-column label="用途标签" width="150">
              <template #default="{ row }">
                <el-tag effect="plain">{{ purposeLabelByValue(resolvePurpose(row)) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="所属模块" width="160" show-overflow-tooltip>
              <template #default="{ row }">{{ resolveModuleLabel(row) }}</template>
            </el-table-column>
            <el-table-column label="向量化状态" width="180">
              <template #default="{ row }">
                <div class="status-line">
                  <span :class="['status-dot', `status-dot--${row.status || 'pending'}`]"></span>
                  <el-icon v-if="row.status === 'failed'" class="status-icon-fail"><WarningFilled /></el-icon>
                  <span>{{ statusLabel(row.status) }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="失败原因" min-width="200" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.status === "failed" ? row.error_message || "-" : "-" }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="230" align="center">
              <template #default="{ row }">
                <el-button class="action-icon-btn" link :icon="View" title="预览" @click="previewDoc(row)" />
                <el-button class="action-icon-btn brain-btn" link title="语义摘要" @click="runSemanticLookup(row)">
                  <span class="brain-svg-icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24" fill="none">
                      <path d="M8 8.2C8 6.43 9.43 5 11.2 5h1.6C14.57 5 16 6.43 16 8.2v.2a2.8 2.8 0 0 1 1.8 2.62v.58A2.8 2.8 0 0 1 16 14.2V15c0 2.21-1.79 4-4 4s-4-1.79-4-4v-.8a2.8 2.8 0 0 1-1.8-2.6v-.58A2.8 2.8 0 0 1 8 8.4v-.2Z" stroke="currentColor" stroke-width="1.6"/>
                      <path d="M12 7.4v9.2M9.4 10.2h2.6M12 13.2h2.8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
                      <circle cx="7.1" cy="11.3" r="1" fill="currentColor"/>
                      <circle cx="16.9" cy="11.3" r="1" fill="currentColor"/>
                    </svg>
                  </span>
                </el-button>
                <el-button
                  class="action-icon-btn"
                  link
                  :icon="RefreshRight"
                  title="重试处理"
                  :disabled="row.status === 'processing'"
                  @click="retryDocument(row)"
                />
                <el-button class="action-icon-btn danger" link :icon="Delete" title="删除" @click="deleteDocument(row)" />
              </template>
            </el-table-column>
          </el-table>
        </section>
      </div>
    </el-card>

    <el-drawer v-model="ingestDrawerVisible" title="导入/新增文档" size="440px" class="cyber-drawer">
      <el-form :model="docIngestForm" label-width="90px" class="ingest-form">
        <el-form-item label="提交模式">
          <el-radio-group v-model="docIngestForm.mode">
            <el-radio-button label="upload">上传文件</el-radio-button>
            <el-radio-button label="url">提交 URL</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="文档分类">
          <el-select v-model="docIngestForm.purpose" style="width: 100%" @change="markFieldTouched('purpose')">
            <el-option label="PRD/需求文档" value="requirement" />
            <el-option label="规范标准" value="standard" />
            <el-option label="报告/计划模版" value="template" />
          </el-select>
        </el-form-item>
        <el-form-item label="文档名称">
          <el-input v-model="docIngestForm.title" placeholder="可选，默认使用文件名或 URL" @input="markFieldTouched('title')" />
        </el-form-item>
        <el-form-item label="关联模块">
          <el-select v-model="docIngestForm.module_id" clearable filterable style="width: 100%" @change="markFieldTouched('module_id')">
            <el-option v-for="item in moduleOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="语义标签">
          <el-input v-model="docIngestForm.tagsText" placeholder="多个关键词请用逗号分隔" @input="markFieldTouched('tagsText')" />
        </el-form-item>
        <el-form-item v-if="docIngestForm.mode === 'upload'" label="上传文件">
          <el-upload
            class="doc-upload"
            drag
            :auto-upload="false"
            :limit="1"
            accept=".pdf,.md"
            :on-change="onDocIngestFileChange"
            :before-upload="beforeDocIngestUpload"
            :on-remove="onRemoveDocIngestUpload"
          >
            <div>拖拽 PDF / MD 到此，或点击上传</div>
          </el-upload>
          <div v-if="docAutoFilling" class="ingest-autofill-tip">
            AI 正在解析文档并自动填写表单...
          </div>
        </el-form-item>
        <el-form-item v-else label="文档 URL">
          <el-input v-model="docIngestForm.url" placeholder="请输入 http(s):// 开头的 URL" />
        </el-form-item>
        <div class="drawer-actions">
          <el-button @click="ingestDrawerVisible = false">取消</el-button>
          <el-button type="primary" :loading="docSubmitting" @click="submitDocumentIngest">提交处理</el-button>
        </div>
      </el-form>
    </el-drawer>

    <el-drawer v-model="semanticDrawerVisible" :title="semanticDrawerTitle" size="46%" class="cyber-drawer">
      <div class="summary-drawer" v-loading="semanticLoading">
        <div class="summary-drawer__meta" v-if="activeDrawerDocument">
          <el-tag effect="plain">{{ purposeLabelByValue(resolvePurpose(activeDrawerDocument)) }}</el-tag>
          <span>{{ activeDrawerDocument.title || activeDrawerDocument.file_name || "-" }}</span>
        </div>
        <div class="summary-drawer__content">{{ drawerSummaryText }}</div>
        <div v-if="drawerMode === 'preview'" class="preview-panel">
          <div class="summary-drawer__chunks-title">原文预览</div>
          <div class="preview-panel__text">{{ previewText }}</div>
        </div>
        <div v-else class="summary-drawer__chunks">
          <div class="summary-drawer__chunks-title">计划/报告结构化输出</div>
          <div class="structured-json-panel">
            <div class="structured-json-actions">
              <el-button size="small" type="primary" @click="copyStructuredPayload">复制 JSON</el-button>
            </div>
            <pre class="structured-json-content">{{ structuredPayloadText }}</pre>
          </div>

          <div class="summary-drawer__chunks-title">语义洞察</div>
          <div class="insight-list">
            <div v-for="(item, idx) in semanticInsightItems" :key="`insight-${idx}`" class="insight-item">
              {{ idx + 1 }}. {{ item }}
            </div>
          </div>
          <div class="summary-drawer__chunks-title">语义切片结果</div>
          <div v-for="(item, idx) in semanticChunkItems" :key="`${idx}-${item.id || ''}`" class="chunk-card">
            <div class="chunk-card__meta">
              <el-tag size="small" effect="plain">Chunk {{ idx + 1 }}</el-tag>
              <el-tag v-if="item.score !== undefined && item.score !== null" size="small" type="success">
                相似度 {{ Number(item.score).toFixed(3) }}
              </el-tag>
            </div>
            <div class="chunk-card__text">{{ item.text || "暂无片段内容" }}</div>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Delete, RefreshRight, View, WarningFilled } from "@element-plus/icons-vue";
import { getModulesApi } from "@/api/testcase";
import {
  autoFillKnowledgeFormApi,
  deleteKnowledgeDocumentApi,
  extractKnowledgeTextApi,
  getKnowledgeDocumentStatusApi,
  getKnowledgeRuntimeStatusApi,
  ingestKnowledgeDocumentApi,
  listKnowledgeDocumentsApi,
  probeKnowledgeDocumentDeleteApi,
  retryKnowledgeDocumentApi,
} from "@/api/assistant";

const loading = ref(false);
const docSubmitting = ref(false);
const docAutoFilling = ref(false);
const semanticLoading = ref(false);
const pageErrorMessage = ref("");
const documentList = ref([]);
const moduleOptions = ref([]);
const activePurpose = ref("all");
const docIngestUploadFile = ref(null);
const ingestDrawerVisible = ref(false);
const semanticDrawerVisible = ref(false);
const semanticDrawerTitle = ref("语义摘要");
const activeDrawerDocument = ref(null);
const semanticResults = ref([]);
const drawerMode = ref("summary");
const deleteCapability = ref({
  status: "checking",
  label: "检测中",
  tagType: "info",
  hint: "待检测",
});
let documentPollingTimer = null;

const purposeTabs = [
  { label: "全部文档", value: "all" },
  { label: "需求文档", value: "requirement" },
  { label: "规范标准", value: "standard" },
  { label: "报告/计划模版", value: "template" },
];
const purposeCategoryMap = {
  requirement: "functional_test",
  standard: "best_practice",
  template: "template",
};
const categoryPurposeMap = {
  template: "template",
  best_practice: "standard",
  faq: "standard",
  functional_test: "requirement",
  api_test: "requirement",
  performance_test: "standard",
  security_test: "standard",
  ui_automation_test: "standard",
};

const runtimeStatus = ref({
  counters: { pending: 0, processing: 0, completed: 0, failed: 0 },
});

const docIngestForm = ref({
  mode: "upload",
  purpose: "requirement",
  title: "",
  module_id: null,
  tagsText: "",
  url: "",
});
const docIngestTouched = ref({
  purpose: false,
  title: false,
  module_id: false,
  tagsText: false,
});

const filteredDocuments = computed(() => {
  if (activePurpose.value === "all") return documentList.value;
  return documentList.value.filter((item) => resolvePurpose(item) === activePurpose.value);
});
const drawerSummaryText = computed(() => {
  if (drawerMode.value === "preview") {
    return "以下为文档原文预览片段（用于快速核对原始内容）。";
  }
  if (semanticResults.value.length) return "以下切片由语义检索生成，用于快速理解文档核心语义。";
  const doc = activeDrawerDocument.value || {};
  return doc.semantic_summary || doc.summary || doc.chunk_preview || "暂无摘要，可先执行语义检索。";
});
const previewText = computed(() => {
  const doc = activeDrawerDocument.value || {};
  const chunks = Array.isArray(doc.semantic_chunks) ? doc.semantic_chunks : [];
  const merged = chunks
    .map((x) => (x?.text || "").trim())
    .filter(Boolean)
    .join("\n\n");
  const candidate = doc.raw_text_preview || doc.preview_text || merged || doc.semantic_summary || "";
  return (candidate || "暂无可预览内容").slice(0, 3200);
});
const semanticChunkItems = computed(() => {
  if (semanticResults.value.length) {
    return semanticResults.value.map((x) => ({
      id: x.id || x.doc_id || "",
      score: x.score,
      text: x.content || x.markdown_content || "",
    }));
  }
  return extractChunkItems(activeDrawerDocument.value || {});
});
const semanticInsightItems = computed(() => {
  const chunks = semanticChunkItems.value || [];
  const texts = chunks.map((x) => (x.text || "").trim()).filter(Boolean);
  if (!texts.length) return ["暂无语义洞察，建议重新入库文档以生成更多切片。"];

  const merged = texts.join(" ");
  const insights = [];
  if (/必须|应当|禁止|不得|需|需要/.test(merged)) insights.push("检测到规范约束语句，可作为用例断言依据。");
  if (/异常|失败|错误|边界|超时|空值|非法/.test(merged)) insights.push("包含异常/边界信息，适合补充负向与鲁棒性用例。");
  if (/接口|API|请求|响应|状态码|鉴权/.test(merged)) insights.push("存在接口语义，可映射为 API 测试点。");
  if (/性能|并发|耗时|吞吐|延迟/.test(merged)) insights.push("包含性能相关线索，可扩展性能基线与压测场景。");
  if (!insights.length) insights.push("建议按切片关键词提炼 3-5 条测试关注点后再生成计划。");
  return insights.slice(0, 4);
});
const structuredPayload = computed(() => {
  const doc = activeDrawerDocument.value || {};
  const chunks = semanticChunkItems.value || [];
  const textBlob = chunks.map((x) => x.text || "").join(" ");
  const hasApi = /接口|API|请求|响应|状态码|鉴权/.test(textBlob);
  const hasPerf = /性能|并发|耗时|吞吐|延迟|压测/.test(textBlob);
  const hasRisk = /异常|失败|错误|边界|非法|超时/.test(textBlob);
  const hasRule = /必须|应当|禁止|不得/.test(textBlob);

  const suggested = [];
  if (hasApi) suggested.push("API");
  if (hasPerf) suggested.push("Performance");
  if (hasRisk) suggested.push("Negative");
  if (!suggested.length) suggested.push("Functional");

  const priority = hasRisk || hasRule ? "P1" : "P2";
  const riskLevel = hasRisk ? "中-高" : "中";

  return {
    document_id: doc.id || null,
    title: doc.title || doc.file_name || "",
    purpose: resolvePurpose(doc),
    test_objective: (doc.semantic_summary || "").slice(0, 160) || "基于文档语义提炼可执行测试目标",
    scope: {
      in_scope: semanticInsightItems.value.slice(0, 3),
      out_of_scope: ["未在文档明确描述的外部依赖行为"],
    },
    risk: {
      level: riskLevel,
      points: semanticInsightItems.value.filter((x) => /异常|风险|边界|错误/.test(x)),
    },
    suggested_test_types: suggested,
    priority,
    recommended_actions: [
      "先覆盖主流程与关键约束断言",
      "补充异常/边界场景",
      "按模块生成自动化回归集合",
    ],
    chunk_refs: chunks.slice(0, 5).map((x, i) => ({
      index: i + 1,
      score: x.score ?? null,
      text: (x.text || "").slice(0, 140),
    })),
  };
});
const structuredPayloadText = computed(() => JSON.stringify(structuredPayload.value, null, 2));

function onPurposeSelect(value) {
  activePurpose.value = value;
}

function resolveApiErrorMessage(error, fallback = "请求失败") {
  const status = error?.response?.status;
  const data = error?.response?.data || {};
  const msg =
    data?.message ||
    data?.msg ||
    data?.error ||
    (typeof data === "string" ? data : "");
  if (msg) return String(msg);
  if (!status) return `${fallback}：网络异常或后端未启动`;
  if (status === 401) return `${fallback}：登录已过期，请重新登录`;
  if (status === 403) return `${fallback}：当前账号无权限`;
  if (status === 404) return `${fallback}：接口不存在，请确认后端已更新并重启`;
  if (status >= 500) return `${fallback}：服务端异常（${status}）`;
  return `${fallback}（HTTP ${status}）`;
}

function purposeCount(value) {
  if (value === "all") return documentList.value.length;
  return documentList.value.filter((x) => resolvePurpose(x) === value).length;
}

function purposeLabelByValue(value) {
  return purposeTabs.find((x) => x.value === value)?.label || "未分类";
}

function resolvePurpose(row) {
  const purpose = row?.purpose || row?.usage || row?.doc_usage || row?.category;
  if (["requirement", "standard", "template"].includes(purpose)) return purpose;
  if (categoryPurposeMap[purpose]) return categoryPurposeMap[purpose];
  return "requirement";
}

function resolveModuleLabel(row) {
  const id = row?.module_id || row?.module;
  if (!id) return "-";
  return moduleOptions.value.find((x) => x.value === id)?.label || `模块 #${id}`;
}

function statusLabel(status) {
  if (status === "completed") return "已完成";
  if (status === "failed") return "失效";
  if (status === "processing") return "处理中";
  return "待处理";
}

function extractChunkItems(doc) {
  const chunkCandidates = doc.chunks || doc.chunk_summaries || doc.semantic_chunks || doc.slices;
  if (Array.isArray(chunkCandidates) && chunkCandidates.length) {
    return chunkCandidates.map((x, idx) => ({
      id: x.id || x.chunk_id || `chunk-${idx}`,
      score: x.score ?? x.similarity ?? x.relevance,
      text: x.summary || x.text || x.content || x.chunk_text || "",
    }));
  }
  const fallback = (doc.semantic_summary || doc.summary || "")
    .split(/\n{2,}|。/g)
    .map((x) => x.trim())
    .filter(Boolean);
  return fallback.map((text, idx) => ({ id: `fallback-${idx}`, text })).slice(0, 8);
}

function openIngestDrawer() {
  ingestDrawerVisible.value = true;
}

async function checkDeleteCapability() {
  try {
    // 发送“删除 id=0”探针：正常后端应返回 404 文档不存在（而不是 405/路由404）。
    await probeKnowledgeDocumentDeleteApi(0);
    // 理论上不会命中（id=0 不存在），保守按可用处理。
    deleteCapability.value = { status: "ok", label: "可用", tagType: "success", hint: "删除接口已生效" };
  } catch (error) {
    const status = error?.response?.status;
    const msg = String(error?.response?.data?.message || error?.response?.data?.msg || "");
    // 401/403 说明路由存在但权限不足，能力应视为可用。
    if (status === 401 || status === 403) {
      deleteCapability.value = {
        status: "limited",
        label: "可用但受限",
        tagType: "warning",
        hint: "删除接口已生效（当前账户权限受限）",
      };
    } else if (status === 404 && msg.includes("文档不存在")) {
      // 能进入删除视图并返回“文档不存在”，说明删除路由已生效。
      deleteCapability.value = {
        status: "ok",
        label: "可用",
        tagType: "success",
        hint: "删除接口已生效",
      };
    } else if (status === 404) {
      deleteCapability.value = {
        status: "down",
        label: "未生效",
        tagType: "danger",
        hint: "后端可能未加载最新删除路由",
      };
    } else if (status === 405) {
      deleteCapability.value = {
        status: "down",
        label: "未生效",
        tagType: "danger",
        hint: "接口方法不支持（旧版本后端）",
      };
    } else {
      deleteCapability.value = {
        status: "down",
        label: "未生效",
        tagType: "danger",
        hint: "探测失败，请检查后端服务",
      };
    }
  }
}

function beforeDocIngestUpload(file) {
  const ext = (file?.name || "").split(".").pop()?.toLowerCase();
  if (!["pdf", "md"].includes(ext)) {
    ElMessage.warning("仅支持 .pdf/.md 文件");
    return false;
  }
  // 始终阻止组件默认上传，提交时统一走 ingest 接口。
  return false;
}

function onDocIngestFileChange(uploadFile) {
  const raw = uploadFile?.raw || null;
  if (!raw) {
    docIngestUploadFile.value = null;
    return;
  }
  const ext = (raw?.name || "").split(".").pop()?.toLowerCase();
  if (!["pdf", "md"].includes(ext)) {
    ElMessage.warning("仅支持 .pdf/.md 文件");
    docIngestUploadFile.value = null;
    return;
  }
  docIngestUploadFile.value = raw;
  autoFillFormByUploadedFile(raw);
}

function onRemoveDocIngestUpload() {
  docIngestUploadFile.value = null;
}

function markFieldTouched(field) {
  if (!field || !Object.prototype.hasOwnProperty.call(docIngestTouched.value, field)) return;
  docIngestTouched.value[field] = true;
}

function resetDocIngestTouched() {
  docIngestTouched.value = {
    purpose: false,
    title: false,
    module_id: false,
    tagsText: false,
  };
}

function normalizeDocText(raw) {
  return String(raw || "")
    .replace(/\r/g, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function inferPurposeByText(text) {
  const body = String(text || "");
  if (/模板|计划|报告|复盘|周报|日报|里程碑/.test(body)) return "template";
  if (/规范|标准|准则|流程|制度|SOP|最佳实践/.test(body)) return "standard";
  return "requirement";
}

function inferTitleByText(fileName, text) {
  const cleanName = String(fileName || "").replace(/\.(pdf|md)$/i, "").trim();
  const firstLine = String(text || "")
    .split("\n")
    .map((x) => x.trim())
    .find((x) => x.length >= 4 && x.length <= 40);
  return firstLine || cleanName || "";
}

function inferModuleIdByText(text) {
  const body = String(text || "");
  if (!body || !Array.isArray(moduleOptions.value) || !moduleOptions.value.length) return null;
  let best = null;
  for (const item of moduleOptions.value) {
    const label = String(item?.label || "").trim();
    if (!label || label.length < 2) continue;
    const score = body.includes(label) ? label.length : 0;
    if (!best || score > best.score) best = { id: item.value, score };
  }
  return best?.score > 0 ? best.id : null;
}

function inferTagsByText(text) {
  const body = String(text || "");
  const dictionary = [
    "登录",
    "注册",
    "鉴权",
    "权限",
    "接口",
    "API",
    "状态码",
    "并发",
    "性能",
    "安全",
    "SQL注入",
    "越权",
    "支付",
    "订单",
    "用户",
    "搜索",
    "消息",
    "文件上传",
    "边界",
    "异常",
  ];
  const hit = [];
  for (const word of dictionary) {
    if (body.toLowerCase().includes(word.toLowerCase())) hit.push(word);
    if (hit.length >= 6) break;
  }
  return hit;
}

async function autoFillFormByUploadedFile(file) {
  docAutoFilling.value = true;
  try {
    const fd = new FormData();
    fd.append("file", file);
    const { data } = await autoFillKnowledgeFormApi(fd);
    if (!data?.success || !data?.data) {
      ElMessage.warning(data?.message || "自动填写失败，已回退本地规则");
      // 回退：接口异常时不阻断，使用页面本地规则兜底
      await autoFillFormByExtractFallback(file);
      return;
    }
    const meta = data.data || {};
    const text = normalizeDocText(meta.text_preview || "");
    const purpose = String(meta.purpose || "").trim();
    if (!docIngestTouched.value.purpose && ["requirement", "standard", "template"].includes(purpose)) {
      docIngestForm.value.purpose = purpose;
    } else if (!docIngestTouched.value.purpose) {
      docIngestForm.value.purpose = inferPurposeByText(text);
    }
    if (!docIngestTouched.value.title && !String(docIngestForm.value.title || "").trim()) {
      docIngestForm.value.title = String(meta.title || "").trim() || inferTitleByText(file?.name || "", text);
    }
    if (!docIngestTouched.value.module_id && !docIngestForm.value.module_id) {
      const mid = Number(meta.module_id || 0);
      docIngestForm.value.module_id = mid > 0 ? mid : inferModuleIdByText(text);
    }
    if (!docIngestTouched.value.tagsText && !String(docIngestForm.value.tagsText || "").trim()) {
      const tags = Array.isArray(meta.tags) && meta.tags.length ? meta.tags : inferTagsByText(text);
      if (tags.length) docIngestForm.value.tagsText = tags.join(", ");
    }
    ElMessage.success(`AI 已自动填写表单（${meta.source === "llm" ? "大模型" : "规则"}）`);
  } catch (error) {
    ElMessage.warning(error?.response?.data?.message || "自动填写失败，已回退本地规则");
    await autoFillFormByExtractFallback(file);
  } finally {
    docAutoFilling.value = false;
  }
}

async function autoFillFormByExtractFallback(file) {
  try {
    const fd = new FormData();
    fd.append("file", file);
    const { data } = await extractKnowledgeTextApi(fd);
    if (!data?.success) return;
    const text = normalizeDocText(data?.text);
    if (!text) return;
    if (!docIngestTouched.value.purpose) {
      docIngestForm.value.purpose = inferPurposeByText(text);
    }
    if (!docIngestTouched.value.title && !String(docIngestForm.value.title || "").trim()) {
      docIngestForm.value.title = inferTitleByText(file?.name || "", text);
    }
    if (!docIngestTouched.value.module_id && !docIngestForm.value.module_id) {
      docIngestForm.value.module_id = inferModuleIdByText(text);
    }
    if (!docIngestTouched.value.tagsText && !String(docIngestForm.value.tagsText || "").trim()) {
      const tags = inferTagsByText(text);
      if (tags.length) docIngestForm.value.tagsText = tags.join(", ");
    }
  } catch (_) {
    // ignore fallback failure
  }
}

async function loadModules() {
  try {
    const { data } = await getModulesApi({ page_size: 300 });
    const rows = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
    moduleOptions.value = rows.map((x) => ({ label: x.name || `模块 #${x.id}`, value: x.id }));
  } catch (_) {
    moduleOptions.value = [];
  }
}

async function loadDocuments() {
  loading.value = true;
  try {
    const { data } = await listKnowledgeDocumentsApi({ page_size: 120 });
    documentList.value = Array.isArray(data?.results) ? data.results : [];
    pageErrorMessage.value = "";
    await loadRuntimeStatus();
    ensureDocumentPolling();
  } catch (error) {
    documentList.value = [];
    stopDocumentPolling();
    pageErrorMessage.value = resolveApiErrorMessage(error, "文档列表加载失败");
    ElMessage.error(pageErrorMessage.value);
  } finally {
    loading.value = false;
  }
}

async function loadRuntimeStatus() {
  try {
    const { data } = await getKnowledgeRuntimeStatusApi();
    runtimeStatus.value = {
      counters: data?.counters || { pending: 0, processing: 0, completed: 0, failed: 0 },
    };
  } catch (_) {
    // ignore
  }
}

function hasProcessingDocuments() {
  return documentList.value.some((x) => x?.status === "processing" || x?.status === "pending");
}

function stopDocumentPolling() {
  if (!documentPollingTimer) return;
  clearInterval(documentPollingTimer);
  documentPollingTimer = null;
}

function ensureDocumentPolling() {
  if (!hasProcessingDocuments()) {
    stopDocumentPolling();
    return;
  }
  if (documentPollingTimer) return;
  documentPollingTimer = setInterval(() => {
    loadDocuments();
  }, 3000);
}

async function submitDocumentIngest() {
  docSubmitting.value = true;
  try {
    const mode = (docIngestForm.value.mode || "upload").trim();
    const title = (docIngestForm.value.title || "").trim();
    const moduleId = docIngestForm.value.module_id;
    const purpose = docIngestForm.value.purpose;
    const category = purposeCategoryMap[purpose] || "functional_test";
    const tags = (docIngestForm.value.tagsText || "")
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);

    if (mode === "upload") {
      if (!docIngestUploadFile.value) {
        ElMessage.warning("请先选择文件");
        return;
      }
      const fd = new FormData();
      fd.append("mode", "upload");
      fd.append("file", docIngestUploadFile.value);
      if (title) fd.append("title", title);
      if (moduleId) fd.append("module_id", String(moduleId));
      fd.append("category", category);
      if (tags.length) fd.append("tags", JSON.stringify(tags));
      await ingestKnowledgeDocumentApi(fd);
    } else {
      const url = (docIngestForm.value.url || "").trim();
      if (!/^https?:\/\//i.test(url)) {
        ElMessage.warning("URL 必须以 http:// 或 https:// 开头");
        return;
      }
      const payload = { mode: "url", url, category, tags };
      if (title) payload.title = title;
      if (moduleId) payload.module_id = moduleId;
      await ingestKnowledgeDocumentApi(payload);
    }

    ElMessage.success("文档已提交处理");
    pageErrorMessage.value = "";
    ingestDrawerVisible.value = false;
    docIngestForm.value = {
      mode: "upload",
      purpose: "requirement",
      title: "",
      module_id: null,
      tagsText: "",
      url: "",
    };
    resetDocIngestTouched();
    docIngestUploadFile.value = null;
    await loadDocuments();
  } catch (error) {
    pageErrorMessage.value = resolveApiErrorMessage(error, "提交失败");
    ElMessage.error(pageErrorMessage.value);
  } finally {
    docSubmitting.value = false;
  }
}

async function previewDoc(row) {
  semanticDrawerTitle.value = "文档预览";
  drawerMode.value = "preview";
  semanticResults.value = [];
  activeDrawerDocument.value = row;
  semanticDrawerVisible.value = true;
  if (!row?.id) return;
  semanticLoading.value = true;
  try {
    const { data } = await getKnowledgeDocumentStatusApi(row.id);
    if (data?.data) activeDrawerDocument.value = { ...row, ...data.data };
  } finally {
    semanticLoading.value = false;
  }
}

async function runSemanticLookup(row) {
  semanticDrawerTitle.value = "语义摘要切片";
  drawerMode.value = "summary";
  semanticDrawerVisible.value = true;
  activeDrawerDocument.value = row;
  semanticResults.value = [];
  semanticLoading.value = true;
  try {
    if (!row?.id) return;
    const { data } = await getKnowledgeDocumentStatusApi(row.id);
    if (data?.data) {
      activeDrawerDocument.value = { ...row, ...data.data };
    }
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || "摘要读取失败");
  } finally {
    semanticLoading.value = false;
  }
}

async function deleteDocument(row) {
  if (!row?.id) return;
  try {
    await ElMessageBox.confirm(`确认删除文档「${row.title || row.file_name || row.id}」吗？`, "删除确认", {
      type: "warning",
    });
    await deleteKnowledgeDocumentApi(row.id);
    ElMessage.success("删除成功");
    await loadDocuments();
  } catch (error) {
    if (error !== "cancel" && error !== "close") {
      const status = error?.response?.status;
      if (status === 403) {
        ElMessage.error("删除失败：当前账号无权限删除该文档");
      } else if (status === 404 || status === 405) {
        ElMessage.error("删除失败：后端删除接口未生效，请重启后端服务后重试");
        deleteCapability.value = {
          status: "down",
          label: "未生效",
          tagType: "danger",
          hint: "删除接口未生效",
        };
      } else {
        ElMessage.error(error?.response?.data?.message || "删除失败");
      }
    }
  }
}

async function retryDocument(row) {
  if (!row?.id) return;
  if (row.status === "processing") {
    ElMessage.warning("当前任务仍在处理中");
    return;
  }
  try {
    await retryKnowledgeDocumentApi(row.id);
    ElMessage.success("已重新提交处理任务");
    await loadDocuments();
  } catch (error) {
    ElMessage.error(resolveApiErrorMessage(error, "重试提交失败"));
  }
}

async function retryPendingDocuments() {
  const pendingRows = (documentList.value || []).filter((x) => x?.status === "pending");
  if (!pendingRows.length) {
    ElMessage.warning("当前没有待处理文档");
    return;
  }
  try {
    const results = await Promise.allSettled(
      pendingRows.map((row) => retryKnowledgeDocumentApi(row.id))
    );
    const success = results.filter((x) => x.status === "fulfilled").length;
    const failed = results.length - success;
    if (failed === 0) {
      ElMessage.success(`已提交 ${success} 条待处理文档`);
    } else {
      ElMessage.warning(`已提交 ${success} 条，失败 ${failed} 条`);
    }
    await loadDocuments();
  } catch (error) {
    ElMessage.error(resolveApiErrorMessage(error, "批量重试失败"));
  }
}

async function copyStructuredPayload() {
  try {
    await navigator.clipboard.writeText(structuredPayloadText.value);
    ElMessage.success("结构化 JSON 已复制");
  } catch (_) {
    ElMessage.warning("复制失败，请手动复制");
  }
}

loadDocuments();
loadModules();
checkDeleteCapability();
onBeforeUnmount(() => stopDocumentPolling());
</script>

<style scoped>
.knowledge-page {
  position: relative;
  overflow: hidden;
  --holo-glitch-duration: 420ms;
  --holo-sweep-duration: 700ms;
  --row-scan-duration: 680ms;
  --row-scan-opacity: 0.28;
  --processing-pulse-duration: 1.25s;
  --failed-pulse-duration: 1.1s;
}

.knowledge-bg-mask {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 20% 20%, rgba(0, 255, 255, 0.08), transparent 36%),
    radial-gradient(circle at 84% 12%, rgba(56, 189, 248, 0.08), transparent 32%),
    repeating-linear-gradient(
      115deg,
      rgba(56, 189, 248, 0.05) 0,
      rgba(56, 189, 248, 0.05) 1px,
      transparent 1px,
      transparent 12px
    );
  opacity: 0.5;
}

.cyber-card {
  position: relative;
  backdrop-filter: blur(8px);
  background: rgba(10, 18, 34, 0.42);
  border: 1px solid rgba(56, 189, 248, 0.28);
  box-shadow: 0 0 10px rgba(56, 189, 248, 0.12);
}

.knowledge-layout {
  display: grid;
  grid-template-columns: 168px 1fr;
  gap: 10px;
}

.knowledge-sidenav,
.knowledge-main {
  backdrop-filter: blur(12px);
  background: rgba(8, 15, 30, 0.38);
  border: 1px solid rgba(34, 211, 238, 0.3);
  box-shadow: inset 0 0 8px rgba(0, 255, 255, 0.08);
  border-radius: 12px;
}

.knowledge-sidenav {
  padding: 8px 6px;
  align-self: start;
}

.knowledge-main {
  padding: 10px;
  min-height: 0;
  position: relative;
}

.knowledge-main::before {
  content: "";
  position: absolute;
  left: 10px;
  right: 10px;
  top: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(34, 211, 238, 0.9), transparent);
  opacity: 0.8;
}

.knowledge-sidenav__title {
  font-size: 12px;
  color: #9be3ff;
  margin-bottom: 8px;
  padding-left: 8px;
}

.cyber-menu :deep(.el-menu) {
  border: none;
  background: transparent;
}

.cyber-menu :deep(.el-menu-item) {
  border-radius: 8px;
  margin: 4px 0;
  display: flex;
  justify-content: space-between;
  border: 1px solid rgba(56, 189, 248, 0.15);
  background: rgba(2, 6, 23, 0.26);
}

.purpose-count-badge {
  min-width: 24px;
  height: 20px;
  border-radius: 999px;
  padding: 0 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #a5f3fc;
  border: 1px solid rgba(34, 211, 238, 0.38);
  background: rgba(8, 47, 73, 0.22);
  box-shadow: inset 0 0 6px rgba(34, 211, 238, 0.2);
}

.knowledge-title {
  margin: 0;
  letter-spacing: 0.4px;
  font-weight: 600;
  font-size: 16px;
  color: #d6f4ff;
  text-shadow: 0 0 10px rgba(56, 189, 248, 0.45);
}

.title-stack {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.title-subline {
  line-height: 1.2;
  margin-top: 2px;
}

.capability-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 22px;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 12px;
  color: #d6f4ff;
  border: 1px solid rgba(56, 189, 248, 0.36);
  background: rgba(8, 47, 73, 0.26);
}

.capability-chip__dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 8px rgba(34, 197, 94, 0.7);
}

.capability-chip--ok .capability-chip__dot {
  background: #22c55e;
  box-shadow: 0 0 8px rgba(34, 197, 94, 0.7);
}

.capability-chip--limited .capability-chip__dot {
  background: #f59e0b;
  box-shadow: 0 0 8px rgba(245, 158, 11, 0.75);
}

.capability-chip--down .capability-chip__dot {
  background: #ef4444;
  box-shadow: 0 0 8px rgba(239, 68, 68, 0.8);
}

.capability-chip--checking .capability-chip__dot {
  background: #38bdf8;
  box-shadow: 0 0 8px rgba(56, 189, 248, 0.8);
}

.holo-btn {
  position: relative;
  overflow: hidden;
  background: linear-gradient(120deg, rgba(34, 211, 238, 0.9), rgba(37, 99, 235, 0.8));
  color: #f8feff;
  border: 1px solid rgba(103, 232, 249, 0.9);
  box-shadow: 0 0 10px rgba(34, 211, 238, 0.5), inset 0 0 8px rgba(255, 255, 255, 0.18);
}

.holo-btn::before {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.25), transparent);
  transform: translateX(-130%);
  pointer-events: none;
}

.holo-btn:hover {
  animation: holoGlitch var(--holo-glitch-duration) ease-in-out 1;
}

.holo-btn:hover::before {
  animation: holoSweep var(--holo-sweep-duration) ease-out 1;
}

.cyber-ghost-btn {
  border-color: rgba(56, 189, 248, 0.45);
  color: #bae6fd;
  background: rgba(15, 23, 42, 0.32);
}

.cyber-ghost-btn:hover {
  border-color: rgba(34, 211, 238, 0.8);
  box-shadow: 0 0 8px rgba(34, 211, 238, 0.35);
}

.runtime-summary {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.knowledge-error-banner {
  margin-bottom: 10px;
}

.knowledge-table :deep(.el-table__cell) {
  background: rgba(255, 255, 255, 0.01);
  border-color: rgba(56, 189, 248, 0.2);
  padding-top: 6px;
  padding-bottom: 6px;
}

.knowledge-table :deep(.el-table__header-wrapper th) {
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.92), rgba(15, 23, 42, 0.72));
  color: #bfeeff;
  text-shadow: 0 0 8px rgba(56, 189, 248, 0.3);
}

.knowledge-table :deep(.el-table__body tr) {
  position: relative;
}

.knowledge-table :deep(.el-table__body tr td) {
  position: relative;
  overflow: hidden;
}

.knowledge-table :deep(.el-table__body tr:hover td)::after {
  content: "";
  position: absolute;
  left: -40%;
  top: 0;
  width: 34%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(34, 211, 238, 0.12),
    rgba(56, 189, 248, var(--row-scan-opacity)),
    transparent
  );
  transform: skewX(-18deg);
  animation: rowScan var(--row-scan-duration) ease-out;
  pointer-events: none;
}

.status-line {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.status-dot--completed {
  background: #10b981;
}

.status-dot--processing {
  background: #38bdf8;
  box-shadow: 0 0 8px rgba(56, 189, 248, 0.8);
  animation: pulse var(--processing-pulse-duration) ease-in-out infinite;
}

.status-dot--pending {
  background: #94a3b8;
}

.status-dot--failed {
  background: #ef4444;
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.9);
  animation: pulseRed var(--failed-pulse-duration) ease-in-out infinite;
}

.status-icon-fail {
  color: #f87171;
}

.action-icon-btn {
  color: #7dd3fc;
}

.action-icon-btn:hover {
  text-shadow: 0 0 8px rgba(34, 211, 238, 0.65);
  transform: translateY(-1px);
}

.action-icon-btn.brain-btn {
  color: #22d3ee;
  text-shadow: 0 0 8px rgba(34, 211, 238, 0.7);
}

.brain-svg-icon {
  width: 16px;
  height: 16px;
  display: inline-flex;
}

.brain-svg-icon svg {
  width: 16px;
  height: 16px;
}

.action-icon-btn.danger {
  color: #f87171;
}

.drawer-actions {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.doc-upload :deep(.el-upload-dragger) {
  border-color: rgba(56, 189, 248, 0.4);
  background: rgba(8, 15, 30, 0.35);
}

.ingest-autofill-tip {
  margin-top: 8px;
  color: #93c5fd;
  font-size: 12px;
}

.summary-drawer {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.summary-drawer__meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.summary-drawer__content {
  border: 1px solid rgba(56, 189, 248, 0.32);
  border-radius: 8px;
  padding: 12px;
  background: rgba(15, 23, 42, 0.26);
  color: #dbeafe;
}

.summary-drawer__chunks-title {
  color: #93c5fd;
}

.summary-drawer__chunks {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chunk-card {
  border: 1px solid rgba(56, 189, 248, 0.3);
  border-radius: 8px;
  padding: 10px;
  background: rgba(15, 23, 42, 0.22);
}

.chunk-card__meta {
  display: flex;
  gap: 8px;
  margin-bottom: 6px;
}

.chunk-card__text {
  white-space: pre-wrap;
  line-height: 1.6;
  color: #cfe8ff;
}

.preview-panel__text {
  border: 1px solid rgba(56, 189, 248, 0.3);
  border-radius: 8px;
  padding: 10px;
  background: rgba(15, 23, 42, 0.22);
  white-space: pre-wrap;
  line-height: 1.65;
  color: #dbeafe;
  max-height: 440px;
  overflow: auto;
}

.insight-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.insight-item {
  border-left: 2px solid rgba(34, 211, 238, 0.55);
  padding: 6px 10px;
  background: rgba(8, 47, 73, 0.2);
  color: #bae6fd;
}

.structured-json-panel {
  border: 1px solid rgba(56, 189, 248, 0.3);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.22);
}

.structured-json-actions {
  padding: 8px 10px 0;
  display: flex;
  justify-content: flex-end;
}

.structured-json-content {
  margin: 0;
  padding: 8px 10px 12px;
  max-height: 220px;
  overflow: auto;
  color: #dbeafe;
  font-size: 12px;
  line-height: 1.5;
}

.cyber-drawer :deep(.el-drawer) {
  background: rgba(7, 14, 28, 0.86);
  backdrop-filter: blur(10px);
}

.cyber-drawer :deep(.el-drawer__header) {
  position: relative;
  border-bottom: 1px solid rgba(34, 211, 238, 0.35);
  color: #cffafe;
  text-shadow: 0 0 8px rgba(34, 211, 238, 0.45);
}

.cyber-drawer :deep(.el-drawer__header)::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(34, 211, 238, 0.95), transparent);
  animation: scanline 2.4s linear infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@keyframes pulseRed {
  0%,
  100% {
    opacity: 1;
    box-shadow: 0 0 10px rgba(239, 68, 68, 0.9);
  }
  50% {
    opacity: 0.5;
    box-shadow: 0 0 3px rgba(239, 68, 68, 0.6);
  }
}

@keyframes scanline {
  0% {
    transform: translateX(-35%);
    opacity: 0.5;
  }
  50% {
    transform: translateX(0%);
    opacity: 1;
  }
  100% {
    transform: translateX(35%);
    opacity: 0.5;
  }
}

@keyframes holoSweep {
  0% {
    transform: translateX(-130%);
    opacity: 0;
  }
  30% {
    opacity: 0.9;
  }
  100% {
    transform: translateX(130%);
    opacity: 0;
  }
}

@keyframes holoGlitch {
  0% {
    transform: translateX(0);
    text-shadow: 0 0 0 transparent;
  }
  25% {
    transform: translateX(0.6px);
    text-shadow:
      -1px 0 rgba(255, 0, 85, 0.32),
      1px 0 rgba(0, 255, 255, 0.35);
  }
  55% {
    transform: translateX(-0.8px);
    text-shadow:
      1px 0 rgba(255, 0, 85, 0.28),
      -1px 0 rgba(0, 255, 255, 0.32);
  }
  100% {
    transform: translateX(0);
    text-shadow: 0 0 0 transparent;
  }
}

@keyframes rowScan {
  0% {
    left: -40%;
    opacity: 0;
  }
  20% {
    opacity: 1;
  }
  100% {
    left: 120%;
    opacity: 0;
  }
}
</style>

