/**
 * Map key.
 *
 * Every symbol on the map appears here. Road status is carried by dash
 * pattern as well as colour, so the map survives a monochrome projector and a
 * colour-blind viewer -- the legend shows both.
 */

interface MapLegendProps {
  safe: number;
  risky: number;
  blocked: number;
}

export function MapLegend({ safe, risky, blocked }: MapLegendProps) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-border px-4 py-2.5">
      <LegendGroup label="Roads">
        <RoadKey colour="var(--color-safe)" label={`Safe ${safe}`} />
        <RoadKey colour="var(--color-warn)" label={`Risky ${risky}`} dash="5 4" />
        <RoadKey colour="var(--color-crit)" label={`Blocked ${blocked}`} dash="6 5" />
      </LegendGroup>

      <span aria-hidden="true" className="h-4 w-px bg-border" />

      <LegendGroup label="Facilities">
        <ShapeKey shape="square" colour="var(--color-info)" label="Hospital" />
        <ShapeKey shape="triangle" colour="var(--color-safe)" label="Shelter" />
        <ShapeKey shape="circle" colour="var(--color-fg-muted)" label="Junction" />
      </LegendGroup>

      <span aria-hidden="true" className="h-4 w-px bg-border" />

      <LegendGroup label="Units">
        <ShapeKey shape="diamond" colour="var(--color-info)" label="Ambulance" />
        <ShapeKey shape="ring" colour="var(--color-crit)" label="Emergency" />
      </LegendGroup>

      <span aria-hidden="true" className="h-4 w-px bg-border" />

      <LegendGroup label="Flooding">
        <span className="flex items-center gap-1">
          <span className="h-2.5 w-6 rounded-[1px] bg-info/10" />
          <span className="h-2.5 w-6 rounded-[1px] bg-info/35" />
          <span className="h-2.5 w-6 rounded-[1px] bg-info/60" />
          <span className="ml-1 font-mono text-2xs text-fg-muted">0 &rarr; 1</span>
        </span>
      </LegendGroup>
    </div>
  );
}

function LegendGroup({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="text-2xs tracking-wide text-fg-muted uppercase">
        {label}
      </span>
      {children}
    </div>
  );
}

function RoadKey({
  colour,
  label,
  dash,
}: {
  colour: string;
  label: string;
  dash?: string;
}) {
  return (
    <span className="flex items-center gap-1.5">
      <svg width={18} height={8} aria-hidden="true">
        <line
          x1={0}
          y1={4}
          x2={18}
          y2={4}
          stroke={colour}
          strokeWidth={2.5}
          strokeDasharray={dash}
        />
      </svg>
      <span className="font-mono text-2xs text-fg-muted">{label}</span>
    </span>
  );
}

function ShapeKey({
  shape,
  colour,
  label,
}: {
  shape: "square" | "triangle" | "circle" | "diamond" | "ring";
  colour: string;
  label: string;
}) {
  return (
    <span className="flex items-center gap-1.5">
      <svg width={14} height={12} aria-hidden="true">
        {shape === "square" && <rect x={3} y={2} width={8} height={8} fill={colour} />}
        {shape === "triangle" && <polygon points="7,2 12,10 2,10" fill={colour} />}
        {shape === "circle" && <circle cx={7} cy={6} r={3} fill={colour} />}
        {shape === "diamond" && <polygon points="7,1 12,6 7,11 2,6" fill={colour} />}
        {shape === "ring" && (
          <circle cx={7} cy={6} r={4} fill="none" stroke={colour} strokeWidth={2} />
        )}
      </svg>
      <span className="font-mono text-2xs text-fg-muted">{label}</span>
    </span>
  );
}
