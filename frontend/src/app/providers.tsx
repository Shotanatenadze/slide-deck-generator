'use client';

import { createContext, useContext, useReducer, useCallback, type ReactNode } from 'react';
import type { AgentEvent, AgentId, AgentState } from '@/types/agent';
import type { GenerationState, GenerationStatus, UploadedFile } from '@/types/generation';

// ── Actions ──────────────────────────────────────────────────────────

type GenerationAction =
  | { type: 'SET_FILES'; files: UploadedFile[] }
  | { type: 'SET_STATUS'; status: GenerationStatus; generationId?: string }
  | { type: 'ADD_AGENT_EVENT'; event: AgentEvent }
  | { type: 'SET_COMPLETED'; complianceReport?: Record<string, unknown> }
  | { type: 'SET_ERROR'; error: string }
  | { type: 'RESET' };

// ── Initial state ────────────────────────────────────────────────────

const initialState: GenerationState = {
  status: 'idle',
  generationId: null,
  uploadedFiles: [],
  agentStates: {},
  complianceReport: null,
  error: null,
};

// ── Reducer ──────────────────────────────────────────────────────────

function generationReducer(state: GenerationState, action: GenerationAction): GenerationState {
  switch (action.type) {
    case 'SET_FILES':
      return { ...state, uploadedFiles: action.files, error: null };

    case 'SET_STATUS':
      return {
        ...state,
        status: action.status,
        generationId: action.generationId ?? state.generationId,
        error: null,
      };

    case 'ADD_AGENT_EVENT': {
      const { event } = action;
      const agentId = event.agent_id as AgentId;
      const existing = state.agentStates[agentId] ?? {
        id: agentId,
        status: 'idle',
        events: [],
      };

      const eventTime = new Date(event.timestamp).getTime();

      const updatedAgent: AgentState = {
        ...existing,
        status: event.status,
        events: [...existing.events, event],
        startTime: event.status === 'started' && !existing.startTime ? eventTime : existing.startTime,
        endTime: event.status === 'completed' || event.status === 'error' ? eventTime : existing.endTime,
      };

      return {
        ...state,
        agentStates: { ...state.agentStates, [agentId]: updatedAgent },
      };
    }

    case 'SET_COMPLETED':
      return {
        ...state,
        status: 'completed',
        complianceReport: action.complianceReport ?? null,
      };

    case 'SET_ERROR':
      return { ...state, status: 'error', error: action.error };

    case 'RESET':
      return initialState;

    default:
      return state;
  }
}

// ── Context ──────────────────────────────────────────────────────────

interface GenerationContextValue {
  state: GenerationState;
  setFiles: (files: UploadedFile[]) => void;
  setStatus: (status: GenerationStatus, generationId?: string) => void;
  addAgentEvent: (event: AgentEvent) => void;
  setCompleted: (complianceReport?: Record<string, unknown>) => void;
  setError: (error: string) => void;
  reset: () => void;
}

const GenerationContext = createContext<GenerationContextValue | null>(null);

export function GenerationProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(generationReducer, initialState);

  const setFiles = useCallback((files: UploadedFile[]) => {
    dispatch({ type: 'SET_FILES', files });
  }, []);

  const setStatus = useCallback((status: GenerationStatus, generationId?: string) => {
    dispatch({ type: 'SET_STATUS', status, generationId });
  }, []);

  const addAgentEvent = useCallback((event: AgentEvent) => {
    dispatch({ type: 'ADD_AGENT_EVENT', event });
  }, []);

  const setCompleted = useCallback((complianceReport?: Record<string, unknown>) => {
    dispatch({ type: 'SET_COMPLETED', complianceReport });
  }, []);

  const setError = useCallback((error: string) => {
    dispatch({ type: 'SET_ERROR', error });
  }, []);

  const reset = useCallback(() => {
    dispatch({ type: 'RESET' });
  }, []);

  return (
    <GenerationContext value={{ state, setFiles, setStatus, addAgentEvent, setCompleted, setError, reset }}>
      {children}
    </GenerationContext>
  );
}

export function useGenerationContext() {
  const ctx = useContext(GenerationContext);
  if (!ctx) {
    throw new Error('useGenerationContext must be used within a GenerationProvider');
  }
  return ctx;
}
