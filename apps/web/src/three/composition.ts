/** Layout of the composition stand-in (CompositionView), kept free of React for tests. */

import type { Vec3 } from '../data/structure';

/** Radius of the ring of element spheres, world units. */
export const RING_RADIUS = 1.9;

export interface CompositionPart {
  symbol: string;
  count: number;
}

/** Sphere size grows slowly with the atom count, so C₂₅₇ does not swallow S₆. */
export function partRadius(count: number): number {
  return Math.min(0.32 + 0.16 * Math.log2(1 + Math.max(count, 0)), 1.15);
}

/** Positions on a ring in the XY plane; a single element sits in the centre. */
export function ringPositions(count: number, radius = RING_RADIUS): Vec3[] {
  if (count <= 1) return [[0, 0, 0]];
  return Array.from({ length: count }, (_, index) => {
    const angle = Math.PI / 2 - (2 * Math.PI * index) / count;
    return [radius * Math.cos(angle), radius * Math.sin(angle), 0] as Vec3;
  });
}

/** Ring radius that keeps neighbouring spheres apart (at least RING_RADIUS). */
export function ringRadius(radii: number[]): number {
  if (radii.length <= 1) return 0;
  const largest = Math.max(...radii);
  return Math.max(RING_RADIUS, (2 * largest + 0.5) / (2 * Math.sin(Math.PI / radii.length)));
}
