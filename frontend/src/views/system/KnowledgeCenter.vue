<template>
  <div class="cyber-page knowledge-page">
    <div class="knowledge-bg-mask"></div>
    <el-card class="admin-list-card cyber-card" shadow="never">
      <div class="knowledge-layout knowledge-layout--module-dock">
        <aside
          class="module-tree-dock"
          :class="{
            'module-tree-dock--wide': isModuleDockWideLayout,
            'module-tree-dock--overlay': !isModuleDockWideLayout,
            'is-expanded': isPurposeDockExpanded,
          }"
        >
          <div class="module-tree-rail" aria-label="文档分类快捷栏">
            <el-tooltip :content="isPurposeDockExpanded ? '收起分类面板' : '展开分类面板'" placement="right" :show-after="200">
              <el-button
                class="module-tree-rail__expand-btn"
                :class="{ 'is-expanded': isPurposeDockExpanded }"
                text
                type="primary"
                :aria-expanded="isPurposeDockExpanded"
                @click.stop="togglePurposeDockExpanded"
              >
                <el-icon :size="20"><DArrowLeft v-if="isPurposeDockExpanded" /><DArrowRight v-else /></el-icon>
              </el-button>
            </el-tooltip>
          </div>

          <div class="module-tree-slide" :class="{ 'is-open': isPurposeDockExpanded }">
            <el-card class="tc-card tc-card--tree admin-list-card tc-tree-panel" shadow="never">
              <div class="tree-panel__head">
                <div class="tree-panel__all-label">文档分类</div>
                <div class="tree-panel__head-actions">
                  <el-tooltip
                    :content="isModuleDockWideLayout ? '收起侧栏' : '关闭分类面板'"
                    placement="bottom"
                    :show-after="400"
                  >
                    <el-button class="tree-panel__icon-btn" text type="primary" size="small" @click="closePurposeDock">
                      <el-icon :size="18"><DArrowLeft v-if="isModuleDockWideLayout" /><Fold v-else /></el-icon>
                    </el-button>
                  </el-tooltip>
                </div>
              </div>
              <div class="tc-card__tree-body tree-panel__body">
                <div class="purpose-dock-list">
                  <button
                    v-for="item in purposeTabs"
                    :key="item.value"
                    type="button"
                    class="purpose-dock-item"
                    :class="{ 'is-active': knowledgeUiStore.activePurpose === item.value }"
                    @click="selectPurpose(item.value)"
                  >
                    <span class="purpose-dock-item__label">{{ item.label }}</span>
                    <span class="purpose-dock-item__badge">{{ purposeDockCount(item.value) }}</span>
                  </button>
                </div>
              </div>
            </el-card>
          </div>
        </aside>

        <div v-if="isPurposeDockExpanded && !isModuleDockWideLayout" class="module-tree-mask" @click="closePurposeDock" />

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
            <el-tag size="small" class="cyber-tag cyber-tag--info">待处理 {{ runtimeStatus.counters.pending || 0 }}</el-tag>
            <el-tag size="small" type="warning" class="cyber-tag cyber-tag--warning">
              处理中 {{ runtimeStatus.counters.processing || 0 }}
            </el-tag>
            <el-tag size="small" type="success" class="cyber-tag cyber-tag--success">
              已完成 {{ runtimeStatus.counters.completed || 0 }}
            </el-tag>
            <el-tag size="small" type="danger" class="cyber-tag cyber-tag--danger">失败 {{ runtimeStatus.counters.failed || 0 }}</el-tag>
          </div>
          <div class="knowledge-filters">
            <el-input
              v-model="docFilters.keyword"
              clearable
              placeholder="搜索标题/文件名/URL"
              @keyup.enter="onSearch"
              style="max-width: 320px"
            />
            <el-select
              v-model="docFilters.module_id"
              clearable
              filterable
              placeholder="所属模块"
              style="width: 220px"
              @change="onSearch"
            >
              <el-option
                v-for="m in moduleOptions"
                :key="m.value"
                :label="m.label"
                :value="m.value"
              />
            </el-select>
            <el-select v-model="docFilters.status" clearable placeholder="状态" style="width: 160px" @change="onSearch">
              <el-option label="待处理" value="pending" />
              <el-option label="处理中" value="processing" />
              <el-option label="已完成" value="completed" />
              <el-option label="失败" value="failed" />
            </el-select>
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
                <el-tag effect="plain" class="cyber-tag cyber-tag--neutral">
                  {{ purposeLabelByValue(resolvePurpose(row)) }}
                </el-tag>
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
          <div class="knowledge-pagination">
            <el-pagination
              background
              layout="total, sizes, prev, pager, next, jumper"
              :total="pagination.total"
              :page-size="pagination.page_size"
              :current-page="pagination.page"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="onPageChange"
              @size-change="onPageSizeChange"
            />
          </div>
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
              <el-button size="small" type="success" @click="saveStructuredPayload">保存为测试资产</el-button>
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

    <el-dialog v-model="importPreviewDialogVisible" title="进一步落地：导入预览" width="860px">
      <div v-if="!importPreviewData" style="color: rgba(226,232,240,.75)">暂无预览数据</div>
      <div v-else class="import-preview">
        <div class="import-preview__section-title">发布计划（可编辑）</div>
        <div class="release-plan-form">
          <el-input v-model="releasePlanForm.release_name" placeholder="发布名称" />
          <el-input v-model="releasePlanForm.version_no" placeholder="版本号（唯一）" />
          <el-date-picker
            v-model="releasePlanForm.release_date"
            type="datetime"
            placeholder="发布日期"
            value-format="YYYY-MM-DDTHH:mm:ss"
            format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
          />
        </div>

        <div class="import-preview__section-title">将要导入/更新的用例（去重合并）</div>
        <el-table :data="importPreviewData.draft_cases || []" border size="small" style="margin-bottom: 12px">
          <el-table-column label="导入" width="72" align="center">
            <template #default="{ row }">
              <el-checkbox :model-value="selectedDraftIdxs.includes(row.idx)" @change="(v)=>toggleDraftIdx(row.idx, v)" />
            </template>
          </el-table-column>
          <el-table-column prop="idx" label="#" width="60" />
          <el-table-column prop="case_name" label="用例名称" min-width="260" show-overflow-tooltip />
          <el-table-column prop="action" label="动作" width="100" />
          <el-table-column prop="step_desc_preview" label="步骤预览" min-width="260" show-overflow-tooltip />
        </el-table>

        <div class="import-preview__section-title">推荐关联的“模块内已有用例”（将绑定到发布计划）</div>
        <el-checkbox-group v-model="selectedExistingCaseIds" class="existing-case-group">
          <div v-for="row in importPreviewData.suggest_existing_cases || []" :key="row.id" class="existing-case-item">
            <el-checkbox :label="row.id">
              <span class="existing-case-name">{{ row.case_name }}</span>
              <span class="existing-case-meta">({{ row.test_type }})</span>
            </el-checkbox>
          </div>
        </el-checkbox-group>
      </div>
      <template #footer>
        <el-button @click="importPreviewDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importingFromPreview" @click="confirmImportFromPreview">确认导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useRouter } from "vue-router";
