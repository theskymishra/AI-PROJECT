/**
 * Interactive disaster map.
 *
 * Replaces the minimal Phase 2 WorldPreview. Everything drawn comes from the
 * backend snapshot: node coordinates, road status, zone flood levels,
 * ambulance and emergency positions. No geometry is invented in the browser
 * and no state is simulated here.
 *
 * INTERACTION
 *   wheel / pinch      zoom, anchored on the pointer
 *   drag               pan
 *   hover              highlight plus a name label
 *   click              select, opening the detail panel
 *   buttons            zoom in / out / reset, for keyboard and projector use
 *
 * The viewBox arithmetic lives in geometry.ts and is unit tested there.
 *
 * TWO MODES
 *   interactive        the full map page
 *   static             the dashboard embed: same rendering, no controls, no
 *                      pointer handlers. One implementation, two presentations
 *                      -- so the dashboard map can never drift from the real one.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { MapControls } from "@/components/map/MapControls";
import { MapDetailPanel } from "@/components/map/MapDetailPanel";
import type { Selection } from "@/components/map/MapDetailPanel";
import { MapLegend } from "@/components/map/MapLegend";
import {
  FULL_VIEW,
  MAX_ZOOM,
  MIN_ZOOM,
  clampView,
  panByScreenDelta,
  screenScale,
  screenToWorld,
  viewBoxToString,
  zoomAt,
  zoomLevel,
} from "@/components/map/geometry";
import type { ViewBox } from "@/components/map/geometry";
import type {
  Ambulance,
  Emergency,
  Hospital,
  Road,
  Shelter,
  WorldNode,
  Zone,
} from "@/types";

const ROAD_STROKE: Record<Road["status"], string> = {
  SAFE: "var(--color-safe)",
  RISKY: "var(--color-warn)",
  BLOCKED: "var(--color-crit)",
};

const ROAD_DASH: Record<Road["status"], string | undefined> = {
  SAFE: undefined,
  RISKY: "5 4",
  BLOCKED: "6 5",
};

const ROAD_BASE_WIDTH: Record<Road["status"], number> = {
  SAFE: 2,
  RISKY: 3,
  BLOCKED: 3.5,
};

export interface DisasterMapProps {
  nodes: WorldNode[];
  zones: Zone[];
  roads: Road[];
  hospitals: Hospital[];
  shelters: Shelter[];
  ambulances: Ambulance[];
  emergencies: Emergency[];
  /** Full map page when true; dashboard embed when false. */
  interactive?: boolean;
  title?: string;
}

