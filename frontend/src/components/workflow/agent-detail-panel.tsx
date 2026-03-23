'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { X, Clock } from 'lucide-react';
import { AGENT_CONFIG } from '@/lib/constants';
import { AgentLogEntry } from './agent-log-entry';
import type { AgentId, AgentState } from '@/types/agent';

interface AgentDetailPanelProps {
  agentId: AgentId;
  agentState: AgentState | null;
  onClose: () => void;
}

export function AgentDetailPanel({ agentId, agentState, onClose }: AgentDetailPanelProps) {
  const config = AGENT_CONFIG[agentId];
  const events = agentState?.events ?? [];
  const status = agentState?.status ?? 'idle';

  const elapsed =
    agentState?.startTime && agentState?.endTime
      ? ((agentState.endTime - agentState.startTime) / 1000).toFixed(1)
      : agentState?.startTime
        ? ((Date.now() - agentState.startTime) / 1000).toFixed(1)
        : null;

  return (
    <AnimatePresence>
      <motion.div
        key={agentId}
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: 'auto' }}
        exit={{ opacity: 0, height: 0 }}
        transition={{ duration: 0.3 }}
        className="glass-card overflow-hidden"
      >
        <div className="p-4">
          {/* Header */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: config.color }}
              />
              <h3 className="text-sm font-semibold text-white">{config.label}</h3>
              <span className="text-xs text-gray-400 capitalize px-2 py-0.5 rounded-full bg-white/5">
                {status}
              </span>
            </div>
            <div className="flex items-center gap-3">
              {elapsed && (
                <span className="flex items-center gap-1 text-xs text-gray-400">
                  <Clock className="w-3 h-3" />
                  {elapsed}s
                </span>
              )}
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Events list */}
          <div className="space-y-1.5 max-h-[200px] overflow-y-auto pr-1">
            {events.length === 0 ? (
              <p className="text-xs text-gray-500 py-4 text-center">
                No events yet
              </p>
            ) : (
              events.map((event, i) => (
                <AgentLogEntry key={`${event.timestamp}-${i}`} event={event} index={i} />
              ))
            )}
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
