'use client';

import { motion } from 'framer-motion';
import { Globe } from 'lucide-react';

const MAX_CHARS = 2000;

interface MarketContextInputProps {
  value: string;
  onChange: (value: string) => void;
}

export function MarketContextInput({ value, onChange }: MarketContextInputProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.05 }}
    >
      <div className="flex items-center gap-2 mb-2">
        <Globe className="w-4 h-4 text-gray-500" />
        <label className="text-sm font-medium text-gray-700">
          Market Context
        </label>
        <span className="text-xs text-gray-400 ml-auto">Optional</span>
      </div>

      <div className="relative">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value.slice(0, MAX_CHARS))}
          placeholder="Enter market commentary, macro outlook, or relevant context that should be incorporated into the deck's market update section..."
          className="w-full min-h-[100px] rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-800 placeholder:text-gray-400 resize-y focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-300 transition-all"
          rows={4}
        />
        <div className="flex justify-end mt-1">
          <span className="text-xs text-gray-400">
            {value.length}/{MAX_CHARS}
          </span>
        </div>
      </div>
    </motion.div>
  );
}
