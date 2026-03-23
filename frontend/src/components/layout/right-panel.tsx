'use client';

import { useState } from 'react';
import { Activity } from 'lucide-react';
import { useGenerationContext } from '@/app/providers';
import { AgentFlowGraph } from '@/components/workflow/agent-flow-graph';
import { AgentDetailPanel } from '@/components/workflow/agent-detail-panel';
import { WorkflowTimeline } from '@/components/workflow/workflow-timeline';
import type { AgentId } from '@/types/agent';

export function RightPanel() {
  const { state } = useGenerationContext();
  const [selectedAgent, setSelectedAgent] = useState<AgentId | null>(null);

  const isActive = state.status === 'generating' || state.status === 'completed';

  return (
    <div className="flex flex-col gap-6 p-6 min-h-full text-white">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-blue-400" />
          <h2 className="text-lg font-semibold text-white">Agent Workflow</h2>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              state.status === 'generating'
                ? 'bg-blue-400 animate-pulse'
                : state.status === 'completed'
                  ? 'bg-green-400'
                  : state.status === 'error'
                    ? 'bg-red-400'
                    : 'bg-gray-500'
            }`}
          />
          <span className="text-sm text-gray-400 capitalize">
            {state.status === 'idle' ? 'Waiting' : state.status}
          </span>
        </div>
      </div>

      {/* Agent Flow Graph */}
      <div className="flex-1 min-h-[400px]">
        <AgentFlowGraph
          agentStates={state.agentStates}
          selectedAgent={selectedAgent}
          onSelectAgent={setSelectedAgent}
        />
      </div>

      {/* Agent Detail Panel */}
      {selectedAgent && (
        <AgentDetailPanel
          agentId={selectedAgent}
          agentState={state.agentStates[selectedAgent] ?? null}
          onClose={() => setSelectedAgent(null)}
        />
      )}

      {/* Workflow Timeline */}
      {isActive && (
        <WorkflowTimeline agentStates={state.agentStates} status={state.status} />
      )}
    </div>
  );
}
