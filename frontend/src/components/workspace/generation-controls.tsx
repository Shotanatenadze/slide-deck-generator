'use client';

import { motion } from 'framer-motion';
import { Play, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useGenerationContext } from '@/app/providers';

interface GenerationControlsProps {
  onGenerate: () => void;
}

export function GenerationControls({ onGenerate }: GenerationControlsProps) {
  const { state } = useGenerationContext();

  const isGenerating = state.status === 'generating';
  const isUploading = state.status === 'uploading';
  const hasFiles = state.uploadedFiles.length > 0;
  const isDisabled = !hasFiles || isGenerating || isUploading;

  const statusText = (() => {
    switch (state.status) {
      case 'uploading':
        return 'Uploading files...';
      case 'generating':
        return 'Generating deck...';
      case 'completed':
        return 'Generation complete';
      case 'error':
        return state.error ?? 'An error occurred';
      default:
        return hasFiles
          ? 'Ready to generate'
          : 'Upload files to begin';
    }
  })();

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.15 }}
    >
      <button
        onClick={onGenerate}
        disabled={isDisabled}
        className={cn(
          'relative w-full py-3.5 rounded-xl text-white font-semibold text-sm flex items-center justify-center gap-2 transition-all duration-300 overflow-hidden',
          isGenerating
            ? 'gradient-generating cursor-wait'
            : isDisabled
              ? 'bg-gray-300 cursor-not-allowed text-gray-500'
              : 'gradient-navy hover:shadow-lg hover:shadow-blue-900/25 active:scale-[0.98]'
        )}
      >
        {isGenerating ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Generating...
          </>
        ) : (
          <>
            <Play className="w-5 h-5" />
            Generate Deck
          </>
        )}
      </button>

      {/* Status text */}
      <div className="flex items-center justify-center mt-2">
        <p
          className={cn(
            'text-xs font-medium',
            state.status === 'error' ? 'text-red-500' : 'text-gray-400'
          )}
        >
          {statusText}
        </p>
      </div>
    </motion.div>
  );
}
