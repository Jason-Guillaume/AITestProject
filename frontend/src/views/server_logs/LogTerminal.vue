<template>
  <div class="log-terminal" :class="{ 'log-terminal--connected': connected }">
    <div class="log-terminal__toolbar">
      <div class="log-terminal__left">
        <span class="log-terminal__path" title="当前日志路径">{{ displayPath }}</span>
        <span class="log-terminal__mode" :class="`is-${mode}`">
          {{ mode === 'live' ? '实时' : '历史' }}
        </span>
      </div>
      <div class="log-terminal__actions">
        <el-button
          size="small"
          class="log-terminal__btn"
          :type="mode === 'live' ? 'primary' : 'default'"
          @click="switchMode('live')"
        >
          实时
        </el-button>
        <el-button
          size="small"
          class="log-terminal__btn"
          :type="mode === 'history' ? 'primary' : 'default'"
          @click="switchMode('history')"
        >
          历史
        </el-button>
        <el-input
          v-if="mode === 'history'"
          v-model="historyKeyword"
          size="small"
          class="log-terminal__kw"
          placeholder="关键字（可空=最近日志）"
          clearable
          @keyup.enter="loadHistory(true)"
        />
        <el-button
          v-if="mode === 'history'"
          size="small"
          class="log-terminal__btn"
          :loading="historyLoading"
          @click="loadHistory(true)"
        >
          搜索
        </el-button>
        <el-button size="small" class="log-terminal__btn" @click="copyPath">复制路径</el-button>
        <el-button size="small" class="log-terminal__btn" @click="clearScreen">清屏</el-button>
        <el-switch
          v-model="autoScroll"
          size="small"
          active-text="自动滚动"
          class="log-terminal__switch"
        />
      </div>
    </div>

    <div
      ref="viewportRef"
      class="log-terminal__viewport"
      @scroll.passive="onScroll"
      @mouseup="onTextSelect"
    >
      <div class="log-terminal__spacer" :style="{ height: topSpacer + 'px' }" />
      <div
        v-for="(line, idx) in visibleSlice"
        :key="startIndex + idx"
        class="log-terminal__line"
        :style="{ height: lineHeight + 'px' }"
      >
        <span v-html="formatLine(line)" />
      </div>
      <div class="log-terminal__spacer" :style="{ height: bottomSpacer + 'px' }" />
    </div>

    <div v-if="statusMsg" class="log-terminal__status">{{ statusMsg }}</div>

    <teleport to="body">
      <transition-group name="fade" tag="div">
        <button
          v-if="fabVisible && selectionText"
          key="ai-diagnose"
          type="button"
          class="log-terminal__fab"
          :style="{ top: fabTop + 'px', left: fabLeft + 'px' }"
          @mousedown.prevent
          @click="openAiDrawer"
        >
          <span class="log-terminal__fab-glow" />
          AI 诊断
        </button>
        <button
          v-if="fabVisible && selectionText"
          key="ticket-draft"
          type="button"
          class="log-terminal__fab log-terminal__fab--secondary"
          :style="{ top: fabTop + 46 + 'px', left: fabLeft + 'px' }"
          @mousedown.prevent
          @click="openTicketDrawer"
        >
          工单草稿
        </button>
      </transition-group>
    </teleport>

    <el-drawer
      v-model="drawerVisible"
      title="日志智能诊断与工单"
      direction="rtl"
      size="min(560px, 92vw)"
      class="log-terminal-drawer"
      append-to-body
    >
      <el-tabs v-model="drawerTab" class="log-terminal__tabs">
        <el-tab-pane label="AI 诊断" name="analyze">
          <div v-if="aiLoading" class="log-terminal__ai-loading">分析中，请稍候…</div>
          <div v-else class="log-terminal__md" v-html="renderedMarkdown" />
        </el-tab-pane>
        <el-tab-pane label="AI 工单草稿" name="ticket">
          <LogAutoTicketDraft :server-id="serverId" :anchor-text="lastAnchor" />
        </el-tab-pane>
      </el-tabs>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, onActivated, nextTick, shallowRef } from "vue";
