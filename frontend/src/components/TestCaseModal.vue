<template>
  <el-dialog
    :model-value="modelValue"
    title="AI 生成测试用例"
    width="920px"
    class="cyber-dialog-dark ai-generate-dialog"
    destroy-on-close
    @update:model-value="onDialogVisible"
    @closed="onDialogClosed"
  >
    <div class="ai-gen-body cyber-page">
      <div
        class="ai-gen-rag-strip"
        :class="{
          'ai-gen-rag-strip--on': aiGenRagLinked,
          'ai-gen-rag-strip--info': !aiGenRagLinked,
        }"
      >
        <span class="ai-gen-rag-strip__dot" aria-hidden="true" />
        <span class="ai-gen-rag-strip__text">
          {{
            aiGenRagLinked
              ? '已链接模块知识库（手选模块或左侧当前模块），将基于 RAG 检索增强生成'
              : '未链接模块知识库，采用大模型通用生成'
          }}
        </span>
      </div>

      <div class="ai-gen-modal-scroll">
        <div class="ai-gen-input-block">
          <div class="ai-gen-label">模块范围（可选）</div>
          <el-form-item label-width="0" class="ai-gen-module-row ai-gen-module-row--top">
            <el-select
              v-model="aiImportModule"
              placeholder="不选则使用左侧树当前选中的模块做向量检索"
              filterable
              clearable
              style="width: 320px"
              :disabled="aiGenerating"
            >
              <el-option v-for="m in flatModules" :key="m.id" :label="m.name" :value="m.id" />
            </el-select>
            <div class="ai-gen-module-hint">
              选定模块后，生成时<strong>仅在该模块内</strong>检索相似用例（RAG 去重）；导入时若某行无
              <code>module_name</code>，可选手动「默认模块」覆盖自动归属（见下方预览区说明）。
            </div>
          </el-form-item>

          <div class="ai-gen-label-row">
            <span class="ai-gen-label ai-gen-label--inline">需求描述</span>
            <el-button
              type="primary"
              link
              size="small"
              :disabled="aiGenerating"
              @click="fillAiQuickStart"
            >
              ✨ 填入示例
            </el-button>
          </div>
          <el-input
            v-model="aiRequirement"
            type="textarea"
            :rows="5"
            placeholder="请描述待测功能、验收标准、边界条件等，便于模型生成结构化用例…"
            :disabled="aiGenerating"
          />

          <template v-if="effectiveTestType === 'api'">
            <div class="ai-gen-label ai-gen-label--sub ai-gen-label--mt">
              接口定义（可选）
              <span class="ai-gen-optional-hint"
                >粘贴 OpenAPI/Swagger JSON、YAML 片段或 cURL；写入 ext_config.api_spec 并启用接口增强提示词</span
              >
            </div>
            <el-input
              v-model="aiApiSpec"
              type="textarea"
              :rows="6"
              placeholder="例如：OpenAPI 3.0 paths、单接口 JSON 片段、cURL 说明等…"
              :disabled="aiGenerating"
              class="ai-gen-api-spec"
            />
          </template>

          <template v-else-if="effectiveTestType === 'functional'">
            <div class="ai-gen-label ai-gen-label--sub ai-gen-label--mt">业务流程 / 前置条件（可选）</div>
            <el-input
              v-model="aiFunctionalFlow"
              type="textarea"
              :rows="4"
              placeholder="描述主流程、分支、数据准备与前置环境等…"
              :disabled="aiGenerating"
            />
          </template>

          <template v-else-if="effectiveTestType === 'ui-automation'">
            <div class="ai-gen-label ai-gen-label--sub ai-gen-label--mt">页面元素 / 定位符（可选）</div>
            <el-input
              v-model="aiUiLocators"
              type="textarea"
              :rows="4"
              placeholder="支持粘贴 HTML 片段或 Page Object 描述，便于生成可自动化步骤…"
              :disabled="aiGenerating"
            />
          </template>

          <template v-else-if="effectiveTestType === 'performance'">
            <div class="ai-gen-label ai-gen-label--sub ai-gen-label--mt">性能指标（可选）</div>
            <el-input
              v-model="aiPerfMetrics"
              type="textarea"
              :rows="3"
              placeholder="例如：并发数、持续时间、P95/P99 响应时间、TPS、错误率阈值等…"
              :disabled="aiGenerating"
            />
          </template>

          <template v-else-if="effectiveTestType === 'security'">
            <div class="ai-gen-label ai-gen-label--sub ai-gen-label--mt">漏洞类型 vulnerability_type（多选）</div>
            <el-select
              v-model="aiSecurityVulnTypes"
              multiple
              collapse-tags
              collapse-tags-tooltip
              placeholder="选择漏洞类型"
              style="width: 100%"
              :disabled="aiGenerating"
              class="ai-gen-security-select"
            >
              <el-option
                v-for="o in SECURITY_VECTOR_OPTIONS"
                :key="o.value"
                :label="o.label"
                :value="o.value"
              />
            </el-select>
            <div class="ai-gen-label ai-gen-label--sub ai-gen-label--mt">风险等级 risk_level</div>
            <el-radio-group v-model="aiSecurityRiskLevel" size="small" :disabled="aiGenerating">
              <el-radio-button label="高">高</el-radio-button>
              <el-radio-button label="中">中</el-radio-button>
              <el-radio-button label="低">低</el-radio-button>
            </el-radio-group>
            <div class="ai-gen-label ai-gen-label--sub ai-gen-label--mt">扫描范围（可选）</div>
            <el-input
              v-model="aiSecurityScanScope"
              type="textarea"
              :rows="3"
              placeholder="说明 IP/域名范围、接口清单、账号角色或需排除的环境等…"
              :disabled="aiGenerating"
            />
          </template>

          <div class="ai-gen-actions">
            <el-button
              :loading="aiPhase1Editing"
              :disabled="aiGenerating || aiPhase1Editing"
              @click="runAiPhase1Preview"
            >
              {{ aiPhase1Editing ? 'Phase1 分析中…' : 'Phase1 预览' }}
            </el-button>
            <el-button
              type="primary"
              :loading="aiGenerating"
              :disabled="aiGenerating"
              @click="runAiGenerate"
            >
              {{ aiGenerating ? 'AI 思考中…' : '开始生成' }}
            </el-button>
          </div>
        </div>
      </div>

      <div v-if="aiGenerating && !aiStreamText" class="ai-gen-skeleton-wrap">
        <el-skeleton animated :rows="8" />
        <div class="ai-gen-thinking-hint">{{ aiLoadingHint || 'AI 正在思考中…' }}</div>
      </div>

      <div v-if="aiPhase1Analysis" class="ai-gen-phase1-card">
        <div class="ai-gen-label">Phase 1 分析结果</div>
        <div class="ai-gen-phase1-module">
          推导模块：<strong>{{ aiPhase1Analysis.module_name || '通用功能模块' }}</strong>
        </div>
        <ul class="ai-gen-phase1-points">
          <li v-for="(p, idx) in aiPhase1Analysis.key_test_points" :key="`${idx}-${p}`">
            {{ p }}
          </li>
        </ul>
        <div v-if="aiPhase1Override" class="ai-gen-phase1-edit">
          <div class="ai-gen-label ai-gen-label--sub">可编辑（用于本次生成）</div>
          <el-input v-model="aiPhase1Override.module_name" placeholder="模块名" :disabled="aiGenerating" />
          <el-input
            v-model="aiPhase1OverridePointsText"
            type="textarea"
            :rows="4"
            :disabled="aiGenerating"
            placeholder="每行一个测试点（将覆盖 Phase1 推导结果）"
          />
        </div>
      </div>

      <div v-if="aiGenerating || aiStreamText" class="ai-gen-stream-block">
        <div class="ai-gen-label">模型输出（实时）</div>
        <pre class="ai-gen-stream-pre">{{ aiStreamText }}<span v-if="aiGenerating" class="ai-gen-stream-cursor">▍</span></pre>
      </div>

      <div v-if="aiPreviewCases.length" class="ai-gen-preview-block">
        <div class="ai-gen-label">生成预览（勾选后导入）</div>
        <el-form-item label="默认模块" class="ai-gen-module-row">
          <el-select
            v-model="aiImportModule"
            placeholder="可选：当无法从用例/需求推断业务模块时，全部归入此模块"
            filterable
            clearable
            style="width: 280px"
          >
            <el-option v-for="m in flatModules" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
          <div class="ai-gen-module-hint">
            模块名表示<strong>业务功能域</strong>（如「用户登录」「订单支付」），与接口/安全等测试类型无关。
            优先用每条用例的 <code>module_name</code>；若无则从<strong>需求首句/首行</strong>按规则抽取业务模块名；再依次用 Phase1「推导模块」、标题+需求关键词推断；仍无法确定时请选「默认模块」。
            匹配到已有模块则复用，否则<strong>自动新建</strong>同名模块。
          </div>
        </el-form-item>
        <el-form-item v-if="effectiveTestType === 'api'" label="预检环境/变量" class="ai-gen-module-row">
          <el-select
            v-model="precheckEnvId"
            placeholder="可选：选择环境用于拼接 base_url"
            filterable
            clearable
            style="width: 240px"
            :disabled="aiGenerating || aiImporting"
            @change="() => runPreImportPrecheck(aiPreviewCases)"
          >
            <el-option v-for="e in envOptions" :key="e.id" :label="e.name" :value="e.id" />
          </el-select>
          <el-input
            v-model="precheckVarsText"
            placeholder='可选：运行时变量 JSON，例如 {"token":"xxx"}'
            style="width: 420px"
            :disabled="aiGenerating || aiImporting"
            @blur="() => runPreImportPrecheck(aiPreviewCases)"
          />
        </el-form-item>
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 6px 0 10px">
          <el-switch v-model="blockImportOnIssues" active-text="发现问题则阻断导入" inactive-text="允许导入（仅提示）" />
          <div style="color: var(--el-text-color-secondary); font-size: 12px">
            已勾选 {{ selectedIssuesSummary.total }} 条，其中 {{ selectedIssuesSummary.bad }} 条存在问题
            <span v-if="preimportPrecheckLoading" style="margin-left: 10px">预检中…</span>
          </div>
        </div>
        <el-table
          ref="aiPreviewTableRef"
          :data="aiPreviewCases"
          :row-class-name="({ row }) => (rowIssues(row).length ? 'ai-row-has-issues' : '')"
          row-key="_rowKey"
          max-height="320"
          size="small"
          border
          class="admin-data-table"
          @selection-change="onAiPreviewSelectionChange"
        >
          <el-table-column type="selection" width="48" align="center" />
          <el-table-column prop="case_name" label="用例名称" min-width="160" align="left" show-overflow-tooltip>
            <template #default="{ row }">
              <el-tooltip v-if="rowIssues(row).length" :content="rowIssues(row).join('；')" placement="top">
                <span style="color: var(--el-color-danger)">{{ row.case_name || '（空）' }}</span>
              </el-tooltip>
              <span v-else>{{ row.case_name }}</span>
            </template>
          </el-table-column>
          <el-table-column
            v-if="effectiveTestType === 'api'"
            prop="business_id"
            label="业务前缀"
            width="88"
            align="center"
            show-overflow-tooltip
          />
          <el-table-column prop="level" label="等级" width="64" align="center" />
          <el-table-column label="相似提示" width="84" align="center">
            <template #default="{ row }">
              <el-tag
                v-if="Array.isArray(row?.similar_candidates?.semantic) && row.similar_candidates.semantic.length"
                size="small"
                type="warning"
                style="cursor: pointer"
                @click="openSimilarDialog(row)"
              >
                相似
              </el-tag>
              <span v-else>—</span>
            </template>
          </el-table-column>
          <el-table-column label="目标模块" min-width="100" align="center" show-overflow-tooltip>
            <template #default="{ row }">
              {{ (row.module_name || '').trim() || '—' }}
            </template>
          </el-table-column>
          <el-table-column label="模块匹配" min-width="200" align="center">
            <template #default="{ row }">
              <el-select
                v-model="row._target_module_id"
                filterable
                clearable
                placeholder="自动匹配/新建"
                style="width: 180px"
                :disabled="aiGenerating || aiImporting"
              >
                <el-option v-for="m in flatModules" :key="m.id" :label="m.name" :value="m.id" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column prop="precondition" label="前置条件" min-width="100" align="center" show-overflow-tooltip />
          <el-table-column label="步骤数" width="76" align="center">
            <template #default="{ row }">
              <el-tag v-if="Array.isArray(row.steps_list) && row.steps_list.length" size="small" type="success">
                {{ row.steps_list.length }}
              </el-tag>
              <span v-else>—</span>
            </template>
          </el-table-column>
          <el-table-column label="操作步骤" min-width="160" align="center" show-overflow-tooltip>
            <template #default="{ row }">
              <el-popover
                v-if="Array.isArray(row.steps_list) && row.steps_list.length"
                placement="top-start"
                :width="520"
                trigger="hover"
              >
                <template #reference>
                  <span style="cursor: pointer; text-decoration: underline; text-underline-offset: 2px">
                    {{ String(row.steps || '').slice(0, 80) || '查看' }}
                  </span>
                </template>
                <div style="max-height: 260px; overflow: auto; white-space: pre-wrap; font-size: 12px">
                  <div v-for="(s, i) in row.steps_list" :key="i" style="margin-bottom: 10px">
                    <div style="font-weight: 700; margin-bottom: 4px">步骤 {{ i + 1 }}</div>
                    <div>{{ s.step_desc || s.desc || s.action || '—' }}</div>
                    <div style="margin-top: 4px; color: var(--el-text-color-secondary)">
                      预期：{{ s.expected_result || s.expected || '—' }}
                    </div>
                  </div>
                </div>
              </el-popover>
              <span v-else>{{ String(row.steps || '') }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="expected_result" label="预期结果" min-width="120" align="center" show-overflow-tooltip />
        </el-table>
      </div>
    </div>
    <template #footer>
      <el-button @click="closeDialog">关闭</el-button>
      <el-button
        type="primary"
        :loading="aiImporting"
        :disabled="!aiPreviewCases.length || aiGenerating"
        @click="confirmAiImport"
      >
        确认导入
      </el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="showSimilarDialog" title="相似用例对比" width="720px">
    <div v-if="!activeSimilarRow" style="color: var(--el-text-color-secondary)">
      未选择用例
    </div>
    <template v-else>
      <div class="ai-sim-block">
        <div class="ai-gen-label">当前生成用例</div>
        <div class="ai-sim-current-title">{{ activeSimilarRow.case_name || '—' }}</div>
        <pre class="ai-sim-current-steps">{{ String(activeSimilarRow.steps || '').slice(0, 600) }}</pre>
      </div>

      <div class="ai-sim-block">
        <div class="ai-gen-label">语义相似候选（Top）</div>
        <el-table :data="semanticSimilarRows" size="small" border>
          <el-table-column label="分数" width="80" align="center">
            <template #default="{ row }">
              <el-tag size="small" type="success">{{ Number(row.score || 0).toFixed(3) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="case_name" label="标题" min-width="160" show-overflow-tooltip />
          <el-table-column label="步骤摘要" min-width="240" show-overflow-tooltip>
            <template #default="{ row }">
              {{ String(row.steps || '').slice(0, 140) }}
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="ai-sim-block">
        <div class="ai-gen-label">字符串相似候选（Top）</div>
        <el-table :data="stringSimilarRows" size="small" border>
          <el-table-column label="分数" width="80" align="center">
            <template #default="{ row }">
              <el-tag size="small" type="info">{{ Number(row.score || 0).toFixed(3) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="case_name" label="标题" min-width="160" show-overflow-tooltip />
          <el-table-column label="步骤摘要" min-width="240" show-overflow-tooltip>
            <template #default="{ row }">
              {{ String(row.steps || '').slice(0, 140) }}
            </template>
          </el-table-column>
        </el-table>
      </div>
    </template>

    <template #footer>
      <el-button @click="showSimilarDialog = false">关闭</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="showPrecheckDialog" title="导入后预检报告（API）" width="860px">
    <el-table :data="precheckRows" size="small" border v-loading="precheckLoading">
      <template #empty>
        <el-empty description="暂无预检结果" :image-size="86" />
      </template>
      <el-table-column prop="id" label="用例ID" width="90" align="center" />
      <el-table-column prop="case_name" label="用例名称" min-width="180" show-overflow-tooltip />
      <el-table-column label="结果" width="90" align="center">
        <template #default="{ row }">
          <el-tag size="small" :type="row.ok ? 'success' : 'danger'" effect="plain">
            {{ row.ok ? '通过' : '有问题' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="未替换变量" min-width="220" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="Array.isArray(row.unresolved_vars) && row.unresolved_vars.length">
            {{ row.unresolved_vars.join(', ') }}
          </span>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column label="请求预览" min-width="240" show-overflow-tooltip>
        <template #default="{ row }">
          {{ (row.request?.method || '—') + ' ' + (row.request?.url || '—') }}
        </template>
      </el-table-column>
      <el-table-column prop="error" label="错误" min-width="180" show-overflow-tooltip />
    </el-table>
    <template #footer>
      <el-button @click="showPrecheckDialog = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createCaseApi,
  createCaseStepApi,
  createModuleApi,
  aiImportCasesApi,
  batchPreviewRunApiCaseApi,
  aiImportPrecheckApi,
} from '@/api/testcase'
import {
  AI_QUICK_START_BY_TYPE,
  mergeTestTypePromptWithRequirement,
} from '@/utils/aiTestTypePrompts'
import { extractBusinessModuleNameFromRequirement } from '@/utils/extractBusinessModuleFromRequirement'
import { previewAiPhase1Api, streamGenerateAiCases } from '@/api/assistant'
import { getEnvironments } from '@/api/environment'

const AI_ASSISTANT_MODEL_ROUTE = '/ai-assistant?tab=model'

const TEST_CASE_ROUTE_TYPES = ['functional', 'api', 'performance', 'security', 'ui-automation'] as const

const SECURITY_VECTOR_OPTIONS = [
  { value: 'SQLi', label: 'SQLi' },
  { value: 'XSS', label: 'XSS' },
  { value: 'CSRF', label: 'CSRF' },
  { value: '越权', label: '越权' },
  { value: '敏感信息泄露', label: '敏感信息泄露' },
]

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    /** 扁平模块列表（与父页一致） */
    flatModules: Array<{ id: number; name: string; parent?: unknown }>
    /** 当前路由/页签测试类型 */
    testCaseType: string
    /** 左侧树当前选中模块 id */
    selectedModuleId?: number | null
    /** 当前项目 id，导入前校验 */
    projectId?: number | null
  }>(),
  {
    selectedModuleId: null,
    projectId: null,
  },
)

const emit = defineEmits<{
  'update:modelValue': [open: boolean]
  /** 导入成功并已关闭弹窗后，父级可 loadModules + fetchTestCases */
  imported: []
  /** 批量导入过程中新建模块，便于父级同步 flatModules */
  'append-flat-module': [row: { id: number; name: string; parent: null }]
}>()

const effectiveTestType = computed(() => {
  const t = String(props.testCaseType || '').trim()
  return TEST_CASE_ROUTE_TYPES.includes(t as (typeof TEST_CASE_ROUTE_TYPES)[number])
    ? t
    : 'functional'
})

/** Phase1 占位名：不作为真实业务模块导入 */
const WEAK_PHASE1_MODULE_NAMES = new Set(
  ['通用功能模块', '通用模块', '未分类模块', '其它', '其他', '未知模块'].map((s) => s.toLowerCase()),
)

/** 从用例标题/步骤与需求描述推断业务模块（按场景而非测试类型） */
const MODULE_NAME_INFER_RULES: Array<{ needles: string[]; moduleName: string }> = [
  {
    needles: ['登录', '登入', '口令', '密码错误', '账号锁定', 'session', 'token', '鉴权', '登出', '单点'],
    moduleName: '用户登录',
  },
  {
    needles: ['注册', '开户', '验证码', '重置密码', '找回密码', '绑定手机'],
    moduleName: '用户注册与账户',
  },
  { needles: ['支付', '付款', '收银', '退款', '对账', '结算'], moduleName: '支付' },
  { needles: ['订单', '下单', '取消订单', '发货', '物流'], moduleName: '订单管理' },
  { needles: ['购物车', '加购'], moduleName: '购物车' },
  { needles: ['优惠券', '促销', '折扣', '满减'], moduleName: '营销优惠' },
  { needles: ['权限', '越权', '角色', 'rbac', '访问控制', '授权'], moduleName: '权限与访问控制' },
  { needles: ['注入', 'sql', 'xss', 'csrf', '漏洞', '渗透', '敏感信息'], moduleName: '安全加固' },
  { needles: ['上传', '附件', '文件下载'], moduleName: '文件与附件' },
  { needles: ['搜索', '筛选', '列表查询', '分页'], moduleName: '检索与列表' },
  { needles: ['通知', '消息', '站内信', '推送', '短信', '邮件'], moduleName: '消息通知' },
]

function collectRowTextForInference(row: Record<string, unknown>): string {
  const parts = [
    row.case_name,
    row.caseName,
    row.name,
    row.precondition,
    row.steps,
    row.expected_result,
    row.expectedResult,
  ]
  return parts.map((x) => String(x ?? '').trim()).filter(Boolean).join(' ')
}

function inferModuleNameFromScenario(row: Record<string, unknown>, requirement: string): string {
  const blob = `${collectRowTextForInference(row)} ${String(requirement || '').trim()}`
  if (!blob.trim()) return ''
  const lower = blob.toLowerCase()
  for (const { needles, moduleName } of MODULE_NAME_INFER_RULES) {
    if (needles.some((n) => blob.includes(n) || lower.includes(n.toLowerCase()))) {
      return moduleName
    }
  }
  return ''
}

function phase1ModuleNameForImport(): string {
  const raw = String(aiPhase1Analysis.value?.module_name ?? '').trim()
  if (!raw) return ''
  if (WEAK_PHASE1_MODULE_NAMES.has(raw.toLowerCase())) return ''
  return raw
}

/** 导入时解析业务模块：用例字段 → 需求首句抽取 → Phase1 → 场景关键词；均无时需「默认模块」 */
function resolvedModuleNameForImport(row: Record<string, unknown>): string {
  const direct = aiRowModuleName(row)
  if (direct) return direct
  const fromReq = extractBusinessModuleNameFromRequirement(aiRequirement.value)
  if (fromReq) return fromReq
  const p1 = phase1ModuleNameForImport()
  if (p1) return p1
  return inferModuleNameFromScenario(row, aiRequirement.value)
}

const aiRequirement = ref('')
const aiApiSpec = ref('')
const aiFunctionalFlow = ref('')
const aiUiLocators = ref('')
const aiPerfMetrics = ref('')
const aiSecurityVulnTypes = ref<string[]>([])
const aiSecurityRiskLevel = ref('中')
const aiSecurityScanScope = ref('')
const aiStreamText = ref('')
const aiGenerating = ref(false)
const aiImporting = ref(false)
const aiPreviewCases = ref<Record<string, unknown>[]>([])
const aiRunId = ref<number | null>(null)
const aiImportModule = ref<number | null>(null)
const aiPreviewTableRef = ref()
const aiSelectedPreview = ref<Record<string, unknown>[]>([])
const aiLoadingHint = ref('')
const aiPhase1Analysis = ref<{ module_name: string; key_test_points: string[] } | null>(null)
const aiPhase1Override = ref<{ module_name: string; key_test_points: string[] } | null>(null)
const aiPhase1OverridePointsText = ref('')
const aiPhase1Editing = ref(false)
let aiLoadingTimer1: ReturnType<typeof setTimeout> | null = null
let aiLoadingTimer2: ReturnType<typeof setTimeout> | null = null

const showSimilarDialog = ref(false)
const activeSimilarRow = ref<Record<string, unknown> | null>(null)

const showPrecheckDialog = ref(false)
const precheckLoading = ref(false)
const precheckRows = ref<Record<string, unknown>[]>([])
const preimportPrecheckLoading = ref(false)

const precheckEnvId = ref<number | null>(null)
const precheckVarsText = ref<string>('{}')
const envOptions = ref<Array<{ id: number; name: string }>>([])

function parsePrecheckVars(): Record<string, unknown> {
  const t = String(precheckVarsText.value || '').trim()
  if (!t) return {}
  try {
    const v = JSON.parse(t)
    return v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : {}
  } catch {
    return {}
  }
}

async function loadEnvOptions() {
  if (effectiveTestType.value !== 'api') return
  try {
    const { data } = await getEnvironments({ page_size: 100 })
    const rows = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : []
    envOptions.value = rows
      .map((x: any) => ({ id: Number(x?.id), name: String(x?.name || '') }))
      .filter((x: any) => Number.isFinite(x.id) && x.name)
  } catch {
    envOptions.value = []
  }
}

const blockImportOnIssues = ref(true)

function rowIssues(row: Record<string, unknown>): string[] {
  const issues: string[] = []
  const name = String(row.case_name || '').trim()
  if (!name) issues.push('缺少用例名称')
  const mid = row._target_module_id
  if (mid == null || mid === '') issues.push('未指定目标模块')
  const stepsText = String(row.steps || '').trim()
  const stepsList = Array.isArray(row.steps_list) ? row.steps_list : Array.isArray(row.stepsList) ? row.stepsList : []
  if (!stepsText && (!Array.isArray(stepsList) || !stepsList.length)) issues.push('缺少步骤')
  const unresolved = Array.isArray(row.unresolved_vars) ? row.unresolved_vars : []
  if (unresolved.length) issues.push(`存在未替换变量：${unresolved.slice(0, 6).join(', ')}`)
  const perr = String((row as any)._precheck_error || '').trim()
  if (perr) issues.push(`预检失败：${perr}`)
  if (effectiveTestType.value === 'api') {
    const url = String(row.api_url || '').trim()
    const method = String(row.api_method || '').trim()
    if (!url) issues.push('API 缺少 url')
    if (!method) issues.push('API 缺少 method')
  }
  return issues
}

async function runPreImportPrecheck(rows: Record<string, unknown>[]) {
  if (effectiveTestType.value !== 'api') return
  if (!rows?.length) return
  preimportPrecheckLoading.value = true
  try {
    const items = rows.map((r) => ({
      case_name: r.case_name,
      api_url: r.api_url,
      api_method: r.api_method,
      api_headers: r.api_headers,
      api_body: r.api_body,
    }))
    const overrides = {
      environment_id: precheckEnvId.value,
      variables: parsePrecheckVars(),
    }
    const res = await aiImportPrecheckApi({ test_type: 'api', overrides, items })
    const d = res?.data || {}
    const list = Array.isArray(d.results) ? d.results : []
    for (const pr of list) {
      const idx = pr.index
      if (typeof idx !== 'number') continue
      const row = rows[idx]
      if (!row) continue
      row.unresolved_vars = Array.isArray(pr.unresolved_vars) ? pr.unresolved_vars : []
      row._precheck_error = pr.error || ''
      // 同步一份最终 URL 用于展示（不改变原字段）
      if (pr.request && typeof pr.request === 'object') {
        row._precheck_final_url = pr.request.url
      }
    }
  } catch {
    // ignore
  } finally {
    preimportPrecheckLoading.value = false
  }
}

const selectedIssuesSummary = computed(() => {
  const rows = aiSelectedPreview.value || []
  let bad = 0
  for (const r of rows) {
    if (rowIssues(r).length) bad += 1
  }
  return { bad, total: rows.length }
})

const semanticSimilarRows = computed(() => {
  const row = activeSimilarRow.value || {}
  const c = row?.similar_candidates
  const list = Array.isArray((c as any)?.semantic) ? (c as any).semantic : []
  return list
})

const stringSimilarRows = computed(() => {
  const row = activeSimilarRow.value || {}
  const c = row?.similar_candidates
  const list = Array.isArray((c as any)?.string) ? (c as any).string : []
  return list
})

const aiGenEffectiveModuleId = computed(() => {
  const m = aiImportModule.value
  if (m != null && m !== '') return m
  const s = props.selectedModuleId
  if (s != null && s !== '') return s
  return null
})

const aiGenRagLinked = computed(
  () => aiGenEffectiveModuleId.value != null && aiGenEffectiveModuleId.value !== '',
)

const aiGenModuleSelected = computed(
  () => aiImportModule.value != null && aiImportModule.value !== '',
)

function onDialogVisible(open: boolean) {
  emit('update:modelValue', open)
}

function closeDialog() {
  emit('update:modelValue', false)
}

function resetAiForm() {
  aiRequirement.value = ''
  aiApiSpec.value = ''
  aiFunctionalFlow.value = ''
  aiUiLocators.value = ''
  aiPerfMetrics.value = ''
  aiSecurityVulnTypes.value = []
  aiSecurityRiskLevel.value = '中'
  aiSecurityScanScope.value = ''
  aiStreamText.value = ''
  aiLoadingHint.value = ''
  aiPhase1Analysis.value = null
  aiPreviewCases.value = []
  aiSelectedPreview.value = []
  aiImportModule.value =
    props.selectedModuleId != null && props.selectedModuleId !== ''
      ? (props.selectedModuleId as number)
      : null
  precheckEnvId.value = null
  precheckVarsText.value = '{}'
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      resetAiForm()
      loadEnvOptions()
    }
  },
)

function onDialogClosed() {
  aiGenerating.value = false
  aiImporting.value = false
  stopAiLoadingHints()
}

function stopAiLoadingHints() {
  if (aiLoadingTimer1) {
    clearTimeout(aiLoadingTimer1)
    aiLoadingTimer1 = null
  }
  if (aiLoadingTimer2) {
    clearTimeout(aiLoadingTimer2)
    aiLoadingTimer2 = null
  }
}

function startAiLoadingHints() {
  stopAiLoadingHints()
  aiLoadingHint.value = '🤖 正在规划测试模块与边界...'
  aiLoadingTimer1 = setTimeout(() => {
    if (!aiGenerating.value) return
    aiLoadingHint.value = '📚 正在检索 AITesta 知识库规范...'
  }, 4000)
  aiLoadingTimer2 = setTimeout(() => {
    if (!aiGenerating.value) return
    aiLoadingHint.value = '✨ 正在结合规范生成详细用例，请稍候...'
  }, 6000)
}

function handleAiAuthExpired(message?: string) {
  const tip =
    message ||
    '模型 API Key 可能已失效或过期，请到「智能助手 -> 模型接入」更新后重试'
  ElMessageBox.confirm(
    `${tip}\n\n是否立即前往模型接入页面？`,
    '模型配置提示',
    {
      confirmButtonText: '前往配置',
      cancelButtonText: '留在当前页',
      type: 'warning',
    },
  )
    .then(() => {
      if (
        window.location.pathname !== '/ai-assistant' ||
        !window.location.search.includes('tab=model')
      ) {
        window.location.href = AI_ASSISTANT_MODEL_ROUTE
      }
    })
    .catch(() => {
      /* 用户选择留在当前页面 */
    })
}

function extractCreatedCaseId(axiosRes: { data?: { data?: { id?: number }; id?: number } }) {
  const d = axiosRes?.data
  if (d && typeof d === 'object' && 'data' in d && d.data && typeof d.data === 'object' && 'id' in d.data) {
    return (d.data as { id?: number }).id
  }
  if (d && typeof d === 'object' && 'id' in d) return (d as { id?: number }).id
  return null
}

function buildAiExtConfig() {
  const tt = effectiveTestType.value
  const ragOn = aiGenRagLinked.value
  const ext: Record<string, unknown> = {
    api_spec: '',
    ui_elements: '',
    perf_targets: {},
    sec_vectors: [] as string[],
    risk_level: '',
    scan_scope: '',
    business_flow: '',
    is_rag_enabled: ragOn,
  }
  if (tt === 'api') {
    ext.api_spec = (aiApiSpec.value || '').trim()
  } else if (tt === 'functional') {
    ext.business_flow = (aiFunctionalFlow.value || '').trim()
  } else if (tt === 'ui-automation') {
    ext.ui_elements = (aiUiLocators.value || '').trim()
  } else if (tt === 'performance') {
    const notes = (aiPerfMetrics.value || '').trim()
    ext.perf_targets = notes ? { notes } : {}
  } else if (tt === 'security') {
    ext.sec_vectors = Array.isArray(aiSecurityVulnTypes.value) ? [...aiSecurityVulnTypes.value] : []
    ext.risk_level = aiSecurityRiskLevel.value || '中'
    ext.scan_scope = (aiSecurityScanScope.value || '').trim()
  }
  return ext
}

function hasAiGenerateAnyInput() {
  const req = (aiRequirement.value || '').trim()
  if (req) return true
  const tt = effectiveTestType.value
  if (tt === 'api' && (aiApiSpec.value || '').trim()) return true
  if (tt === 'functional' && (aiFunctionalFlow.value || '').trim()) return true
  if (tt === 'ui-automation' && (aiUiLocators.value || '').trim()) return true
  if (tt === 'performance' && (aiPerfMetrics.value || '').trim()) return true
  if (tt === 'security') {
    if ((aiSecurityScanScope.value || '').trim()) return true
    if (aiSecurityVulnTypes.value?.length) return true
  }
  return false
}

function fillAiQuickStart() {
  const tt = effectiveTestType.value
  aiRequirement.value =
    AI_QUICK_START_BY_TYPE[tt as keyof typeof AI_QUICK_START_BY_TYPE] ??
    AI_QUICK_START_BY_TYPE.functional
}

function onAiPreviewSelectionChange(rows: Record<string, unknown>[]) {
  aiSelectedPreview.value = rows || []
}

function openSimilarDialog(row: Record<string, unknown>) {
  activeSimilarRow.value = row || null
  showSimilarDialog.value = true
}

function normalizePhase1Analysis(input: unknown) {
  if (!input || typeof input !== 'object') return null
  const obj = input as { module_name?: unknown; key_test_points?: unknown }
  const moduleName = String(obj.module_name ?? '').trim() || '通用功能模块'
  const pointsRaw = obj.key_test_points
  const points = Array.isArray(pointsRaw)
    ? pointsRaw.map((x) => String(x ?? '').trim()).filter(Boolean)
    : []
  return { module_name: moduleName, key_test_points: points }
}

async function runAiGenerate() {
  if (!hasAiGenerateAnyInput()) {
    ElMessage.warning('请填写需求描述，或完善当前测试类型下的补充字段')
    return
  }
  const effectiveType = effectiveTestType.value
  const req = (aiRequirement.value || '').trim()
  const spec = (aiApiSpec.value || '').trim()
  const promptTextMerged = req ? mergeTestTypePromptWithRequirement(effectiveType, req) : ''
  const ext_config = buildAiExtConfig()
  const payload: Record<string, unknown> = {
    test_type: effectiveType,
    prompt_text: promptTextMerged,
    ext_config,
    requirement: promptTextMerged,
    testType: effectiveType,
    dedup_mode: 'highlight',
  }
  if (aiPhase1Override.value) {
    payload.phase1_override = {
      module_name: aiPhase1Override.value.module_name,
      key_test_points: aiPhase1OverridePointsText.value
        .split('\n')
        .map((x) => x.trim())
        .filter(Boolean),
    }
  }
  if (spec && effectiveType === 'api') {
    payload.api_spec = spec
  }
  let ragMid = aiImportModule.value
  if (ragMid == null || ragMid === '') {
    ragMid = props.selectedModuleId as number | null
  }
  if (ragMid != null && ragMid !== '') {
    payload.module_id = ragMid
  }
  aiGenerating.value = true
  startAiLoadingHints()
  aiPreviewCases.value = []
  aiSelectedPreview.value = []
  aiStreamText.value = ''
  aiRunId.value = null
  aiPhase1Analysis.value = null
  aiPhase1Override.value = null
  aiPhase1OverridePointsText.value = ''
  aiPhase1Editing.value = false
  let finished = false
  try {
    let deltaRun = ''
    await streamGenerateAiCases(payload, {
      onEvent: async (evt: any) => {
        if (!evt || finished) return
        if (evt.type === 'connected') return
        if (evt.type === 'phase' && typeof evt.message === 'string') {
          aiLoadingHint.value = evt.message
          return
        }
        if (evt.type === 'phase1_analysis') {
          const norm = normalizePhase1Analysis(evt.data)
          if (norm) aiPhase1Analysis.value = norm
          return
        }
        if (evt.type === 'all_covered') {
          const coveredPhase1 = normalizePhase1Analysis(evt.phase1_analysis)
          if (coveredPhase1) aiPhase1Analysis.value = coveredPhase1
          deltaRun = ''
          aiStreamText.value = ''
          ElMessage.info(evt.message || '语义检索：当前模块下已有用例已覆盖该需求，未生成新用例。')
          finished = true
          return
        }
        if (evt.type === 'delta' && typeof evt.text === 'string') {
          const chunkTrim = evt.text.trim()
          if (/^\[ALL_COVERED\]$/i.test(chunkTrim)) {
            deltaRun = ''
            aiStreamText.value = ''
            ElMessage.info('语义检索：当前模块下已有用例已覆盖该需求，未生成新用例。')
            finished = true
            return
          }
          deltaRun += evt.text
          return
        }
        if (evt.type === 'malformed') {
          console.error('[AI Stream] 收到格式错误的 SSE 事件:', evt)
          ElMessage.error('服务器返回数据格式错误，请重试或联系管理员')
          finished = true
          return
        }
        if (evt.type === 'error') {
          if (deltaRun) {
            aiStreamText.value += deltaRun
            deltaRun = ''
          }
          const evtCode = String(evt.code || '').trim()
          const evtMsg = String(evt.message || '').trim() || '生成失败'

          // 如果是解析失败，显示更详细的信息
          if (evt.parse_failed) {
            console.error('[AI Stream] JSON 解析失败:', {
              snippet: evt.snippet,
              failure_fragment: evt.failure_fragment,
              parse_error: evt.parse_error,
              truncated: evt.truncated
            })

            // 将失败片段保存到流式文本中，方便用户查看
            if (evt.failure_fragment) {
              aiStreamText.value = String(evt.failure_fragment)
            }

            // 显示详细错误信息
            let detailMsg = evtMsg
            if (evt.parse_error) {
              detailMsg += `\n\n错误详情: ${evt.parse_error}`
            }
            if (evt.truncated) {
              detailMsg += '\n\n提示: 模型输出可能因长度限制被截断'
            }

            ElMessage({
              type: 'error',
              message: detailMsg,
              duration: 8000,
              showClose: true
            })
          } else if (evtCode === 'AUTH_ERROR') {
            handleAiAuthExpired(evtMsg)
          } else {
            ElMessage.error(evtMsg)
          }
          finished = true
          return
        }
        if (evt.type === 'done' && evt.success && Array.isArray(evt.cases)) {
          const donePhase1 = normalizePhase1Analysis(evt.phase1_analysis)
          if (donePhase1) aiPhase1Analysis.value = donePhase1
          if (deltaRun) {
            aiStreamText.value += deltaRun
            deltaRun = ''
          }
          const cases = evt.cases as Record<string, unknown>[]
          const rid = evt.run_id
          if (typeof rid === 'number' && Number.isFinite(rid)) {
            aiRunId.value = rid
          }
          aiPreviewCases.value = cases.map((row, idx) => {
            const headersRaw = (row as any).api_headers
            const headersClone =
              headersRaw && typeof headersRaw === 'object' && !Array.isArray(headersRaw)
                ? { ...(headersRaw as object) }
                : {}
            let bodyClone: unknown = {}
            const ab = (row as any).api_body
            if (ab !== undefined && ab !== null && typeof ab === 'object') {
              try {
                bodyClone = JSON.parse(JSON.stringify(ab))
              } catch {
                bodyClone = ab
              }
            } else if (ab !== undefined && ab !== null) {
              bodyClone = ab
            }
            const base = { ...(row as any), api_headers: headersClone, api_body: bodyClone, _rowKey: idx }
            return { ...base, _target_module_id: suggestTargetModuleId(base) }
          })
          await runPreImportPrecheck(aiPreviewCases.value)
          aiStreamText.value = ''
          ElMessage.success(evt.message || `已生成 ${cases.length} 条用例`)
          finished = true
        }
      },
    })

    if (deltaRun) {
      const merged = (aiStreamText.value + deltaRun).replace(/\s+/g, ' ').trim()
      if (/^\[ALL_COVERED\]$/i.test(merged)) {
        aiStreamText.value = ''
        ElMessage.info('语义检索：当前模块下已有用例已覆盖该需求，未生成新用例。')
        finished = true
      } else {
        aiStreamText.value += deltaRun
      }
    }
    if (!finished && !aiPreviewCases.value.length) {
      if (aiStreamText.value) {
        ElMessage.warning('流已结束，但未能解析为结构化用例，请检查模型输出或缩短需求后重试')
      } else {
        ElMessage.warning('未收到模型输出，请重试')
      }
    }
  } catch (err) {
    ElMessage.error((err as Error)?.message || '生成请求失败')
  } finally {
    aiGenerating.value = false
    stopAiLoadingHints()
  }
}

async function runAiPhase1Preview() {
  if (!hasAiGenerateAnyInput()) {
    ElMessage.warning('请先填写需求描述（或补充字段）')
    return
  }
  const effectiveType = effectiveTestType.value
  const req = (aiRequirement.value || '').trim()
  const spec = (aiApiSpec.value || '').trim()
  const promptTextMerged = req ? mergeTestTypePromptWithRequirement(effectiveType, req) : ''
  const ext_config = buildAiExtConfig()
  const payload: Record<string, unknown> = {
    test_type: effectiveType,
    prompt_text: promptTextMerged,
    ext_config,
    requirement: promptTextMerged,
    testType: effectiveType,
  }
  if (spec && effectiveType === 'api') payload.api_spec = spec
  let ragMid = aiImportModule.value
  if (ragMid == null || ragMid === '') ragMid = props.selectedModuleId as number | null
  if (ragMid != null && ragMid !== '') payload.module_id = ragMid
  aiPhase1Editing.value = true
  try {
    const res = await previewAiPhase1Api(payload)
    const d = res?.data?.data || res?.data || {}
    const norm = normalizePhase1Analysis(d)
    if (!norm) {
      ElMessage.warning('Phase1 结果为空，请重试')
      return
    }
    aiPhase1Analysis.value = norm
    aiPhase1Override.value = { ...norm, key_test_points: [...(norm.key_test_points || [])] }
    aiPhase1OverridePointsText.value = (norm.key_test_points || []).join('\n')
    ElMessage.success('已获取 Phase1 预览结果，可编辑后再生成')
  } catch (e: any) {
    ElMessage.error(e?.message || 'Phase1 预览失败')
  } finally {
    aiPhase1Editing.value = false
  }
}

function buildStepDescFromAi(row: Record<string, unknown>) {
  const parts: string[] = []
  const pre = String(row.precondition ?? '').trim()
  if (pre) {
    parts.push(`【前置条件】\n${pre}`)
  }
  const steps = String(row.steps ?? '').trim()
  if (steps) {
    parts.push(`【操作步骤】\n${steps}`)
  }
  return parts.join('\n\n') || '（无详细步骤，请编辑补充）'
}

function aiRowModuleName(row: Record<string, unknown>) {
  return String(row.module_name ?? row.moduleName ?? '').trim()
}

function normModuleNameKey(name: string) {
  return String(name || '').trim().toLowerCase()
}

function findFlatModuleByName(name: string) {
  const k = normModuleNameKey(name)
  if (!k) return null
  return props.flatModules.find((m) => normModuleNameKey(m.name) === k) ?? null
}

function suggestTargetModuleId(row: Record<string, unknown>): number | null {
  const name = resolvedModuleNameForImport(row)
  const hit = findFlatModuleByName(name)
  return hit?.id ?? null
}

async function ensureModuleIdForAiImport(moduleName: string, createdByKey: Map<string, number>) {
  const pid = props.projectId
  if (pid == null) {
    throw new Error('请先在顶部选择项目')
  }
  const raw = String(moduleName || '').trim()
  if (!raw) return null
  const tt = effectiveTestType.value
  if (!TEST_CASE_ROUTE_TYPES.includes(tt as (typeof TEST_CASE_ROUTE_TYPES)[number])) {
    throw new Error('当前测试类型无效，请刷新页面后重试')
  }
  const k = normModuleNameKey(raw)
  if (createdByKey.has(k)) {
    return createdByKey.get(k)!
  }
  const existing = findFlatModuleByName(raw)
  if (existing) {
    createdByKey.set(k, existing.id)
    return existing.id
  }
  const res = await createModuleApi({
    project: pid as number,
    name: raw,
    parent: null,
    test_type: tt,
  })
  const d = res?.data as { id?: number; data?: { id?: number } } | undefined
  const newId = d?.id ?? d?.data?.id
  if (newId == null) {
    throw new Error('创建模块后未返回 ID')
  }
  createdByKey.set(k, newId)
  emit('append-flat-module', { id: newId, name: raw, parent: null })
  return newId
}

/** 回收站同名冲突时自动改名再建，避免批量 AI 导入整批失败 */
async function createCaseApiResolvingRecycleConflict(
  payload: Record<string, unknown>,
  originalCaseName: string,
) {
  try {
    return await createCaseApi(payload)
  } catch (err: unknown) {
    const ax = err as { response?: { status?: number; data?: Record<string, unknown> } }
    const status = ax.response?.status
    const data = ax.response?.data || {}
    const codeRaw = data.code
    const code = Array.isArray(codeRaw) ? codeRaw[0] : codeRaw
    if (status === 409 && String(code || '') === 'RECYCLE_CONFLICT') {
      const base = String(originalCaseName || payload.case_name || '').trim() || '用例'
      const suffix = `·${Date.now().toString(36).slice(-6)}`
      const nextName = `${base}${suffix}`.slice(0, 255)
      return await createCaseApi({ ...payload, case_name: nextName })
    }
    throw err
  }
}

async function confirmAiImport() {
  const selected = aiSelectedPreview.value.length ? aiSelectedPreview.value : []
  if (!selected.length) {
    ElMessage.warning('请先在表格中勾选要导入的用例')
    return
  }
  if (props.projectId == null) {
    ElMessage.warning('请先在顶部选择项目')
    return
  }
  if (blockImportOnIssues.value) {
    const badRows = selected.filter((r) => rowIssues(r).length)
    if (badRows.length) {
      ElMessage.warning(`已阻断导入：所选 ${badRows.length} 条存在问题（请在表格中查看红色提示）`)
      return
    }
  }
  try {
    aiImporting.value = true
    const tt = effectiveTestType.value
    const items = selected.map((row) => ({
      case_name: row.case_name,
      level: row.level,
      module_id: row._target_module_id ?? null,
      module_name: resolvedModuleNameForImport(row),
      expected_result: row.expected_result,
      precondition: row.precondition,
      steps: row.steps,
      steps_list: Array.isArray(row.steps_list) ? row.steps_list : (Array.isArray(row.stepsList) ? row.stepsList : null),
      api_url: row.api_url,
      api_method: row.api_method,
      api_headers: row.api_headers,
      api_body: row.api_body,
      api_expected_status: row.api_expected_status,
      api_source_curl: row.api_source_curl,
      attack_surface: row.attack_surface,
      tool_preset: row.tool_preset,
      risk_level: row.risk_level,
    }))
    const res = await aiImportCasesApi({
      project_id: props.projectId,
      test_type: tt,
      run_id: aiRunId.value || null,
      default_module_id: aiImportModule.value ?? null,
      module_match_threshold: 0.92,
      strict: true,
      precheck_overrides: {
        environment_id: precheckEnvId.value,
        variables: parsePrecheckVars(),
      },
      items,
    })
    const d = res?.data || {}
    const ok = Array.isArray(d.imported) ? d.imported.length : 0
    const skipped = Number(d.skipped || 0)
    const failed = Array.isArray(d.failed) ? d.failed : []

    if (!ok) {
      ElMessage.warning(
        skipped
          ? '未能导入：缺少业务模块归属。请在需求中写明功能域（如登录、订单）、或勾选「默认模块」、或重新生成带 module_name 的用例。'
          : failed.length
            ? `未能导入：${failed[0]?.error || '未知错误'}`
            : '没有成功导入任何用例',
      )
      return
    }
    // 导入后自动预检（仅 API 类型）：预览最终请求 + 检测未替换变量
    if (tt === 'api') {
      const importedIds = Array.isArray(d.imported)
        ? d.imported.map((x: any) => x?.case_id).filter((x: any) => typeof x === 'number')
        : []
      if (importedIds.length) {
        try {
          precheckLoading.value = true
          showPrecheckDialog.value = true
          precheckRows.value = []
          const r = await batchPreviewRunApiCaseApi({
            ids: importedIds,
            overrides: { environment_id: precheckEnvId.value, variables: parsePrecheckVars() },
          })
          const pd = r?.data || {}
          precheckRows.value = Array.isArray(pd.results) ? pd.results : []
        } catch {
          precheckRows.value = []
        } finally {
          precheckLoading.value = false
        }
      }
    }
    if (failed.length) {
      ElMessage.warning(`已导入 ${ok} 条；失败 ${failed.length} 条（可在控制台查看原因）`)
      // eslint-disable-next-line no-console
      console.warn('AI import failed items:', failed)
    } else if (skipped) {
      ElMessage.warning(`已导入 ${ok} 条；另有 ${skipped} 条因缺少模块归属已跳过`)
    } else {
      ElMessage.success(`成功导入 ${ok} 条用例`)
    }
    emit('update:modelValue', false)
    emit('imported')
  } catch (err) {
    const msg =
      (err as { response?: { data?: { msg?: string } } })?.response?.data?.msg ||
      (err as Error)?.message ||
      '导入失败'
    ElMessage.error(typeof msg === 'string' ? msg : '导入失败')
  } finally {
    aiImporting.value = false
  }
}

onBeforeUnmount(() => {
  stopAiLoadingHints()
})
</script>

<style scoped>
.ai-row-has-issues :deep(td) {
  background: rgba(239, 68, 68, 0.08) !important;
}
.ai-generate-dialog :deep(.el-dialog__body) {
  overflow: visible;
  padding-top: 10px;
}
.ai-generate-dialog .ai-gen-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.ai-gen-rag-strip {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid rgba(59, 130, 246, 0.35);
  background: linear-gradient(
    90deg,
    rgba(30, 64, 175, 0.22),
    rgba(15, 23, 42, 0.55)
  );
  margin-bottom: 4px;
}
.ai-gen-rag-strip--info {
  border-color: rgba(59, 130, 246, 0.35);
  background: linear-gradient(
    90deg,
    rgba(30, 64, 175, 0.22),
    rgba(15, 23, 42, 0.55)
  );
}
.ai-gen-rag-strip--on {
  border-color: rgba(34, 197, 94, 0.45);
  background: linear-gradient(
    90deg,
    rgba(22, 101, 52, 0.22),
    rgba(15, 23, 42, 0.55)
  );
}
.ai-gen-rag-strip__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: rgba(96, 165, 250, 0.9);
  flex-shrink: 0;
}
.ai-gen-rag-strip--on .ai-gen-rag-strip__dot {
  background: #22c55e;
  box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.65);
  animation: ai-rag-breathe 2.2s ease-in-out infinite;
}
@keyframes ai-rag-breathe {
  0%,
  100% {
    opacity: 1;
    box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.55);
  }
  50% {
    opacity: 0.88;
    box-shadow: 0 0 14px 4px rgba(34, 197, 94, 0.35);
  }
}
.ai-gen-rag-strip__text {
  font-size: 13px;
  font-weight: 600;
  color: rgba(226, 232, 240, 0.92);
  letter-spacing: 0.02em;
}
.ai-gen-modal-scroll {
  max-height: min(52vh, 480px);
  overflow-y: auto;
  padding-right: 6px;
}
.ai-gen-skeleton-wrap {
  padding: 8px 0 4px;
}
.ai-gen-thinking-hint {
  margin-top: 10px;
  font-size: 12px;
  color: rgba(148, 163, 184, 0.95);
  text-align: center;
}
.ai-gen-label {
  font-size: 13px;
  font-weight: 600;
  color: rgba(226, 232, 240, 0.9);
  margin-bottom: 8px;
}
.ai-gen-label--inline {
  margin-bottom: 0;
}
.ai-gen-label--mt {
  margin-top: 12px;
}
.ai-gen-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.ai-gen-security-select {
  margin-bottom: 8px;
}
.ai-gen-label--sub {
  margin-top: 12px;
  font-weight: 500;
}
.ai-gen-optional-hint {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  font-weight: 400;
  color: rgba(148, 163, 184, 0.95);
  line-height: 1.45;
}
.ai-gen-api-spec :deep(textarea) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
}
.ai-gen-actions {
  margin-top: 10px;
}
.ai-gen-stream-block {
  margin-top: 4px;
}
.ai-gen-phase1-card {
  margin-top: 4px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid rgba(0, 216, 255, 0.18);
  background: rgba(6, 10, 20, 0.35);
}
.ai-gen-phase1-module {
  font-size: 12px;
  color: rgba(226, 232, 240, 0.92);
  margin-bottom: 6px;
}
.ai-gen-phase1-points {
  margin: 0;
  padding-left: 18px;
  color: rgba(203, 213, 225, 0.92);
  font-size: 12px;
  line-height: 1.5;
}
.ai-gen-phase1-points li + li {
  margin-top: 2px;
}

