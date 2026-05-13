<template>
  <div
    v-if="showChrome"
    class="global-copilot"
  >
    <button
      type="button"
      class="copilot-fab"
      :class="{ 'copilot-fab--open': copilot.drawerOpen }"
      aria-label="打开 AI Copilot"
      @click="copilot.toggleDrawer()"
    >
      <el-icon :size="18">
        <Cpu />
      </el-icon>
    </button>

    <el-drawer
      v-model="drawerVisible"
      direction="rtl"
      size="min(440px, 92vw)"
      :z-index="5100"
      append-to-body
      class="copilot-drawer-root"
      :show-close="true"
      :close-on-click-modal="false"
    >
      <template #header>
        <div class="copilot-header">
          <span class="copilot-title">CYBER COPILOT</span>
          <span class="copilot-sub">数字同事 · 上下文感知</span>
        </div>
      </template>

      <div class="copilot-body">
        <div class="context-strip">
          <div class="context-line">
            <span class="ctx-k">页面</span>
            <span class="ctx-v">{{ route.path }}</span>
          </div>
          <div class="context-line">
            <span class="ctx-k">场景</span>
            <span class="ctx-v">{{ sceneHint }}</span>
          </div>
          <div
            v-if="copilot.workflowContext.executionLogId"
            class="context-line"
          >
            <span class="ctx-k">失败日志</span>
            <span class="ctx-v">#{{ copilot.workflowContext.executionLogId }}
              {{ copilot.workflowContext.executionLogLabel }}</span>
          </div>
          <div
            v-if="copilot.workflowContext.reportHint"
            class="context-line"
          >
            <span class="ctx-k">报告</span>
            <span class="ctx-v">{{ copilot.workflowContext.reportHint }}</span>
          </div>
          <div class="context-line">
            <span class="ctx-k">编辑器</span>
            <span class="ctx-v">{{ editorHint }}</span>
          </div>
        </div>

        <div class="quick-actions">
          <el-button
            size="small"
            class="cyber-btn"
            :disabled="!activeEditor"
            @click="injectEditorSnapshot"
          >
            读取当前代码
          </el-button>
          <el-button
            size="small"
            type="primary"
            class="cyber-btn-primary"
            :disabled="!copilot.workflowContext.executionLogId || analyzingLog"
            :loading="analyzingLog"
            @click="runFailureAnalysis"
          >
            分析失败原因
          </el-button>
        </div>

        <div
          ref="scrollRef"
          class="msg-scroll"
        >
          <div
            v-for="(m, idx) in messages"
            :key="idx"
            class="msg"
            :class="`msg--${m.role}`"
          >
            <div class="msg-role">
              {{ m.role === 'user' ? '你' : 'AI' }}
            </div>
            <div
              v-if="m.role === 'assistant'"
              class="msg-bubble md"
              v-html="renderMd(m.content)"
            />
            <pre
              v-else
              class="msg-bubble msg-bubble--raw"
            >{{ m.content }}</pre>

            <div
              v-if="m.role === 'assistant' && m.codeBlocks?.length && activeEditor && !activeEditor.isReadOnly()"
              class="apply-row"
            >
              <span class="apply-label">一键应用（取最后一段代码块）</span>
              <el-button
                size="small"
                type="warning"
                plain
                class="cyber-btn"
                @click="applyCode(m, 'replace')"
              >
                覆盖编辑器
              </el-button>
              <el-button
                size="small"
                type="success"
                plain
                class="cyber-btn"
                @click="applyCode(m, 'insert')"
              >
                插入到光标
              </el-button>
            </div>
          </div>
        </div>

        <div class="composer">
          <el-input
            v-model="input"
            type="textarea"
            :rows="3"
            resize="none"
            placeholder="描述问题、请求修复或追问…（已自动附带页面/编辑器上下文）"
            class="copilot-input"
            @keydown.enter.exact.prevent="sendChat"
          />
          <div class="composer-actions">
            <el-button
              :loading="sending"
              type="primary"
              class="send-btn"
              @click="sendChat"
            >
              发送
            </el-button>
            <el-button
              class="cyber-btn"
              @click="clearThread"
            >
              清空对话
            </el-button>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Cpu } from '@element-plus/icons-vue'
import MarkdownIt from 'markdown-it'
import { storeToRefs } from 'pinia'
import { useCopilotStore } from '@/stores/copilotStore'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { useAppContextStore } from '@/stores/appContextStore'
import { askKnowledgeApi } from '@/api/aiKnowledge'
import { suggestCaseFixFromExecutionLogApi } from '@/api/assistant'