import { ElMessage } from "element-plus";
import MarkdownIt from "markdown-it";
import LogAutoTicketDraft from "@/components/server_logs/LogAutoTicketDraft.vue";
import { analyzeServerLog, analyzeServerLogWithContext, searchServerLogs } from "@/api/serverLogs";

const props = defineProps({
  serverId: { type: [Number, String], default: null },
  logPath: { type: String, default: "/var/log/messages" },
  streaming: { type: Boolean, default: false },
});

const lineHeight = 17;
const overscan = 8;
const maxLines = 12000;

const viewportRef = ref(null);
const lines = shallowRef([]);
const scrollTop = ref(0);
const viewportH = ref(480);
const autoScroll = ref(true);
const connected = ref(false);
const statusMsg = ref("");

const startIndex = computed(() => {
  const st = scrollTop.value;
  const raw = Math.floor(st / lineHeight) - overscan;
  return Math.max(0, raw);
});

const visibleCount = computed(() => {
  const n = Math.ceil(viewportH.value / lineHeight) + overscan * 2;
  return Math.max(24, n);
});

const endIndex = computed(() =>
  Math.min(lines.value.length, startIndex.value + visibleCount.value)
);

const visibleSlice = computed(() =>
  lines.value.slice(startIndex.value, endIndex.value)
);

const topSpacer = computed(() => startIndex.value * lineHeight);
const bottomSpacer = computed(() =>
  Math.max(0, (lines.value.length - endIndex.value) * lineHeight)
);

const displayPath = computed(() => props.logPath || "/var/log/messages");

let ws = null;
const md = new MarkdownIt({ html: false, linkify: true, breaks: true });
const drawerVisible = ref(false);
const drawerTab = ref("analyze");
const lastAnchor = ref("");
const aiLoading = ref(false);
const renderedMarkdown = ref("");
const selectionText = ref("");
const fabVisible = ref(false);
const fabTop = ref(0);
const fabLeft = ref(0);

const mode = ref("live"); // live | history
const historyKeyword = ref("");
const historyLoading = ref(false);

function measureViewport() {
  const el = viewportRef.value;
  if (el) viewportH.value = el.clientHeight || 480;
}

function onScroll() {
  const el = viewportRef.value;
  if (!el) return;
  scrollTop.value = el.scrollTop;
  const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < lineHeight * 4;
  if (!nearBottom) autoScroll.value = false;
}

function pushLine(text) {
  const next = lines.value.concat([text]);
  if (next.length > maxLines) next.splice(0, next.length - maxLines);
  lines.value = next;
  if (autoScroll.value) queueScrollBottom();
}

function queueScrollBottom() {
  requestAnimationFrame(() => {
    const el = viewportRef.value;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
    scrollTop.value = el.scrollTop;
  });
}

function clearScreen() {
  lines.value = [];
  statusMsg.value = "";
}

function switchMode(next) {
  if (next !== "live" && next !== "history") return;
  mode.value = next;
}

async function loadHistory(reset = false) {
  if (!props.serverId) return;
  historyLoading.value = true;
  try {
    if (reset) {
      lines.value = [];
      statusMsg.value = "正在检索历史日志…";
    }
    const keyword = String(historyKeyword.value || "").trim();
    const { data } = await searchServerLogs({ server_id: props.serverId, keyword, limit: 200 });
    if (!data?.enabled) {
      statusMsg.value = data?.message || "历史检索未启用";
      return;
    }
    const rows = Array.isArray(data?.results) ? data.results : [];
    // ES 返回时间倒序，这里按时间正序展示更像“回放”
    const ordered = rows.slice().sort((a, b) => Number(a?.timestamp || 0) - Number(b?.timestamp || 0));
    const merged = ordered.map((r) => `[${r.timestamp}] ${r.message || ""}`);
    lines.value = merged;
    statusMsg.value = merged.length ? `历史日志：${merged.length} 行` : "没有命中";
    autoScroll.value = true;
    queueScrollBottom();
  } catch (e) {
    statusMsg.value = `历史检索失败：${e?.response?.data?.message || e?.message || "unknown"}`;
  } finally {
    historyLoading.value = false;
  }
}

