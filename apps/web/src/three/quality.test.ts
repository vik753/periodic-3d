import { describe, expect, it } from 'vitest';

import type { QualityState } from './quality';
import { maxQualityLevel, nextQualityLevel, pixelRatioFor } from './quality';

function run(state: QualityState, delta: number, seconds: number, maxLevel: number): number {
  let level = state.level;
  for (let time = 0; time < seconds; time += delta) level = nextQualityLevel(state, delta, maxLevel);
  return level;
}

describe('adaptive quality', () => {
  it('caps the pixel ratio by the device', () => {
    expect(pixelRatioFor(maxQualityLevel(1))).toBe(1);
    expect(pixelRatioFor(maxQualityLevel(1.5))).toBe(1.5);
    expect(pixelRatioFor(maxQualityLevel(3))).toBe(1.75);
  });

  it('steps down after slow frames and back up after fast ones', () => {
    const state: QualityState = { level: 3, average: 1 / 60, slow: 0, fast: 0 };
    expect(run(state, 1 / 30, 2.5, 3)).toBe(2);
    expect(run(state, 1 / 30, 10, 3)).toBe(0);
    expect(run(state, 1 / 60, 9, 3)).toBe(1);
  });

  it('ignores idle gaps between on-demand frames', () => {
    const state: QualityState = { level: 3, average: 1 / 60, slow: 0, fast: 0 };
    for (let i = 0; i < 20; i += 1) nextQualityLevel(state, 2, 3);
    expect(state.level).toBe(3);
    expect(state.average).toBeCloseTo(1 / 60);
  });

  it('treats frames on the pacing beat as paced, not slow', () => {
    const state: QualityState = { level: 3, average: 1 / 60, slow: 0, fast: 0 };
    for (let i = 0; i < 300; i += 1) nextQualityLevel(state, 1 / 30, 3, 1 / 30);
    expect(state.level).toBe(3);
    // A device that cannot keep the beat still steps down.
    for (let i = 0; i < 100; i += 1) nextQualityLevel(state, 1 / 20, 3, 1 / 30);
    expect(state.level).toBeLessThan(3);
  });
});
