import type { AgentState } from './agent';

export type GenerationStatus = 'idle' | 'uploading' | 'generating' | 'completed' | 'error';

export interface UploadedFile {
  name: string;
  size: number;
  type: 'board_report' | 'holdings' | 'pdf' | 'unknown';
}

export interface GenerationState {
  status: GenerationStatus;
  generationId: string | null;
  uploadedFiles: UploadedFile[];
  agentStates: Record<string, AgentState>;
  complianceReport: Record<string, unknown> | null;
  error: string | null;
}
