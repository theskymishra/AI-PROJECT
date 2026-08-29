/**
 * A* search animation.
 *
 * Replays a completed search's `expansion_order` one node at a time. The
 * search itself already ran on the backend — this does NOT re-implement A* in
 * the browser, and it cannot: the frame at index k is simply the first k
 * entries of the order the real search produced.
 *
 * That distinction matters. A client-side animation that "searched" as it drew
 * would be a second implementation free to disagree with the first, and the
 * numbers on screen would no longer be the numbers the algorithm produced.
 *
 * On a 24-node graph a search expands roughly 8–16 nodes, so a full replay is
 * a few seconds at the default step interval. The animation is pedagogical —
 * it shows the frontier growing towards the goal — not a performance readout.
 */

import { useCallback, useEffect, useRef, useState } from "react";

export type PlaybackState = "idle" | "playing" | "paused" | "finished";

export interface SearchPlayback {
  state: PlaybackState;
  /** How many expansions are currently revealed. */
  step: number;
  totalSteps: number;
  /** The prefix of expansion_order revealed so far. */
  revealed: string[];
  play: () => void;
  pause: () => void;
  stepForward: () => void;
  reset: () => void;
  /** Reveal everything at once, for when the animation is not wanted. */
  showAll: () => void;
}

const DEFAULT_INTERVAL_MS = 220;

export function useSearchPlayback(
  expansionOrder: string[] | undefined,
  intervalMs: number = DEFAULT_INTERVAL_MS,
): SearchPlayback {
  const order = expansionOrder ?? [];
  const total = order.length;

  const [step, setStep] = useState(0);
  const [state, setState] = useState<PlaybackState>("idle");
  const timer = useRef<number | null>(null);

  const clear = useCallback(() => {
    if (timer.current !== null) {
      window.clearInterval(timer.current);
      timer.current = null;
    }
  }, []);

  // A new search result resets the animation. Without this, switching
  // start/goal would leave the previous run's progress on screen.
  useEffect(() => {
    clear();
    setStep(0);
    setState("idle");
  }, [expansionOrder, clear]);

  useEffect(() => {
    if (state !== "playing") {
      clear();
      return;
    }
    timer.current = window.setInterval(() => {
      setStep((current) => {
        if (current >= total) {
          setState("finished");
          return total;
        }
        return current + 1;
      });
    }, intervalMs);
    return clear;
  }, [state, total, intervalMs, clear]);

  useEffect(() => {
    if (step >= total && state === "playing") setState("finished");
  }, [step, total, state]);

  return {
    state,
    step,
    totalSteps: total,
    revealed: order.slice(0, step),
    play: () => {
      if (total === 0) return;
      if (step >= total) setStep(0);
      setState("playing");
    },
    pause: () => setState("paused"),
    stepForward: () => {
      if (total === 0) return;
      setState("paused");
      setStep((current) => Math.min(current + 1, total));
    },
    reset: () => {
      setStep(0);
      setState("idle");
    },
    showAll: () => {
      setStep(total);
      setState("finished");
    },
  };
}
