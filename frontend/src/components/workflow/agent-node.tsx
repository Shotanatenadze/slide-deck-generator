'use client';

import { motion } from 'framer-motion';
import type { LucideProps } from 'lucide-react';
import {
  Brain,
  PieChart,
  TrendingUp,
  Layers,
  ShieldCheck,
  Check,
  X,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { AGENT_CONFIG } from '@/lib/constants';
import type { AgentId, AgentState } from '@/types/agent';

const ICON_MAP: Record<string, React.ComponentType<LucideProps>> = {
  Brain,
  PieChart,
  TrendingUp,
  Layers,
  ShieldCheck,
};

interface AgentNodeProps {
  agentId: AgentId;
  state: AgentState | null;
  isSelected: boolean;
  onSelect: (id: AgentId) => void;
  style?: React.CSSProperties;
}

export function AgentNode({ agentId, state, isSelected, onSelect, style }: AgentNodeProps) {
  const config = AGENT_CONFIG[agentId];
  const status = state?.status ?? 'idle';
  const IconComponent = ICON_MAP[config.icon] ?? Brain;

  const isActive = status === 'started' || status === 'thinking';
  const isToolCall = status === 'tool_call';
  const isCompleted = status === 'completed';
  const isError = status === 'error';
  const isIdle = status === 'idle';

  // Last message from the agent
  const lastMessage = state?.events.length
    ? state.events[state.events.length - 1].message
    : config.description;

  return (
    <motion.div
      layout
      style={style}
      className="absolute -translate-x-1/2 -translate-y-1/2"
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      <motion.button
        onClick={() => onSelect(agentId)}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.98 }}
        className={cn(
          'relative w-[160px] rounded-xl p-3 text-left transition-all duration-300 cursor-pointer',
          'glass-card',
          isSelected && 'ring-2 ring-white/30',
          isIdle && 'opacity-40',
          isActive && 'animate-pulse-ring',
          isCompleted && 'border-green-500/50',
          isError && 'border-red-500/50'
        )}
        style={{
          boxShadow: isActive
            ? `0 0 20px ${config.color}40, 0 0 40px ${config.color}20`
            : isToolCall
              ? `0 0 15px #F59E0B40`
              : isCompleted
                ? `0 0 15px #10B98130`
                : 'none',
        }}
      >
        {/* Status indicator dot */}
        <div className="absolute -top-1 -right-1">
          {isActive && (
            <motion.div
              animate={{ scale: [1, 1.3, 1] }}
              transition={{ repeat: Infinity, duration: 1.5 }}
              className="w-3 h-3 rounded-full bg-blue-400"
            />
          )}
          {isToolCall && (
            <motion.div
              animate={{ opacity: [1, 0.4, 1] }}
              transition={{ repeat: Infinity, duration: 0.6 }}
              className="w-3 h-3 rounded-full bg-amber-400"
            />
          )}
          {isCompleted && (
            <div className="w-3 h-3 rounded-full bg-green-400 flex items-center justify-center">
              <Check className="w-2 h-2 text-white" />
            </div>
          )}
          {isError && (
            <div className="w-3 h-3 rounded-full bg-red-400 flex items-center justify-center">
              <X className="w-2 h-2 text-white" />
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex items-start gap-2.5">
          <div
            className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ backgroundColor: `${config.color}20` }}
          >
            {isActive ? (
              <Loader2 className="w-4 h-4 animate-spin" style={{ color: config.color }} />
            ) : (
              <IconComponent className="w-4 h-4" style={{ color: config.color }} />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-white truncate">{config.label}</p>
            <p className="text-[10px] text-gray-400 truncate mt-0.5" title={lastMessage}>
              {lastMessage}
            </p>
          </div>
        </div>

        {/* Timing */}
        {state?.startTime && (
          <div className="mt-2 pt-2 border-t border-white/5">
            <p className="text-[10px] text-gray-500">
              {state.endTime
                ? `${((state.endTime - state.startTime) / 1000).toFixed(1)}s`
                : 'Running...'}
            </p>
          </div>
        )}
      </motion.button>
    </motion.div>
  );
}
