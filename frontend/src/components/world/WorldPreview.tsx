/**
 * Minimal world visualisation.
 *
 * SCOPE — READ BEFORE EXTENDING THIS FILE
 * ---------------------------------------
 * This exists to demonstrate four Phase 2 claims and nothing else:
 *   1. the world exists (24 nodes, 5 zones)
 *   2. roads exist (38 of them)
 *   3. road status changes as the disaster evolves
 *   4. facilities are placed in the world
 *
 * DELIBERATELY ABSENT, because they are Phase 3:
 *   zoom, pan, hover tooltips, click-to-inspect, the MapLegend component,
 *   flood-zone shading, ambulance movement, route overlays, animation.
 *
 * The four static swatches below are a colour key, not the Phase 3 interactive
 * legend — a road-status view with no key is unreadable, which would defeat
 * the point of drawing it. If you find yourself adding interaction here, stop:
 * that work belongs in components/map/ in Phase 3.
 *
 * Everything rendered comes from the backend snapshot. No coordinates,
 * statuses or shapes are invented in the browser.
 */

import { useMemo } from "react";

import type { Hospital, Road, Shelter, WorldNode, Zone } from "@/types";

// Matches MAP_WIDTH_UNITS / MAP_HEIGHT_UNITS in backend/app/config.py.
const VIEW_WIDTH = 1000;
const VIEW_HEIGHT = 700;

// Semantic colours from the design system. Referenced as CSS variables so the
// SVG cannot drift from the rest of the interface.
const ROAD_STROKE: Record<Road["status"], string> = {
  SAFE: "var(--color-safe)",
  RISKY: "var(--color-warn)",
  BLOCKED: "var(--color-crit)",
};

const ROAD_WIDTH: Record<Road["status"], number> = {
  SAFE: 2,
  RISKY: 3,
  BLOCKED: 3.5,
};

interface WorldPreviewProps {
  nodes: WorldNode[];
  zones: Zone[];
  roads: Road[];
  hospitals: Hospital[];
  shelters: Shelter[];
}

export function WorldPreview({
  nodes,
  zones,
  roads,
  hospitals,
  shelters,
}: WorldPreviewProps) {
  const nodeById = useMemo(
    () => new Map(nodes.map((node) => [node.id, node])),
    [nodes],
  );

  const hospitalNodes = useMemo(
    () => new Set(hospitals.map((h) => h.node_id)),
    [hospitals],
  );
  const shelterNodes = useMemo(
    () => new Set(shelters.map((s) => s.node_id)),
    [shelters],
  );

  const counts = useMemo(() => {
    let blocked = 0;
    let risky = 0;
    for (const road of roads) {
      if (road.status === "BLOCKED") blocked += 1;
      else if (road.status === "RISKY") risky += 1;
    }
    return { blocked, risky, safe: roads.length - blocked - risky };
  }, [roads]);

  return (
    <section className="rounded-panel border border-border bg-panel">
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <h2 className="text-2xs font-medium tracking-wide text-fg-muted uppercase">
          World Overview
        </h2>
        <span className="font-mono text-2xs text-fg-muted">
          {nodes.length} nodes &middot; {roads.length} roads
        </span>
      </div>

      <div className="p-3">
        <svg
          viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
          className="h-auto w-full"
          role="img"
          aria-label={`Region overview: ${nodes.length} nodes, ${roads.length} roads, ${counts.blocked} blocked and ${counts.risky} at risk.`}
        >
          {/* Zones, drawn first so everything else sits above them. */}
          {zones.map((zone) => (
            <polygon
              key={zone.id}
              points={zone.polygon.map(([x, y]) => `${x},${y}`).join(" ")}
              fill="var(--color-panel-2)"
              stroke="var(--color-border)"
              strokeWidth={1}
            />
          ))}

          {zones.map((zone) => {
            const [first] = zone.polygon;
            if (!first) return null;
            return (
              <text
                key={`${zone.id}-label`}
                x={first[0] + 10}
                y={first[1] + 20}
                fill="var(--color-fg-muted)"
                fontSize={13}
                fontFamily="var(--font-mono)"
              >
                {zone.name}
              </text>
            );
          })}

          {roads.map((road) => {
            const from = nodeById.get(road.source);
            const to = nodeById.get(road.destination);
            if (!from || !to) return null;
            return (
              <line
                key={road.id}
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
                stroke={ROAD_STROKE[road.status]}
                strokeWidth={ROAD_WIDTH[road.status]}
                strokeLinecap="round"
                // Blocked roads are dashed as well as red, so status survives a
                // monochrome projector and a colour-blind viewer.
                strokeDasharray={road.status === "BLOCKED" ? "6 5" : undefined}
                opacity={road.status === "SAFE" ? 0.55 : 0.95}
              />
            );
          })}

          {nodes.map((node) => {
            const isHospital = hospitalNodes.has(node.id);
            const isShelter = shelterNodes.has(node.id);

            if (isHospital) {
              return (
                <rect
                  key={node.id}
                  x={node.x - 6}
                  y={node.y - 6}
                  width={12}
                  height={12}
                  fill="var(--color-info)"
                  stroke="var(--color-bg)"
                  strokeWidth={1.5}
                />
              );
            }
            if (isShelter) {
              return (
                <polygon
                  key={node.id}
                  points={`${node.x},${node.y - 7} ${node.x + 7},${node.y + 5} ${node.x - 7},${node.y + 5}`}
                  fill="var(--color-safe)"
                  stroke="var(--color-bg)"
                  strokeWidth={1.5}
                />
              );
            }
            return (
              <circle
                key={node.id}
                cx={node.x}
                cy={node.y}
                r={3.5}
                fill="var(--color-fg-muted)"
              />
            );
          })}
        </svg>

        {/* Static colour key. Not the Phase 3 interactive MapLegend. */}
        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 border-t border-border pt-3">
          <KeyItem colour="var(--color-safe)" label={`Safe ${counts.safe}`} />
          <KeyItem colour="var(--color-warn)" label={`Risky ${counts.risky}`} />
          <KeyItem colour="var(--color-crit)" label={`Blocked ${counts.blocked}`} />
          <KeyItem colour="var(--color-info)" label="Hospital" shape="square" />
          <KeyItem colour="var(--color-safe)" label="Shelter" shape="triangle" />
        </div>
      </div>
    </section>
  );
}

function KeyItem({
  colour,
  label,
  shape = "line",
}: {
  colour: string;
  label: string;
  shape?: "line" | "square" | "triangle";
}) {
  return (
    <span className="flex items-center gap-1.5">
      <svg width={14} height={10} aria-hidden="true">
        {shape === "line" && (
          <line x1={0} y1={5} x2={14} y2={5} stroke={colour} strokeWidth={2.5} />
        )}
        {shape === "square" && (
          <rect x={3} y={1} width={8} height={8} fill={colour} />
        )}
        {shape === "triangle" && (
          <polygon points="7,1 12,9 2,9" fill={colour} />
        )}
      </svg>
      <span className="font-mono text-2xs text-fg-muted">{label}</span>
    </span>
  );
}
