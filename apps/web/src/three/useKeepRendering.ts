import { useFrame, useThree } from '@react-three/fiber';
import { useEffect } from 'react';

/**
 * The canvas renders on demand (frameloop="demand") to save battery on static
 * screens. Components that animate call this hook: while `active` is true it
 * requests the next frame after every rendered frame.
 */
export function useKeepRendering(active: boolean): void {
  const invalidate = useThree((state) => state.invalidate);
  useEffect(() => {
    if (active) invalidate();
  }, [active, invalidate]);
  useFrame(() => {
    if (active) invalidate();
  });
}

/** True when the visitor asked the OS to reduce motion. */
export function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true;
}

/** Frame-rate independent exponential smoothing. */
export function damp(current: number, target: number, lambda: number, dt: number): number {
  return current + (target - current) * (1 - Math.exp(-lambda * dt));
}
