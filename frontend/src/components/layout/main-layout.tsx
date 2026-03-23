'use client';

import { useState, useCallback, useRef } from 'react';
import { LeftPanel } from './left-panel';
import { RightPanel } from './right-panel';

export function MainLayout() {
  const [leftWidth, setLeftWidth] = useState(45); // percentage
  const isDragging = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleMouseDown = useCallback(() => {
    isDragging.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging.current || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const pct = ((e.clientX - rect.left) / rect.width) * 100;
    setLeftWidth(Math.min(70, Math.max(25, pct)));
  }, []);

  const handleMouseUp = useCallback(() => {
    isDragging.current = false;
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }, []);

  return (
    <div
      ref={containerRef}
      className="flex h-screen w-full overflow-hidden"
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* Left panel - workspace */}
      <div
        className="h-full overflow-y-auto bg-white"
        style={{ width: `${leftWidth}%`, minWidth: 400 }}
      >
        <LeftPanel />
      </div>

      {/* Drag handle */}
      <div
        onMouseDown={handleMouseDown}
        className="w-1.5 flex-shrink-0 bg-gray-200 hover:bg-blue-400 active:bg-blue-500 transition-colors cursor-col-resize"
      />

      {/* Right panel - agent workflow */}
      <div className="flex-1 h-full overflow-y-auto gradient-dark">
        <RightPanel />
      </div>
    </div>
  );
}
