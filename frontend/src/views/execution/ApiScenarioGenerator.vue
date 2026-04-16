<template>
  <div class="page-wrap cyber-page scenario-gen-page">
    <el-card class="sys-page-head" shadow="never">
      <div class="sys-page-head__row">
        <div>
          <h2 class="sys-page-head__title">接口场景生成</h2>
          <p class="sys-page-head__sub">
            从 OpenAPI(JSON/YAML) 或 cURL 列表生成可执行场景草稿；可选一键落库为 API 用例 + 场景编排。
          </p>
        </div>
        <div class="sys-page-head__actions">
          <el-button :loading="loading" @click="generate(false)">生成草稿</el-button>
          <el-button type="primary" :loading="creating" :disabled="!canCreate" @click="generate(true)">
            创建并保存
          </el-button>
        </div>
      </div>
    </el-card>

    <el-card class="sys-filter-card" shadow="never">
      <div class="form-row">
        <div class="field">
          <div class="label">当前项目</div>
          <div class="value">{{ projectId || "未选择" }}</div>
        </div>
        <div class="field">
          <div class="label">当前环境</div>
          <div class="value">{{ envId || "未选择" }}</div>
        </div>
        <div class="field field--wide">
          <div class="label">模块（用例归属）</div>
          <el-select v-model="moduleId" filterable clearable placeholder="请选择模块" style="width: 100%" @visible-change="onModuleDropdown">
            <el-option v-for="m in modules" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </div>
        <div class="field field--wide">
          <div class="label">base_url（可选）</div>
          <el-input v-model="baseUrl" placeholder="如 https://api.example.com（优先于 OpenAPI servers[0].url）" />
        </div>
        <div class="field field--wide">
          <div class="label">场景名称（可选）</div>
          <el-input v-model="scenarioName" placeholder="留空将自动命名" />
        </div>
        <div class="field">
          <div class="label">最大步数</div>
          <el-input-number v-model="maxSteps" :min="1" :max="100" />
        </div>
      </div>
    </el-card>

    <el-card class="sys-table-card" shadow="never">
      <el-tabs v-model="mode" class="mode-tabs">
        <el-tab-pane label="OpenAPI" name="openapi">
          <el-input
            v-model="openapiSpec"
            type="textarea"
            :autosize="{ minRows: 10, maxRows: 22 }"
            placeholder="粘贴 OpenAPI JSON/YAML（含 paths），支持 servers[0].url"
          />
        </el-tab-pane>
        <el-tab-pane label="cURL 列表" name="curl">
          <el-input
            v-model="curlText"
            type="textarea"
            :autosize="{ minRows: 10, maxRows: 22 }"
            placeholder="每行一个 curl（支持 -X/-H/-d/--data-raw），用于生成步骤草稿"
          />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-card v-if="draft" class="sys-table-card" shadow="never">
      <div class="result-head">
        <div class="result-head__title">生成结果</div>
        <div class="result-head__sub">steps: {{ (draft.steps || []).length }}</div>
      </div>
      <el-table :data="draft.steps" border class="admin-data-table sys-enterprise-table" max-height="380">
        <el-table-column prop="order" label="#" width="60" align="center" />
        <el-table-column prop="name" label="步骤名" min-width="220" show-overflow-tooltip />
        <el-table-column label="请求" min-width="320" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="mono">{{ row?.request?.method }} {{ row?.request?.url }}</span>
          </template>
        </el-table-column>
        <el-table-column label="期望状态码" width="120" align="center">
          <template #default="{ row }">
            {{ row?.request?.expected_status ?? "—" }}
          </template>
        </el-table-column>
        <el-table-column label="提取规则" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="info" effect="plain">{{ (row?.extraction_rules || []).length }}</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="createdScenarioId" class="created-tip">
        已创建场景：ID = <span class="mono">{{ createdScenarioId }}</span>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { ElMessage } from "element-plus";
import { useAppContextStore } from "@/stores/appContextStore";
import { getModulesApi } from "@/api/testcase";
import { generateApiScenarioApi } from "@/api/execution";

