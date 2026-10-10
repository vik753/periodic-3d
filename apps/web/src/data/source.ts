/**
 * Where the data comes from (ADR 0003).
 *
 * static (default): JSON files exported from the API, served with the site:
 *   <base>data/meta.json, then <base>data/<version>/<path>.json
 * api: the live API: <VITE_API_URL>/<path>  (VITE_DATA_MODE=api)
 *
 * The path is the same in both modes: "elements/Fe", "compounds/Q283", "pairs/O-Fe".
 */

export type DataMode = 'static' | 'api';

export const DATA_MODE: DataMode = import.meta.env.VITE_DATA_MODE === 'api' ? 'api' : 'static';

const API_URL = String(import.meta.env.VITE_API_URL ?? '/api/v1').replace(/\/$/, '');
const STATIC_ROOT = `${import.meta.env.BASE_URL}data`;

/** The resource does not exist (unknown compound, or no dataset deployed). */
export class NotFoundError extends Error {
  constructor(readonly url: string) {
    super(`not found: ${url}`);
    this.name = 'NotFoundError';
  }
}

export function metaUrl(mode: DataMode = DATA_MODE): string {
  return mode === 'api' ? `${API_URL}/meta` : `${STATIC_ROOT}/meta.json`;
}

export function resourceUrl(version: string, path: string, mode: DataMode = DATA_MODE): string {
  return mode === 'api' ? `${API_URL}/${path}` : `${STATIC_ROOT}/${encodeURIComponent(version)}/${path}.json`;
}

export async function fetchJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal, headers: { Accept: 'application/json' } });
  if (response.status === 404) throw new NotFoundError(url);
  if (!response.ok) throw new Error(`HTTP ${response.status} for ${url}`);
  const type = response.headers.get('content-type') ?? '';
  // A static host may answer a missing file with the SPA page: that is "not found" too.
  if (type.includes('text/html')) throw new NotFoundError(url);
  return (await response.json()) as T;
}

/** Pair path in the dataset order: lower atomic number first ("O-Fe", not "Fe-O"). */
export function pairPath(a: { z: number; symbol: string }, b: { z: number; symbol: string }): string {
  const [first, second] = a.z <= b.z ? [a, b] : [b, a];
  return `pairs/${first.symbol}-${second.symbol}`;
}
