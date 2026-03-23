'use client';

import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useGenerationContext } from '@/app/providers';
import { useWebSocket } from '@/hooks/use-websocket';
import { uploadFiles as apiUpload, startGeneration as apiGenerate, getDownloadUrl, type GenerateParams } from '@/lib/api';
import type { AgentEvent } from '@/types/agent';
import type { UploadedFile } from '@/types/generation';

function detectFileType(name: string): UploadedFile['type'] {
  const lower = name.toLowerCase();
  if (lower.endsWith('.pdf')) return 'pdf';
  const upper = name.toUpperCase();
  if (upper.includes('HOLDINGS')) return 'holdings';
  if (upper.includes('REPORT DATA') || upper.includes('BOARD')) return 'board_report';
  return 'unknown';
}

export function useGeneration() {
  const { state, setFiles, setStatus, addAgentEvent, setCompleted, setError, reset } = useGenerationContext();

  // Track whether we should auto-start generation after WS connects
  const pendingGenerateRef = useRef<Omit<GenerateParams, 'generation_id'> | null>(null);
  const wsConnectedRef = useRef(false);

  // WebSocket handler for agent events
  const handleWsMessage = useCallback(
    (data: unknown) => {
      const msg = data as Record<string, unknown>;

      if (msg.type === 'agent_event') {
        addAgentEvent(msg.payload as AgentEvent);
      } else if (msg.type === 'generation_completed') {
        const payload = msg.payload as Record<string, unknown> | undefined;
        setCompleted(payload?.compliance_report as Record<string, unknown> | undefined);
      } else if (msg.type === 'generation_error') {
        const payload = msg.payload as Record<string, unknown> | undefined;
        setError((payload?.message as string) ?? 'Generation failed');
      }
    },
    [addAgentEvent, setCompleted, setError]
  );

  // Connect WebSocket as soon as we have a generationId AND status is generating
  const { isConnected } = useWebSocket({
    generationId: state.generationId,
    onMessage: handleWsMessage,
    enabled: state.status === 'generating',
  });

  // When WS connects and we have a pending generate, fire the API call
  useEffect(() => {
    if (isConnected && pendingGenerateRef.current && state.generationId) {
      const params = pendingGenerateRef.current;
      pendingGenerateRef.current = null;

      apiGenerate({ ...params, generation_id: state.generationId }).catch((err) => {
        setError(err instanceof Error ? err.message : 'Generation failed');
      });
    }
  }, [isConnected, state.generationId, setError]);

  // Track WS connection state in ref for sync access
  useEffect(() => {
    wsConnectedRef.current = isConnected;
  }, [isConnected]);

  // Upload files
  const upload = useCallback(
    async (files: File[]) => {
      try {
        setStatus('uploading');
        const result = await apiUpload(files);

        const uploadedFiles: UploadedFile[] = files.map((f) => ({
          name: f.name,
          size: f.size,
          type: detectFileType(f.name),
        }));

        setFiles(uploadedFiles);
        setStatus('idle', result.generation_id);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Upload failed');
      }
    },
    [setFiles, setStatus, setError]
  );

  // Start generation — sets status to 'generating' first so WS connects,
  // then the useEffect fires the actual API call once WS is ready
  const generate = useCallback(
    async (params: Omit<GenerateParams, 'generation_id'>) => {
      if (!state.generationId) {
        setError('No generation ID. Upload files first.');
        return;
      }

      // Store params for when WS connects
      pendingGenerateRef.current = params;
      // Set status to 'generating' — this enables the WebSocket hook
      setStatus('generating');
    },
    [state.generationId, setStatus, setError]
  );

  // Download URL
  const downloadUrl = useMemo(() => {
    if (state.status === 'completed' && state.generationId) {
      return getDownloadUrl(state.generationId);
    }
    return null;
  }, [state.status, state.generationId]);

  return {
    state,
    upload,
    generate,
    reset,
    downloadUrl,
    isConnected,
  };
}
