"use client";

/**
 * Module 6 — Geospatial Priority MAP view (additive; the ranked table is unchanged).
 *
 * A lightweight Leaflet map centered on India. Each city returned by
 * GET /api/v1/geo/priority renders as a CircleMarker whose radius + color reflect
 * the SAME `priority_score` shown in the table. Clicking a marker opens a popup with
 * the same fields as the table row (score, trend, dominant category, complaints) and
 * the same ?city= drill-through into /reports.
 *
 * CircleMarker (SVG) is used deliberately so we don't depend on Leaflet's default
 * marker image assets. Loaded client-side only (dynamic import, ssr:false) since
 * Leaflet touches `window`.
 */
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import type { GeoPriorityRow } from "@/lib/types";
import { coordsForCity } from "@/lib/cityCoords";

const INDIA_CENTER: [number, number] = [22.9734, 78.6569];

// Color by priority score — reuses the app's severity palette feel.
function scoreColor(score: number): string {
  if (score >= 75) return "#D6303C"; // error / critical
  if (score >= 50) return "#E8A33D"; // tertiary / high
  if (score >= 25) return "#4da2ff"; // secondary / moderate
  return "#8d90a0"; // outline / low
}

// Radius scales with score (6px min → 24px max) so hotspots read bigger.
function scoreRadius(score: number): number {
  return 6 + (Math.max(0, Math.min(100, score)) / 100) * 18;
}

function trendLabel(trend: string): string {
  if (trend === "rising") return "▲ Rising";
  if (trend === "falling") return "▼ Falling";
  return "▬ Stable";
}

export default function GeoMap({
  rows,
  onCityClick,
}: {
  rows: GeoPriorityRow[];
  onCityClick?: (city: string) => void;
}) {
  const located = rows
    .map((r) => ({ row: r, coords: coordsForCity(r.city) }))
    .filter((x): x is { row: GeoPriorityRow; coords: [number, number] } => x.coords !== null);

  const unlocatedCount = rows.length - located.length;

  return (
    <div className="relative h-full w-full">
      <MapContainer
        center={INDIA_CENTER}
        zoom={5}
        scrollWheelZoom
        style={{ height: "100%", width: "100%", background: "#0f1012" }}
        className="rounded-xl"
      >
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        {located.map(({ row, coords }) => (
          <CircleMarker
            key={row.city}
            center={coords}
            radius={scoreRadius(row.priority_score)}
            pathOptions={{
              color: scoreColor(row.priority_score),
              fillColor: scoreColor(row.priority_score),
              fillOpacity: 0.55,
              weight: 1.5,
            }}
            eventHandlers={onCityClick ? { click: () => onCityClick(row.city) } : undefined}
          >
            <Popup>
              <div style={{ minWidth: 180, color: "#111", fontSize: 13, lineHeight: 1.5 }}>
                <div style={{ fontWeight: 700, fontSize: 14 }}>{row.city}</div>
                <div>
                  Priority score: <b>{row.priority_score}</b>
                </div>
                <div>Trend: {trendLabel(row.trend)}</div>
                <div>Dominant: {row.dominant_category || "—"}</div>
                <div>Complaints: {row.complaint_count}</div>
                {onCityClick && (
                  <button
                    onClick={() => onCityClick(row.city)}
                    style={{
                      marginTop: 6,
                      color: "#2563eb",
                      textDecoration: "underline",
                      background: "none",
                      border: "none",
                      padding: 0,
                      cursor: "pointer",
                      fontSize: 12,
                    }}
                  >
                    View complaints →
                  </button>
                )}
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
      {unlocatedCount > 0 && (
        <div className="absolute bottom-2 left-2 z-[1000] bg-surface-container-high/90 text-on-surface-variant text-[11px] px-2 py-1 rounded-md pointer-events-none">
          {unlocatedCount} city(ies) without map coordinates — see table
        </div>
      )}
    </div>
  );
}
