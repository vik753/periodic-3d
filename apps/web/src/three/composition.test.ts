import { describe, expect, it } from 'vitest';

import { partRadius, RING_RADIUS, ringPositions, ringRadius } from './composition';

describe('composition layout', () => {
  it('puts a single element in the centre and others on a ring', () => {
    expect(ringPositions(1)).toEqual([[0, 0, 0]]);
    const ring = ringPositions(4);
    expect(ring).toHaveLength(4);
    for (const [x, y, z] of ring) {
      expect(Math.hypot(x, y)).toBeCloseTo(RING_RADIUS);
      expect(z).toBe(0);
    }
    expect(ring[0]![1]).toBeCloseTo(RING_RADIUS); // first element on top
    const pair = ringPositions(2);
    expect(pair[0]![0]).toBeCloseTo(-RING_RADIUS); // two elements: left and right
    expect(pair[1]![0]).toBeCloseTo(RING_RADIUS);
  });

  it('grows spheres slowly and caps them', () => {
    expect(partRadius(1)).toBeCloseTo(0.48);
    expect(partRadius(6)).toBeGreaterThan(partRadius(1));
    expect(partRadius(257)).toBe(1.15);
  });

  it('widens the ring so big spheres do not touch', () => {
    expect(ringRadius([0.5])).toBe(0);
    expect(ringRadius([0.5, 0.5])).toBe(RING_RADIUS);
    const radius = ringRadius([1.15, 1.15, 1.15, 1.15, 1.15, 1.15]);
    const gap = 2 * radius * Math.sin(Math.PI / 6) - 2 * 1.15;
    expect(gap).toBeGreaterThanOrEqual(0.5 - 1e-9);
  });
});
