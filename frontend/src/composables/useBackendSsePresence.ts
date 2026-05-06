import { ref, watch, onBeforeUnmount, type Ref } from "vue";
import { ElMessage } from "element-plus";
import { EMERGENCY_DISABLE_REALTIME_CONNECTIONS } from "@/config/emergencyDisableRealtime";
import { getDashboardStreamUrl } from "@/api/dashboard";
import {
  DASHBOARD_SSE_MAX_RECONNECT_ATTEMPTS,
  DASHBOARD_SSE_INITIAL_CONNECT_DELAY_MS,
  dashboardSseBackoffMs,
  DASHBOARD_SSE_FAILURE_MESSAGE,
} from "@/utils/dashboardSseHelpers";

type ReconnectBackoffFn = (zeroBasedAttempt: number) => number;

export type SsePresenceStatus = "idle" | "connecting" | "online" | "reconnecting" | "failed";

interface UseBackendSsePresenceOptions {
  /** 为 false 时不建立连接 */
  enabled: Ref<boolean>;
  projectId: Ref<string | number | null | undefined>;
  /** 重连前等待时长（毫秒）；参数与 dashboardSseBackoffMs 一致，为已连续失败次数减一 */
  reconnectBackoffMs?: ReconnectBackoffFn;
}

/**
 * 订阅 Dashboard SSE（状态栏心跳）。
 * - 首次连接延迟，避免与路由首帧争用主线程
 * - 失败时指数退避重连，超过次数后停止并提示
 */
export function useBackendSsePresence(options: UseBackendSsePresenceOptions) {
  /** 紧急封印：不执行 new EventSource，避免 dashboard/stream 拖死主线程 */
  if (EMERGENCY_DISABLE_REALTIME_CONNECTIONS) {
    const status = ref<SsePresenceStatus>("idle");
    watch(
      () => options.enabled.value,
      () => {
        status.value = "idle";
      },
      { immediate: true },
    );
    return {
      status,
      reconnect: () => {},
    };
  }

  const status = ref<SsePresenceStatus>("idle");
  let source: EventSource | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  /** 取消已排队的重连/首连定时器 */
  let timerAbort: AbortController | null = null;
  let stopped = false;
  let errorsSinceLastSuccess = 0;

  function clearScheduledConnect() {
    if (reconnectTimer != null) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    timerAbort?.abort();
    timerAbort = null;
  }

  function closeSourceOnly() {
    if (!source) return;
    try {
      source.close();
    } catch {
      /* EventSource.close 不应抛错，忽略 */
    }
    source = null;
  }

  function hardTeardown() {
    clearScheduledConnect();
    closeSourceOnly();
  }

  function scheduleConnect(delayMs: number, run: () => void) {
    clearScheduledConnect();
    timerAbort = new AbortController();
    const { signal } = timerAbort;
    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null;
      if (stopped || signal.aborted) return;
      if (!options.enabled.value) return;
      try {
        run();
      } catch {
        handleConnectFailure();
      }
    }, delayMs);
  }

  function openEventSource() {
    if (stopped || typeof document === "undefined") return;
    if (!options.enabled.value) {
      hardTeardown();
      status.value = "idle";
      return;
    }
    if (document.visibilityState !== "visible") {
      closeSourceOnly();
      return;
    }
    const token = localStorage.getItem("token");
    if (!token) {
      hardTeardown();
      status.value = "idle";
      return;
    }

    closeSourceOnly();

    let url: string;
    try {
      const pid = options.projectId.value;
      url = getDashboardStreamUrl(
        pid != null && String(pid).trim() !== "" ? { project_id: String(pid) } : {},
      );
    } catch {
      handleConnectFailure();
      return;
    }
    if (!url) {
      status.value = "idle";
      return;
    }

    status.value = "connecting";

    let es: EventSource;
    try {
      es = new EventSource(url);
    } catch {
      handleConnectFailure();
      return;
    }

    source = es;

    es.onopen = () => {
      errorsSinceLastSuccess = 0;
      status.value = "online";
    };

    es.onmessage = () => {
      /* tick */
    };

    es.onerror = () => {
      try {
        es.close();
      } catch {
        /* ignore */
      }
      if (source === es) source = null;
      handleConnectFailure();
    };
  }

  function handleConnectFailure() {
    if (stopped) return;
    if (!options.enabled.value) {
      hardTeardown();
      status.value = "idle";
      return;
    }

    errorsSinceLastSuccess += 1;
    if (errorsSinceLastSuccess > DASHBOARD_SSE_MAX_RECONNECT_ATTEMPTS) {
      hardTeardown();
      status.value = "failed";
      try {
        ElMessage.error(DASHBOARD_SSE_FAILURE_MESSAGE);
      } catch {
        /* 避免 message 异常影响主流程 */
      }
      return;
    }

    status.value = "reconnecting";
    const backoff = options.reconnectBackoffMs ?? dashboardSseBackoffMs;
    const delay = backoff(errorsSinceLastSuccess - 1);
    scheduleConnect(delay, openEventSource);
  }

  function startConnectionCycle(resetErrors: boolean) {
    if (stopped) return;
    if (resetErrors) errorsSinceLastSuccess = 0;
    if (!options.enabled.value) {
      hardTeardown();
      status.value = "idle";
      return;
    }
    if (typeof document === "undefined" || document.visibilityState !== "visible") {
      hardTeardown();
      status.value = "idle";
      return;
    }
    hardTeardown();
    status.value = "connecting";
    scheduleConnect(DASHBOARD_SSE_INITIAL_CONNECT_DELAY_MS, openEventSource);
  }

  function handleVisibilityChange() {
    if (typeof document === "undefined") return;
    if (document.visibilityState === "visible") {
      if (options.enabled.value && status.value !== "failed") {
        startConnectionCycle(true);
      }
      return;
    }
    hardTeardown();
    status.value = "idle";
  }

  watch(
    [() => options.enabled.value, () => options.projectId.value],
    () => {
      if (!options.enabled.value) {
        hardTeardown();
        errorsSinceLastSuccess = 0;
        status.value = "idle";
        return;
      }
      if (status.value === "failed") {
        errorsSinceLastSuccess = 0;
        status.value = "idle";
      }
      startConnectionCycle(true);
    },
    { immediate: true },
  );

  onBeforeUnmount(() => {
    stopped = true;
    hardTeardown();
    if (typeof document !== "undefined") {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    }
  });

  if (typeof document !== "undefined") {
    document.addEventListener("visibilitychange", handleVisibilityChange);
  }

  return {
    status,
    /** 手动再试（重置失败计数并排队首连） */
    reconnect: () => startConnectionCycle(true),
  };
}