const appContextStore = useAppContextStore();
const projectId = computed(() => appContextStore.state.activeProject.id);
const envId = computed(() => appContextStore.state.activeEnvironment.id);

const loading = ref(false);
const creating = ref(false);
const createdScenarioId = ref(null);

const modules = ref([]);
const moduleId = ref(null);

const baseUrl = ref("");
const scenarioName = ref("");
const maxSteps = ref(30);

const mode = ref("openapi");
const openapiSpec = ref("");
const curlText = ref("");

const draft = ref(null);

const canCreate = computed(() => Boolean(projectId.value) && Boolean(moduleId.value));

async function onModuleDropdown(visible) {
  if (!visible) return;
  if (!projectId.value) {
    ElMessage.error("请先在顶部选择项目");
    return;
  }
  try {
    const { data } = await getModulesApi({ project: projectId.value, page_size: 2000 });
    const rows = Array.isArray(data?.results) ? data.results : Array.isArray(data?.data) ? data.data : Array.isArray(data) ? data : [];
    modules.value = rows
      .map((x) => ({ id: x.id, name: x.name || x.module_name || `#${x.id}` }))
      .filter((x) => x.id != null);
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || e?.message || "加载模块失败");
  }
}

function curlListFromText() {
  const lines = String(curlText.value || "")
    .split(/\r?\n/)
    .map((x) => x.trim())
    .filter(Boolean);
  return lines;
}

async function generate(confirmCreate) {
  createdScenarioId.value = null;
  const pid = projectId.value;
  if (!pid) {
    ElMessage.error("请先在顶部选择项目");
    return;
  }
  if (confirmCreate && !moduleId.value) {
    ElMessage.error("创建前必须选择模块");
    return;
  }
  const payload = {
    project_id: Number(pid),
    module_id: moduleId.value ? Number(moduleId.value) : 0,
    environment_id: envId.value ? Number(envId.value) : null,
    base_url: String(baseUrl.value || "").trim(),
    scenario_name: String(scenarioName.value || "").trim(),
    max_steps: Number(maxSteps.value || 30),
    confirm_create: Boolean(confirmCreate),
  };
  if (mode.value === "openapi") {
    payload.openapi_spec = String(openapiSpec.value || "").trim();
  } else {
    payload.curl_list = curlListFromText();
  }

  if (confirmCreate) creating.value = true;
  else loading.value = true;
  try {
    const { data } = await generateApiScenarioApi(payload);
    if (!data?.success) {
      ElMessage.error(data?.message || "生成失败");
      return;
    }
    if (confirmCreate) {
      createdScenarioId.value = data.scenario_id;
      ElMessage.success("已创建场景与用例");
    } else {
      draft.value = data.draft || null;
      ElMessage.success("已生成草稿");
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.response?.data?.detail || e?.message || "请求失败");
  } finally {
    loading.value = false;
    creating.value = false;
  }
}
</script>

<style scoped>
.form-row {
  display: grid;
  grid-template-columns: 180px 180px 1fr 1fr;
  gap: 14px 14px;
  align-items: end;
}
.field {
  min-width: 0;
}
.field--wide {
  grid-column: span 2;
}
.label {
  font-size: 12px;
  color: rgba(226, 232, 240, 0.65);
  margin-bottom: 6px;
}
.value {
  font-size: 13px;
  color: rgba(226, 232, 240, 0.88);
  padding: 8px 10px;
  border: 1px solid rgba(0, 255, 255, 0.12);
  border-radius: 8px;
  background: rgba(10, 16, 28, 0.45);
}
.mono {
  font-family: ui-monospace, "Cascadia Code", monospace;
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
.created-tip {
  margin-top: 12px;
  padding: 10px 12px;
  border: 1px solid rgba(0, 255, 255, 0.12);
  border-radius: 8px;
  background: rgba(10, 16, 28, 0.35);
  color: rgba(226, 232, 240, 0.85);
}
</style>

