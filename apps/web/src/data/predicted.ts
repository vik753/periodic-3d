/**
 * Helpers for the layer of predicted materials (GNoME, ADR 0007): partners of an element,
 * the materials of a pair and of a set of elements, from the compact API files.
 */

import type { CompoundSummary, MaterialList, MaterialListRow, MaterialPairs, Partner } from './api';
import { elementByZ } from './periodic';

/** Element symbols a formula names, once each: "PrNdPa(InPd)3" → Pr, Nd, Pa, In, Pd. */
export function formulaElements(formula: string): string[] {
  return [...new Set(formula.match(/[A-Z][a-z]?/g) ?? [])];
}

/** How many predicted materials contain the element. */
export function predictedCount(pairs: MaterialPairs, z: number): number {
  return pairs.elements.find(([value]) => value === z)?.[1] ?? 0;
}

/** Partners of an element among predicted materials: one violet ray each, most materials first. */
export function predictedPartners(pairs: MaterialPairs, z: number): Partner[] {
  const partners: Partner[] = [];
  for (const [a, b, count] of pairs.pairs) {
    if (a !== z && b !== z) continue;
    const other = a === z ? b : a;
    const cell = elementByZ(other);
    if (cell) partners.push({ z: other, symbol: cell.symbol, count });
  }
  return partners.sort((x, y) => y.count - x.count || x.z - y.z);
}

/** Number of predicted materials with both elements. */
export function predictedPairCount(pairs: MaterialPairs, za: number, zb: number): number {
  const [a, b] = za < zb ? [za, zb] : [zb, za];
  return pairs.pairs.find(([x, y]) => x === a && y === b)?.[2] ?? 0;
}

/** Of several elements, the one with the fewest predicted materials: its list is the smallest file. */
export function rarestElement(pairs: MaterialPairs, zs: number[]): number | null {
  let best: number | null = null;
  let bestCount = Infinity;
  for (const z of zs) {
    const count = predictedCount(pairs, z);
    if (count < bestCount) {
      best = z;
      bestCount = count;
    }
  }
  return best;
}

/**
 * Rows of an element list that contain all `symbols` ("contains") or exactly them
 * ("only"). The list is already ordered: fewer elements first, then the most stable.
 */
export function filterMaterials(list: MaterialList, symbols: string[], mode: 'contains' | 'only' = 'contains'): MaterialListRow[] {
  return list.rows.filter((row) => {
    const elements = formulaElements(row[1]);
    if (!symbols.every((symbol) => elements.includes(symbol))) return false;
    return mode === 'contains' || elements.length === symbols.length;
  });
}

/** A predicted material in the shape the walk and the cloud use for compounds. */
export function materialSummary(row: MaterialListRow): CompoundSummary {
  return { id: row[0], formula: row[1], names: {}, elements: formulaElements(row[1]), fame: 0, kind: 'crystal' };
}
