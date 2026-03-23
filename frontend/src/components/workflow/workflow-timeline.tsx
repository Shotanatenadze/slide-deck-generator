'use client';

import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { WORKFLOW_STAGES } from '@/lib/constants';
import type { AgentState } from '@/types/agent';
import type { GenerationStatus } from '@/types/generation';

// Map workflow stages to agent statuses
function getStageStatus(
  stageKey: string,
  agentStates: Record<string, AgentState>,
  generationStatus: GenerationStatus
): 'pending' | 'active' | 'completed' {
  switch (stageKey) {
    case 'upload':
      // Upload stage is completed once we're generating
      if (generationStatus === 'generating' || generationStatus === 'completed') return 'completed';
      if (generationStatus === 'uploading') return 'active';
      return 'pending';

    case 'parse': {
      const portfolio = agentStates.portfolio;
      if (portfolio?.status === 'completed') return 'completed';
      if (portfolio && portfolio.status !== 'idle') return 'active';
      return 'pending';
    }

    case 'market': {
      const market = agentStates.market_data;
      if (market?.status === 'completed') return 'completed';
      if (market && market.status !== 'idle') return 'active';
      return 'pending';
    }

    case 'build': {
      const builder = agentStates.deck_builder;
      if (builder?.status === 'completed') return 'completed';
      if (builder && builder.status !== 'idle') return 'active';
      return 'pending';
    }

    case 'compliance': {
      const compliance = agentStates.compliance;
      if (compliance?.status === 'completed') return 'completed';
      if (compliance && compliance.status !== 'idle') return 'active';
      return 'pending';
    }

    case 'done':
      if (generationStatus === 'completed') return 'completed';
      return 'pending';

    default:
      return 'pending';
  }
}

interface WorkflowTimelineProps {
  agentStates: Record<string, AgentState>;
  status: GenerationStatus;
}

export function WorkflowTimeline({ agentStates, status }: WorkflowTimelineProps) {
  return (
    <div className="glass-card p-4">
      <div className="flex items-center gap-1">
        {WORKFLOW_STAGES.map((stage, index) => {
          const stageStatus = getStageStatus(stage.key, agentStates, status);
          const isLast = index === WORKFLOW_STAGES.length - 1;

          return (
            <div key={stage.key} className="flex items-center flex-1">
              {/* Stage dot and label */}
              <div className="flex flex-col items-center gap-1.5 min-w-0">
                <motion.div
                  className={cn(
                    'w-3 h-3 rounded-full border-2 transition-colors duration-500',
                    stageStatus === 'completed'
                      ? 'bg-green-400 border-green-400'
                      : stageStatus === 'active'
                        ? 'bg-blue-400 border-blue-400 animate-pulse'
                        : 'bg-transparent border-gray-600'
                  )}
                  initial={false}
                  animate={
                    stageStatus === 'completed'
                      ? { scale: [1, 1.3, 1] }
                      : { scale: 1 }
                  }
                  transition={{ duration: 0.3 }}
                />
                <span
                  className={cn(
                    'text-[10px] font-medium whitespace-nowrap',
                    stageStatus === 'completed'
                      ? 'text-green-400'
                      : stageStatus === 'active'
                        ? 'text-blue-400'
                        : 'text-gray-500'
                  )}
                >
                  {stage.label}
                </span>
              </div>

              {/* Connector line */}
              {!isLast && (
                <div className="flex-1 h-px mx-1 mt-[-16px]">
                  <div
                    className={cn(
                      'h-full transition-colors duration-500',
                      stageStatus === 'completed' ? 'bg-green-400/50' : 'bg-gray-700'
                    )}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
