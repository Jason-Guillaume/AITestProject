<template>
  <div class="mini-status-bar" role="status" aria-live="polite">
    <div class="mini-status-bar__inner">
      <span class="mini-status-bar__sep" aria-hidden="true" />
      <span class="mini-status-bar__item" title="当前项目">
        <span class="mini-status-bar__key">PROJ</span>
        <span class="mini-status-bar__val">{{ projectLabel }}</span>
      </span>
      <span class="mini-status-bar__sep" aria-hidden="true" />
      <span class="mini-status-bar__item" title="当前测试环境">
        <span class="mini-status-bar__key">ENV</span>
        <span class="mini-status-bar__val">{{ envLabel }}</span>
      </span>
      <span class="mini-status-bar__sep" aria-hidden="true" />
      <span
        class="mini-status-bar__item mini-status-bar__item--link"
        :title="linkTitle"
      >
        <span
          class="mini-status-bar__dot"
          :class="{
            'mini-status-bar__dot--online': linkVisual === 'online',
            'mini-status-bar__dot--busy': linkVisual === 'busy',
            'mini-status-bar__dot--warn': linkVisual === 'warn',
            'mini-status-bar__dot--off': linkVisual === 'off',
          }"
        />
        <span class="mini-status-bar__key">SSE</span>
        <span class="mini-status-bar__val">{{ linkText }}</span>
      </span>
      <template v-if="hostSupported">
        <span class="mini-status-bar__sep" aria-hidden="true" />
        <span class="mini-status-bar__item" title="后端进程所在主机负载（本地开发）">
          <span class="mini-status-bar__key">LOAD</span>
          <span class="mini-status-bar__val"
            >CPU {{ hostCpu }}% · MEM {{ hostMem }}%</span
          >
          <span v-if="hostCpuCount" class="mini-status-bar__meta">({{ hostCpuCount }}c)</span>
        </span>
      </template>
      <span class="mini-status-bar__fill" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import { useRoute } from "vue-router";
import { storeToRefs } from "pinia";
import { useWorkspaceStore } from "@/stores/workspaceStore";
import { useUiRealtimeStore } from "@/stores/uiRealtimeStore";
import { useBackendSsePresence } from "@/composables/useBackendSsePresence";
import { getDashboardHostMetricsApi } from "@/api/dashboard";
import { EMERGENCY_DISABLE_REALTIME_CONNECTIONS } from "@/config/emergencyDisableRealtime";
import {
  dashboardSseBackoffMs,
  scriptHubSseFuseBackoffMs,
} from "@/utils/dashboardSseHelpers";

const route = useRoute();
const workspaceStore = useWorkspaceStore();
const { projectOptions, envOptions, selectedProjectId, selectedEnvironmentId } =
  storeToRefs(workspaceStore);

const authed = ref(typeof localStorage !== "undefined" && !!localStorage.getItem("token"));
const realtimeStore = useUiRealtimeStore();

function syncAuth() {
  authed.value = !!localStorage.getItem("token");
}

const showBar = computed(() => route.meta?.public !== true && authed.value);

/** 融合工作台首屏不自动连 SSE，避免与 Monaco 等同帧争用主线程 */
const isAutomationCenterFusion = computed(
  () =>
    route.name === "AutomationCenter" ||
    route.path === "/automation-center" ||
    route.path.startsWith("/automation-center/"),
);

/** 非脚本中心：首屏延迟再允许 SSE，避免与路由切换同帧抢主线程 */
const barStreamPrimed = ref(false);
let ssePrimeTimer = null;

function clearSsePrimeTimer() {
  if (ssePrimeTimer != null) {
    clearTimeout(ssePrimeTimer);
    ssePrimeTimer = null;
  }
}

watch(
  () => ({ on: showBar.value, hub: isAutomationCenterFusion.value }),
  ({ on, hub }) => {
    clearSsePrimeTimer();
    if (!on) {
      barStreamPrimed.value = false;
      return;
    }
    if (hub) {
      barStreamPrimed.value = true;
      return;
    }
    barStreamPrimed.value = false;
    ssePrimeTimer = window.setTimeout(() => {
      barStreamPrimed.value = true;
      ssePrimeTimer = null;
    }, 500);
  },
  { immediate: true },
);

const sseEnabled = computed(() => {
  if (!showBar.value) return false;
  if (isAutomationCenterFusion.value) {
    return realtimeStore.dashboardSseArmedOnAutomationCenter;
  }
  return barStreamPrimed.value;
});

const projectLabel = computed(() => {
  const p = projectOptions.value.find(
    (item) => String(item.id) === String(selectedProjectId.value),
  );
  return p?.project_name ? String(p.project_name) : "未选择";
});

const envLabel = computed(() => {
  const e = envOptions.value.find(
    (item) => String(item.id) === String(selectedEnvironmentId.value),
  );
  return e?.name ? String(e.name) : "未选择";
});

const { status: sseStatus } = useBackendSsePresence({
  enabled: sseEnabled,
  projectId: selectedProjectId,
  reconnectBackoffMs: (zero) => {
    if (isAutomationCenterFusion.value && realtimeStore.dashboardSseArmedOnAutomationCenter) {
      return scriptHubSseFuseBackoffMs(zero);
    }
    return dashboardSseBackoffMs(zero);
  },
});

const linkVisual = computed(() => {
  if (!showBar.value) return "off";
  if (EMERGENCY_DISABLE_REALTIME_CONNECTIONS) return "off";
  if (!sseEnabled.value) return "off";
  const s = sseStatus.value;
  if (s === "failed") return "warn";
  if (s === "online") return "online";
  if (s === "connecting") return "busy";
  if (s === "reconnecting") return "warn";
  return "off";
});