import {
  DArrowLeft,
  DArrowRight,
  Delete,
  Fold,
  FolderOpened,
  RefreshRight,
  View,
  WarningFilled,
} from "@element-plus/icons-vue";
import { getModulesApi } from "@/api/testcase";
import { KNOWLEDGE_PURPOSE_TABS, useKnowledgeUiStore } from "@/stores/knowledgeUiStore";
import {
  autoFillKnowledgeFormApi,
  createGeneratedTestArtifactApi,
  importGeneratedTestArtifactApi,
  previewImportGeneratedTestArtifactApi,
  deleteKnowledgeDocumentApi,
  extractKnowledgeTextApi,
  getKnowledgeDocumentStatusApi,
  getKnowledgeRuntimeStatusApi,
  ingestKnowledgeDocumentApi,
  listKnowledgeDocumentsApi,
  previewKnowledgeDocumentChunksApi,
  retryKnowledgeDocumentApi,
} from "@/api/assistant";

const loading = ref(false);
const docSubmitting = ref(false);
const docAutoFilling = ref(false);
const semanticLoading = ref(false);
const pageErrorMessage = ref("");
const documentList = ref([]);
const moduleOptions = ref([]);
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
let documentsLoadingInFlight = false;

const purposeTabs = KNOWLEDGE_PURPOSE_TABS;
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
const pagination = ref({ page: 1, page_size: 20, total: 0 });
const docFilters = ref({ keyword: "", status: "", module_id: null });

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

