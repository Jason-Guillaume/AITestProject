import { onActivated, onBeforeUnmount, onDeactivated, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { EMERGENCY_DISABLE_REALTIME_CONNECTIONS } from "@/config/emergencyDisableRealtime";
import {
  DASHBOARD_SSE_MAX_RECONNECT_ATTEMPTS,
  DASHBOARD_SSE_INITIAL_CONNECT_DELAY_MS,
  dashboardSseBackoffMs,
  DASHBOARD_SSE_FAILURE_MESSAGE,
} from "@/utils/dashboardSseHelpers";

interface UseSseRefreshTriggerOptions {
  buildUrl: () => string;
  /** @deprecated 已由指数退避替代，保留仅为兼容旧调用 */
  reconnectMs?: number;
  /** 在首连退避基础上额外延迟（ms） */
  connectDelayMs?: number;
  refreshEvents?: string[];
  onConnectionChange?: (connected: boolean) => void;
}

/**
 * Dashboard 等页：SSE 触发刷新。带指数退避、最大重试、卸载清理。
 */
export function useSseRefreshTrigger(
  refreshFn: () => Promise<void> | void,
  options: UseSseRefreshTriggerOptions,
) {
  /** 紧急封印：不执行 new EventSource；用定时拉取 mock 一次刷新，保证看板有数据 */
  if (EMERGENCY_DISABLE_REALTIME_CONNECTIONS) {
    const connectDelayMs = options.connectDelayMs ?? 0;
    const refreshEvents = options.refreshEvents ?? [];
    let stopped = false;

    async function executeRefresh() {
      if (stopped) return;
      try {
        await refreshFn();
      } catch {
        /* ignore */
      }
    }

    function handleContextChanged() {
      void executeRefresh();
    }

    function handleVisibilityChange() {
      if (document.visibilityState === "visible") {
        void executeRefresh();
      }
    }

    onMounted(() => {
      try {
        /* Mock：让看板显示「已连接」态，实际未建立 EventSource */
        options.onConnectionChange?.(true);
      } catch {
        /* ignore */
      }
      window.setTimeout(() => {
        void executeRefresh();
      }, Math.max(0, connectDelayMs));

      for (const eventName of refreshEvents) {
        window.addEventListener(eventName, handleContextChanged);
      }
      document.addEventListener("visibilitychange", handleVisibilityChange);
    });

    onDeactivated(() => {});

    onActivated(() => {
      if (!stopped) void executeRefresh();
    });

    onBeforeUnmount(() => {
      stopped = true;
      for (const eventName of refreshEvents) {
        window.removeEventListener(eventName, handleContextChanged);
      }
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      try {
        options.onConnectionChange?.(false);
      } catch {
        /* ignore */
      }
    });

    return {
      reconnect: () => void executeRefresh(),
    };
  }

  const connectDelayMs = options.connectDelayMs ?? 0;
  const refreshEvents = options.refreshEvents ?? [];
  let source: EventSource | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let timerAbort: AbortController | null = null;
  let stopped = false;
  let refreshing = false;
  let errorsSinceLastSuccess = 0;

  async function executeRefresh() {
    if (refreshing) return;
    refreshing = true;
    try {
      await refreshFn();
    } catch {
      /* 刷新失败不阻断 SSE */
    } finally {
      refreshing = false;
    }
  }

  function setConnected(connected: boolean) {
    try {
      options.onConnectionChange?.(connected);
    } catch {
      /* ignore */
    }
  }

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
      /* ignore */
    }
    source = null;
    setConnected(false);
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
      if (document.visibilityState !== "visible") return;
      try {
        run();
      } catch {
        handleFailure();
      }
    }, delayMs);
  }

  function openEventSource() {
    if (stopped || document.visibilityState !== "visible") return;
    closeSourceOnly();

    let url: string;
    try {
      url = options.buildUrl();
    } catch {
      handleFailure();
      return;
    }
    if (!url) {
      setConnected(false);
      return;
    }

    let es: EventSource;
    try {
      es = new EventSource(url);
    } catch {
      handleFailure();
      return;
    }

    source = es;

    es.onopen = () => {
      errorsSinceLastSuccess = 0;
      setConnected(true);
    };

    es.onmessage = () => {
      void executeRefresh();
    };

    es.onerror = () => {
      try {
        es.close();
      } catch {
        /* ignore */
      }
      if (source === es) source = null;
      setConnected(false);
      handleFailure();
    };
  }

  function handleFailure() {
    if (stopped) return;
    if (document.visibilityState !== "visible") {
      hardTeardown();
      return;
    }

    errorsSinceLastSuccess += 1;
    if (errorsSinceLastSuccess > DASHBOARD_SSE_MAX_RECONNECT_ATTEMPTS) {
      hardTeardown();
      try {
        ElMessage.error(DASHBOARD_SSE_FAILURE_MESSAGE);
      } catch {
        /* ignore */
      }
      return;
    }

    const delay = dashboardSseBackoffMs(errorsSinceLastSuccess - 1);
    scheduleConnect(delay, openEventSource);
  }

  function startCycle(resetErrors: boolean) {
    if (stopped) return;
    if (document.visibilityState !== "visible") return;
    if (resetErrors) errorsSinceLastSuccess = 0;
    hardTeardown();
    const initialDelay = DASHBOARD_SSE_INITIAL_CONNECT_DELAY_MS + Math.max(0, connectDelayMs);
    scheduleConnect(initialDelay, openEventSource);
  }

  function handleVisibilityChange() {
    if (document.visibilityState === "visible") {
      startCycle(true);
      void executeRefresh();
      return;
    }
    hardTeardown();
  }

  function handleContextChanged() {
    void executeRefresh();
    errorsSinceLastSuccess = 0;
    startCycle(true);
  }

  onMounted(() => {
    startCycle(true);
    for (const eventName of refreshEvents) {
      window.addEventListener(eventName, handleContextChanged);
    }
    document.addEventListener("visibilitychange", handleVisibilityChange);
  });

  onDeactivated(() => {
    hardTeardown();
  });

  onActivated(() => {
    if (stopped) return;
    startCycle(true);
  });

  onBeforeUnmount(() => {
    stopped = true;
    hardTeardown();
    for (const eventName of refreshEvents) {
      window.removeEventListener(eventName, handleContextChanged);
    }
    document.removeEventListener("visibilitychange", handleVisibilityChange);
  });

  return {
    reconnect: () => startCycle(true),
  };
}
