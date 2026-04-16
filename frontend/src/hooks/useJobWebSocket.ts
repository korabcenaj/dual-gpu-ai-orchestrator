import { useEffect, useRef } from "react";

export interface JobStatusMessage {
  job_id: string;
  status: string;
  backend: string;
  result?: Record<string, unknown>;
  error?: string;
  duration_ms?: number;
}

export function useJobWebSocket(onMessage: (msg: JobStatusMessage) => void) {
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(
      (window.location.protocol === "https:" ? "wss://" : "ws://") +
        window.location.host + "/ws/jobs"
    );
    wsRef.current = ws;
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        onMessage(msg);
      } catch {}
    };
    return () => {
      ws.close();
    };
  }, [onMessage]);
}