const importPreviewDialogVisible = ref(false);
const importingFromPreview = ref(false);
const importPreviewData = ref(null);
const importPreviewArtifactId = ref(null);
const selectedExistingCaseIds = ref([]);
const selectedDraftIdxs = ref([]);
const releasePlanForm = ref({ release_name: "", version_no: "", release_date: "" });

const router = useRouter();
const knowledgeUiStore = useKnowledgeUiStore();
const isPurposeDockExpanded = ref(false);
const windowInnerWidth = ref(typeof window !== "undefined" ? window.innerWidth : 1600);

const MODULE_DOCK_PUSH_BREAKPOINT_PX = 1280;
const isModuleDockWideLayout = computed(() => windowInnerWidth.value >= MODULE_DOCK_PUSH_BREAKPOINT_PX);

function syncViewportWidth() {
  if (typeof window !== "undefined") windowInnerWidth.value = window.innerWidth;
}

function togglePurposeDockExpanded() {
  isPurposeDockExpanded.value = !isPurposeDockExpanded.value;
}

function openPurposeDockPanel() {
  isPurposeDockExpanded.value = true;
}

function closePurposeDock() {
  isPurposeDockExpanded.value = false;
}

function purposeDockCount(value) {
  const pc = knowledgeUiStore.purposeCounts || {};
  if (value === "all") return Number(pc.all ?? 0);
  return Number(pc[value] ?? 0);
}

function selectPurpose(value) {
  knowledgeUiStore.setActivePurpose(value);
  if (!isModuleDockWideLayout.value) {
    // overlay 模式下点击后收起，避免遮挡表格
    isPurposeDockExpanded.value = false;
  }
}