const route = useRoute()
const copilot = useCopilotStore()
const { drawerOpen } = storeToRefs(copilot)

const showChrome = computed(() => route.meta?.public !== true)

const drawerVisible = computed({
  get: () => drawerOpen.value,
  set: (v) => {
    if (v) copilot.openDrawer()
    else copilot.closeDrawer()
  },
})

const activeEditor = computed(() => copilot.activeBridge)
const workspaceStore = useWorkspaceStore()
const appContext = useAppContextStore()

const projectIdForApi = computed(() => {
  const w = workspaceStore.selectedProjectId
  if (w != null && w !== '') return Number(w)
  const a = appContext.state?.activeProject?.id
  if (a != null && a !== '') return Number(a)
  return null
})

const sceneHint = computed(() => {
  const p = route.path || ''
  if (/automation-center|script-hub|workbench|workstation|web-ui|api-work|perf/i.test(p))
    return '脚本 / Monaco 工作台'
  if (p.includes('/test-report')) return '测试报告'
  if (p.includes('/test-case')) return '用例与执行日志'
  if (p.includes('/knowledge')) return '知识库'
  return '通用'
})

const editorHint = computed(() => {
  const b = activeEditor.value
  if (!b) return '无活动 Monaco（点击编辑器聚焦）'
  const ro = b.isReadOnly() ? '只读' : '可编辑'
  return `${b.getLabel()} · ${b.getLanguage()} · ${ro}`
})

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })
function renderMd(raw) {
  const s = String(raw || '').trim()
  if (!s) return '<p class="md-empty">—</p>'
  return md.render(s)
}

const messages = ref([])
const input = ref('')
const sending = ref(false)
const analyzingLog = ref(false)
const scrollRef = ref(null)

function buildContextPrefix() {
  const parts = []
  parts.push(`【路由】${route.fullPath}`)
  parts.push(`【场景】${sceneHint.value}`)
  if (copilot.workflowContext.executionLogId) {
    parts.push(
      `【失败执行日志】execution_log_id=${copilot.workflowContext.executionLogId} ${copilot.workflowContext.executionLogLabel || ''}`.trim(),
    )
  }
  if (copilot.workflowContext.reportHint) {
    parts.push(`【测试报告上下文】${copilot.workflowContext.reportHint}`)
  }
  const b = activeEditor.value
  if (b) {
    parts.push(
      `【Monaco】${b.getLabel()} 语言=${b.getLanguage()} 只读=${b.isReadOnly() ? '是' : '否'}`,
    )
  } else {
    parts.push('【Monaco】当前无焦点编辑器')
  }
  parts.push(
    '请根据用户问题作答。若涉及代码修改，请在末尾给出单一 ``` 代码块（语言标签与编辑器一致），便于用户一键应用。',
  )
  return parts.join('\n')
}

function extractFencedCodeBlocks(text) {
  const re = /```(\w*)\n([\s\S]*?)```/g
  const out = []
  let m
  const s = String(text || '')
  while ((m = re.exec(s))) {
    out.push({ lang: (m[1] || 'text').trim(), code: m[2].replace(/\n$/, '') })
  }
  return out
}

async function scrollToBottom() {
  await nextTick()
  const el = scrollRef.value
  if (el) el.scrollTop = el.scrollHeight
}

function injectEditorSnapshot() {
  const b = activeEditor.value
  if (!b) {
    ElMessage.warning('请先在页面中点击 Monaco 编辑器使其获得焦点')
    return
  }
  const code = b.getValue() ?? ''
  const lim = 12000
  const snippet = code.length > lim ? `${code.slice(0, lim)}\n\n…(已截断)` : code
  const prefix = `以下为当前 ${b.getLanguage()} 编辑器「${b.getLabel()}」中的代码：\n\`\`\`${b.getLanguage()}\n${snippet}\n\`\`\`\n\n`
  input.value = prefix + (input.value || '')
  ElMessage.success('已插入代码快照到输入框，可继续描述问题并发送')
}

