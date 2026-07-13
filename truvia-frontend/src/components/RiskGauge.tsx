"use client";

import { severityStroke } from "@/lib/format";

export function RiskGauge({
  value,
  severity,
  size = 128,
}: {
  value: number;
  severity?: string;
  size?: number;
}) {
  const r = 45;
  const circumference = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(100, value));
  const offset = circumference - (circumference * clamped) / 100;
  const stroke = severityStroke(severity);

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg className="w-full h-full -rotate-90" viewBox="0 0 128 128">
        <circle
          className="text-surface-container-high"
          cx="64"
          cy="64"
          fill="transparent"
          r={r}
          stroke="currentColor"
          strokeWidth="8"
        />
        <circle
          cx="64"
          cy="64"
          fill="transparent"
          r={r}
          stroke={stroke}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 1s ease-out", filter: `drop-shadow(0 0 8px ${stroke})` }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="text-headline-lg font-bold"
          style={{ color: stroke, textShadow: `0 0 10px ${stroke}55` }}
        >
          {Math.round(clamped)}%
        </span>
        <span className="font-label-md text-on-surface-variant uppercase text-[10px]">Risk</span>
      </div>
    </div>
  );
}