.ai-sim-block {
  margin-top: 12px;
}
.ai-sim-current-title {
  font-weight: 600;
  margin: 6px 0;
}
.ai-sim-current-steps {
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 160px;
  overflow: auto;
  background: rgba(6, 10, 20, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 10px;
  border-radius: 8px;
  color: rgba(226, 232, 240, 0.92);
  font-size: 12px;
  line-height: 1.55;
}
.ai-gen-stream-pre {
  margin: 0;
  max-height: 220px;
  overflow: auto;
  padding: 12px;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
  color: rgba(226, 232, 240, 0.92);
  background: rgba(6, 10, 20, 0.55);
  border: 1px solid rgba(0, 255, 255, 0.12);
  border-radius: 8px;
}
.ai-gen-stream-cursor {
  display: inline-block;
  color: #00d8ff;
  animation: ai-stream-blink 1s step-end infinite;
}
@keyframes ai-stream-blink {
  50% {
    opacity: 0;
  }
}
.ai-gen-preview-block {
  margin-top: 8px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
.ai-gen-module-row--top {
  margin-bottom: 12px;
}
.ai-gen-module-row {
  margin-bottom: 12px;
}
.ai-gen-module-row :deep(.el-form-item__content) {
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}
.ai-gen-module-hint {
  font-size: 12px;
  line-height: 1.45;
  color: rgba(226, 232, 240, 0.5);
  max-width: 520px;
}
.ai-gen-module-hint code {
  font-size: 11px;
  padding: 0 4px;
  border-radius: 4px;
  background: rgba(0, 216, 255, 0.12);
  color: rgba(0, 216, 255, 0.95);
}
.ai-gen-module-row :deep(.el-form-item__label) {
  color: rgba(226, 232, 240, 0.78);
}
</style>
