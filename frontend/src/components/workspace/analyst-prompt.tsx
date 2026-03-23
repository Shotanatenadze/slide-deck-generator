'use client';

import { motion } from 'framer-motion';
import { MessageSquare, User } from 'lucide-react';
import { PROMPT_PRESETS } from '@/lib/constants';

interface AnalystPromptProps {
  prompt: string;
  onPromptChange: (value: string) => void;
  clientName: string;
  onClientNameChange: (value: string) => void;
}

export function AnalystPrompt({
  prompt,
  onPromptChange,
  clientName,
  onClientNameChange,
}: AnalystPromptProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.1 }}
      className="flex flex-col gap-4"
    >
      {/* Client name */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <User className="w-4 h-4 text-gray-500" />
          <label className="text-sm font-medium text-gray-700">Client Name</label>
        </div>
        <input
          type="text"
          value={clientName}
          onChange={(e) => onClientNameChange(e.target.value)}
          placeholder="Enter client name"
          className="w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-300 transition-all"
        />
      </div>

      {/* Analyst prompt */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <MessageSquare className="w-4 h-4 text-gray-500" />
          <label className="text-sm font-medium text-gray-700">Analyst Prompt</label>
        </div>

        {/* Preset buttons */}
        <div className="flex flex-wrap gap-1.5 mb-2">
          {PROMPT_PRESETS.map((preset) => (
            <button
              key={preset.label}
              onClick={() => onPromptChange(preset.prompt)}
              className="px-2.5 py-1 text-xs font-medium rounded-md border border-gray-200 text-gray-600 hover:text-gray-800 hover:bg-gray-50 transition-colors"
            >
              {preset.label}
            </button>
          ))}
        </div>

        <textarea
          value={prompt}
          onChange={(e) => onPromptChange(e.target.value)}
          placeholder="Describe what you want in the deck: emphasis areas, visual preferences, specific data points to highlight..."
          className="w-full min-h-[120px] rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-800 placeholder:text-gray-400 resize-y focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-300 transition-all"
          rows={5}
        />
      </div>
    </motion.div>
  );
}
