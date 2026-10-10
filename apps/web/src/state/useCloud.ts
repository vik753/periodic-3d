import { useMemo } from 'react';

import type { CloudResult } from '../data/compoundIndex';
import { queryCloud, useCompoundIndex } from '../data/compoundIndex';
import { useMeta } from '../data/hooks';
import { elementBySymbol } from '../data/periodic';
import { useAppStore } from './store';

export interface CloudState {
  /** Atomic numbers of the selected elements. */
  zs: number[];
  result: CloudResult | null;
  isPending: boolean;
  /** No dataset is deployed (demo mode). */
  unavailable: boolean;
}

/** The compounds of the current multi-element selection (set scene). */
export function useCloud(): CloudState {
  const scene = useAppStore((state) => state.scene);
  const mode = useAppStore((state) => state.cloudMode);
  const active = scene.kind === 'set';
  const key = active ? scene.symbols.join('-') : '';
  const zs = useMemo(
    () =>
      key
        .split('-')
        .map((symbol) => elementBySymbol(symbol)?.z)
        .filter((z): z is number => z != null),
    [key],
  );
  const meta = useMeta();
  const index = useCompoundIndex(active);
  const result = useMemo(
    () => (index.data && zs.length > 0 ? queryCloud(index.data, zs, mode) : null),
    [index.data, zs, mode],
  );
  return { zs, result, isPending: active && index.isPending && !meta.isError, unavailable: meta.isError };
}
