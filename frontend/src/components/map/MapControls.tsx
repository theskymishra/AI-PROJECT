/**
 * Zoom and reset controls.
 *
 * Buttons exist alongside wheel and drag because pointer gestures are not
 * reachable from a keyboard, and because a projector demo is easier to drive
 * with discrete steps than with a trackpad.
 */

import { Maximize2, Minus, Plus } from "lucide-react";

interface MapControlsProps {
  zoom: number;
  minZoom: number;
  maxZoom: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
}

const BUTTON =
  "flex size-7 items-center justify-center rounded-panel border border-border " +
  "bg-panel-2/90 text-fg-muted transition-colors duration-150 " +
  "hover:border-info/50 hover:text-fg disabled:cursor-not-allowed disabled:opacity-40";

export function MapControls({
  zoom,
  minZoom,
  maxZoom,
  onZoomIn,
  onZoomOut,
  onReset,
}: MapControlsProps) {
  return (
    <div className="absolute top-3 right-3 flex flex-col items-end gap-1.5">
      <div className="flex flex-col gap-1">
        <button
          type="button"
          onClick={onZoomIn}
          disabled={zoom >= maxZoom}
          aria-label="Zoom in"
          className={BUTTON}
        >
          <Plus aria-hidden="true" className="size-3.5" />
        </button>
        <button
          type="button"
          onClick={onZoomOut}
          disabled={zoom <= minZoom}
          aria-label="Zoom out"
          className={BUTTON}
        >
          <Minus aria-hidden="true" className="size-3.5" />
        </button>
        <button
          type="button"
          onClick={onReset}
          disabled={zoom === minZoom}
          aria-label="Reset view"
          className={BUTTON}
        >
          <Maximize2 aria-hidden="true" className="size-3.5" />
        </button>
      </div>
      <span className="rounded-panel border border-border bg-panel-2/90 px-1.5 py-0.5 font-mono text-2xs text-fg-muted">
        {zoom.toFixed(1)}x
      </span>
    </div>
  );
}
