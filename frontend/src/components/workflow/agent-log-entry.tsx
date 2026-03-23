'use client';

import { motion } from 'framer-motion';
import { Brain, Wrench, CheckCircle, AlertCircle, MessageSquare } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { AgentEvent } from '@/types/agent';

const STATUS_CONFIG: Record<
  string,
  { color: string; borderColor: string; Icon: React.ComponentType<{ className?: string }> }
> = {
  started: { color: 'text-blue-400', borderColor: 'border-blue-400', Icon: MessageSquare },
  thinking: { color: 'text-blue-400', borderColor: 'border-blue-400', Icon: Brain },
  tool_call: { color: 'text-amber-400', borderColor: 'border-amber-400', Icon: Wrench },
  tool_result: { color: 'text-emerald-400', borderColor: 'border-emerald-400', Icon: CheckCircle },
  completed: { color: 'text-green-400', borderColor: 'border-green-400', Icon: CheckCircle },
  error: { color: 'text-red-400', borderColor: 'border-red-400', Icon: AlertCircle },
};

function getRelativeTime(timestamp: string): string {
  const diff = Date.now() - new Date(timestamp).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 5) return 'just now';
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  return `${Math.floor(minutes / 60)}h ago`;
}

interface AgentLogEntryProps {
  event: AgentEvent;
  index: number;
}

export function AgentLogEntry({ event, index }: AgentLogEntryProps) {
  const config = STATUS_CONFIG[event.status] ?? STATUS_CONFIG.started;
  const { Icon, color, borderColor } = config;

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.25, delay: index * 0.05 }}
      className={cn(
        'flex items-start gap-3 pl-3 py-2 border-l-2 rounded-r-lg',
        borderColor,
        'bg-white/[0.02] hover:bg-white/[0.04] transition-colors'
      )}
    >
      <Icon className={cn('w-4 h-4 mt-0.5 flex-shrink-0', color)} />
      <div className="flex-1 min-w-0">
        <p className="text-xs text-gray-300 leading-relaxed">{event.message}</p>
        {event.detail && (
          <pre className="mt-1 text-[10px] text-gray-500 font-mono overflow-hidden text-ellipsis">
            {JSON.stringify(event.detail, null, 2).slice(0, 200)}
          </pre>
        )}
      </div>
    </motion.div>
  );
}