async function sendChat() {
  const q = String(input.value || '').trim()
  if (!q) {
    ElMessage.warning('请输入内容')
    return
  }
  sending.value = true
  messages.value.push({ role: 'user', content: q })
  input.value = ''
  await scrollToBottom()
  try {
    const question = `${buildContextPrefix()}\n\n【用户问题】\n${q}`
    const payload = {
      question,
      top_k: 5,
    }
    const pid = projectIdForApi.value
    if (pid != null && !Number.isNaN(pid)) payload.project_id = pid

    const { data } = await askKnowledgeApi(payload)
    if (!data?.success) {
      messages.value.push({
        role: 'assistant',
        content: String(data?.message || '请求失败'),
        codeBlocks: [],
      })
      ElMessage.error(data?.message || '提问失败')
      return
    }
    const answer = String(data.answer_markdown || '')
    messages.value.push({
      role: 'assistant',
      content: answer,
      codeBlocks: extractFencedCodeBlocks(answer),
    })
  } catch (e) {
    const msg = e?.response?.data?.message || e?.response?.data?.detail || e?.message || '请求失败'
    messages.value.push({ role: 'assistant', content: String(msg), codeBlocks: [] })
    ElMessage.error(typeof msg === 'string' ? msg : '请求失败')
  } finally {
    sending.value = false
    await scrollToBottom()
  }
}

async function runFailureAnalysis() {
  const eid = copilot.workflowContext.executionLogId
  if (!eid) {
    ElMessage.warning('请先在用例页的执行日志表格中点击一条「未通过」记录以绑定上下文')
    return
  }
  analyzingLog.value = true
  messages.value.push({
    role: 'user',
    content: `请基于 execution_log_id=${eid} 分析失败原因并给出可执行的修订思路（已请求后端专用接口）。`,
  })
  await scrollToBottom()
  try {
    const { data } = await suggestCaseFixFromExecutionLogApi({ execution_log_id: eid })
    const d = data?.data !== undefined ? data.data : data
    if (!d || d.success !== true) {
      const msg = d?.message || data?.message || '分析失败'
      messages.value.push({ role: 'assistant', content: String(msg), codeBlocks: [] })
      ElMessage.error(typeof msg === 'string' ? msg : '分析失败')
      return
    }
    const summary = String(d.summary || '')
    const steps = Array.isArray(d.suggested_steps) ? d.suggested_steps : []
    const risks = String(d.risks || '')
    let mdText = `### 失败摘要\n${summary}\n\n### 建议步骤\n`
    if (steps.length) {
      steps.forEach((s, i) => {
        mdText += `${i + 1}. **${String(s.step_desc || '').trim()}**  — 预期：${String(s.expected_result || '').trim()}\n`
      })
    } else {
      mdText += '_（无结构化步骤）_\n'
    }
    mdText += `\n### 风险\n${risks || '—'}\n`
    messages.value.push({
      role: 'assistant',
      content: mdText,
      codeBlocks: extractFencedCodeBlocks(mdText),
    })
  } catch (e) {
    const msg = e?.response?.data?.message || e?.response?.data?.detail || e?.message || '请求失败'
    messages.value.push({ role: 'assistant', content: String(msg), codeBlocks: [] })
    ElMessage.error(typeof msg === 'string' ? msg : '请求失败')
  } finally {
    analyzingLog.value = false
    await scrollToBottom()
  }
}

function applyCode(msg, mode) {
  const b = activeEditor.value
  if (!b || b.isReadOnly()) {
    ElMessage.warning('当前编辑器只读或未就绪')
    return
  }
  const blocks = msg.codeBlocks?.length ? msg.codeBlocks : extractFencedCodeBlocks(msg.content)
  if (!blocks.length) {
    ElMessage.warning('该条回复中没有可识别的 ``` 代码块')
    return
  }
  const last = blocks[blocks.length - 1]
  const code = last.code ?? ''
  if (!code.trim()) {
    ElMessage.warning('代码块为空')
    return
  }
  try {
    if (mode === 'replace') {
      b.setValue(code)
      ElMessage.success('已覆盖编辑器内容')
    } else {
      b.insertAtCursor(code)
      ElMessage.success('已插入到光标处')
    }
    b.focus?.()
  } catch {
    ElMessage.error('写入编辑器失败')
  }
}

function clearThread() {
  messages.value = []
}

watch(drawerOpen, (open) => {
  if (open) nextTick(() => scrollToBottom())
})
</script>

<style scoped>
.global-copilot {
  pointer-events: none;
}

