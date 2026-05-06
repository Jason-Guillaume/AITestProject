// Simple WebSocket composable used by Vue components.
// It creates a WebSocket instance and registers a message handler.
// The returned object can be closed by the caller when needed.

import { EMERGENCY_DISABLE_REALTIME_CONNECTIONS } from "@/config/emergencyDisableRealtime";

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
  onMessage: (event: MessageEvent) => void
): WebSocket {
  if (EMERGENCY_DISABLE_REALTIME_CONNECTIONS) {
    return mockClosedWebSocket();
  }
  const ws = new WebSocket(url);
  ws.onmessage = onMessage;
  return ws;
}
