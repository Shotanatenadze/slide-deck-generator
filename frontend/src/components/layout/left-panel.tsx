'use client';

import { useState, useRef, useCallback } from 'react';
import Image from 'next/image';
import { FileUploadZone } from '@/components/workspace/file-upload-zone';
import { MarketContextInput } from '@/components/workspace/market-context-input';
import { AnalystPrompt } from '@/components/workspace/analyst-prompt';
import { GenerationControls } from '@/components/workspace/generation-controls';
import { DownloadSection } from '@/components/workspace/download-section';
import { useGeneration } from '@/hooks/use-generation';

export function LeftPanel() {
  const { state, upload, generate, reset, downloadUrl } = useGeneration();

  // Actual browser File objects for upload
  const rawFilesRef = useRef<File[]>([]);

  // Form state
  const [clientName, setClientName] = useState('');
  const [prompt, setPrompt] = useState('');
  const [marketContext, setMarketContext] = useState('');

  const handleFilesSelected = useCallback(
    (files: File[]) => {
      const existingNames = new Set(files.map((f) => f.name));
      const kept = rawFilesRef.current.filter((f) => !existingNames.has(f.name));
      rawFilesRef.current = [...kept, ...files];
    },
    []
  );

  const handleFileRemoved = useCallback(
    (name: string) => {
      rawFilesRef.current = rawFilesRef.current.filter((f) => f.name !== name);
    },
    []
  );

  // Track pending generate params after upload
  const pendingParamsRef = useRef<{
    client_name: string;
    analyst_prompt: string;
    market_context?: string;
  } | null>(null);

  const handleGenerateClick = useCallback(async () => {
    if (rawFilesRef.current.length === 0) return;

    const params = {
      client_name: clientName || 'Client',
      analyst_prompt: prompt || 'Generate a comprehensive quarterly review deck.',
      market_context: marketContext || undefined,
    };

    // If we already completed/errored, reset first for a fresh run
    if (state.status === 'completed' || state.status === 'error') {
      reset();
    }

    // Always upload fresh — creates a new generationId each time
    pendingParamsRef.current = params;
    await upload(rawFilesRef.current);
  }, [upload, reset, state.status, clientName, prompt, marketContext]);

  // After upload completes and generationId is set, trigger generation
  const prevGenIdRef = useRef<string | null>(null);
  if (
    pendingParamsRef.current &&
    state.generationId &&
    state.generationId !== prevGenIdRef.current &&
    state.status === 'idle'
  ) {
    const params = pendingParamsRef.current;
    prevGenIdRef.current = state.generationId;
    pendingParamsRef.current = null;
    setTimeout(() => {
      generate(params);
    }, 0);
  }

  return (
    <div className="flex flex-col gap-6 p-6 min-h-full overflow-y-auto">
      {/* Header */}
      <div className="flex items-center gap-3 pb-2 border-b border-gray-100">
        <Image
          src="/logo.svg"
          alt="Logo"
          width={140}
          height={32}
          priority
        />
        <div className="ml-auto">
          <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">
            Slide Deck Generator
          </span>
        </div>
      </div>

      {/* File upload */}
      <FileUploadZone
        onFilesSelected={handleFilesSelected}
        onFileRemoved={handleFileRemoved}
      />

      {/* Market context */}
      <MarketContextInput value={marketContext} onChange={setMarketContext} />

      {/* Analyst prompt */}
      <AnalystPrompt
        prompt={prompt}
        onPromptChange={setPrompt}
        clientName={clientName}
        onClientNameChange={setClientName}
      />

      {/* Generate button */}
      <GenerationControls onGenerate={handleGenerateClick} />

      {/* Download section */}
      {state.status === 'completed' && downloadUrl && (
        <DownloadSection downloadUrl={downloadUrl} />
      )}
    </div>
  );
}