.copilot-fab {
  pointer-events: auto;
  position: fixed;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  z-index: 5050;
  width: 22px;
  height: 56px;
  padding: 0;
  margin: 0;
  border: none;
  border-radius: 10px 0 0 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(
    165deg,
    rgba(12, 18, 32, 0.92),
    rgba(22, 32, 56, 0.88)
  );
  color: var(--cyber-cyan, #00d8ff);
  box-shadow:
    0 0 14px rgba(0, 216, 255, 0.45),
    inset 0 0 12px rgba(0, 216, 255, 0.12);
  border: 1px solid rgba(0, 216, 255, 0.35);
  transition:
    box-shadow 0.2s ease,
    width 0.2s ease;
}

.copilot-fab:hover {
  width: 28px;
  box-shadow:
    0 0 22px rgba(0, 216, 255, 0.65),
    inset 0 0 16px rgba(0, 216, 255, 0.18);
}

.copilot-fab--open {
  color: var(--cyber-magenta, #ff00aa);
  border-color: rgba(255, 0, 170, 0.45);
  box-shadow:
    0 0 18px rgba(255, 0, 170, 0.4),
    inset 0 0 12px rgba(255, 0, 170, 0.12);
}

.copilot-header {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.copilot-title {
  font-family: var(--cyber-font-display, 'Orbitron', sans-serif);
  font-size: 14px;
  letter-spacing: 0.12em;
  color: var(--cyber-cyan, #00d8ff);
}

.copilot-sub {
  font-size: 11px;
  color: rgba(148, 163, 184, 0.85);
}

.copilot-body {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  gap: 10px;
  margin-top: -8px;
}

.context-strip {
  font-size: 11px;
  line-height: 1.45;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(0, 216, 255, 0.06);
  border: 1px solid rgba(0, 216, 255, 0.2);
}

.context-line {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.ctx-k {
  color: rgba(148, 163, 184, 0.9);
  min-width: 48px;
}

.ctx-v {
  color: rgba(226, 232, 240, 0.95);
  word-break: break-all;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.cyber-btn {
  border-color: rgba(0, 216, 255, 0.35) !important;
  background: rgba(12, 18, 32, 0.6) !important;
  color: rgba(226, 232, 240, 0.95) !important;
}

.cyber-btn-primary {
  border-color: rgba(0, 216, 255, 0.5) !important;
  background: linear-gradient(135deg, rgba(0, 216, 255, 0.2), rgba(124, 58, 237, 0.15)) !important;
}

.msg-scroll {
  flex: 1;
  min-height: 180px;
  overflow: auto;
  padding: 4px 2px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.msg {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.msg-role {
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(148, 163, 184, 0.75);
}

.msg--user .msg-role {
  color: rgba(0, 216, 255, 0.7);
}

.msg-bubble {
  margin: 0;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

.msg--user .msg-bubble--raw {
  background: rgba(0, 216, 255, 0.08);
  border: 1px solid rgba(0, 216, 255, 0.22);
  color: rgba(241, 245, 249, 0.95);
}

.msg--assistant .md {
  background: rgba(15, 23, 42, 0.75);
  border: 1px solid rgba(124, 58, 237, 0.25);
  color: rgba(226, 232, 240, 0.95);
}

.msg--assistant .md :deep(p) {
  margin: 0.4em 0;
}

.msg--assistant .md :deep(pre) {
  margin: 0.5em 0;
  padding: 10px;
  border-radius: 8px;
  overflow: auto;
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(0, 216, 255, 0.15);
}

.msg--assistant .md :deep(code) {
  font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
  font-size: 12px;
}

.apply-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: rgba(148, 163, 184, 0.9);
}

.composer {
  border-top: 1px solid rgba(0, 216, 255, 0.15);
  padding-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.copilot-input :deep(.el-textarea__inner) {
  font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
  font-size: 12px;
  background: rgba(15, 23, 42, 0.85) !important;
  color: rgba(241, 245, 249, 0.95) !important;
  border-color: rgba(0, 216, 255, 0.25) !important;
}

.composer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.send-btn {
  min-width: 88px;
}
</style>

<style>
/* Element Plus drawer 外壳：赛博暗色 */
.copilot-drawer-root.el-drawer {
  --el-drawer-bg-color: rgba(10, 14, 24, 0.97);
}

.copilot-drawer-root .el-drawer__header {
  margin-bottom: 8px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 216, 255, 0.15);
}

.copilot-drawer-root .el-drawer__body {
  padding: 12px 16px 20px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  box-sizing: border-box;
}
</style>
