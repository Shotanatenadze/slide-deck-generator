'use client';

import { useCallback, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, FileSpreadsheet, FileText, X, FolderOpen } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useGenerationContext } from '@/app/providers';
import type { UploadedFile } from '@/types/generation';

function detectFileType(name: string): UploadedFile['type'] {
  const lower = name.toLowerCase();
  if (lower.endsWith('.pdf')) return 'pdf';
  const upper = name.toUpperCase();
  if (upper.includes('HOLDINGS')) return 'holdings';
  if (upper.includes('REPORT DATA') || upper.includes('BOARD')) return 'board_report';
  return 'unknown';
}

const FILE_TYPE_LABELS: Record<UploadedFile['type'], { label: string; color: string }> = {
  board_report: { label: 'Board Report', color: 'bg-blue-100 text-blue-700' },
  holdings: { label: 'Holdings', color: 'bg-emerald-100 text-emerald-700' },
  pdf: { label: 'PDF', color: 'bg-red-100 text-red-700' },
  unknown: { label: 'Unknown', color: 'bg-gray-100 text-gray-600' },
};

interface FileUploadZoneProps {
  onFilesSelected: (files: File[]) => void;
  onFileRemoved: (name: string) => void;
}

export function FileUploadZone({ onFilesSelected, onFileRemoved }: FileUploadZoneProps) {
  const { state, setFiles } = useGenerationContext();
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const [loadingSamples, setLoadingSamples] = useState(false);
  const isDisabled = state.status === 'uploading' || state.status === 'generating';

  const SAMPLE_FILES = [
    'SAMPLE REPORT DATA AGG 2.xlsx',
    'SAMPLE REPORT DATA SMA 2.xlsx',
    'SAMPLE HOLDINGS REPORT.xlsx',
  ];

  const loadSampleFiles = useCallback(async () => {
    if (isDisabled || loadingSamples) return;
    setLoadingSamples(true);
    try {
      const files: File[] = [];
      for (const name of SAMPLE_FILES) {
        const res = await fetch(`/samples/${encodeURIComponent(name)}`);
        const blob = await res.blob();
        files.push(new File([blob], name, { type: blob.type }));
      }
      const newUploadedFiles: UploadedFile[] = files.map((f) => ({
        name: f.name,
        size: f.size,
        type: detectFileType(f.name),
      }));
      setFiles(newUploadedFiles);
      onFilesSelected(files);
    } catch (err) {
      console.error('Failed to load sample files:', err);
    } finally {
      setLoadingSamples(false);
    }
  }, [isDisabled, loadingSamples, setFiles, onFilesSelected]);

  const handleFiles = useCallback(
    (fileList: FileList) => {
      const accepted = Array.from(fileList).filter((f) => {
        const ext = f.name.toLowerCase();
        return ext.endsWith('.xlsx') || ext.endsWith('.xls') || ext.endsWith('.pdf');
      });

      if (accepted.length === 0) return;

      const newFiles: UploadedFile[] = accepted.map((f) => ({
        name: f.name,
        size: f.size,
        type: detectFileType(f.name),
      }));

      // Merge with existing, replacing by name
      const existing = state.uploadedFiles.filter(
        (ef) => !newFiles.some((nf) => nf.name === ef.name)
      );
      setFiles([...existing, ...newFiles]);

      // Notify parent with actual File objects
      onFilesSelected(accepted);
    },
    [state.uploadedFiles, setFiles, onFilesSelected]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      if (!isDisabled && e.dataTransfer.files.length > 0) {
        handleFiles(e.dataTransfer.files);
      }
    },
    [handleFiles, isDisabled]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const removeFile = useCallback(
    (name: string) => {
      setFiles(state.uploadedFiles.filter((f) => f.name !== name));
      onFileRemoved(name);
    },
    [state.uploadedFiles, setFiles, onFileRemoved]
  );

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Clearwater Data Files
      </label>

      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !isDisabled && inputRef.current?.click()}
        className={cn(
          'relative flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-6 cursor-pointer transition-all duration-200',
          isDragOver
            ? 'border-blue-400 bg-blue-50'
            : 'border-gray-300 bg-gray-50 hover:border-gray-400 hover:bg-gray-100',
          isDisabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        <Upload
          className={cn(
            'w-8 h-8 transition-colors',
            isDragOver ? 'text-blue-500' : 'text-gray-400'
          )}
        />
        <p className="text-sm text-gray-600">
          <span className="font-medium text-gray-800">Click to upload</span> or drag and drop
        </p>
        <p className="text-xs text-gray-400">.xlsx, .xls, or .pdf files</p>

        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls,.pdf"
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files) handleFiles(e.target.files);
            e.target.value = '';
          }}
          disabled={isDisabled}
        />
      </div>

      {/* Load sample files */}
      {state.uploadedFiles.length === 0 && (
        <button
          onClick={loadSampleFiles}
          disabled={isDisabled || loadingSamples}
          className={cn(
            'mt-2 flex items-center justify-center gap-2 w-full py-2 rounded-lg text-xs font-medium transition-all',
            'border border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100',
            (isDisabled || loadingSamples) && 'opacity-50 cursor-not-allowed'
          )}
        >
          <FolderOpen className="w-3.5 h-3.5" />
          {loadingSamples ? 'Loading...' : 'Load sample Clearwater files'}
        </button>
      )}

      {/* Uploaded files */}
      <AnimatePresence mode="popLayout">
        {state.uploadedFiles.length > 0 && (
          <motion.div
            className="flex flex-wrap gap-2 mt-3"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
          >
            {state.uploadedFiles.map((file) => {
              const typeInfo = FILE_TYPE_LABELS[file.type];
              return (
                <motion.div
                  key={file.name}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  className="flex items-center gap-2 rounded-lg bg-white border border-gray-200 px-3 py-2 shadow-sm"
                >
                  {file.type === 'pdf' ? (
                    <FileText className="w-4 h-4 text-red-500 flex-shrink-0" />
                  ) : (
                    <FileSpreadsheet className="w-4 h-4 text-green-600 flex-shrink-0" />
                  )}
                  <div className="flex flex-col min-w-0">
                    <span className="text-xs font-medium text-gray-800 truncate max-w-[180px]">
                      {file.name}
                    </span>
                    <span className="text-[10px] text-gray-400">{formatSize(file.size)}</span>
                  </div>
                  <span
                    className={cn(
                      'text-[10px] font-medium px-1.5 py-0.5 rounded-full whitespace-nowrap',
                      typeInfo.color
                    )}
                  >
                    {typeInfo.label}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(file.name);
                    }}
                    className="ml-1 text-gray-400 hover:text-red-500 transition-colors"
                    disabled={isDisabled}
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </motion.div>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>

      {/* File summary */}
      {state.uploadedFiles.length > 0 && (
        <div className="mt-3 p-3 rounded-lg bg-blue-50 border border-blue-100">
          <p className="text-xs font-medium text-blue-800">
            {state.uploadedFiles.length} file{state.uploadedFiles.length > 1 ? 's' : ''} ready
            {' — '}
            {formatSize(state.uploadedFiles.reduce((sum, f) => sum + f.size, 0))} total
          </p>
          <p className="text-[11px] text-blue-600 mt-1">
            {state.uploadedFiles.map((f) => f.name).join(', ')}
          </p>
        </div>
      )}
    </motion.div>
  );
}
