<template>
  <div class="page-wrap cyber-page knowledge-ask-page">
    <el-card class="sys-page-head" shadow="never">
      <div class="sys-page-head__row">
        <div>
          <h2 class="sys-page-head__title">知识库问答（可追溯）</h2>
          <p class="sys-page-head__sub">回答会返回 citations 引用来源，便于审计与追溯。</p>
        </div>
        <div class="sys-page-head__actions">
          <el-button type="primary" :loading="asking" :disabled="!question.trim()" @click="ask">提问</el-button>
          <el-button :disabled="!answer" @click="saveAsArtifact">保存为测试资产</el-button>
        </div>
      </div>
    </el-card>

    <el-card class="sys-filter-card" shadow="never">
      <div class="ask-grid">
        <div class="field field--wide">
          <div class="label">问题</div>
          <el-input v-model="question" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" placeholder="例如：如何设计登录接口的越权测试？" />
        </div>
        <div class="field">
          <div class="label">top_k</div>
          <el-input-number v-model="topK" :min="1" :max="10" />
        </div>
        <div class="field">
          <div class="label">category（可选）</div>
          <el-input v-model="category" placeholder="如 template/standard" />
        </div>
        <div class="field">
          <div class="label">tag（可选）</div>
          <el-input v-model="tag" placeholder="如 登录" />
        </div>
      </div>
    </el-card>

    <el-card class="sys-table-card" shadow="never">
      <div class="result-head">
        <div class="result-head__title">回答</div>
        <div class="result-head__sub">{{ modelLabel }}</div>
      </div>
      <div class="answer-markdown" v-loading="asking" v-html="renderedAnswer"></div>
    </el-card>

    <el-card class="sys-table-card" shadow="never">
      <div class="result-head">
        <div class="result-head__title">引用来源（citations）</div>
        <div class="result-head__sub">共 {{ citations.length }} 条</div>
      </div>
      <el-table :data="citations" border class="admin-data-table sys-enterprise-table">
        <template #empty>
          <el-empty description="暂无引用" :image-size="78" />
        </template>
        <el-table-column prop="idx" label="#" width="60" align="center" />
        <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
        <el-table-column prop="type" label="类型" width="100" align="center" />
        <el-table-column prop="id" label="ID" width="110" align="center" />
        <el-table-column prop="retrieve_mode" label="检索方式" width="140" align="center" />
        <el-table-column prop="score" label="score" width="110" align="center" />
        <el-table-column label="打开" width="100" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="open(row.url)">打开</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

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
import { computed, ref } from "vue";
import { ElMessage } from "element-plus";
import { ElMessageBox } from "element-plus";
import { useRouter } from "vue-router";
import { askKnowledgeApi } from "@/api/aiKnowledge";
import {
  createGeneratedTestArtifactApi,
  importGeneratedTestArtifactApi,
  previewImportGeneratedTestArtifactApi,
} from "@/api/assistant";
import { useAppContextStore } from "@/stores/appContextStore";
import MarkdownIt from "markdown-it";

const asking = ref(false);
const question = ref("");
const topK = ref(5);
const category = ref("");
const tag = ref("");

const answer = ref("");
const citations = ref([]);
const model = ref("");

const modelLabel = computed(() => (model.value ? `model: ${model.value}` : ""));
const md = new MarkdownIt({ html: false, linkify: true, breaks: true });
const renderedAnswer = computed(() => {
  const raw = String(answer.value || "").trim();
  if (!raw) return "—";
  return md.render(raw);
});

const appContextStore = useAppContextStore();
const projectId = computed(() => appContextStore.state.activeProject.id);
const router = useRouter();

const importPreviewDialogVisible = ref(false);
const importingFromPreview = ref(false);
const importPreviewData = ref(null);
const importPreviewArtifactId = ref(null);
const selectedExistingCaseIds = ref([]);
const selectedDraftIdxs = ref([]);
const releasePlanForm = ref({ release_name: "", version_no: "", release_date: "" });

