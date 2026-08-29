/**
 * Viewport geometry tests.
 *
 * This is the arithmetic behind every pan and zoom. It is the part of the map
 * a type checker cannot see and a screenshot cannot confirm: a transform that
 * is wrong by a factor of the zoom level looks correct at 1x and drifts
 * further with every step in.
 */

import { describe, expect, it } from "vitest";

import {
  FULL_VIEW,
  MAX_ZOOM,
  MIN_ZOOM,
  WORLD_HEIGHT,
  WORLD_WIDTH,
  clampView,
  panByScreenDelta,
  screenScale,
  screenToWorld,
  viewBoxToString,
  zoomAt,
  zoomLevel,
} from "@/components/map/geometry";

const BOUNDS = { left: 0, top: 0, width: 800, height: 560 };

describe("viewBoxToString", () => {
  it("formats as the SVG viewBox attribute", () => {
    expect(viewBoxToString(FULL_VIEW)).toBe("0 0 1000 700");
  });
});

describe("zoomLevel", () => {
  it("reports 1 for the full world", () => {
    expect(zoomLevel(FULL_VIEW)).toBe(1);
  });

  it("reports 4 when a quarter of the width is visible", () => {
    expect(zoomLevel({ x: 0, y: 0, width: 250, height: 175 })).toBe(4);
  });
});

describe("clampView", () => {
  it("leaves the full view untouched", () => {
    expect(clampView(FULL_VIEW)).toEqual(FULL_VIEW);
  });

  it("refuses to zoom out past the whole world", () => {
    const clamped = clampView({ x: 0, y: 0, width: 5000, height: 3500 });
    expect(clamped.width).toBe(WORLD_WIDTH / MIN_ZOOM);
    expect(clamped.height).toBe(WORLD_HEIGHT);
  });

  it("refuses to zoom in past MAX_ZOOM", () => {
    const clamped = clampView({ x: 0, y: 0, width: 1, height: 1 });
    expect(clamped.width).toBe(WORLD_WIDTH / MAX_ZOOM);
  });

  it("locks the aspect ratio to the world", () => {
    // A deliberately distorted input must come back proportional.
    const clamped = clampView({ x: 0, y: 0, width: 500, height: 20 });
    expect(clamped.height).toBeCloseTo((500 * WORLD_HEIGHT) / WORLD_WIDTH, 6);
  });

  it("stops the window being panned off the right or bottom edge", () => {
    const clamped = clampView({ x: 900, y: 600, width: 500, height: 350 });
    expect(clamped.x).toBe(WORLD_WIDTH - 500);
    expect(clamped.y).toBe(WORLD_HEIGHT - 350);
  });

  it("stops the window being panned off the left or top edge", () => {
    const clamped = clampView({ x: -300, y: -200, width: 500, height: 350 });
    expect(clamped.x).toBe(0);
    expect(clamped.y).toBe(0);
  });
});

describe("zoomAt", () => {
  it("holds the anchor point still while zooming in", () => {
    const anchor = { x: 250, y: 175 };
    const zoomed = zoomAt(FULL_VIEW, 2, anchor);

    // The anchor must sit at the same fractional position afterwards.
    const fxBefore = (anchor.x - FULL_VIEW.x) / FULL_VIEW.width;
    const fxAfter = (anchor.x - zoomed.x) / zoomed.width;
    expect(fxAfter).toBeCloseTo(fxBefore, 6);
  });

  it("halves the visible width when zooming in by 2", () => {
    const zoomed = zoomAt(FULL_VIEW, 2, { x: 500, y: 350 });
    expect(zoomed.width).toBe(500);
    expect(zoomLevel(zoomed)).toBe(2);
  });

  it("is reversible: zoom in then out returns to the full view", () => {
    const centre = { x: 500, y: 350 };
    const back = zoomAt(zoomAt(FULL_VIEW, 2, centre), 0.5, centre);
    expect(back.width).toBeCloseTo(FULL_VIEW.width, 6);
    expect(back.x).toBeCloseTo(FULL_VIEW.x, 6);
    expect(back.y).toBeCloseTo(FULL_VIEW.y, 6);
  });

  it("never exceeds MAX_ZOOM however many times it is called", () => {
    let view = FULL_VIEW;
    for (let i = 0; i < 20; i += 1) view = zoomAt(view, 2, { x: 500, y: 350 });
    expect(zoomLevel(view)).toBeLessThanOrEqual(MAX_ZOOM);
  });

  it("never zooms out past the whole world", () => {
    let view = FULL_VIEW;
    for (let i = 0; i < 20; i += 1) view = zoomAt(view, 0.5, { x: 500, y: 350 });
    expect(view).toEqual(FULL_VIEW);
  });

  it("keeps the view inside the world when anchored at a corner", () => {
    const zoomed = zoomAt(FULL_VIEW, 4, { x: 0, y: 0 });
    expect(zoomed.x).toBeGreaterThanOrEqual(0);
    expect(zoomed.y).toBeGreaterThanOrEqual(0);
    expect(zoomed.x + zoomed.width).toBeLessThanOrEqual(WORLD_WIDTH + 1e-9);
    expect(zoomed.y + zoomed.height).toBeLessThanOrEqual(WORLD_HEIGHT + 1e-9);
  });
});

