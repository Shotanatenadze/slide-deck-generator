'use client';

import { motion } from 'framer-motion';

interface DataFlowParticleProps {
  from: { x: number; y: number };
  to: { x: number; y: number };
  color: string;
  delay?: number;
  duration?: number;
}

export function DataFlowParticle({
  from,
  to,
  color,
  delay = 0,
  duration = 1.8,
}: DataFlowParticleProps) {
  return (
    <motion.circle
      r={3}
      fill={color}
      filter="url(#glow)"
      initial={{ cx: from.x, cy: from.y, opacity: 0 }}
      animate={{
        cx: [from.x, to.x],
        cy: [from.y, to.y],
        opacity: [0, 1, 1, 0],
      }}
      transition={{
        duration,
        delay,
        repeat: Infinity,
        ease: 'linear',
      }}
    />
  );
}
