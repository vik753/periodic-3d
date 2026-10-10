import { useQuery } from '@tanstack/react-query';

import type { CompoundDetail, ElementDetail, ElementList, Meta, PairDetail } from './api';
import { fetchJson, metaUrl, NotFoundError, resourceUrl } from './source';

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
    queryFn: ({ signal }) => fetchJson<T>(resourceUrl(version as string, path as string), signal),
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
  return useDataset<ElementList>('elements');
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
