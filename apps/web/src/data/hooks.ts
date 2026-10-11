import { useQuery } from '@tanstack/react-query';
import { useEffect, useMemo } from 'react';

import type {
  CompoundDetail,
  ElementDetail,
  ElementList,
  Material,
  MaterialList,
  MaterialPairs,
  MaterialShard,
  Meta,
  PairDetail,
} from './api';
import { registerElementColors } from './chemistry';
import { elementBySymbol, elementByZ } from './periodic';
import {
  filterMaterials,
  materialSummary,
  predictedCount,
  predictedPairCount,
  predictedPartners,
  rarestElement,
} from './predicted';
import { checkFreshVersion, fetchJson, metaUrl, NotFoundError, resourceUrl } from './source';

/** Retry network hiccups, not missing files. */
function retry(failureCount: number, error: unknown): boolean {
  return !(error instanceof NotFoundError) && failureCount < 2;
}

export function useMeta() {
  return useQuery({
    queryKey: ['meta'],
    queryFn: ({ signal }) => fetchJson<Meta>(metaUrl(), signal),
    retry,
  });
}

/** A dataset file of the current version. `path` null keeps the query idle. */
function useDataset<T>(path: string | null) {
  const meta = useMeta();
  const version = meta.data?.version;
  const query = useQuery({
    queryKey: ['dataset', version, path],
    queryFn: async ({ signal }) => {
      try {
        return await fetchJson<T>(resourceUrl(version as string, path as string), signal);
      } catch (error) {
        // An old page asks for a dataset the site no longer has: reload for the new one.
        if (error instanceof NotFoundError) checkFreshVersion(version as string, (fresh) => fresh.version);
        throw error;
      }
    },
    enabled: Boolean(version && path),
    retry,
  });
  return {
    ...query,
    /** True when no dataset is deployed: the app falls back to built-in demo data. */
    unavailable: meta.isError,
    isPending: query.isPending && !meta.isError && path !== null,
  };
}

export function useElements() {
  const query = useDataset<ElementList>('elements');
  useEffect(() => {
    if (query.data) registerElementColors(query.data.elements);
  }, [query.data]);
  return query;
}

export function useElement(symbol: string | null) {
  return useDataset<ElementDetail>(symbol ? `elements/${symbol}` : null);
}

export function useCompound(id: string | null) {
  return useDataset<CompoundDetail>(id && !id.startsWith('demo-') ? `compounds/${id}` : null);
}

export function usePair(path: string | null) {
  return useDataset<PairDetail>(path);
}

/** Characters of a material id that name its shard file (MATERIAL_SHARD_CHARS in the API). */
export const MATERIAL_SHARD_CHARS = 4;

/** True for a GNoME material id: 10 hex characters. */
export function isMaterialId(id: string): boolean {
  return /^[0-9a-f]{10}$/.test(id);
}

/** A file of the GNoME layer (its own version). Idle when the site has no layer or `path` is null. */
function useGnomeFile<T>(path: string | null) {
  const meta = useMeta();
  const version = meta.data?.gnome?.version;
  const query = useQuery({
    queryKey: ['gnome', version, path],
    queryFn: async ({ signal }) => {
      try {
        return await fetchJson<T>(resourceUrl(version as string, path as string), signal);
      } catch (error) {
        if (error instanceof NotFoundError) checkFreshVersion(version as string, (fresh) => fresh.gnome?.version);
        throw error;
      }
    },
    enabled: Boolean(version && path),
    retry,
    staleTime: Infinity,
  });
  return {
    ...query,
    /** The site has no layer of predicted materials. */
    unavailable: meta.isError || (meta.isSuccess && !meta.data?.gnome),
    isPending: query.isPending && Boolean(version) && path !== null,
  };
}

/** The layer's description from meta.json (license, citation, counts), or null. */
export function useGnome() {
  const meta = useMeta();
  return meta.data?.gnome ?? null;
}

/** One predicted material: its shard file holds about 8 materials (≈ 3 KB gzip). */
export function useMaterial(id: string | null) {
  const valid = id && isMaterialId(id) ? id : null;
  const shard = useGnomeFile<MaterialShard>(valid ? `materials/shard/${valid.slice(0, MATERIAL_SHARD_CHARS)}` : null);
  const material: Material | undefined = shard.data?.materials.find((item) => item.id === valid);
  return { ...shard, data: material, missing: shard.isSuccess && !material };
}

/** Counts of predicted materials per element and per pair of elements (≈ 12 KB gzip). */
export function useMaterialPairs(enabled = true) {
  return useGnomeFile<MaterialPairs>(enabled ? 'materials/pairs' : null);
}

/** Every predicted material that contains the element; loaded only when asked for. */
export function useMaterialsByElement(symbol: string | null) {
  return useGnomeFile<MaterialList>(symbol ? `materials/by-element/${symbol}` : null);
}

/** Rays of predicted materials for an element: partners and the element's own count. */
export function usePredictedPartners(symbol: string | null, enabled: boolean) {
  const cell = symbol ? elementBySymbol(symbol) : undefined;
  const pairs = useMaterialPairs(enabled && Boolean(cell));
  const data = useMemo(
    () =>
      pairs.data && cell
        ? { partners: predictedPartners(pairs.data, cell.z), count: predictedCount(pairs.data, cell.z) }
        : undefined,
    [pairs.data, cell],
  );
  return { ...pairs, data };
}

/** How many predicted beads a walk shows (RayWalk draws at most 30). */
export const PREDICTED_WALK_SIZE = 30;

/**
 * Predicted materials of a set of elements, read from the list of its rarest element:
 * the simplest and most stable first. A pair is a set of two.
 */
export function usePredictedSet(symbols: string[] | null, mode: 'contains' | 'only' = 'contains', limit = PREDICTED_WALK_SIZE) {
  const key = symbols?.join('-') ?? '';
  const zs = useMemo(
    () => (key ? key.split('-').map((symbol) => elementBySymbol(symbol)?.z ?? 0).filter((z) => z > 0) : []),
    [key],
  );
  const pairs = useMaterialPairs(zs.length > 0);
  const rarest = pairs.data ? rarestElement(pairs.data, zs) : null;
  const rarestSymbol = rarest != null ? (elementByZ(rarest)?.symbol ?? null) : null;
  // An element without predicted materials has no list file: the set is empty.
  const hasList = Boolean(pairs.data && rarest != null && predictedCount(pairs.data, rarest) > 0);
  const list = useMaterialsByElement(hasList ? rarestSymbol : null);
  const data = useMemo(() => {
    if (!pairs.data) return undefined;
    if (!hasList) return { total: 0, materials: [] };
    if (!list.data) return undefined;
    const symbolsInSet = zs.map((z) => elementByZ(z)?.symbol ?? '');
    const rows = filterMaterials(list.data, symbolsInSet, mode);
    const total = zs.length === 2 && mode === 'contains' ? predictedPairCount(pairs.data, zs[0]!, zs[1]!) : rows.length;
    return { total, materials: rows.slice(0, limit).map(materialSummary) };
  }, [pairs.data, hasList, list.data, zs, mode, limit]);
  return {
    data,
    isPending: data === undefined && !pairs.isError && !list.isError && !pairs.unavailable,
    isError: pairs.isError || list.isError,
    unavailable: pairs.unavailable,
  };
}
