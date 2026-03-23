'use client';

import { motion } from 'framer-motion';
import { Download, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';
import { useGenerationContext } from '@/app/providers';
import { getDownloadUrl } from '@/lib/api';

interface DownloadSectionProps {
  downloadUrl: string;
}

export function DownloadSection({ downloadUrl }: DownloadSectionProps) {
  const { state } = useGenerationContext();

  // Parse compliance report summary
  const compliance = state.complianceReport;
  const passCount = (compliance?.pass_count as number) ?? 0;
  const warnCount = (compliance?.warn_count as number) ?? 0;
  const failCount = (compliance?.fail_count as number) ?? 0;
  const hasCompliance = compliance != null;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, type: 'spring', stiffness: 200, damping: 20 }}
      className="rounded-xl border border-green-200 bg-green-50 p-5"
    >
      <div className="flex items-center gap-2 mb-4">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.2, type: 'spring', stiffness: 300 }}
        >
          <CheckCircle className="w-6 h-6 text-green-600" />
        </motion.div>
        <h3 className="text-sm font-semibold text-green-800">
          Deck Generated Successfully
        </h3>
      </div>

      {/* Download button */}
      <a
        href={downloadUrl}
        download
        className="flex items-center justify-center gap-2 w-full py-3 rounded-xl bg-green-600 hover:bg-green-700 text-white font-semibold text-sm transition-colors shadow-sm"
      >
        <Download className="w-5 h-5" />
        Download PPTX
      </a>

      {/* Compliance summary */}
      {hasCompliance && (
        <div className="flex items-center gap-3 mt-3 pt-3 border-t border-green-200">
          <span className="text-xs font-medium text-green-700">Compliance:</span>
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1 text-xs text-green-600">
              <CheckCircle className="w-3 h-3" />
              {passCount} pass
            </span>
            {warnCount > 0 && (
              <span className="flex items-center gap-1 text-xs text-amber-600">
                <AlertTriangle className="w-3 h-3" />
                {warnCount} warn
              </span>
            )}
            {failCount > 0 && (
              <span className="flex items-center gap-1 text-xs text-red-600">
                <XCircle className="w-3 h-3" />
                {failCount} fail
              </span>
            )}
          </div>
        </div>
      )}
    </motion.div>
  );
}
