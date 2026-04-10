import { onBeforeUnmount, onMounted } from "vue";

interface UseRealtimePollingOptions {
  intervalMs?: number;
  runOnMount?: boolean;
  refreshEvents?: string[];
  shouldSkip?: () => boolean;
}

export function useRealtimePolling(
  refreshFn: () => Promise<void> | void,
  options: UseRealtimePollingOptions = {},
) {
  const intervalMs = options.intervalMs ?? 5000;
  const runOnMount = options.runOnMount ?? true;
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

  onMounted(() => {
    if (runOnMount) {
      void executeRefresh();
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
