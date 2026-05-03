// Simple WebSocket composable used by Vue components.
// It creates a WebSocket instance and registers a message handler.
// The returned object can be closed by the caller when needed.

export function useWebSocket(
  url: string,
  onMessage: (event: MessageEvent) => void
): WebSocket {
  const ws = new WebSocket(url)
  ws.onmessage = onMessage
  return ws
}