function copyPath() {
  const p = displayPath.value;
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(p).then(
      () => ElMessage.success("已复制路径"),
      () => ElMessage.error("复制失败")
    );
  } else {
    ElMessage.warning("浏览器不支持剪贴板 API");
  }
}

function onTextSelect() {
  const sel = window.getSelection();
  const text = (sel?.toString() || "").trim();
  if (!text || text.length > 80000) {
    fabVisible.value = false;
    selectionText.value = "";
    return;
  }
  selectionText.value = text;
  try {
    if (sel.rangeCount > 0) {
      const rect = sel.getRangeAt(0).getBoundingClientRect();
  fabTop.value = rect.bottom + 6;
  fabLeft.value = rect.left;
    }
  } catch {
    fabVisible.value = false;
    return;
  }
  fabVisible.value = true;
}

function openTicketDrawer() {
  const chunk = selectionText.value;
  fabVisible.value = false;
  lastAnchor.value = chunk;
  drawerTab.value = "ticket";
  drawerVisible.value = true;
}

async function openAiDrawer() {
  const chunk = selectionText.value;
  fabVisible.value = false;
  lastAnchor.value = chunk;
  drawerTab.value = "analyze";
  drawerVisible.value = true;
  aiLoading.value = true;
  renderedMarkdown.value = "";
  try {
    // 优先走 ES 上下文增强诊断；失败则降级为原始单段诊断
    let data = null;
    try {
      const res = await analyzeServerLogWithContext({
        server_id: props.serverId,
        anchor_text: chunk,
        window_seconds: 300,
        limit: 200,
      });
      data = res?.data;
    } catch {
      data = null;
    }
    if (!data) {
      const res2 = await analyzeServerLog({ log_text: chunk });
      data = res2?.data;
    }
    if (!data?.success) {
      renderedMarkdown.value = `<p class="err">${escapeHtml(data?.error || "分析失败")}</p>`;
      return;
    }
    renderedMarkdown.value = md.render(data.markdown || "");
  } catch (e) {
    renderedMarkdown.value = `<p class="err">${escapeHtml(e?.message || "请求失败")}</p>`;
  } finally {
    aiLoading.value = false;
  }
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatLine(raw) {
  // 先转义，再做高亮（避免 XSS）
  const safe = escapeHtml(raw ?? "");
  // ERROR/WARN/Exception 霓虹高亮
  return safe
    .replace(/\b(ERROR|Error|error)\b/g, '<span class="hl hl--error">$1</span>')
    .replace(/\b(WARN|Warning|warning)\b/g, '<span class="hl hl--warn">$1</span>')
    .replace(/\b(Exception|Traceback)\b/g, '<span class="hl hl--exc">$1</span>');
}

function wsUrl() {
  const token = localStorage.getItem("token") || "";
  const path = encodeURIComponent(props.logPath || "/var/log/messages");
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  return `${proto}//${host}/ws/server-logs/${props.serverId}/?token=${encodeURIComponent(token)}&path=${path}`;
}

function connectWs() {
  disconnectWs();
  if (!props.serverId || !props.streaming) return;
  if (mode.value !== "live") return;
  lines.value = [];
  measureViewport();
  statusMsg.value = "正在连接…";
  try {
    ws = new WebSocket(wsUrl());
  } catch (e) {
    statusMsg.value = `连接失败：${e?.message || e}`;
    return;
  }
  ws.onopen = () => {
    connected.value = true;
    statusMsg.value = "已连接";
  };
  ws.onclose = () => {
    connected.value = false;
    if (statusMsg.value === "已连接") statusMsg.value = "连接已关闭";
  };
  ws.onerror = () => {
    statusMsg.value = "WebSocket 错误";
  };
  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      if (msg.type === "log" && msg.line != null) pushLine(String(msg.line));
      else if (msg.type === "status") statusMsg.value = msg.message || msg.phase || "";
      else if (msg.type === "error") {
        statusMsg.value = msg.message || "错误";
        ElMessage.error(statusMsg.value);
      }
    } catch {
      /* ignore */
    }
  };
}