describe("screenToWorld", () => {
  it("maps the top-left pixel to the view origin", () => {
    expect(screenToWorld({ x: 0, y: 0 }, BOUNDS, FULL_VIEW)).toEqual({
      x: 0,
      y: 0,
    });
  });

  it("maps the centre pixel to the centre of the world", () => {
    const world = screenToWorld({ x: 400, y: 280 }, BOUNDS, FULL_VIEW);
    expect(world.x).toBeCloseTo(500, 6);
    expect(world.y).toBeCloseTo(350, 6);
  });

  it("accounts for the container offset on the page", () => {
    const offset = { left: 100, top: 50, width: 800, height: 560 };
    const world = screenToWorld({ x: 100, y: 50 }, offset, FULL_VIEW);
    expect(world).toEqual({ x: 0, y: 0 });
  });

  it("accounts for the current zoom, not just the world size", () => {
    // THE regression this file exists for. At 2x the same pixel is a
    // different world point; dividing by the world size instead of the view
    // width makes hit-testing drift as you zoom.
    const zoomed = { x: 250, y: 175, width: 500, height: 350 };
    const world = screenToWorld({ x: 400, y: 280 }, BOUNDS, zoomed);
    expect(world.x).toBeCloseTo(500, 6);
    expect(world.y).toBeCloseTo(350, 6);
  });

  it("does not divide by zero for an unmeasured container", () => {
    const empty = { left: 0, top: 0, width: 0, height: 0 };
    const world = screenToWorld({ x: 10, y: 10 }, empty, FULL_VIEW);
    expect(Number.isFinite(world.x)).toBe(true);
    expect(Number.isFinite(world.y)).toBe(true);
  });
});

describe("panByScreenDelta", () => {
  it("moves the window opposite to the drag, so content follows the cursor", () => {
    const zoomed = { x: 250, y: 175, width: 500, height: 350 };
    const panned = panByScreenDelta(zoomed, { x: 80, y: 0 }, BOUNDS);
    expect(panned.x).toBeLessThan(zoomed.x);
  });

  it("translates screen pixels into world units at the current zoom", () => {
    const zoomed = { x: 250, y: 175, width: 500, height: 350 };
    // 80px of an 800px-wide container is a tenth of the visible 500 units.
    const panned = panByScreenDelta(zoomed, { x: 80, y: 0 }, BOUNDS);
    expect(zoomed.x - panned.x).toBeCloseTo(50, 6);
  });

  it("cannot drag the view outside the world", () => {
    const zoomed = { x: 0, y: 0, width: 500, height: 350 };
    const panned = panByScreenDelta(zoomed, { x: 5000, y: 5000 }, BOUNDS);
    expect(panned.x).toBe(0);
    expect(panned.y).toBe(0);
  });

  it("is a no-op for an unmeasured container", () => {
    const empty = { left: 0, top: 0, width: 0, height: 0 };
    expect(panByScreenDelta(FULL_VIEW, { x: 10, y: 10 }, empty)).toEqual(FULL_VIEW);
  });
});

describe("screenScale", () => {
  it("is 1 at full zoom", () => {
    expect(screenScale(FULL_VIEW)).toBe(1);
  });

  it("shrinks as you zoom in, so markers keep a constant screen size", () => {
    expect(screenScale({ x: 0, y: 0, width: 250, height: 175 })).toBe(0.25);
  });
});