export function DisasterMap({
  nodes,
  zones,
  roads,
  hospitals,
  shelters,
  ambulances,
  emergencies,
  interactive = true,
  title = "Disaster Map",
}: DisasterMapProps) {
  const [view, setView] = useState<ViewBox>(FULL_VIEW);
  const [hovered, setHovered] = useState<Selection | null>(null);
  const [selected, setSelected] = useState<Selection | null>(null);
  const [dragging, setDragging] = useState(false);

  const svgRef = useRef<SVGSVGElement>(null);
  const dragOrigin = useRef<{ x: number; y: number } | null>(null);

  const nodeById = useMemo(
    () => new Map(nodes.map((n) => [n.id, n])),
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
  const emergencyNodes = useMemo(
    () => new Set(emergencies.map((e) => e.node_id)),
    [emergencies],
  );
  const ambulanceCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const a of ambulances) {
      counts.set(a.node_id, (counts.get(a.node_id) ?? 0) + 1);
    }
    return counts;
  }, [ambulances]);

  const roadCounts = useMemo(() => {
    let blocked = 0;
    let risky = 0;
    for (const road of roads) {
      if (road.status === "BLOCKED") blocked += 1;
      else if (road.status === "RISKY") risky += 1;
    }
    return { blocked, risky, safe: roads.length - blocked - risky };
  }, [roads]);

  const scale = screenScale(view);
  const zoom = zoomLevel(view);

  const bounds = useCallback(() => {
    const rect = svgRef.current?.getBoundingClientRect();
    return rect
      ? { left: rect.left, top: rect.top, width: rect.width, height: rect.height }
      : { left: 0, top: 0, width: 0, height: 0 };
  }, []);

  /**
   * Wheel zoom is bound imperatively because React attaches onWheel as a
   * passive listener, and a passive listener cannot preventDefault -- so the
   * page would scroll behind the map while zooming.
   */
  useEffect(() => {
    if (!interactive) return;
    const node = svgRef.current;
    if (!node) return;

    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      setView((current) => {
        const anchor = screenToWorld(
          { x: event.clientX, y: event.clientY },
          bounds(),
          current,
        );
        // Exponential in the delta so a trackpad flick and a mouse notch both
        // feel proportionate.
        return zoomAt(current, Math.exp(-event.deltaY * 0.0015), anchor);
      });
    };

    node.addEventListener("wheel", onWheel, { passive: false });
    return () => node.removeEventListener("wheel", onWheel);
  }, [interactive, bounds]);

  const onPointerDown = (event: React.PointerEvent<SVGSVGElement>) => {
    if (!interactive || event.button !== 0) return;
    dragOrigin.current = { x: event.clientX, y: event.clientY };
    setDragging(true);
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const onPointerMove = (event: React.PointerEvent<SVGSVGElement>) => {
    const origin = dragOrigin.current;
    if (!interactive || !origin) return;
    const delta = {
      x: event.clientX - origin.x,
      y: event.clientY - origin.y,
    };
    dragOrigin.current = { x: event.clientX, y: event.clientY };
    setView((current) => panByScreenDelta(current, delta, bounds()));
  };

  const endDrag = (event: React.PointerEvent<SVGSVGElement>) => {
    if (!dragOrigin.current) return;
    dragOrigin.current = null;
    setDragging(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  const zoomStep = (factor: number) =>
    setView((current) =>
      zoomAt(current, factor, {
        x: current.x + current.width / 2,
        y: current.y + current.height / 2,
      }),
    );

  const isHovered = (kind: Selection["kind"], id: string) =>
    hovered?.kind === kind && hovered.id === id;
  const isSelected = (kind: Selection["kind"], id: string) =>
    selected?.kind === kind && selected.id === id;

  const select = (next: Selection) =>
    setSelected((current) =>
      current?.kind === next.kind && current.id === next.id ? null : next,
    );

  const hoveredNode =
    hovered?.kind === "node" ? nodeById.get(hovered.id) : undefined;

  return (
    <section className="flex flex-col rounded-panel border border-border bg-panel">
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <h2 className="text-2xs font-medium tracking-wide text-fg-muted uppercase">
          {title}
        </h2>
        <span className="font-mono text-2xs text-fg-muted">
          {nodes.length} nodes &middot; {roads.length} roads &middot;{" "}
          {zones.length} zones
        </span>
      </div>

      <div className="relative">
        <svg
          ref={svgRef}
          viewBox={viewBoxToString(view)}
          className={`h-auto w-full touch-none select-none ${
            interactive ? (dragging ? "cursor-grabbing" : "cursor-grab") : ""
          }`}
          role="img"
          aria-label={`Disaster map. ${nodes.length} nodes, ${roads.length} roads. ${roadCounts.blocked} blocked, ${roadCounts.risky} at risk.`}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={endDrag}
          onPointerCancel={endDrag}
          onPointerLeave={() => setHovered(null)}
        >
          {/* Zones, tinted by flood level. Drawn first, everything sits above. */}
          <g data-testid="map-zones">
            {zones.map((zone) => (
              <polygon
                key={zone.id}
                data-testid={`zone-${zone.id}`}
                data-flood={zone.flood_level.toFixed(3)}
                points={zone.polygon.map(([x, y]) => `${x},${y}`).join(" ")}
                fill="var(--color-panel-2)"
                stroke={
                  isHovered("zone", zone.id) || isSelected("zone", zone.id)
                    ? "var(--color-info)"
                    : "var(--color-border)"
                }
                strokeWidth={1 * scale}
                onMouseEnter={
                  interactive ? () => setHovered({ kind: "zone", id: zone.id }) : undefined
                }
                onClick={
                  interactive ? () => select({ kind: "zone", id: zone.id }) : undefined
                }
                className={interactive ? "cursor-pointer" : undefined}
              />
            ))}
          </g>

          {/* Flood overlay. Opacity is the zone's flood_level, straight from
              the backend -- this is the "flood zones" layer, not decoration. */}
          <g data-testid="map-flood" pointerEvents="none">
            {zones
              .filter((zone) => zone.flood_level > 0.01)
              .map((zone) => (
                <polygon
                  key={`flood-${zone.id}`}
                  data-testid={`flood-${zone.id}`}
                  points={zone.polygon.map(([x, y]) => `${x},${y}`).join(" ")}
                  fill="var(--color-info)"
                  opacity={Math.min(zone.flood_level, 1) * 0.55}
                />
              ))}
          </g>

          <g data-testid="map-zone-labels" pointerEvents="none">
            {zones.map((zone) => {
              const [first] = zone.polygon;
              if (!first) return null;
              return (
                <text
                  key={`${zone.id}-label`}
                  x={first[0] + 10 * scale}
                  y={first[1] + 20 * scale}
                  fill="var(--color-fg-muted)"
                  fontSize={13 * scale}
                  fontFamily="var(--font-mono)"
                >
                  {zone.name}
                </text>
              );
            })}
          </g>

          <g data-testid="map-roads">
            {roads.map((road) => {
              const from = nodeById.get(road.source);
              const to = nodeById.get(road.destination);
              if (!from || !to) return null;
              const active = isHovered("road", road.id) || isSelected("road", road.id);
              return (
                <g key={road.id}>
                  {/* Invisible fat hit target: a 2px line is very hard to
                      click, and widening the visible stroke to compensate
                      would misrepresent road status. */}
                  {interactive && (
                    <line
                      x1={from.x}
                      y1={from.y}
                      x2={to.x}
                      y2={to.y}
                      stroke="transparent"
                      strokeWidth={12 * scale}
                      className="cursor-pointer"
                      onMouseEnter={() => setHovered({ kind: "road", id: road.id })}
                      onClick={() => select({ kind: "road", id: road.id })}
                    />
                  )}
                  <line
                    data-testid={`road-${road.id}`}
                    data-status={road.status}
                    x1={from.x}
                    y1={from.y}
                    x2={to.x}
                    y2={to.y}
                    stroke={active ? "var(--color-info)" : ROAD_STROKE[road.status]}
                    strokeWidth={(ROAD_BASE_WIDTH[road.status] + (active ? 1.5 : 0)) * scale}
                    strokeDasharray={
                      ROAD_DASH[road.status]
                        ? ROAD_DASH[road.status]
                            ?.split(" ")
                            .map((n) => Number(n) * scale)
                            .join(" ")
                        : undefined
                    }
                    strokeLinecap="round"
                    opacity={road.status === "SAFE" && !active ? 0.55 : 0.95}
                    pointerEvents="none"
                  />
                </g>
              );
            })}
          </g>

          <g data-testid="map-nodes">
            {nodes.map((node) => {
              const active = isHovered("node", node.id) || isSelected("node", node.id);
              const isHospital = hospitalNodes.has(node.id);
              const isShelter = shelterNodes.has(node.id);
              const size = (isHospital || isShelter ? 7 : 4) * scale;

              return (
                <g
                  key={node.id}
                  data-testid={`node-${node.id}`}
                  className={interactive ? "cursor-pointer" : undefined}
                  onMouseEnter={
                    interactive
                      ? () => setHovered({ kind: "node", id: node.id })
                      : undefined
                  }
                  onClick={
                    interactive ? () => select({ kind: "node", id: node.id }) : undefined
                  }
                >
                  {active && (
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r={size * 2.1}
                      fill="var(--color-info)"
                      opacity={0.2}
                    />
                  )}

                  {isHospital ? (
                    <rect
                      data-testid={`hospital-${node.id}`}
                      x={node.x - size}
                      y={node.y - size}
                      width={size * 2}
                      height={size * 2}
                      fill="var(--color-info)"
                      stroke="var(--color-bg)"
                      strokeWidth={1.5 * scale}
                    />
                  ) : isShelter ? (
                    <polygon
                      data-testid={`shelter-${node.id}`}
                      points={`${node.x},${node.y - size} ${node.x + size},${node.y + size * 0.75} ${node.x - size},${node.y + size * 0.75}`}
                      fill="var(--color-safe)"
                      stroke="var(--color-bg)"
                      strokeWidth={1.5 * scale}
                    />
                  ) : (
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r={size}
                      fill="var(--color-fg-muted)"
                    />
                  )}

                  {/* Emergency ring, drawn around whatever is underneath. */}
                  {emergencyNodes.has(node.id) && (
                    <circle
                      data-testid={`emergency-at-${node.id}`}
                      cx={node.x}
                      cy={node.y}
                      r={size * 2.4}
                      fill="none"
                      stroke="var(--color-crit)"
                      strokeWidth={2.5 * scale}
                    />
                  )}

                  {/* Ambulance diamond, offset so it does not hide the node. */}
                  {(ambulanceCounts.get(node.id) ?? 0) > 0 && (
                    <polygon
                      data-testid={`ambulance-at-${node.id}`}
                      points={`${node.x + size * 2},${node.y - size * 2.8} ${node.x + size * 3},${node.y - size * 1.8} ${node.x + size * 2},${node.y - size * 0.8} ${node.x + size},${node.y - size * 1.8}`}
                      fill="var(--color-info)"
                      stroke="var(--color-bg)"
                      strokeWidth={1 * scale}
                    />
                  )}
                </g>
              );
            })}
          </g>

          {/* Hover label, last so it is never occluded. */}
          {hoveredNode && (
            <text
              data-testid="hover-label"
              x={hoveredNode.x + 12 * scale}
              y={hoveredNode.y - 10 * scale}
              fill="var(--color-fg)"
              fontSize={13 * scale}
              fontFamily="var(--font-mono)"
              pointerEvents="none"
            >
              {hoveredNode.name}
            </text>
          )}
        </svg>

        {interactive && (
          <MapControls
            zoom={zoom}
            minZoom={MIN_ZOOM}
            maxZoom={MAX_ZOOM}
            onZoomIn={() => zoomStep(1.5)}
            onZoomOut={() => zoomStep(1 / 1.5)}
            onReset={() => setView(clampView(FULL_VIEW))}
          />
        )}

        {interactive && selected && (
          <MapDetailPanel
            selection={selected}
            nodes={nodes}
            zones={zones}
            roads={roads}
            hospitals={hospitals}
            shelters={shelters}
            ambulances={ambulances}
            emergencies={emergencies}
            onClose={() => setSelected(null)}
          />
        )}
      </div>

      <MapLegend
        safe={roadCounts.safe}
        risky={roadCounts.risky}
        blocked={roadCounts.blocked}
      />
    </section>
  );
}