function disconnectWs() {
  if (ws) {
    try {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "stop" }));
      }
    } catch {
      /* ignore */
    }
    try {
      ws.close();
    } catch {
      /* ignore */
    }
    ws = null;
  }
  connected.value = false;
}

function sendPing() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "ping", ts: Date.now() }));
  }
}

let pingTimer = null;
watch(
  () => [props.serverId, props.logPath, props.streaming, mode.value],
  () => {
    if (mode.value === "history") {
      disconnectWs();
      loadHistory(true);
      return;
    }
    if (props.streaming && props.serverId) connectWs();
    else disconnectWs();
  },
  { immediate: true }
);

watch(autoScroll, (v) => {
  if (v) queueScrollBottom();
});

watch(
  () => lines.value.length,
  () => {
    if (autoScroll.value) queueScrollBottom();
  }
);

onMounted(() => {
  measureViewport();
  window.addEventListener("resize", measureViewport);
  pingTimer = setInterval(sendPing, 25000);
});

// keep-alive：页面切换回来时，DOM 尺寸可能变化（尤其在隐藏/恢复后 clientHeight 变为 0），
// 需要重新测量并在连接被关闭时尝试恢复。
onActivated(async () => {
  await nextTick();
  measureViewport();
  // 若处于实时模式且 streaming 开启，但 WS 已被浏览器/代理关闭，则自动重连
  if (mode.value === "live" && props.streaming) {
    if (!ws || ws.readyState === WebSocket.CLOSED || ws.readyState === WebSocket.CLOSING) {
      connectWs();
    }
  }
});

onUnmounted(() => {
  window.removeEventListener("resize", measureViewport);
  disconnectWs();
  if (pingTimer) clearInterval(pingTimer);
});
</script>

<style scoped lang="scss">
.log-terminal {
  --term-bg: #0a192f;
  --term-fg: #00cfec;
  --term-border: rgba(0, 207, 236, 0.35);
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 420px;
  background: var(--term-bg);
  border: 1px solid var(--term-border);
  border-radius: 10px;
  box-shadow:
    0 0 0 1px rgba(0, 207, 236, 0.08),
    0 0 24px rgba(0, 120, 180, 0.25);
  color: var(--term-fg);
  font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
  font-size: 13px;
  position: relative;
}

.log-terminal--connected {
  box-shadow:
    0 0 0 1px rgba(0, 207, 236, 0.15),
    0 0 32px rgba(0, 180, 220, 0.35);
}

.log-terminal__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(0, 207, 236, 0.2);
  background: linear-gradient(90deg, rgba(0, 40, 80, 0.5), transparent);
}

.log-terminal__left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

.log-terminal__path {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  opacity: 0.9;
  letter-spacing: 0.02em;
}

.log-terminal__mode {
  flex-shrink: 0;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid rgba(0, 207, 236, 0.22);
  color: #b6f7ff;
  background: rgba(0, 207, 236, 0.08);
}
.log-terminal__mode.is-history {
  border-color: rgba(167, 139, 250, 0.35);
  color: #e9d5ff;
  background: rgba(167, 139, 250, 0.1);
}

.log-terminal__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.log-terminal__kw {
  width: 220px;
}

.log-terminal__btn {
  --el-button-bg-color: rgba(0, 207, 236, 0.12);
  --el-button-border-color: rgba(0, 207, 236, 0.45);
  --el-button-text-color: #b6f7ff;
}

