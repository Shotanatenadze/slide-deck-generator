import type { AgentId } from '@/types/agent';

export const AGENT_CONFIG: Record<AgentId, { label: string; description: string; color: string; icon: string }> = {
  orchestrator: { label: 'Orchestrator', description: 'Coordinates all agents', color: '#8B5CF6', icon: 'Brain' },
  portfolio: { label: 'Portfolio Agent', description: 'Parses Excel data', color: '#106280', icon: 'PieChart' },
  market_data: { label: 'Market Data', description: 'Market context analysis', color: '#0EA5E9', icon: 'TrendingUp' },
  deck_builder: { label: 'Deck Builder', description: 'Assembles PPTX', color: '#F59E0B', icon: 'Layers' },
  compliance: { label: 'Compliance', description: 'Regulatory validation', color: '#10B981', icon: 'ShieldCheck' },
};

export const PROMPT_PRESETS = [
  {
    label: 'Full Review',
    prompt:
      'Generate a comprehensive quarterly review deck covering portfolio performance, asset allocation changes, market outlook, and compliance status. Include all standard sections with detailed commentary.',
  },
  {
    label: 'Board Meeting',
    prompt:
      'Create a board-ready presentation focusing on high-level performance metrics, strategic allocation decisions, risk posture, and forward-looking market outlook. Keep it concise and executive-friendly.',
  },
  {
    label: 'Quick Check-in',
    prompt:
      'Prepare a concise check-in deck highlighting portfolio value changes, key allocation shifts, and any compliance flags. Minimal commentary, focus on data.',
  },
  {
    label: 'SMA Deep Dive',
    prompt:
      'Build a detailed SMA portfolio analysis with individual holdings breakdown, duration and yield analytics, sector concentration, credit quality distribution, and maturity ladder.',
  },
];

export const BRAND = {
  primaryBlue: '#106280',
  darkGray: '#394849',
  navy: '#0f2e55',
} as const;

export const WORKFLOW_STAGES = [
  { key: 'upload', label: 'Upload' },
  { key: 'parse', label: 'Parse' },
  { key: 'market', label: 'Market' },
  { key: 'build', label: 'Build' },
  { key: 'compliance', label: 'Compliance' },
  { key: 'done', label: 'Done' },
] as const;
