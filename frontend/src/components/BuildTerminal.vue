<template>
  <div class="build-terminal">
    <header class="build-terminal__status-bar">
      <div class="build-terminal__meta">
        <span class="build-terminal__label">项目</span>
        <span class="build-terminal__project">{{ projectName || "—" }}</span>
        <span class="build-terminal__divider" aria-hidden="true" />
        <span class="build-terminal__label">任务 ID</span>
        <code class="build-terminal__task-id">{{ taskIdDisplay }}</code>
        <span class="build-terminal__divider" aria-hidden="true" />
        <span class="build-terminal__label">WS</span>
        <span
          class="build-terminal__ws-dot"
          :class="{ 'is-on': wsConnected, 'is-off': !wsConnected }"
          :title="wsConnected ? 'WebSocket 已连接' : 'WebSocket 未连接'"
        />
      </div>
      <div class="build-terminal__actions">
        <el-tag :type="statusTagType" effect="dark" class="build-terminal__tag">
          {{ statusLabel }}
        </el-tag>
        <el-button
          type="danger"
          plain
          class="build-terminal__stop-btn"
          :disabled="!canStop || stopLoading"
          :loading="stopLoading"
          @click="handleStopBuild"
        >
          停止构建
        </el-button>
      </div>
    </header>

    <div ref="terminalWrapRef" class="build-terminal__xterm-wrap">
      <div ref="terminalHostRef" class="build-terminal__xterm-host" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";

import request from "@/utils/request";
import { EMERGENCY_DISABLE_REALTIME_CONNECTIONS } from "@/config/emergencyDisableRealtime";

export type BuildTerminalStatus = "pending" | "running" | "success" | "failed";

const props = withDefaults(
  defineProps<{
    /** 构建所属项目展示名 */
    projectName: string;
    /**
     * WebSocket 路径参数：与后端约定为 ``/ws/logs/{task_id}/``。
     * 当前 Django 实现为构建记录 ID（build_record_id），传入该数字即可。
     */
    taskId: string | number;
    /** 可由父组件传入并同步（例如轮询流水线状态） */
    buildStatus?: BuildTerminalStatus;
    /**
     * WebSocket 主机（不含协议），如 ``192.168.1.10:8000``。
     * 默认使用 ``window.location.host``（配合 Vite ``/ws`` 代理）。
     */
    wsHost?: string;
    /**
     * 中止构建的 REST 地址（相对 ``/api`` 的 path，如 ``/project/pipelines/1/builds/12/cancel/``）。
     * 未配置时点击按钮仅触发 ``stop`` 事件，由父级自行调 API。
     */
    stopUrl?: string | null;
  }>(),
  {
    buildStatus: "pending",
    wsHost: "",
    stopUrl: null,
  }
);

const emit = defineEmits<{
  (e: "stop"): void;
  (e: "update:buildStatus", v: BuildTerminalStatus): void;
  (e: "ws-open"): void;
  (e: "ws-close", ev: CloseEvent): void;
  (e: "ws-error", ev: Event): void;
}>();

const terminalWrapRef = ref<HTMLElement | null>(null);
const terminalHostRef = ref<HTMLElement | null>(null);

let term: Terminal | null = null;
let fitAddon: FitAddon | null = null;
let resizeObserver: ResizeObserver | null = null;
let ws: WebSocket | null = null;

const wsConnected = ref(false);
const stopLoading = ref(false);
const localStatus = ref<BuildTerminalStatus>(props.buildStatus);

watch(
  () => props.buildStatus,
  (v) => {
    if (v) localStatus.value = v;
  }
);

const taskIdDisplay = computed(() => String(props.taskId ?? "—"));

const displayStatus = computed(() => localStatus.value);

const statusLabel = computed(() => {
  const m: Record<BuildTerminalStatus, string> = {
    pending: "Pending",
    running: "Running",
    success: "Success",
    failed: "Failed",
  };
  return m[displayStatus.value] ?? displayStatus.value;
});

const statusTagType = computed(() => {
  switch (displayStatus.value) {
    case "running":
      return "warning";
    case "success":
      return "success";
    case "failed":
      return "danger";
    default:
      return "info";
  }
});

const canStop = computed(() => displayStatus.value === "running");