.log-terminal__switch {
  --el-switch-on-color: #00cfec;
}

.log-terminal__viewport {
  flex: 1;
  overflow: auto;
  padding: 8px 12px 12px;
  scroll-behavior: auto;
  background: radial-gradient(1200px 400px at 50% 0%, rgba(0, 80, 120, 0.2), transparent);
}

.log-terminal__line {
  line-height: 17px;
  white-space: pre-wrap;
  word-break: break-all;
  color: #7eebfd;
  text-shadow: 0 0 6px rgba(0, 207, 236, 0.25);
}

.hl {
  font-weight: 700;
  padding: 0 2px;
  border-radius: 3px;
}
.hl--error {
  color: #ffb4b4;
  text-shadow: 0 0 10px rgba(255, 80, 80, 0.45);
  background: rgba(255, 80, 80, 0.08);
  border: 1px solid rgba(255, 80, 80, 0.18);
}
.hl--warn {
  color: #ffd6a5;
  text-shadow: 0 0 10px rgba(255, 180, 80, 0.35);
  background: rgba(255, 180, 80, 0.08);
  border: 1px solid rgba(255, 180, 80, 0.16);
}
.hl--exc {
  color: #c7b6ff;
  text-shadow: 0 0 10px rgba(167, 139, 250, 0.45);
  background: rgba(167, 139, 250, 0.1);
  border: 1px solid rgba(167, 139, 250, 0.18);
}

.log-terminal__spacer {
  width: 100%;
}

.log-terminal__status {
  padding: 6px 12px 10px;
  font-size: 12px;
  opacity: 0.75;
  border-top: 1px solid rgba(0, 207, 236, 0.12);
}

.log-terminal__fab {
  position: fixed;
  z-index: 3000;
  padding: 8px 16px;
  border-radius: 999px;
  border: 1px solid rgba(0, 207, 236, 0.55);
  background: linear-gradient(135deg, #062a4a, #0b3d5c);
  color: #e6fbff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 0 20px rgba(0, 207, 236, 0.45);
}

.log-terminal__fab-glow {
  pointer-events: none;
  position: absolute;
  inset: -2px;
  border-radius: inherit;
  background: radial-gradient(circle at 30% 30%, rgba(0, 207, 236, 0.35), transparent 55%);
  opacity: 0.9;
  z-index: -1;
}

.log-terminal__fab--secondary {
  padding: 6px 14px;
  font-size: 12px;
  border-color: rgba(167, 139, 250, 0.55);
  box-shadow: 0 0 16px rgba(167, 139, 250, 0.35);
}

.log-terminal__ai-loading {
  color: #b6f7ff;
  padding: 12px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

<style lang="scss">
.log-terminal-drawer .el-drawer__body {
  background: #0a192f;
  color: #d8f7ff;
}

.log-terminal__tabs {
  --el-tabs-header-height: 40px;
}
.log-terminal__tabs :deep(.el-tabs__header) {
  margin-bottom: 12px;
}
.log-terminal__tabs :deep(.el-tabs__item) {
  color: #8ecae6;
}
.log-terminal__tabs :deep(.el-tabs__item.is-active) {
  color: #5cf0ff;
}
.log-terminal__tabs :deep(.el-tabs__active-bar) {
  background-color: #00cfec;
}
.log-terminal__md {
  font-size: 14px;
  line-height: 1.65;
  h1,
  h2,
  h3 {
    color: #5cf0ff;
    margin: 0.6em 0 0.35em;
  }
  code {
    background: rgba(0, 207, 236, 0.12);
    padding: 1px 6px;
    border-radius: 4px;
  }
  pre code {
    display: block;
    padding: 10px;
    overflow: auto;
    border: 1px solid rgba(0, 207, 236, 0.25);
  }
  .err {
    color: #ffb4b4;
  }
}
</style>