const filteredDocuments = computed(() => {
  // 列表已在后端按 category 过滤；这里不再二次过滤，避免分页/切换分类时出现空列表。
  return documentList.value;
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

function resolveApiErrorMessage(error, fallback = "请求失败") {
  const status = error?.response?.status;
  const data = error?.response?.data || {};
  const msg =
    data?.message ||
    data?.msg ||
    data?.error ||
    (typeof data === "string" ? data : "");
  const rawStr = typeof msg === "string" ? msg.trim() : "";
  if (/^<!doctype html/i.test(rawStr) || /^<html/i.test(rawStr)) {
    return `${fallback}：后端返回 HTML 错误页（可能未迁移/未重启或后端异常）`;
  }
  if (msg) return String(msg);
  if (!status) return `${fallback}：网络异常或后端未启动`;
  if (status === 401) return `${fallback}：登录已过期，请重新登录`;
  if (status === 403) return `${fallback}：当前账号无权限`;
  if (status === 404) return `${fallback}：接口不存在，请确认后端已更新并重启`;
  if (status >= 500) return `${fallback}：服务端异常（${status}）`;
  return `${fallback}（HTTP ${status}）`;
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
    // 用 DELETE 探针：0 不存在应返回 404（也说明路由可用），避免依赖 Allow 头。
    await deleteKnowledgeDocumentApi(0);
    // 若真的删掉了（极小概率），也说明能力可用
    deleteCapability.value = { status: "ok", label: "可用", tagType: "success", hint: "删除接口已生效" };
  } catch (error) {
    const status = error?.response?.status;
    if (status === 404) {
      deleteCapability.value = {
        status: "ok",
        label: "可用",
        tagType: "success",
        hint: "删除接口已生效（探针 ID 不存在）",
      };
      return;
    }
    // 401/403 说明路由存在但权限不足，能力应视为可用。
    if (status === 401 || status === 403) {
      deleteCapability.value = {
        status: "limited",
        label: "可用但受限",
        tagType: "warning",
        hint: "删除接口已生效（当前账户权限受限）",
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
  if (documentsLoadingInFlight) return;
  documentsLoadingInFlight = true;
  loading.value = true;
  try {
    const purpose = knowledgeUiStore.activePurpose || "all";
    const category = purpose !== "all" ? purposeCategoryMap[purpose] || "" : "";
    const params = {
      page: pagination.value.page,
      page_size: pagination.value.page_size,
      ...(category ? { category } : {}),
      ...(String(docFilters.value.keyword || "").trim() ? { q: String(docFilters.value.keyword || "").trim() } : {}),
      ...(String(docFilters.value.status || "").trim() ? { status: String(docFilters.value.status || "").trim() } : {}),
      ...(docFilters.value.module_id ? { module_id: Number(docFilters.value.module_id) } : {}),
    };
    const { data } = await listKnowledgeDocumentsApi(params);
    documentList.value = Array.isArray(data?.results) ? data.results : [];
    pagination.value.total = Number(data?.count ?? documentList.value.length ?? 0);
    if (data?.purpose_counts) knowledgeUiStore.setPurposeCounts(data.purpose_counts);
    pageErrorMessage.value = "";
    await loadRuntimeStatus();
    ensureDocumentPolling();
  } catch (error) {
    documentList.value = [];
    pagination.value.total = 0;
    stopDocumentPolling();
    pageErrorMessage.value = resolveApiErrorMessage(error, "文档列表加载失败");
    ElMessage.error(pageErrorMessage.value);
  } finally {
    loading.value = false;
    documentsLoadingInFlight = false;
  }
}

function onSearch() {
  pagination.value.page = 1;
  loadDocuments();
}

function onPageChange(p) {
  pagination.value.page = Number(p || 1);
  loadDocuments();
}

function onPageSizeChange(size) {
  pagination.value.page_size = Number(size || 20);
  pagination.value.page = 1;
  loadDocuments();
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
  const counters = runtimeStatus.value?.counters || {};
  return Number(counters.pending || 0) > 0 || Number(counters.processing || 0) > 0;
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
    try {
      const { data: p } = await previewKnowledgeDocumentChunksApi(row.id, { limit: 50 });
      const payload = p?.data || {};
      const previewChunks = Array.isArray(payload?.preview_chunks) ? payload.preview_chunks : [];
      if (previewChunks.length) {
        const normalized = previewChunks.map((x, idx) => ({
          id: `preview-${idx}`,
          text: String(x?.text || ""),
        }));
        activeDrawerDocument.value = {
          ...(activeDrawerDocument.value || {}),
          semantic_chunks: normalized,
          semantic_summary: payload?.summary || (activeDrawerDocument.value?.semantic_summary || ""),
        };
      }
    } catch (_) {
      // ignore: preview 接口不可用时回退原有 status 结果
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

async function saveStructuredPayload() {
  try {
    const doc = activeDrawerDocument.value || {};
    const payload = structuredPayload.value || {};
    const res = await createGeneratedTestArtifactApi({
      artifact_type: "test_plan",
      title: String(payload?.title || doc?.title || doc?.file_name || "").trim(),
      doc_id: doc?.id || null,
      module_id: doc?.module_id || null,
      content: payload,
      citations: Array.isArray(payload?.chunk_refs) ? payload.chunk_refs : [],
    });
    ElMessage.success("已保存为测试资产，正在生成导入预览...");
    const id = res?.data?.data?.id;
    if (!id) return;
    importPreviewArtifactId.value = Number(id);
    const previewRes = await previewImportGeneratedTestArtifactApi(id, { module_id: doc?.module_id || null });
    importPreviewData.value = previewRes?.data?.data || null;
    selectedExistingCaseIds.value = Array.isArray(importPreviewData.value?.default_selected_existing_case_ids)
      ? importPreviewData.value.default_selected_existing_case_ids
      : [];
    selectedDraftIdxs.value = Array.isArray(importPreviewData.value?.draft_cases)
      ? (importPreviewData.value.draft_cases || []).map((x) => x.idx).filter(Boolean)
      : [];
    const rp = importPreviewData.value?.suggest_release_plan || {};
    releasePlanForm.value = {
      release_name: String(rp.release_name || "").trim(),
      version_no: String(rp.version_no || "").trim(),
      release_date: String(rp.release_date || "").trim(),
    };
    importPreviewDialogVisible.value = true;
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || "保存失败");
  }
}

function toggleDraftIdx(idx, checked) {
  const id = Number(idx || 0);
  if (!id) return;
  const cur = new Set(selectedDraftIdxs.value || []);
  if (checked) cur.add(id);
  else cur.delete(id);
  selectedDraftIdxs.value = Array.from(cur).sort((a, b) => a - b);
}

async function confirmImportFromPreview() {
  if (!importPreviewArtifactId.value) return;
  importingFromPreview.value = true;
  try {
    const res = await importGeneratedTestArtifactApi(importPreviewArtifactId.value, {
      mode: "dedup_merge",
      enable_release_plan: true,
      existing_case_ids: selectedExistingCaseIds.value || [],
      selected_draft_idxs: selectedDraftIdxs.value || [],
      release_plan: {
        release_name: String(releasePlanForm.value?.release_name || "").trim(),
        version_no: String(releasePlanForm.value?.version_no || "").trim(),
        release_date: String(releasePlanForm.value?.release_date || "").trim(),
      },
    });
    const data = res?.data?.data || {};
    const rpId = data?.release_plan_id || null;
    const msg = `导入完成：新增用例 ${data?.created_cases ?? 0} 条，更新用例 ${data?.updated_cases ?? 0} 条，计划关联 ${data?.linked_to_release_plan ?? 0} 条`;
    if (rpId) {
      try {
        await ElMessageBox.confirm(`${msg}\n\n是否跳转到发布计划详情？`, "落地完成", {
          confirmButtonText: "跳转",
          cancelButtonText: "留在当前页",
          type: "success",
        });
        router.push(`/defect/release/${rpId}`);
      } catch (_) {
        // cancelled
      }
    } else {
      ElMessage.success(msg);
    }
    importPreviewDialogVisible.value = false;
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || "导入失败");
  } finally {
    importingFromPreview.value = false;
  }
}

loadDocuments();
loadModules();
checkDeleteCapability();
onBeforeUnmount(() => stopDocumentPolling());
onMounted(() => {
  syncViewportWidth();
  window.addEventListener("resize", syncViewportWidth);
});
onBeforeUnmount(() => window.removeEventListener("resize", syncViewportWidth));

watch(
  () => knowledgeUiStore.activePurpose,
  () => {
    pagination.value.page = 1;
    loadDocuments();
  }
);
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
  display: flex;
  flex-direction: row;
  gap: 10px;
  align-items: stretch;
  min-height: 0;
}

.knowledge-main {
  flex: 1;
  min-width: 0;
  backdrop-filter: blur(12px);
  background: rgba(8, 15, 30, 0.38);
  border: 1px solid rgba(34, 211, 238, 0.3);
  box-shadow: inset 0 0 8px rgba(0, 255, 255, 0.08);
  border-radius: 12px;
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

/* ====== 复用 TestCase 的“窄竖条 + 侧滑面板”结构（仅保留所需样式） ====== */
.module-tree-dock {
  --aitesta-module-dock-surface: #111827;
  --aitesta-module-rail-w: 52px;
  --aitesta-module-tree-w: 190px;
  position: relative;
  z-index: 52;
  flex-shrink: 0;
  display: flex;
  flex-direction: row;
  align-items: stretch;
  min-height: 0;
  height: 100%;
  align-self: stretch;
  width: var(--aitesta-module-rail-w);
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-sizing: border-box;
}

.module-tree-dock.module-tree-dock--wide.is-expanded {
  width: calc(var(--aitesta-module-rail-w) + var(--aitesta-module-tree-w));
}

.module-tree-dock--wide .module-tree-slide {
  position: relative;
  z-index: 1;
  flex: 0 0 0;
  width: 0;
  min-width: 0;
  max-width: 0;
  height: 100%;
  opacity: 0;
  overflow: hidden;
  pointer-events: none;
  transition:
    flex-basis 0.3s cubic-bezier(0.4, 0, 0.2, 1),
    width 0.3s cubic-bezier(0.4, 0, 0.2, 1),
    max-width 0.3s cubic-bezier(0.4, 0, 0.2, 1),
    opacity 0.22s ease;
}

.module-tree-dock--wide.is-expanded .module-tree-slide.is-open {
  flex: 0 0 var(--aitesta-module-tree-w);
  width: var(--aitesta-module-tree-w);
  min-width: var(--aitesta-module-tree-w);
  max-width: var(--aitesta-module-tree-w);
  height: 100%;
  opacity: 1;
  pointer-events: auto;
  border-radius: 0 12px 12px 0;
  background: rgba(17, 24, 39, 0.55);
}

.module-tree-dock--overlay .module-tree-slide {
  position: absolute;
  left: var(--aitesta-module-rail-w);
  top: 0;
  bottom: 0;
  width: var(--aitesta-module-tree-w);
  z-index: 55;
  transform: translate3d(-100%, 0, 0);
  opacity: 0;
  pointer-events: none;
  transition:
    transform 0.28s cubic-bezier(0.4, 0, 0.2, 1),
    opacity 0.22s ease,
    box-shadow 0.28s ease;
  will-change: transform;
}

.module-tree-dock--overlay .module-tree-slide.is-open {
  transform: translate3d(0, 0, 0);
  opacity: 1;
  pointer-events: auto;
}

.module-tree-dock--overlay.is-expanded .module-tree-slide.is-open {
  box-shadow:
    12px 0 36px rgba(0, 0, 0, 0.5),
    0 0 0 1px rgba(0, 216, 255, 0.08);
  border-radius: 0 14px 14px 0;
  overflow: hidden;
  background: rgba(17, 24, 39, 0.9);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}

.module-tree-rail {
  width: 52px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 14px 0;
  z-index: 60;
  box-sizing: border-box;
  height: 100%;
  background: var(--aitesta-module-dock-surface);
  border: 1px solid rgba(0, 216, 255, 0.1);
  border-radius: 12px;
  box-shadow: 0 3px 14px rgba(0, 0, 0, 0.24);
}

.module-tree-rail__expand-btn {
  width: 40px;
  height: 40px;
  min-height: 40px;
  padding: 0;
  border-radius: 10px;
  color: rgba(0, 216, 255, 0.88) !important;
  background: rgba(255, 255, 255, 0.04) !important;
}

.module-tree-rail__expand-btn:hover:not(:disabled) {
  background: rgba(0, 216, 255, 0.12) !important;
  color: #7aebff !important;
  box-shadow: 0 0 12px rgba(0, 216, 255, 0.15);
}

.module-tree-rail__expand-btn.is-expanded {
  background: rgba(0, 216, 255, 0.14) !important;
  color: #7aebff !important;
  box-shadow: 0 0 14px rgba(0, 216, 255, 0.12);
}

.module-tree-rail__btn {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.03);
  color: rgba(226, 232, 240, 0.82);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease, color 0.2s ease;
}

.module-tree-rail__btn:hover:not(:disabled) {
  border-color: rgba(0, 216, 255, 0.22);
  background: rgba(0, 216, 255, 0.08);
  box-shadow: 0 0 14px rgba(0, 216, 255, 0.12);
  color: #dbeafe;
}

.module-tree-rail__btn.is-active {
  border-color: rgba(0, 216, 255, 0.35);
  background: rgba(0, 216, 255, 0.12);
  color: #dbeafe;
}

.module-tree-mask {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: rgba(0, 0, 0, 0.38);
}

/* Tree card 充满滑出面板高度，列表区滚动 */
.tc-tree-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.tree-panel__body {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

/* 目的分类列表 */
.purpose-dock-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.purpose-dock-item {
  width: 100%;
  height: 36px;
  padding: 0 10px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(2, 6, 23, 0.22);
  color: rgba(226, 232, 240, 0.82);
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  transition: border-color 0.22s ease, box-shadow 0.22s ease, background-color 0.22s ease, color 0.22s ease;
}

.purpose-dock-item:hover {
  border-color: rgba(0, 216, 255, 0.22);
  background: rgba(0, 216, 255, 0.06);
  color: #e2e8f0;
}

.purpose-dock-item.is-active {
  border-color: rgba(0, 216, 255, 0.55);
  background: rgba(0, 216, 255, 0.08);
  color: #e2e8f0;
  box-shadow:
    inset 4px 0 18px -4px rgba(0, 216, 255, 0.45),
    0 0 22px rgba(0, 216, 255, 0.14);
}

.purpose-dock-item__label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.purpose-dock-item__badge {
  min-width: 22px;
  height: 17px;
  padding: 0 6px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  color: rgba(0, 216, 255, 0.85);
  border: 1px solid rgba(0, 216, 255, 0.22);
  background: rgba(0, 216, 255, 0.08);
  box-shadow: 0 0 12px rgba(0, 216, 255, 0.12);
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

/* ===== 统一 Tag：低饱和语义色 + 赛博材质 ===== */
.cyber-tag {
  --cyber-tag-fg: rgba(226, 232, 240, 0.86);
  --cyber-tag-border: rgba(34, 211, 238, 0.18);
  --cyber-tag-bg: rgba(2, 6, 23, 0.18);
  --cyber-tag-glow: rgba(34, 211, 238, 0.12);
  --cyber-tag-h: 22px;
  --cyber-tag-fs: 11px;
  --cyber-tag-px: 8px;
}

.cyber-tag.cyber-tag--neutral,
.cyber-tag.cyber-tag--info {
  --cyber-tag-fg: rgba(165, 243, 252, 0.9);
  --cyber-tag-border: rgba(34, 211, 238, 0.22);
  --cyber-tag-bg: rgba(8, 47, 73, 0.18);
  --cyber-tag-glow: rgba(34, 211, 238, 0.12);
}

.cyber-tag.cyber-tag--success {
  --cyber-tag-fg: rgba(187, 247, 208, 0.92);
  --cyber-tag-border: rgba(34, 197, 94, 0.22);
  --cyber-tag-bg: rgba(20, 83, 45, 0.14);
  --cyber-tag-glow: rgba(34, 197, 94, 0.1);
}

.cyber-tag.cyber-tag--warning {
  /* 琥珀但降饱和，避免亮黄抢眼 */
  --cyber-tag-fg: rgba(253, 230, 138, 0.9);
  --cyber-tag-border: rgba(245, 158, 11, 0.22);
  --cyber-tag-bg: rgba(120, 53, 15, 0.14);
  --cyber-tag-glow: rgba(245, 158, 11, 0.1);
}

.cyber-tag.cyber-tag--danger {
  /* 偏玫红/暗红，降饱和 */
  --cyber-tag-fg: rgba(254, 202, 202, 0.9);
  --cyber-tag-border: rgba(244, 63, 94, 0.22);
  --cyber-tag-bg: rgba(136, 19, 55, 0.12);
  --cyber-tag-glow: rgba(244, 63, 94, 0.1);
}

.cyber-tag :deep(.el-tag) {
  height: var(--cyber-tag-h);
  line-height: calc(var(--cyber-tag-h) - 2px);
  padding: 0 var(--cyber-tag-px);
  border-radius: 999px;
  border: 1px solid var(--cyber-tag-border);
  background: var(--cyber-tag-bg);
  box-shadow: 0 0 14px var(--cyber-tag-glow);
}

.cyber-tag :deep(.el-tag__content) {
  font-size: var(--cyber-tag-fs);
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--cyber-tag-fg);
}

.cyber-tag :deep(.el-tag__close) {
  color: color-mix(in srgb, var(--cyber-tag-fg) 70%, transparent);
}

.knowledge-filters {
  display: flex;
  gap: 10px;
  align-items: center;
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

.knowledge-pagination {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.import-preview__section-title {
  font-size: 12px;
  color: rgba(226, 232, 240, 0.75);
  margin: 6px 0 8px;
}

.existing-case-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 240px;
  overflow: auto;
  padding: 6px 8px;
  border: 1px solid rgba(56, 189, 248, 0.18);
  border-radius: 8px;
  background: rgba(2, 6, 23, 0.25);
}

.existing-case-name {
  color: rgba(226, 232, 240, 0.9);
}

.existing-case-meta {
  margin-left: 6px;
  color: rgba(226, 232, 240, 0.55);
  font-size: 12px;
}

.release-plan-form {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 10px;
  margin-bottom: 10px;
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

