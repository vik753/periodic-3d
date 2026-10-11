import { useFrame, useThree } from '@react-three/fiber';
import { useRef } from 'react';

import type { QualityState } from './quality';
import { framePacing, maxQualityLevel, nextQualityLevel, pixelRatioFor } from './quality';

/**
 * Keeps the frame rate within the budget (60 FPS on laptops, 45+ on phones) by
 * rendering fewer pixels when frames get slow. Geometry and effects stay the same.
 */
export function AdaptiveQuality() {
  const setDpr = useThree((state) => state.setDpr);
  const maxLevel = useRef(maxQualityLevel(window.devicePixelRatio || 1));
  const state = useRef<QualityState>({ level: maxLevel.current, average: 1 / 60, slow: 0, fast: 0 });

  useFrame((_, delta) => {
    const before = state.current.level;
    const after = nextQualityLevel(state.current, delta, maxLevel.current, framePacing.interval);
    if (after !== before) {
      setDpr(pixelRatioFor(after));
      if (window.__p3d) window.__p3d.dpr = pixelRatioFor(after);
    }
  });
  return null;
}
