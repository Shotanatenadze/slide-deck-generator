'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000';
const MAX_RETRIES = 3;
const RETRY_DELAY = 2000;

interface UseWebSocketOptions {
  generationId: string | null;
  onMessage: (data: unknown) => void;
  enabled?: boolean;
}

export function useWebSocket({ generationId, onMessage, enabled = true }: UseWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const onMessageRef = useRef(onMessage);

  // Keep onMessage ref up to date without triggering reconnects
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const connect = useCallback(() => {
    if (!generationId || !enabled) return;

    const url = `${WS_URL}/ws/generation/${generationId}`;

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        retriesRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessageRef.current(data);
        } catch {
          console.error('Failed to parse WebSocket message:', event.data);
        }
      };

      ws.onerror = () => {
        setError('WebSocket connection error');
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        wsRef.current = null;

        // Don't retry on normal closure (code 1000) or if disabled
        if (event.code === 1000) return;

        if (retriesRef.current < MAX_RETRIES) {
          retriesRef.current += 1;
          setTimeout(connect, RETRY_DELAY * retriesRef.current);
        } else {
          setError('WebSocket connection failed after maximum retries');
        }
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect');
    }
  }, [generationId, enabled]);

  useEffect(() => {
    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close(1000);
        wsRef.current = null;
      }
    };
  }, [connect]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close(1000);
      wsRef.current = null;
    }
  }, []);

  return { isConnected, error, disconnect };
}
