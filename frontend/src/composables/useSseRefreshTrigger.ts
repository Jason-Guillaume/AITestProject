import { onBeforeUnmount, onMounted } from "vue";

interface UseSseRefreshTriggerOptions {
  buildUrl: () => string;
  reconnectMs?: number;
  refreshEvents?: string[];
  onConnectionChange?: (connected: boolean) => void;
}

export function useSseRefreshTrigger(
  refreshFn: () => Promise<void> | void,
  options: UseSseRefreshTriggerOptions,
) {
  const reconnectMs = options.reconnectMs ?? 3000;
  const refreshEvents = options.refreshEvents ?? [];
  let source: EventSource | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let stopped = false;
  let refreshing = false;

  async function executeRefresh() {
    if (refreshing) return;
    refreshing = true;
    try {
      await refreshFn();
    } finally {
      refreshing = false;
    }
  }

  function setConnected(connected: boolean) {
    options.onConnectionChange?.(connected);
  }

  function clearReconnectTimer() {
    if (!reconnectTimer) return;
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }

  function closeSource() {
    if (!source) return;
    source.close();
    source = null;
    setConnected(false);
  }

  function scheduleReconnect() {
    if (stopped || document.visibilityState !== "visible") return;
    clearReconnectTimer();
    reconnectTimer = setTimeout(() => {
      connect();
    }, reconnectMs);
  }

  function connect() {
    if (stopped || document.visibilityState !== "visible") return;
    clearReconnectTimer();
    closeSource();
    const url = options.buildUrl();
    if (!url) return;
    source = new EventSource(url);
    source.onopen = () => {
      setConnected(true);
    };
    source.onmessage = () => {
      void executeRefresh();
    };
    source.onerror = () => {
      closeSource();
      scheduleReconnect();
    };
  }

  function handleVisibilityChange() {
    if (document.visibilityState === "visible") {
      connect();
      void executeRefresh();
      return;
    }
    closeSource();
    clearReconnectTimer();
  }

  function handleContextChanged() {
    void executeRefresh();
    connect();
  }

  onMounted(() => {
    connect();
    for (const eventName of refreshEvents) {
      window.addEventListener(eventName, handleContextChanged);
    }
    document.addEventListener("visibilitychange", handleVisibilityChange);
  });

  onBeforeUnmount(() => {
    stopped = true;
    closeSource();
    clearReconnectTimer();
    for (const eventName of refreshEvents) {
      window.removeEventListener(eventName, handleContextChanged);
    }
    document.removeEventListener("visibilitychange", handleVisibilityChange);
  });

  return {
    reconnect: connect,
  };
}
