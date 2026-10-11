import { describe, expect, it } from 'vitest';

import { FULL_RANGE_PIXELS, wheelPixels, zoomDistance, zoomRig } from './zoom';

describe('table zoom', () => {
  it('crosses the whole range in one firm scroll', () => {
    expect(zoomDistance(24, -FULL_RANGE_PIXELS, 2.4, 24)).toBeCloseTo(2.4);
    expect(zoomDistance(24, -FULL_RANGE_PIXELS / 2, 2.4, 24)).toBeCloseTo(Math.sqrt(24 * 2.4));
    expect(zoomDistance(2.4, 10_000, 2.4, 24)).toBe(24);
  });

  it('converts lines and pages to pixels', () => {
    expect(wheelPixels(3, 1)).toBe(120);
    expect(wheelPixels(1, 2)).toBe(800);
    expect(wheelPixels(53, 0)).toBe(53);
  });

  it('keeps the point under the cursor and returns home when zoomed out', () => {
    const home = { position: [0, 0, 20] as [number, number, number], target: [0, 0, 0] as [number, number, number] };
    const point: [number, number, number] = [4, 2, 0];
    const closer = zoomRig(home, point, 20, 5, home, 22);
    expect(closer.target).toEqual([3, 1.5, 0]);
    expect(closer.position).toEqual([3, 1.5, 5]);
    const back = zoomRig(closer, point, 5, 22, home, 22);
    expect(back.target).toEqual(home.target);
    expect(back.position).toEqual(home.position);
  });
});
