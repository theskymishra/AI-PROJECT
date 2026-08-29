/**
 * Detail panel for the selected map entity.
 *
 * Everything shown is a field the backend actually sends. Nothing is derived
 * in the browser, and nothing is invented to fill the panel out — an empty row
 * is better than a plausible-looking guess.
 */

import { X } from "lucide-react";

import { StatusBadge } from "@/components/layout/StatusBadge";
import type { BadgeTone } from "@/components/layout/StatusBadge";
import type {
  Ambulance,
  Emergency,
  Hospital,
  Road,
  Shelter,
  WorldNode,
  Zone,
} from "@/types";

export type Selection =
  | { kind: "node"; id: string }
  | { kind: "road"; id: string }
  | { kind: "zone"; id: string };

interface MapDetailPanelProps {
  selection: Selection;
  nodes: WorldNode[];
  zones: Zone[];
  roads: Road[];
  hospitals: Hospital[];
  shelters: Shelter[];
  ambulances: Ambulance[];
  emergencies: Emergency[];
  onClose: () => void;
}

const ROAD_TONE: Record<Road["status"], BadgeTone> = {
  SAFE: "safe",
  RISKY: "warn",
  BLOCKED: "crit",
};

export function MapDetailPanel({
  selection,
  nodes,
  zones,
  roads,
  hospitals,
  shelters,
  ambulances,
  emergencies,
  onClose,
}: MapDetailPanelProps) {
  const content = buildContent();

  if (!content) return null;

  return (
    <aside
      data-testid="map-detail-panel"
      className="absolute bottom-3 left-3 w-72 rounded-panel border border-border bg-panel/95 shadow-lg backdrop-blur-sm">
      <div className="flex items-start justify-between gap-2 border-b border-border px-3 py-2">
        <div className="min-w-0">
          <div
            data-testid="detail-kind"
            className="text-2xs tracking-wide text-fg-muted uppercase"
          >
            {content.kindLabel}
          </div>
          <div className="truncate text-[13px] text-fg">{content.title}</div>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          {content.badge}
          <button
            type="button"
            onClick={onClose}
            aria-label="Close details"
            className="rounded-panel p-0.5 text-fg-muted transition-colors duration-150 hover:text-fg"
          >
            <X aria-hidden="true" className="size-3.5" />
          </button>
        </div>
      </div>
      <dl className="px-3 py-2">
        {content.rows.map((row) => (
          <div
            key={row.label}
            className="flex items-baseline justify-between gap-3 border-b border-border/60 py-1 last:border-b-0"
          >
            <dt className="text-2xs tracking-wide text-fg-muted uppercase">
              {row.label}
            </dt>
            <dd className="font-mono text-2xs text-fg">{row.value}</dd>
          </div>
        ))}
      </dl>
    </aside>
  );

  function buildContent() {
    if (selection.kind === "road") {
      const road = roads.find((r) => r.id === selection.id);
      if (!road) return null;
      const from = nodes.find((n) => n.id === road.source);
      const to = nodes.find((n) => n.id === road.destination);
      return {
        kindLabel: `Road ${road.id}`,
        title: `${from?.name ?? road.source} \u2192 ${to?.name ?? road.destination}`,
        badge: (
          <StatusBadge tone={ROAD_TONE[road.status]}>{road.status}</StatusBadge>
        ),
        rows: [
          { label: "Length", value: `${road.distance.toFixed(2)} km` },
          {
            label: "Straight line",
            value: `${road.geometric_length.toFixed(2)} km`,
          },
          { label: "Detour factor", value: road.detour_factor.toFixed(3) },
          { label: "Elevation band", value: road.elevation_band },
          { label: "Flood level", value: road.flood_level.toFixed(3) },
          { label: "Damage level", value: road.damage_level.toFixed(3) },
          {
            label: "P(failure)",
            value: road.failure_probability.toFixed(3),
          },
        ],
      };
    }

    if (selection.kind === "zone") {
      const zone = zones.find((z) => z.id === selection.id);
      if (!zone) return null;
      return {
        kindLabel: `Zone ${zone.id}`,
        title: zone.name,
        badge: null,
        rows: [
          { label: "Population", value: zone.population.toLocaleString() },
          { label: "Elevation", value: zone.elevation.toFixed(2) },
          { label: "Elevation band", value: zone.elevation_band },
          { label: "Flood level", value: zone.flood_level.toFixed(3) },
        ],
      };
    }

    const node = nodes.find((n) => n.id === selection.id);
    if (!node) return null;

    const hospital = hospitals.find((h) => h.node_id === node.id);
    const shelter = shelters.find((s) => s.node_id === node.id);
    const here = ambulances.filter((a) => a.node_id === node.id);
    const incidents = emergencies.filter((e) => e.node_id === node.id);
    const zone = zones.find((z) => z.id === node.zone_id);

    const rows: Array<{ label: string; value: string }> = [
      { label: "Zone", value: zone?.name ?? node.zone_id },
      { label: "Position", value: `${node.x}, ${node.y}` },
    ];

    if (hospital) {
      rows.push(
        {
          label: "Beds",
          value: `${hospital.available_beds} / ${hospital.total_beds}`,
        },
        {
          label: "ICU",
          value: `${hospital.available_icu} / ${hospital.total_icu}`,
        },
        { label: "Hospital status", value: hospital.status },
      );
    }
    if (shelter) {
      rows.push(
        {
          label: "Occupancy",
          value: `${shelter.occupancy} / ${shelter.capacity}`,
        },
        { label: "Safety score", value: shelter.safety_score.toFixed(2) },
        { label: "Shelter status", value: shelter.status },
      );
    }
    if (here.length > 0) {
      rows.push({
        label: "Ambulances",
        value: here.map((a) => `${a.id} ${a.status}`).join(", "),
      });
    }
    for (const incident of incidents) {
      rows.push(
        { label: `${incident.id} severity`, value: incident.severity },
        {
          label: `${incident.id} people`,
          value: `${incident.people_affected} (${incident.patients} patients)`,
        },
        { label: `${incident.id} status`, value: incident.status },
      );
    }

    return {
      kindLabel: hospital
        ? "Hospital"
        : shelter
          ? "Shelter"
          : incidents.length > 0
            ? "Emergency site"
            : "Junction",
      title: hospital?.name ?? shelter?.name ?? node.name,
      badge:
        incidents.length > 0 ? (
          <StatusBadge tone="crit">Emergency</StatusBadge>
        ) : hospital ? (
          <StatusBadge tone={hospital.status === "FULL" ? "crit" : "info"}>
            {hospital.status}
          </StatusBadge>
        ) : null,
      rows,
    };
  }
}
