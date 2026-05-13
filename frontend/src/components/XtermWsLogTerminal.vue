<template>
  <div
    ref="wrapRef"
    class="xterm-ws-log"
    :style="wrapStyle"
  >
    <div
      ref="hostRef"
      class="xterm-ws-log__host"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";

import { EMERGENCY_DISABLE_REALTIME_CONNECTIONS } from "@/config/emergencyDisableRealtime";

const props = withDefaults(
  defineProps<{
    /** 日志流任务 ID，对应路径 `/ws/logs/:taskId/` */
    taskId: string | number;
    /**
     * WebSocket 主机 IP 或域名（不含端口）。
     * 默认读取 `import.meta.env.VITE_CICD_LOG_WS_IP`，未配置时为 `127.0.0.1`。
     */
    wsIp?: string;
    /** 容器高度，例如 `320px`、`min(50vh,420px)` */
    height?: string;
  }>(),
  {
    wsIp: "",
    height: "320px",
  },
);

const emit = defineEmits<{
  (e: "open"): void;
  (e: "close", ev: CloseEvent): void;
  (e: "error", ev: Event): void;
}>();

const wrapRef = ref<HTMLElement | null>(null);
const hostRef = ref<HTMLElement | null>(null);

const wrapStyle = computed(() => ({
  height: props.height,
}));

let term: Terminal | null = null;
let fitAddon: FitAddon | null = null;
let resizeObserver: ResizeObserver | null = null;
let ws: WebSocket | null = null;

function resolveWsIp(): string {
  const fromProp = props.wsIp?.trim();
  if (fromProp) return fromProp;
  const fromEnv = import.meta.env.VITE_CICD_LOG_WS_IP;
  if (fromEnv != null && String(fromEnv).trim() !== "") {
    return String(fromEnv).trim();
  }
  return "127.0.0.1";
}

/** ws://${IP}:8001/ws/logs/${taskId}/ */
function buildWsUrl(): string {
  const ip = resolveWsIp();
  const id = encodeURIComponent(String(props.taskId ?? ""));
  const token = typeof localStorage !== "undefined" ? localStorage.getItem("token") : null;
  const q = token ? `?token=${encodeURIComponent(token)}` : "";
  return `ws://${ip}:8001/ws/logs/${id}/${q}`;
}

function scrollBottom() {
  if (!term) return;
  term.scrollToBottom();
}

/** 将服务端推送的字符串按行 writeln，并保持视口在底部 */
function writeIncoming(text: string) {
  if (!term) return;
  const normalized = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const lines = normalized.split("\n");
  for (const line of lines) {
    term.writeln(line);
  }
  scrollBottom();
}

function tryFit() {
  if (!fitAddon || !term) return;
  const el = wrapRef.value;
  if (!el || el.clientWidth < 2 || el.clientHeight < 2) return;
  try {
    fitAddon.fit();
  } catch {
    /* 布局未就绪 */
  }
}

function scheduleFit() {
  requestAnimationFrame(() => {
    requestAnimationFrame(() => tryFit());
  });
}

function disconnect() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    try {
      ws.close(1000, "xterm-ws-log unmount");
    } catch {
      /* ignore */
    }
  }
  ws = null;
}

function connect() {
  disconnect();

  if (EMERGENCY_DISABLE_REALTIME_CONNECTIONS) {
    writeIncoming("[system] 实时连接已禁用（EMERGENCY_DISABLE_REALTIME_CONNECTIONS）。");
    return;
  }

  const id = String(props.taskId ?? "").trim();
  if (!id) {
    writeIncoming("[system] taskId 为空，跳过 WebSocket。");
    return;
  }

  const url = buildWsUrl();
  try {
    ws = new WebSocket(url);
  } catch {
    writeIncoming("[system] 无法创建 WebSocket。");
    return;
  }

  ws.addEventListener("open", () => {
    emit("open");
    scheduleFit();
  });

  ws.addEventListener("message", (ev) => {
    const handle = (raw: string) => {
      if (!raw) return;
      writeIncoming(raw);
    };
    if (typeof ev.data === "string") {
      handle(ev.data);
      return;
    }
    if (ev.data instanceof Blob) {
      void ev.data.text().then(handle);
    }
  });

  ws.addEventListener("error", (ev) => {
    emit("error", ev);
    writeIncoming("[system] WebSocket 错误");
  });

  ws.addEventListener("close", (ev) => {
    emit("close", ev);
    if (ev.code !== 1000 && ev.code !== 1001) {
      writeIncoming(`[system] WebSocket 已关闭 code=${ev.code}`);
    }
  });
}

onMounted(() => {
  const host = hostRef.value;
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
    theme: {
      foreground: "#e2e8f0",
      background: "#000000",
      cursor: "#00f2ff",
      cursorAccent: "#000000",
      selectionBackground: "rgba(0, 242, 255, 0.25)",
    },
  });

  fitAddon = new FitAddon();
  term.loadAddon(fitAddon);
  term.open(host);

  resizeObserver = new ResizeObserver(() => scheduleFit());
  if (wrapRef.value) {
    resizeObserver.observe(wrapRef.value);
  }
  window.addEventListener("resize", scheduleFit);

  nextTick(() => {
    scheduleFit();
    connect();
  });
});

onBeforeUnmount(() => {
  disconnect();
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
    term?.clear();
    nextTick(() => {
      scheduleFit();
      connect();
    });
  },
);

defineExpose({
  reconnect: () => connect(),
  fit: () => scheduleFit(),
  clear: () => term?.clear(),
});
</script>

<style scoped>
.xterm-ws-log {
  box-sizing: border-box;
  width: 100%;
  min-height: 0;
  background: #000000;
  border-radius: 6px;
  box-shadow: 0 0 10px #00f2ff;
  overflow: hidden;
}

.xterm-ws-log__host {
  width: 100%;
  height: 100%;
  min-height: 0;
  box-sizing: border-box;
}

.xterm-ws-log :deep(.xterm),
.xterm-ws-log :deep(.xterm-viewport),
.xterm-ws-log :deep(.xterm-screen) {
  background-color: #000000 !important;
}
</style>