const linkText = computed(() => {
  if (!showBar.value) return "—";
  if (EMERGENCY_DISABLE_REALTIME_CONNECTIONS) return "SSE已关";
  if (!sseEnabled.value) return "待机";
  const s = sseStatus.value;
  if (s === "failed") return "已停止";
  if (s === "online") return "在线";
  if (s === "connecting") return "连接中";
  if (s === "reconnecting") return "重连中";
  return "空闲";
});

const linkTitle = computed(() => {
  if (!showBar.value) return "未登录或公开页";
  if (EMERGENCY_DISABLE_REALTIME_CONNECTIONS) {
    return "紧急封印：Dashboard SSE 已全局关闭（config/emergencyDisableRealtime.ts）";
  }
  if (isAutomationCenterFusion.value && !realtimeStore.dashboardSseArmedOnAutomationCenter) {
    return "自动化指挥中心首屏不自动连接 SSE；点击「执行」或切换到「终端」后建立 Dashboard 推送链路";
  }
  return "Dashboard SSE（约 3s 心跳）；绿色=链路正常，红色=正在重连";
});

const hostSupported = ref(false);
const hostCpu = ref("—");
const hostMem = ref("—");
const hostCpuCount = ref(0);
let hostTimer = null;

async function fetchHostMetrics() {
  if (
    !showBar.value ||
    (typeof document !== "undefined" && document.visibilityState !== "visible")
  ) {
    return;
  }
  try {
    const { data } = await getDashboardHostMetricsApi();
    const d = data?.data !== undefined ? data.data : data;
    if (!d?.supported) {
      hostSupported.value = false;
      return;
    }
    hostSupported.value = true;
    hostCpu.value = d.cpu_percent != null ? String(d.cpu_percent) : "—";
    hostMem.value = d.memory_percent != null ? String(d.memory_percent) : "—";
    hostCpuCount.value = Number(d.cpu_count) || 0;
  } catch {
    hostSupported.value = false;
  }
}

function startHostPolling() {
  stopHostPolling();
  void fetchHostMetrics();
  hostTimer = window.setInterval(() => {
    void fetchHostMetrics();
  }, 10000);
}

function stopHostPolling() {
  if (hostTimer != null) {
    clearInterval(hostTimer);
    hostTimer = null;
  }
}

watch(
  showBar,
  (v) => {
    if (v) {
      startHostPolling();
      void workspaceStore.ensureWorkspaceContext();
    } else {
      stopHostPolling();
      hostSupported.value = false;
    }
  },
  { immediate: true },
);

watch(
  () => route.fullPath,
  () => {
    syncAuth();
  },
);

function onStorage(ev) {
  if (!ev.key || ev.key === "token") syncAuth();
}

onMounted(() => {
  syncAuth();
  window.addEventListener("storage", onStorage);
  window.addEventListener("app:permissions", syncAuth);
});

onBeforeUnmount(() => {
  clearSsePrimeTimer();
  stopHostPolling();
  window.removeEventListener("storage", onStorage);
  window.removeEventListener("app:permissions", syncAuth);
});
</script>

<style scoped>
.mini-status-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 4800;
  height: 24px;
  box-sizing: border-box;
  background: #0d0d0d;
  border-top: 1px solid rgba(0, 216, 255, 0.22);
  font-size: 11px;
  line-height: 22px;
  font-family: "JetBrains Mono", "Fira Code", Consolas, ui-monospace, monospace;
  color: rgba(0, 216, 255, 0.92);
  user-select: none;
}

.mini-status-bar__inner {
  display: flex;
  align-items: center;
  height: 100%;
  padding: 0 8px;
  gap: 0;
  min-width: 0;
}

.mini-status-bar__fill {
  flex: 1;
  min-width: 8px;
}

.mini-status-bar__sep {
  width: 1px;
  height: 14px;
  margin: 0 10px;
  background: rgba(0, 216, 255, 0.2);
  flex-shrink: 0;
}

.mini-status-bar__item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  min-width: 0;
}

.mini-status-bar__item--link {
  cursor: default;
}

.mini-status-bar__key {
  font-size: 10px;
  letter-spacing: 0.06em;
  color: rgba(0, 216, 255, 0.45);
}

.mini-status-bar__val {
  color: rgba(224, 251, 255, 0.95);
  overflow: hidden;
  text-overflow: ellipsis;
}

.mini-status-bar__meta {
  font-size: 10px;
  color: rgba(0, 216, 255, 0.5);
  margin-left: 2px;
}

.mini-status-bar__dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
  background: rgba(100, 116, 139, 0.85);
  box-shadow: 0 0 6px rgba(100, 116, 139, 0.35);
}

.mini-status-bar__dot--online {
  background: #22c55e;
  box-shadow: 0 0 8px rgba(34, 197, 94, 0.65);
}

.mini-status-bar__dot--busy {
  background: #eab308;
  box-shadow: 0 0 8px rgba(234, 179, 8, 0.55);
}

.mini-status-bar__dot--warn {
  background: #ef4444;
  box-shadow: 0 0 8px rgba(239, 68, 68, 0.6);
  animation: mini-bar-pulse 1.2s ease-in-out infinite;
}

.mini-status-bar__dot--off {
  background: rgba(71, 85, 105, 0.9);
  box-shadow: none;
}

@keyframes mini-bar-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.45;
  }
}
</style>
