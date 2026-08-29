/**
 * Live event feed.
 *
 * Entries arrive over SSE as `timeline_tail` on each tick and are appended by
 * the reducer. Categories are whatever the backend emits -- currently WEATHER,
 * WATER, ROAD and EMERGENCY -- and are NOT invented here. An unrecognised
 * category renders neutral rather than being dropped, so a category added in a
 * later phase shows up instead of silently vanishing.
 */

import { useEffect, useRef } from "react";

import type { BadgeTone } from "@/components/layout/StatusBadge";
import type { TimelineEntry } from "@/types";

const CATEGORY_TONE: Record<string, BadgeTone> = {
  WEATHER: "info",
  WATER: "info",
  ROAD: "warn",
  EMERGENCY: "crit",
  SIMULATION: "idle",
};

const RULE_COLOUR: Record<BadgeTone, string> = {
  info: "bg-info",
  safe: "bg-safe",
  warn: "bg-warn",
  crit: "bg-crit",
  idle: "bg-idle",
};

function tickLabel(tick: number): string {
  const m = Math.floor(tick / 60);
  const s = tick % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function EventTimeline({ entries }: { entries: TimelineEntry[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const count = entries.length;

  // Follow the feed as it grows. Newest is at the bottom, which is how a log
  // reads; jumping to the top on each event would fight the reader.
  useEffect(() => {
    const node = scrollRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [count]);

  return (
    <section className="flex min-h-0 flex-col rounded-panel border border-border bg-panel">
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <h2 className="text-2xs font-medium tracking-wide text-fg-muted uppercase">
          Event Timeline
        </h2>
        <span className="font-mono text-2xs text-fg-muted">{count}</span>
      </div>

      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto p-2">
        {count === 0 ? (
          <p className="px-2 py-6 text-center text-[13px] text-fg-muted">
            No events yet. Start the simulation to populate the timeline.
          </p>
        ) : (
          <ol className="flex flex-col gap-0.5">
            {entries.map((entry) => {
              const tone = CATEGORY_TONE[entry.category] ?? "idle";
              return (
                <li
                  key={entry.id}
                  className="flex gap-2.5 rounded-panel px-2 py-1.5 hover:bg-panel-2"
                >
                  <span
                    aria-hidden="true"
                    className={`mt-1 w-0.5 shrink-0 rounded-full ${RULE_COLOUR[tone]}`}
                  />
                  <span className="mt-px shrink-0 font-mono text-2xs text-fg-muted">
                    {tickLabel(entry.tick)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[13px] leading-snug text-fg">
                      {entry.headline}
                    </span>
                    {entry.detail && (
                      <span className="block text-2xs leading-snug text-fg-muted">
                        {entry.detail}
                      </span>
                    )}
                  </span>
                  <span className="shrink-0 self-start font-mono text-2xs text-fg-muted">
                    {entry.category}
                  </span>
                </li>
              );
            })}
          </ol>
        )}
      </div>
    </section>
  );
}
