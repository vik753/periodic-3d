/** Adaptive pixel-ratio controller (pure logic, used by AdaptiveQuality). */

/** Pixel ratios to step through; the highest one is the starting quality. */
const STEPS = [1, 1.25, 1.5, 1.75] as const;
/** Gaps longer than this are idle time (frameloop "demand"), not slow frames. */
const IDLE_GAP_S = 0.25;
const SLOW_FRAME_S = 1 / 42;
const FAST_FRAME_S = 1 / 56;
const DECLINE_AFTER_S = 1.5;
const INCLINE_AFTER_S = 8;

export interface QualityState {
  level: number;
  average: number;
  slow: number;
  fast: number;
}

/**
 * A background animation that asks for frames at a fixed, lower rate (the table's dust,
 * 30 FPS) sets the interval here. Frames that arrive on that beat are paced, not slow.
 */
export const framePacing = { interval: 0 };

/**
 * One step of the quality controller. Returns the new level.
 * Slow frames for 1.5 s of active rendering lower the pixel ratio by one step;
 * 8 s of fast frames raise it again, up to the device limit (maxLevel).
 * With pacedInterval > 0, frames that arrive about one pacing interval apart are skipped.
 */
export function nextQualityLevel(state: QualityState, delta: number, maxLevel: number, pacedInterval = 0): number {
  if (delta > IDLE_GAP_S) return state.level;
  if (pacedInterval > 0 && delta > pacedInterval * 0.8 && delta < pacedInterval * 1.4) return state.level;
  state.average = state.average * 0.9 + delta * 0.1;
  if (state.average > SLOW_FRAME_S) {
    state.slow += delta;
    state.fast = 0;
  } else if (state.average < FAST_FRAME_S) {
    state.fast += delta;
    state.slow = 0;
  } else {
    state.slow = 0;
    state.fast = 0;
  }
  if (state.slow > DECLINE_AFTER_S && state.level > 0) {
    state.level -= 1;
    state.slow = 0;
    state.average = 1 / 60; // give the new pixel ratio a fair start
  } else if (state.fast > INCLINE_AFTER_S && state.level < maxLevel) {
    state.level += 1;
    state.fast = 0;
  }
  return state.level;
}

/** Highest step not above the device pixel ratio (at least the first step). */
export function maxQualityLevel(devicePixelRatio: number): number {
  let level = 0;
  STEPS.forEach((step, index) => {
    if (step <= devicePixelRatio + 1e-6) level = index;
  });
  return level;
}

export function pixelRatioFor(level: number): number {
  return STEPS[Math.max(0, Math.min(level, STEPS.length - 1))] ?? 1;
}
