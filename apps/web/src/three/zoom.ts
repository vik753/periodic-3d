/**
 * Wheel zoom of the table view (TableZoom): log-linear steps towards the point under the
 * cursor. The whole range — from the full table to one tile filling half the screen —
 * takes about one firm scroll, so nobody has to scroll for long.
 */

import type { Vec3 } from '../data/structure';

/** Wheel movement (CSS pixels) that crosses the whole zoom range. */
export const FULL_RANGE_PIXELS = 520;
/** Trackpad pinch on macOS arrives as ctrl + wheel with small deltas. */
export const PINCH_BOOST = 4;

export interface Rig {
  position: Vec3;
  target: Vec3;
}

/** Wheel delta in CSS pixels: lines and pages converted. */
export function wheelPixels(deltaY: number, deltaMode: number): number {
  if (deltaMode === 1) return deltaY * 40;
  if (deltaMode === 2) return deltaY * 800;
  return deltaY;
}

/** Camera distance after a wheel movement; positive pixels move away. */
export function zoomDistance(distance: number, pixels: number, min: number, max: number): number {
  const range = Math.log(max / min);
  const next = Math.exp(Math.log(distance) + (pixels / FULL_RANGE_PIXELS) * range);
  return Math.min(max, Math.max(min, next));
}

function mix(a: Vec3, b: Vec3, t: number): Vec3 {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
}

function scaleAbout(point: Vec3, value: Vec3, k: number): Vec3 {
  return [point[0] + (value[0] - point[0]) * k, point[1] + (value[1] - point[1]) * k, point[2] + (value[2] - point[2]) * k];
}

/**
 * New camera rig: scaled about `point`, so the point stays under the cursor. Zooming out
 * also drifts towards the home view and reaches it exactly at the maximum distance, so the
 * table is never lost off-centre.
 */
export function zoomRig(rig: Rig, point: Vec3, distance: number, next: number, home: Rig, max: number): Rig {
  const k = next / distance;
  let position = scaleAbout(point, rig.position, k);
  let target = scaleAbout(point, rig.target, k);
  if (next > distance) {
    const share = max > distance ? Math.min(1, Math.max(0, (next - distance) / (max - distance))) : 1;
    position = mix(position, home.position, share);
    target = mix(target, home.target, share);
  }
  return { position, target };
}
