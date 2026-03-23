export type AgentId = 'orchestrator' | 'portfolio' | 'market_data' | 'compliance' | 'deck_builder';
export type AgentStatus = 'idle' | 'started' | 'thinking' | 'tool_call' | 'tool_result' | 'completed' | 'error';

export interface AgentEvent {
  generation_id: string;
  agent_id: AgentId;
  status: AgentStatus;
  message: string;
  detail?: Record<string, unknown>;
  timestamp: string;
}

export interface AgentState {
  id: AgentId;
  status: AgentStatus;
  events: AgentEvent[];
  startTime?: number;
  endTime?: number;
}
