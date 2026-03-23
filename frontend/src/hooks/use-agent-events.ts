'use client';

import { useMemo } from 'react';
import type { AgentEvent, AgentId, AgentState } from '@/types/agent';

const AGENT_IDS: AgentId[] = ['orchestrator', 'portfolio', 'market_data', 'deck_builder', 'compliance'];

export function useAgentEvents(agentEvents: AgentEvent[]) {
  const agentStates = useMemo(() => {
    const states: Record<AgentId, AgentState> = {} as Record<AgentId, AgentState>;

    // Initialize all agents with idle state
    for (const id of AGENT_IDS) {
      states[id] = {
        id,
        status: 'idle',
        events: [],
        startTime: undefined,
        endTime: undefined,
      };
    }

    // Group events by agent and derive state
    for (const event of agentEvents) {
      const agentId = event.agent_id;
      if (!states[agentId]) continue;

      states[agentId].events.push(event);

      // Update status to the latest event status
      states[agentId].status = event.status;

      // Track timing
      const eventTime = new Date(event.timestamp).getTime();
      if (event.status === 'started' && !states[agentId].startTime) {
        states[agentId].startTime = eventTime;
      }
      if (event.status === 'completed' || event.status === 'error') {
        states[agentId].endTime = eventTime;
      }
    }

    return states;
  }, [agentEvents]);

  return { agentStates };
}
