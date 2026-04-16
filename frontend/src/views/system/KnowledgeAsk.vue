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
      <pre class="answer-pre" v-loading="asking">{{ answer || "—" }}</pre>
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
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { ElMessage } from "element-plus";
import { askKnowledgeApi } from "@/api/aiKnowledge";
import { useAppContextStore } from "@/stores/appContextStore";

const asking = ref(false);
const question = ref("");
const topK = ref(5);
const category = ref("");
const tag = ref("");

const answer = ref("");
const citations = ref([]);
const model = ref("");

const modelLabel = computed(() => (model.value ? `model: ${model.value}` : ""));

const appContextStore = useAppContextStore();
const projectId = computed(() => appContextStore.state.activeProject.id);

function open(url) {
  const u = String(url || "").trim();
  if (!u) return;
  window.location.href = u;
}

async function ask() {
  asking.value = true;
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
.answer-pre {
  margin: 0;
  padding: 12px;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
  background: rgba(10, 16, 28, 0.45);
  border: 1px solid rgba(0, 255, 255, 0.12);
  border-radius: 8px;
  color: rgba(226, 232, 240, 0.88);
  min-height: 120px;
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

