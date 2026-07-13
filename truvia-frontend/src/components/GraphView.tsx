"use client";

import { useMemo } from "react";
import type { GraphNode, GraphEdge } from "@/lib/types";

const TYPE_COLOR: Record<string, string> = {
  phone: "#c1c1ff",
  upi: "#edc221",
  domain: "#adaefe",
  email: "#908fa0",
  ip: "#5d5fef",
  device: "#c1c1ff",
};

function colorForNode(n: GraphNode): string {
  if (n.risk_score >= 80) return "#ffb4ab";
  return TYPE_COLOR[n.type] ?? "#c1c1ff";
}

interface Positioned extends GraphNode {
  x: number;
  y: number;
  r: number;
}

const W = 1000;
const H = 620;

function computeLayout(nodes: GraphNode[]): Positioned[] {
  const groups = Array.from(new Set(nodes.map((n) => n.group)));
  const groupCenters = new Map<number, { cx: number; cy: number }>();
  const gcount = groups.length;
  const ringR = Math.min(W, H) * 0.34;
  groups.forEach((g, i) => {
    if (gcount === 1) {
      groupCenters.set(g, { cx: W / 2, cy: H / 2 });
    } else {
      const angle = (i / gcount) * Math.PI * 2;
      groupCenters.set(g, {
        cx: W / 2 + Math.cos(angle) * ringR,
        cy: H / 2 + Math.sin(angle) * ringR,
      });
    }
  });

  const byGroup = new Map<number, GraphNode[]>();
  nodes.forEach((n) => {
    if (!byGroup.has(n.group)) byGroup.set(n.group, []);
    byGroup.get(n.group)!.push(n);
  });

  const positioned: Positioned[] = [];
  byGroup.forEach((members, g) => {
    const center = groupCenters.get(g)!;
    const localR = Math.min(140, 24 + members.length * 9);
    members.forEach((n, i) => {
      const angle = (i / Math.max(1, members.length)) * Math.PI * 2;
      const jitter = members.length === 1 ? 0 : localR;
      positioned.push({
        ...n,
        x: center.cx + Math.cos(angle) * jitter,
        y: center.cy + Math.sin(angle) * jitter,
        r: 8 + (n.risk_score / 100) * 14,
      });
    });
  });
  return positioned;
}

export function GraphView({
  nodes,
  edges,
  selectedId,
  onSelect,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedId?: string | null;
  onSelect: (id: string) => void;
}) {
  const positioned = useMemo(() => computeLayout(nodes), [nodes]);
  const posMap = useMemo(() => {
    const m = new Map<string, Positioned>();
    positioned.forEach((p) => m.set(p.id, p));
    return m;
  }, [positioned]);

  if (nodes.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center text-on-surface-variant font-body-md">
        No entities in the graph yet.
      </div>
    );
  }

  return (
    <svg className="w-full h-full" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet">
      <defs>
        <linearGradient id="edgeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#5d5fef" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#c1c1ff" stopOpacity="0.3" />
        </linearGradient>
      </defs>
      {edges.map((e, i) => {
        const a = posMap.get(e.source);
        const b = posMap.get(e.target);
        if (!a || !b) return null;
        return (
          <line
            key={i}
            x1={a.x}
            y1={a.y}
            x2={b.x}
            y2={b.y}
            stroke="url(#edgeGrad)"
            strokeWidth={Math.min(3, 0.5 + e.weight * 0.5)}
          />
        );
      })}
      {positioned.map((n) => {
        const selected = n.id === selectedId;
        const color = colorForNode(n);
        return (
          <g
            key={n.id}
            className="cursor-pointer"
            onClick={() => onSelect(n.id)}
            style={{ transition: "all 0.2s" }}
          >
            <circle
              cx={n.x}
              cy={n.y}
              r={selected ? n.r + 4 : n.r}
              fill={color}
              fillOpacity={selected ? 1 : 0.85}
              stroke={selected ? "#ffffff" : color}
              strokeWidth={selected ? 3 : 1}
              style={{ filter: `drop-shadow(0 0 ${selected ? 12 : 6}px ${color})` }}
            />
            {(n.r > 14 || selected) && (
              <text
                x={n.x}
                y={n.y + n.r + 12}
                textAnchor="middle"
                fill="#c7c4d7"
                fontSize="10"
                fontFamily="JetBrains Mono, monospace"
              >
                {n.label.length > 16 ? n.label.slice(0, 14) + "…" : n.label}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
