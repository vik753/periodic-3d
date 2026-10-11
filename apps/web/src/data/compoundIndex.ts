/**
 * The compact list of all compounds (index.json). The browser filters it for the
 * multi-element cloud and for search, the same way in the static and the live mode.
 */

import { useQuery } from '@tanstack/react-query';

import type { CompoundIndex, Names, StructureKind } from './api';
import { useMeta } from './hooks';
import { fetchJson, resourceUrl } from './source';

export interface IndexEntry {
  id: string;
  formula: string;
  /** Atomic numbers of the elements, ascending. */
  zs: number[];
  fame: number;
  kind: StructureKind | null;
  names: Names;
  /** Normalized formula and names for search. */
  haystack: string;
  /** Normalized formula alone, for exact formula matches ("h2o"). */
  plainFormula: string;
  /** Wikidata "mineral species". */
  mineral: boolean;
}

const FLAG_MINERAL = 1;
const Z_HYDROGEN = 1;
const Z_CARBON = 6;

const SUBSCRIPT_DIGITS = /[₀-₉]/g;
const SUPERSCRIPTS = /[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]/g;
const COMBINING_MARKS = /[̀-ͯ]/g;

/** Lower case, no stress marks or diacritics, "₂" → "2", "ё" → "е": "Гемати́т" → "гематит". */
export function normalizeText(text: string): string {
  return text
    .toLowerCase()
    .replace(/ё/g, 'е')
    .replace(/й/g, 'и')
    .normalize('NFD')
    .replace(COMBINING_MARKS, '')
    .replace(SUBSCRIPT_DIGITS, (digit) => String(digit.charCodeAt(0) - 0x2080))
    .replace(SUPERSCRIPTS, '')
    .replace(/\s+/g, ' ')
    .trim();
}

export function parseIndex(index: CompoundIndex): IndexEntry[] {
  return index.rows.map(([id, formula, zs, fame, kind, names, flags = 0]) => {
    const plainFormula = normalizeText(formula).replace(/\s/g, '');
    return {
      id,
      formula,
      zs: [...zs].sort((a, b) => a - b),
      fame,
      kind,
      names,
      plainFormula,
      mineral: (flags & FLAG_MINERAL) !== 0,
      haystack: [plainFormula, ...Object.values(names).map((name) => normalizeText(name ?? ''))].join(' | '),
    };
  });
}

export function useCompoundIndex(enabled = true) {
  const meta = useMeta();
  const version = meta.data?.version;
  return useQuery({
    queryKey: ['dataset', version, 'index'],
    queryFn: async ({ signal }) => parseIndex(await fetchJson<CompoundIndex>(resourceUrl(version as string, 'index'), signal)),
    enabled: enabled && Boolean(version),
  });
}

export type CloudMode = 'contains' | 'only';

/** Filter of the cloud by kind of substance. Organic: has carbon and hydrogen. */
export type CompoundGroup = 'all' | 'organic' | 'inorganic' | 'mineral';
export const COMPOUND_GROUPS: readonly CompoundGroup[] = ['all', 'organic', 'inorganic', 'mineral'];

export function inGroup(entry: IndexEntry, group: CompoundGroup): boolean {
  if (group === 'all') return true;
  if (group === 'mineral') return entry.mineral;
  const organic = entry.zs.includes(Z_CARBON) && entry.zs.includes(Z_HYDROGEN);
  return group === 'organic' ? organic : !organic;
}

export interface CloudResult {
  total: number;
  /** Matches per group before the group filter (for the filter chips). */
  groups: Record<CompoundGroup, number>;
  /** Matching compounds, most famous first. */
  items: IndexEntry[];
  /** Elements that occur in the matches besides the selected ones, with how many matches have each. */
  extras: Map<number, number>;
}

/** Compounds that contain all the selected elements, or consist of exactly them. */
export function queryCloud(
  entries: IndexEntry[],
  selected: number[],
  mode: CloudMode,
  group: CompoundGroup = 'all',
): CloudResult {
  const wanted = [...new Set(selected)];
  const matches = entries.filter(
    (entry) => wanted.every((z) => entry.zs.includes(z)) && (mode === 'contains' || entry.zs.length === wanted.length),
  );
  const groups = Object.fromEntries(
    COMPOUND_GROUPS.map((name) => [name, matches.filter((entry) => inGroup(entry, name)).length]),
  ) as Record<CompoundGroup, number>;
  const items = group === 'all' ? matches : matches.filter((entry) => inGroup(entry, group));
  const extras = new Map<number, number>();
  for (const entry of items) {
    for (const z of entry.zs) if (!wanted.includes(z)) extras.set(z, (extras.get(z) ?? 0) + 1);
  }
  return { total: items.length, groups, items, extras };
}

/** Search by formula or name in any language; best matches first, famous ones break ties. */
export function searchIndex(entries: IndexEntry[], query: string, limit = 12): IndexEntry[] {
  const needle = normalizeText(query);
  if (!needle) return [];
  const compact = needle.replace(/\s/g, '');
  const scored: Array<{ entry: IndexEntry; score: number }> = [];
  for (const entry of entries) {
    let score = 0;
    if (entry.plainFormula === compact) score = 100;
    else if (entry.haystack.startsWith(needle)) score = 70;
    else if (entry.haystack.includes(` ${needle}`) || entry.haystack.includes(`| ${needle}`)) score = 60;
    else if (entry.haystack.includes(needle)) score = 40;
    if (score > 0) scored.push({ entry, score: score + Math.log1p(entry.fame) });
  }
  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, limit).map((item) => item.entry);
}