function open(url) {
  const u = String(url || "").trim();
  if (!u) return;
  window.open(u, "_blank", "noopener,noreferrer");
}

async function ask() {
  asking.value = true;
  answer.value = "";
  citations.value = [];
  model.value = "";
  try {
    const payload = {
      question: String(question.value || "").trim(),
      top_k: Number(topK.value || 5),
      ...(projectId.value ? { project_id: Number(projectId.value) } : {}),
      ...(String(category.value || "").trim() ? { category: String(category.value || "").trim() } : {}),
      ...(String(tag.value || "").trim() ? { tag: String(tag.value || "").trim() } : {}),
    };
    const { data } = await askKnowledgeApi(payload);
    if (!data?.success) {
      ElMessage.error(data?.message || "提问失败");
      answer.value = "";
      citations.value = [];
      model.value = "";
      return;
    }
    answer.value = String(data.answer_markdown || "");
    citations.value = Array.isArray(data.citations) ? data.citations : [];
    model.value = String(data.model || data.engine || "");
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.response?.data?.detail || e?.message || "请求失败");
  } finally {
    asking.value = false;
  }
}

async function saveAsArtifact() {
  try {
    const res = await createGeneratedTestArtifactApi({
      artifact_type: "test_points",
      title: String(question.value || "").trim().slice(0, 255),
      content: {
        question: String(question.value || "").trim(),
        answer_markdown: String(answer.value || ""),
        model: String(model.value || ""),
      },
      citations: Array.isArray(citations.value) ? citations.value : [],
      project_id: projectId.value ? Number(projectId.value) : null,
      source_question: String(question.value || "").trim(),
      model_used: String(model.value || ""),
    });
    ElMessage.success("已保存为测试资产，正在生成导入预览...");
    const id = res?.data?.data?.id;
    if (!id) return;
    importPreviewArtifactId.value = Number(id);
    const previewRes = await previewImportGeneratedTestArtifactApi(id, {});
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
    const importRes = await importGeneratedTestArtifactApi(importPreviewArtifactId.value, {
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
    const imp = importRes?.data?.data || {};
    const rpId = imp?.release_plan_id || null;
    const msg = `导入完成：新增用例 ${imp?.created_cases ?? 0} 条，更新用例 ${imp?.updated_cases ?? 0} 条，计划关联 ${imp?.linked_to_release_plan ?? 0} 条`;
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
</script>

<style scoped>
.ask-grid {
  display: grid;
  grid-template-columns: 1fr 160px 220px 220px;
  gap: 14px;
}
.field {
  min-width: 0;
}
.field--wide {
  grid-column: span 4;
}
.label {
  font-size: 12px;
  color: rgba(226, 232, 240, 0.65);
  margin-bottom: 6px;
}
.answer-markdown {
  margin: 0;
  padding: 12px;
  font-size: 12px;
  line-height: 1.55;
  background: rgba(10, 16, 28, 0.45);
  border: 1px solid rgba(0, 255, 255, 0.12);
  border-radius: 8px;
  color: rgba(226, 232, 240, 0.88);
  min-height: 120px;
}
.answer-markdown :deep(p) {
  margin: 0 0 8px 0;
}
.answer-markdown :deep(pre) {
  margin: 8px 0;
  padding: 10px;
  background: rgba(2, 6, 23, 0.55);
  border: 1px solid rgba(56, 189, 248, 0.18);
  border-radius: 8px;
  overflow: auto;
}
.answer-markdown :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}
.import-preview__section-title {
  font-size: 12px;
  color: rgba(226, 232, 240, 0.75);
  margin: 6px 0 8px;
}
.release-plan-form {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 10px;
  margin-bottom: 10px;
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
.result-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 10px;
}
.result-head__title {
  font-weight: 600;
  color: rgba(226, 232, 240, 0.92);
}
.result-head__sub {
  font-size: 12px;
  color: rgba(226, 232, 240, 0.55);
}
</style>

