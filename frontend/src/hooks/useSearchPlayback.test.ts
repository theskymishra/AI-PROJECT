/**
 * Search playback tests.
 *
 * The animation must be a faithful replay of the backend's expansion_order --
 * never a browser-side re-run of A*. These assert it reveals a strict prefix
 * of that order and nothing else.
 */

import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useSearchPlayback } from "@/hooks/useSearchPlayback";

const ORDER = ["N1", "N2", "N5", "N10", "N11"];

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("initial state", () => {
  it("starts idle with nothing revealed", () => {
    const { result } = renderHook(() => useSearchPlayback(ORDER));
    expect(result.current.state).toBe("idle");
    expect(result.current.step).toBe(0);
    expect(result.current.revealed).toEqual([]);
  });

  it("reports the total from the backend's expansion order", () => {
    const { result } = renderHook(() => useSearchPlayback(ORDER));
    expect(result.current.totalSteps).toBe(5);
  });

  it("handles an absent order without crashing", () => {
    const { result } = renderHook(() => useSearchPlayback(undefined));
    expect(result.current.totalSteps).toBe(0);
    expect(result.current.revealed).toEqual([]);
  });
});

describe("stepping", () => {
  it("reveals one node per step, in backend order", () => {
    const { result } = renderHook(() => useSearchPlayback(ORDER));
    act(() => result.current.stepForward());
    expect(result.current.revealed).toEqual(["N1"]);
    act(() => result.current.stepForward());
    expect(result.current.revealed).toEqual(["N1", "N2"]);
  });

  it("never reveals more than the search actually expanded", () => {
    const { result } = renderHook(() => useSearchPlayback(ORDER));
    for (let i = 0; i < 20; i += 1) act(() => result.current.stepForward());
    expect(result.current.step).toBe(5);
    expect(result.current.revealed).toEqual(ORDER);
  });

  it("only ever reveals a prefix of the backend order", () => {
    const { result } = renderHook(() => useSearchPlayback(ORDER));
    for (let i = 0; i < 5; i += 1) {
      act(() => result.current.stepForward());
      expect(result.current.revealed).toEqual(ORDER.slice(0, i + 1));
    }
  });

  it("stepping pauses playback", () => {
    const { result } = renderHook(() => useSearchPlayback(ORDER));
    act(() => result.current.play());
    act(() => result.current.stepForward());
    expect(result.current.state).toBe("paused");
  });
});

describe("playback", () => {
  it("advances on a timer once playing", () => {
    const { result } = renderHook(() => useSearchPlayback(ORDER, 100));
    act(() => result.current.play());
    act(() => void vi.advanceTimersByTime(250));
    expect(result.current.step).toBeGreaterThan(0);
  });

  it("finishes at the last expansion", () => {
    const { result } = renderHook(() => useSearchPlayback(ORDER, 100));
    act(() => result.current.play());
    act(() => void vi.advanceTimersByTime(1000));
    expect(result.current.state).toBe("finished");
    expect(result.current.revealed).toEqual(ORDER);
  });

  it("pause stops the timer", () => {
    const { result } = renderHook(() => useSearchPlayback(ORDER, 100));
    act(() => result.current.play());
    act(() => void vi.advanceTimersByTime(200));
    const stopped = result.current.step;
    act(() => result.current.pause());
    act(() => void vi.advanceTimersByTime(1000));
    expect(result.current.step).toBe(stopped);
  });

  it("play after finishing replays from the start", () => {
    const { result } = renderHook(() => useSearchPlayback(ORDER, 100));
    act(() => result.current.showAll());
    act(() => result.current.play());
    expect(result.current.step).toBe(0);
  });

  it("play on an empty order does nothing", () => {
    const { result } = renderHook(() => useSearchPlayback([], 100));
    act(() => result.current.play());
    expect(result.current.state).toBe("idle");
  });
});

describe("reset and show all", () => {
  it("reset returns to idle with nothing revealed", () => {
    const { result } = renderHook(() => useSearchPlayback(ORDER));
    act(() => result.current.showAll());
    act(() => result.current.reset());
    expect(result.current.step).toBe(0);
    expect(result.current.state).toBe("idle");
  });

  it("show all reveals the complete order at once", () => {
    const { result } = renderHook(() => useSearchPlayback(ORDER));
    act(() => result.current.showAll());
    expect(result.current.revealed).toEqual(ORDER);
    expect(result.current.state).toBe("finished");
  });
});

describe("a new search result", () => {
  it("resets the animation", () => {
    const { result, rerender } = renderHook(
      ({ order }) => useSearchPlayback(order),
      { initialProps: { order: ORDER } },
    );
    act(() => result.current.showAll());
    expect(result.current.step).toBe(5);

    rerender({ order: ["N3", "N4"] });
    expect(result.current.step).toBe(0);
    expect(result.current.totalSteps).toBe(2);
  });
});