/** 赛博朋克终端配色：深底 + 青灰字 + 霓虹点缀 */
const cyberTheme = {
  foreground: "#b8c5cc",
  background: "#1a1a1a",
  cursor: "#00e5ff",
  cursorAccent: "#1a1a1a",
  selectionBackground: "rgba(0, 229, 255, 0.22)",
  black: "#1a1a1a",
  red: "#ff4d6d",
  green: "#5dffbf",
  yellow: "#ffe14a",
  blue: "#3dccff",
  magenta: "#ff2bd6",
  cyan: "#5ce1ff",
  white: "#e8eef2",
  brightBlack: "#6b7780",
  brightRed: "#ff7a8c",
  brightGreen: "#8fffd4",
  brightYellow: "#fff566",
  brightBlue: "#7ddbff",
  brightMagenta: "#ff7ae8",
  brightCyan: "#9af5ff",
  brightWhite: "#f4f8fb",
} as const;

function setStatus(v: BuildTerminalStatus) {
  localStatus.value = v;
  emit("update:buildStatus", v);
}

function buildWsUrl(): string {
  const token = localStorage.getItem("token") || "";
  const host = props.wsHost?.trim() || window.location.host;
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const id = encodeURIComponent(String(props.taskId));
  const q = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${proto}//${host}/ws/logs/${id}/${q}`;
}

function tryFit() {
  if (!fitAddon || !term) return;
  const w = terminalWrapRef.value;
  if (!w || w.clientWidth < 2 || w.clientHeight < 2) return;
  try {
    fitAddon.fit();
  } catch {
    /* 布局未稳定 */
  }
}

function scheduleFit() {
  requestAnimationFrame(() => {
    requestAnimationFrame(() => tryFit());
  });
}

function appendToTerminal(chunk: string, addNewline = true) {
  if (!term) return;
  term.write(chunk);
  if (addNewline && !/\r?\n$/.test(chunk)) {
    term.write("\r\n");
  }
  term.scrollToBottom();
}

function handleWsMessage(raw: string) {
  const text = raw.trim();
  if (!text) return;
  try {
    const msg = JSON.parse(text) as Record<string, unknown>;
    const t = String(msg.type || "");

    if (t === "log") {
      const line =
        (typeof msg.line === "string" && msg.line) ||
        (typeof msg.text === "string" && msg.text) ||
        (typeof msg.message === "string" && msg.message) ||
        "";
      appendToTerminal(line || JSON.stringify(msg));
      return;
    }

    if (t === "status") {
      appendToTerminal(`[status] ${JSON.stringify(msg)}`, true);
      const phase =
        (typeof msg.phase === "string" && msg.phase) ||
        (typeof msg.status === "string" && msg.status);
      if (phase === "subscribed" && localStatus.value === "pending") {
        setStatus("running");
      }
      return;
    }

    appendToTerminal(text, true);
  } catch {
    appendToTerminal(raw, true);
  }
}

function connectWebSocket() {
  disconnectWebSocket();

  if (EMERGENCY_DISABLE_REALTIME_CONNECTIONS) {
    appendToTerminal(
      "[system] 实时连接已禁用（EMERGENCY_DISABLE_REALTIME_CONNECTIONS）。",
      true
    );
    return;
  }

  const url = buildWsUrl();
  try {
    ws = new WebSocket(url);
  } catch (e) {
    ElMessage.error("无法创建 WebSocket");
    setStatus("failed");
    return;
  }

  ws.addEventListener("open", () => {
    wsConnected.value = true;
    emit("ws-open");
    if (localStatus.value === "pending") {
      setStatus("running");
    }
    appendToTerminal(`[system] 已连接 ${url.replace(/\?token=.*/, "?token=***")}`, true);
    scheduleFit();
  });

  ws.addEventListener("message", (ev) => {
    if (typeof ev.data === "string") {
      handleWsMessage(ev.data);
    }
  });

  ws.addEventListener("error", (ev) => {
    emit("ws-error", ev);
    appendToTerminal("[system] WebSocket 错误", true);
  });

  ws.addEventListener("close", (ev) => {
    wsConnected.value = false;
    emit("ws-close", ev);
    if (ev.code !== 1000 && ev.code !== 1001) {
      appendToTerminal(`[system] WebSocket 关闭 code=${ev.code}`, true);
    }
  });
}

function disconnectWebSocket() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    try {
      ws.close(1000, "component unmount");
    } catch {
      /* ignore */
    }
  }
  ws = null;
  wsConnected.value = false;
}

async function handleStopBuild() {
  if (!canStop.value) return;
  stopLoading.value = true;
  try {
    if (props.stopUrl && String(props.stopUrl).trim()) {
      await request.post(String(props.stopUrl).trim());
      ElMessage.success("已请求中止构建");
    } else {
      emit("stop");
      ElMessage.info("已触发停止（由父组件处理）");
    }
  } catch (e) {
    ElMessage.error("停止构建请求失败");
    console.error(e);
  } finally {
    stopLoading.value = false;
  }
}

