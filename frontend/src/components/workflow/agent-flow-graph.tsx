'use client';

import { useRef, useState, useEffect } from 'react';
import { AgentNode } from './agent-node';
import { AgentEdge } from './agent-edge';
import { DataFlowParticle } from './data-flow-particle';
import { AGENT_CONFIG } from '@/lib/constants';
import type { AgentId, AgentState } from '@/types/agent';

// Node positions as percentages of the container
const NODE_POSITIONS: Record<AgentId, { x: number; y: number }> = {
  orchestrator: { x: 50, y: 8 },
  portfolio: { x: 22, y: 38 },
  market_data: { x: 78, y: 38 },
  deck_builder: { x: 50, y: 65 },
  compliance: { x: 50, y: 90 },
};

// Edge definitions: from → to
const EDGES: { from: AgentId; to: AgentId }[] = [
  { from: 'orchestrator', to: 'portfolio' },
  { from: 'orchestrator', to: 'market_data' },
  { from: 'portfolio', to: 'deck_builder' },
  { from: 'market_data', to: 'deck_builder' },
  { from: 'deck_builder', to: 'compliance' },
];

/**
 * Edge status is determined by the TARGET node's state.
 * Data flows TO the target, so:
 * - inactive: target hasn't started yet
 * - active: target is currently running
 * - completed: target has completed
 */
function getEdgeStatus(
  fromId: AgentId,
  toId: AgentId,
  agentStates: Record<string, AgentState>
): 'inactive' | 'active' | 'completed' {
  const fromState = agentStates[fromId];
  const toState = agentStates[toId];

  // Source hasn't even started — edge can't be active
  if (!fromState || fromState.status === 'idle') return 'inactive';

  // Target status drives the edge
  if (!toState || toState.status === 'idle') {
    // Source is running but target hasn't started — show as inactive
    // EXCEPT: if source is completed, show as "ready" (still inactive visually)
    return 'inactive';
  }

  if (toState.status === 'completed') return 'completed';
  if (toState.status === 'error') return 'inactive';

  // Target is running (started/thinking/tool_call/tool_result)
  return 'active';
}

interface AgentFlowGraphProps {
  agentStates: Record<string, AgentState>;
  selectedAgent: AgentId | null;
  onSelectAgent: (id: AgentId) => void;
}

export function AgentFlowGraph({
  agentStates,
  selectedAgent,
  onSelectAgent,
}: AgentFlowGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setSize({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const getPixelPos = (pos: { x: number; y: number }) => ({
    x: (pos.x / 100) * size.width,
    y: (pos.y / 100) * size.height,
  });

  const agentIds = Object.keys(NODE_POSITIONS) as AgentId[];

  return (
    <div ref={containerRef} className="relative w-full h-full min-h-[400px]">
      {/* SVG layer for edges and particles */}
      {size.width > 0 && size.height > 0 && (
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none"
          viewBox={`0 0 ${size.width} ${size.height}`}
        >
          <defs>
            <filter id="glow">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Edges */}
          {EDGES.map(({ from, to }) => {
            const fromPos = getPixelPos(NODE_POSITIONS[from]);
            const toPos = getPixelPos(NODE_POSITIONS[to]);
            const status = getEdgeStatus(from, to, agentStates);

            return (
              <AgentEdge
                key={`${from}-${to}`}
                from={fromPos}
                to={toPos}
                status={status}
              />
            );
          })}

          {/* Data flow particles on active edges */}
          {EDGES.map(({ from, to }) => {
            const status = getEdgeStatus(from, to, agentStates);
            if (status !== 'active') return null;

            const fromPos = getPixelPos(NODE_POSITIONS[from]);
            const toPos = getPixelPos(NODE_POSITIONS[to]);
            const color = AGENT_CONFIG[to].color;

            return [0, 0.7, 1.4].map((delay, i) => (
              <DataFlowParticle
                key={`particle-${from}-${to}-${i}`}
                from={fromPos}
                to={toPos}
                color={color}
                delay={delay}
                duration={1.8}
              />
            ));
          })}
        </svg>
      )}

      {/* Agent nodes */}
      {agentIds.map((id) => {
        const pos = NODE_POSITIONS[id];
        return (
          <AgentNode
            key={id}
            agentId={id}
            state={agentStates[id] ?? null}
            isSelected={selectedAgent === id}
            onSelect={onSelectAgent}
            style={{
              left: `${pos.x}%`,
              top: `${pos.y}%`,
            }}
          />
        );
      })}
    </div>
  );
}
