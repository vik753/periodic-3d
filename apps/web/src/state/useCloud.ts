import { useMemo } from 'react';

import type { CompoundSummary } from '../data/api';
import type { CloudResult, IndexEntry } from '../data/compoundIndex';
import { queryCloud, useCompoundIndex } from '../data/compoundIndex';
import { useMeta, usePredictedSet } from '../data/hooks';
import { elementBySymbol } from '../data/periodic';
import { CLOUD_MAX } from '../three/cloudLimits';
import { useAppStore } from './store';

/** Predicted materials in the cloud and in its list, at most. */
export const PREDICTED_CLOUD_SIZE = 40;
/** Known compounds keep at least this many orbs when predicted ones join the cloud. */
const KNOWN_SHARE = 55;

export interface PredictedCloud {
  entries: IndexEntry[];
  total: number;
}

/** A predicted material as a cloud entry (violet orb). */
export function predictedEntry(material: CompoundSummary): IndexEntry {
  const zs = material.elements
    .map((symbol) => elementBySymbol(symbol)?.z)
    .filter((z): z is number => z != null)
    .sort((a, b) => a - b);
  return {
    id: material.id,
    formula: material.formula,
    zs,
    fame: 0,
    kind: 'crystal',
    names: {},
    haystack: '',
    plainFormula: '',
    mineral: false,
    predicted: true,
  };
}

/** Orbs of the cloud: known compounds in the core, predicted ones around them. */
export function cloudEntries(known: IndexEntry[], predicted: IndexEntry[]): IndexEntry[] {
  const knownShown = Math.min(known.length, predicted.length > 0 ? Math.max(KNOWN_SHARE, CLOUD_MAX - predicted.length) : CLOUD_MAX);
  const predictedShown = Math.min(predicted.length, CLOUD_MAX - knownShown);
  return [...known.slice(0, knownShown), ...predicted.slice(0, predictedShown)];
}

export interface CloudState {
  /** Atomic numbers of the selected elements. */
  zs: number[];
  result: CloudResult | null;
  /** Predicted materials of the set, when the layer is switched on. */
  predicted: PredictedCloud | null;
  predictedPending: boolean;
  isPending: boolean;
  /** No dataset is deployed (demo mode). */
  unavailable: boolean;
}

/** The compounds of the current multi-element selection (set scene). */
export function useCloud(): CloudState {
  const scene = useAppStore((state) => state.scene);
  const mode = useAppStore((state) => state.cloudMode);
  const group = useAppStore((state) => state.cloudGroup);
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
    () => (index.data && zs.length > 0 ? queryCloud(index.data, zs, mode, group) : null),
    [index.data, zs, mode, group],
  );
  const showPredicted = useAppStore((state) => state.showPredicted);
  const set = usePredictedSet(active && showPredicted && key ? key.split('-') : null, mode, PREDICTED_CLOUD_SIZE);
  const predicted = useMemo(
    () => (set.data ? { entries: set.data.materials.map(predictedEntry), total: set.data.total } : null),
    [set.data],
  );
  return {
    zs,
    result,
    predicted: active && showPredicted ? predicted : null,
    predictedPending: active && showPredicted && set.isPending,
    isPending: active && index.isPending && !meta.isError,
    unavailable: meta.isError,
  };
}