onMounted(() => {
  const host = terminalHostRef.value;
  if (!host) return;

  term = new Terminal({
    allowTransparency: false,
    convertEol: true,
    disableStdin: true,
    fontFamily: "'JetBrains Mono', 'Fira Code', Consolas, ui-monospace, monospace",
    fontSize: 13,
    lineHeight: 1.25,
    cursorBlink: false,
    scrollback: 8000,
    theme: { ...cyberTheme },
  });

  fitAddon = new FitAddon();
  term.loadAddon(fitAddon);
  term.open(host);

  resizeObserver = new ResizeObserver(() => scheduleFit());
  if (terminalWrapRef.value) {
    resizeObserver.observe(terminalWrapRef.value);
  }
  window.addEventListener("resize", scheduleFit);

  nextTick(() => {
    scheduleFit();
    connectWebSocket();
  });
});

onBeforeUnmount(() => {
  disconnectWebSocket();
  window.removeEventListener("resize", scheduleFit);
  resizeObserver?.disconnect();
  resizeObserver = null;
  term?.dispose();
  term = null;
  fitAddon = null;
});

watch(
  () => props.taskId,
  () => {
    nextTick(() => {
      connectWebSocket();
      scheduleFit();
    });
  }
);

defineExpose({
  /** 外部强制写入一行日志 */
  writeLine: (line: string) => appendToTerminal(line, true),
  reconnect: () => connectWebSocket(),
  fit: () => scheduleFit(),
});
</script>

<style scoped>
.build-terminal {
  display: flex;
  flex-direction: column;
  min-height: 420px;
  height: 100%;
  box-sizing: border-box;
  background: #1a1a1a;
  border: 1px solid rgba(0, 229, 255, 0.55);
  border-radius: 10px;
  box-shadow:
    0 0 0 1px rgba(0, 229, 255, 0.12) inset,
    0 0 24px rgba(0, 229, 255, 0.08);
  overflow: hidden;
}

.build-terminal__status-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  background: linear-gradient(180deg, rgba(26, 26, 26, 0.98) 0%, #141414 100%);
  border-bottom: 1px solid rgba(0, 229, 255, 0.45);
  box-shadow: 0 0 12px rgba(0, 229, 255, 0.12);
}

.build-terminal__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 10px;
  min-width: 0;
  color: #9db3c0;
  font-size: 13px;
}

.build-terminal__label {
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 10px;
  color: #5a6d78;
}

.build-terminal__project {
  color: #c8dce4;
  font-weight: 600;
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.build-terminal__task-id {
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(0, 229, 255, 0.08);
  border: 1px solid rgba(0, 229, 255, 0.35);
  color: #7aefff;
  font-size: 12px;
}

.build-terminal__divider {
  width: 1px;
  height: 14px;
  background: rgba(0, 229, 255, 0.25);
  margin: 0 4px;
}

.build-terminal__ws-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #444;
  box-shadow: 0 0 6px transparent;
}
.build-terminal__ws-dot.is-on {
  background: #00e5ff;
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.85);
}
.build-terminal__ws-dot.is-off {
  background: #555;
}

.build-terminal__actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.build-terminal__tag {
  border: 1px solid rgba(0, 229, 255, 0.35) !important;
  background: rgba(0, 229, 255, 0.06) !important;
  color: #c8eef5 !important;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 600;
}

.build-terminal__stop-btn {
  border-color: rgba(255, 77, 109, 0.65) !important;
  color: #ff8a9a !important;
  background: rgba(255, 77, 109, 0.08) !important;
}
.build-terminal__stop-btn:hover:not(:disabled) {
  border-color: #ff4d6d !important;
  color: #fff !important;
  box-shadow: 0 0 12px rgba(255, 77, 109, 0.35);
}

.build-terminal__xterm-wrap {
  flex: 1;
  min-height: 320px;
  min-width: 0;
  padding: 8px 10px 10px;
  background: #1a1a1a;
}

.build-terminal__xterm-host {
  height: 100%;
  min-height: 300px;
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: 6px;
  overflow: hidden;
  box-sizing: border-box;
  background: #1a1a1a;
}

/* xterm 与外壳统一深灰底，避免默认白边 */
.build-terminal__xterm-wrap :deep(.xterm) {
  height: 100%;
  padding: 6px 8px;
}

.build-terminal__xterm-wrap :deep(.xterm-viewport),
.build-terminal__xterm-wrap :deep(.xterm-screen) {
  background-color: #1a1a1a !important;
}

.build-terminal__xterm-wrap :deep(.xterm .xterm-scrollable) {
  background: #1a1a1a;
}
</style>
