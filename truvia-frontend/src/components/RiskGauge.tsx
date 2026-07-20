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
  const isCritical = (severity || "").toLowerCase() === "critical";

  return (
    <div
      className={`relative rounded-full${isCritical ? " critical-glow" : ""}`}
      style={{ width: size, height: size }}
    >
      <svg className="w-full h-full -rotate-90" viewBox="0 0 128 128">
        <circle
          cx="64"
          cy="64"
          fill="transparent"
          r={r}
          stroke="#343538"
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
          className="font-heading text-headline-lg font-bold"
          style={{ color: stroke, textShadow: `0 0 10px ${stroke}55` }}
        >
          {Math.round(clamped)}%
        </span>
        <span className="text-outline text-[10px] uppercase tracking-widest">Risk</span>
      </div>
    </div>
  );
}
