import { onBeforeUnmount, onMounted } from "vue";

interface UseRealtimePollingOptions {
  intervalMs?: number;
  runOnMount?: boolean;
  /** 首次拉取延后（ms），再交给 requestIdleCallback，降低首屏与其它接口抢带宽 */
  deferredInitialRunMs?: number;
  refreshEvents?: string[];
  shouldSkip?: () => boolean;
}

export function useRealtimePolling(
  refreshFn: () => Promise<void> | void,
  options: UseRealtimePollingOptions = {},
) {
  const intervalMs = options.intervalMs ?? 15000;
  const runOnMount = options.runOnMount ?? true;
  const deferredInitialRunMs = options.deferredInitialRunMs ?? 0;
  const refreshEvents = options.refreshEvents ?? [];
  let timer: ReturnType<typeof setInterval> | null = null;
  let loading = false;

  async function executeRefresh() {
    if (loading) return;
    loading = true;
    try {
      await refreshFn();
    } finally {
      loading = false;
    }
  }

  function startPolling() {
    if (timer) return;
    timer = setInterval(() => {
      if (document.visibilityState !== "visible") return;
      if (options.shouldSkip?.()) return;
      void executeRefresh();
    }, intervalMs);
  }

  function stopPolling() {
    if (!timer) return;
    clearInterval(timer);
    timer = null;
  }

  function handleVisibilityChange() {
    if (document.visibilityState === "visible") {
      void executeRefresh();
    }
  }

  function bindRefreshEvents() {
    for (const eventName of refreshEvents) {
      window.addEventListener(eventName, executeRefresh);
    }
  }

  function unbindRefreshEvents() {
    for (const eventName of refreshEvents) {
      window.removeEventListener(eventName, executeRefresh);
    }
  }

  function scheduleInitialRefresh() {
    const kick = () => {
      void executeRefresh();
    };
    const idleKick =
      typeof requestIdleCallback !== "undefined"
        ? () => requestIdleCallback(kick, { timeout: 2000 })
        : () => setTimeout(kick, 0);
    if (deferredInitialRunMs > 0) {
      setTimeout(idleKick, deferredInitialRunMs);
    } else {
      idleKick();
    }
  }

  onMounted(() => {
    if (runOnMount) {
      scheduleInitialRefresh();
    }
    startPolling();
    bindRefreshEvents();
    document.addEventListener("visibilitychange", handleVisibilityChange);
  });

  onBeforeUnmount(() => {
    stopPolling();
    unbindRefreshEvents();
    document.removeEventListener("visibilitychange", handleVisibilityChange);
  });

  return {
    refreshNow: executeRefresh,
    startPolling,
    stopPolling,
  };
}
