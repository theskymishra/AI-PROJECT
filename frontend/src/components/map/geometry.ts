/**
 * Map viewport geometry.
 *
 * Pure functions, no React, no DOM. Every pan/zoom decision the map makes
 * lives here so it can be tested directly — this is arithmetic that is easy
 * to get subtly wrong (a transform that is off by a factor of the zoom level
 * looks almost right until you zoom in twice) and impossible to check by
 * reading the code.
 *
 * COORDINATE SPACES
 * -----------------
 *   world   The backend's map units, 0..1000 x 0..700. Node x/y are in these.
 *   view    The SVG viewBox: a window onto world space. Panning moves it,
 *           zooming shrinks or grows it.
 *   screen  Client pixels. Only pointer events live here.
 */

/** Backend MAP_WIDTH_UNITS / MAP_HEIGHT_UNITS. */
export const WORLD_WIDTH = 1000;
export const WORLD_HEIGHT = 700;

/** Zoom bounds, expressed as a scale factor against the full world view. */
export const MIN_ZOOM = 1;
export const MAX_ZOOM = 8;

export interface ViewBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export const FULL_VIEW: ViewBox = {
  x: 0,
  y: 0,
  width: WORLD_WIDTH,
  height: WORLD_HEIGHT,
};

export function viewBoxToString(view: ViewBox): string {
  return `${view.x} ${view.y} ${view.width} ${view.height}`;
}

/** Current zoom factor. 1 = whole world visible, 4 = quarter width visible. */
export function zoomLevel(view: ViewBox): number {
  return WORLD_WIDTH / view.width;
}

/**
 * Keep the view inside the world.
 *
 * Width is clamped to the zoom bounds first, then the origin is clamped so the
 * window cannot be dragged off the edge. Without this, panning at high zoom
 * walks off into empty space and the map appears to have vanished.
 */
export function clampView(view: ViewBox): ViewBox {
  const width = clamp(view.width, WORLD_WIDTH / MAX_ZOOM, WORLD_WIDTH / MIN_ZOOM);
  // Aspect ratio is locked to the world so the map never distorts.
  const height = (width * WORLD_HEIGHT) / WORLD_WIDTH;

  return {
    width,
    height,
    x: clamp(view.x, 0, WORLD_WIDTH - width),
    y: clamp(view.y, 0, WORLD_HEIGHT - height),
  };
}

/**
 * Zoom by `factor`, holding the world point under the cursor still.
 *
 * The anchor is what makes wheel-zoom feel right: without it the view zooms
 * to its own centre and whatever you were pointing at slides away.
 */
export function zoomAt(view: ViewBox, factor: number, anchor: Point): ViewBox {
  const width = clamp(
    view.width / factor,
    WORLD_WIDTH / MAX_ZOOM,
    WORLD_WIDTH / MIN_ZOOM,
  );
  const height = (width * WORLD_HEIGHT) / WORLD_WIDTH;

  // Fraction of the way across the current view that the anchor sits at.
  // Preserving those fractions is what pins the anchor in place.
  const fx = view.width === 0 ? 0.5 : (anchor.x - view.x) / view.width;
  const fy = view.height === 0 ? 0.5 : (anchor.y - view.y) / view.height;

  return clampView({
    x: anchor.x - fx * width,
    y: anchor.y - fy * height,
    width,
    height,
  });
}

export interface Point {
  x: number;
  y: number;
}

export interface Rect {
  left: number;
  top: number;
  width: number;
  height: number;
}

/**
 * Convert a client-pixel point to world coordinates.
 *
 * Note the division by the RENDERED size, not the viewBox size: the SVG is
 * responsive, so one screen pixel is worth a different number of world units
 * at every container width.
 */
export function screenToWorld(
  screen: Point,
  bounds: Rect,
  view: ViewBox,
): Point {
  if (bounds.width === 0 || bounds.height === 0) {
    return { x: view.x, y: view.y };
  }
  return {
    x: view.x + ((screen.x - bounds.left) / bounds.width) * view.width,
    y: view.y + ((screen.y - bounds.top) / bounds.height) * view.height,
  };
}

/** Translate the view by a screen-pixel drag delta. */
export function panByScreenDelta(
  view: ViewBox,
  deltaScreen: Point,
  bounds: Rect,
): ViewBox {
  if (bounds.width === 0 || bounds.height === 0) return view;
  return clampView({
    ...view,
    // Dragging right must move the world right, so the window moves left.
    x: view.x - (deltaScreen.x / bounds.width) * view.width,
    y: view.y - (deltaScreen.y / bounds.height) * view.height,
  });
}

/**
 * Scale a constant screen size into world units.
 *
 * Node markers and stroke widths are authored at a size that reads well on
 * screen. Without this they would balloon as you zoom in and disappear as you
 * zoom out, because SVG scales geometry with the viewBox.
 */
export function screenScale(view: ViewBox): number {
  return view.width / WORLD_WIDTH;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}
