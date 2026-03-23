'use client';

interface AgentEdgeProps {
  from: { x: number; y: number };
  to: { x: number; y: number };
  status: 'inactive' | 'active' | 'completed';
}

export function AgentEdge({ from, to, status }: AgentEdgeProps) {
  // Use a simple straight line — clean and avoids crossing artifacts
  const pathD = `M ${from.x} ${from.y} L ${to.x} ${to.y}`;

  const strokeColor =
    status === 'completed'
      ? '#10B981'
      : status === 'active'
        ? '#3B82F6'
        : '#374151';

  const strokeOpacity = status === 'inactive' ? 0.25 : 0.8;

  return (
    <g>
      {/* Base path */}
      <path
        d={pathD}
        fill="none"
        stroke={strokeColor}
        strokeWidth={status === 'inactive' ? 1 : 2}
        strokeOpacity={strokeOpacity}
        strokeDasharray={status === 'inactive' ? '4 4' : 'none'}
        strokeLinecap="round"
      />

      {/* Animated dash overlay for active edges */}
      {status === 'active' && (
        <path
          d={pathD}
          fill="none"
          stroke="#60A5FA"
          strokeWidth={2}
          strokeOpacity={0.6}
          strokeDasharray="6 14"
          strokeLinecap="round"
          className="animate-dash-flow"
        />
      )}
    </g>
  );
}
