import { ref, onBeforeUnmount } from "vue";
import { EMERGENCY_DISABLE_REALTIME_CONNECTIONS } from "@/config/emergencyDisableRealtime";

interface UseWebSocketOptions {
  heartbeatIntervalMs?: number;
  reconnectMaxRetries?: number;
  reconnectBaseDelayMs?: number;
}

function mockClosedWebSocket(): WebSocket {
  return {
    close: () => {},
    send: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    get readyState() {
      return 3;
    },
  } as unknown as WebSocket;
}

export function useWebSocket(
  url: string,
  onMessage: (event: MessageEvent) => void,
  options: UseWebSocketOptions = {}
): { ws: WebSocket; isConnected: ReturnType<typeof ref<boolean>> } {
  if (EMERGENCY_DISABLE_REALTIME_CONNECTIONS) {
    return { ws: mockClosedWebSocket(), isConnected: ref(false) };
  }

  const heartbeatIntervalMs = options.heartbeatIntervalMs ?? 30000;
  const reconnectMaxRetries = options.reconnectMaxRetries ?? 5;
  const reconnectBaseDelayMs = options.reconnectBaseDelayMs ?? 1000;
  const isConnected = ref(false);

  let ws: WebSocket = new WebSocket(url);
  let retryCount = 0;
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let stopped = false;

  function startHeartbeat() {
    stopHeartbeat();
    heartbeatTimer = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "ping" }));
      }
    }, heartbeatIntervalMs);
  }

  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    }
  }

  function scheduleReconnect() {
    if (stopped || retryCount >= reconnectMaxRetries) return;
    const delay = reconnectBaseDelayMs * Math.pow(2, retryCount);
    retryCount++;
    reconnectTimer = setTimeout(() => {
      if (stopped) return;
      ws = new WebSocket(url);
      bindEvents();
    }, Math.min(delay, 30000));
  }

  function bindEvents() {
    ws.onopen = () => {
      retryCount = 0;
      isConnected.value = true;
      startHeartbeat();
    };
    ws.onmessage = onMessage;
    ws.onclose = () => {
      isConnected.value = false;
      stopHeartbeat();
      scheduleReconnect();
    };
    ws.onerror = () => {
      isConnected.value = false;
      stopHeartbeat();
    };
  }

  bindEvents();

  onBeforeUnmount(() => {
    stopped = true;
    stopHeartbeat();
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
      ws.close();
    }
  });

  return { ws, isConnected };
}
