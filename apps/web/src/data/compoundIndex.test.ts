import { describe, expect, it } from 'vitest';

import type { CompoundIndex } from './api';
import { inGroup, normalizeText, parseIndex, queryCloud, searchIndex } from './compoundIndex';

const index: CompoundIndex = {
  version: 'test',
  fields: ['id', 'formula', 'elements', 'fame', 'kind', 'names'],
  rows: [
    ['Q283', 'H₂O', [1, 8], 330, 'molecule', { en: 'Water', ru: 'Вода', uk: 'Вода' }],
    ['Q36933', 'O₃', [8], 107, 'molecule', { en: 'Ozone', ru: 'Озон' }],
    ['Q103223', 'Fe₂O₃', [8, 26], 73, 'crystal', { en: 'Hematite', ru: 'Гематит', uk: 'Гематит' }, 1],
    ['Q189703', 'FeO(OH)', [1, 8, 26], 54, 'crystal', { en: 'Goethite', ru: 'Гётит' }, 1],
    ['Q2270', 'C₆H₆', [1, 6], 93, 'molecule', { en: 'Benzene' }, 0],
  ],
};

describe('compound index', () => {
  const entries = parseIndex(index);

  it('normalizes text for search', () => {
    expect(normalizeText('Гемати́т')).toBe('гематит');
    expect(normalizeText('H₂O')).toBe('h2o');
    expect(normalizeText('Гётит')).toBe('гетит');
    expect(normalizeText('NH₄⁺')).toBe('nh4');
  });

  it('finds compounds with all selected elements', () => {
    const result = queryCloud(entries, [8, 26], 'contains');
    expect(result.items.map((entry) => entry.id)).toEqual(['Q103223', 'Q189703']);
    expect([...result.extras.entries()]).toEqual([[1, 1]]);
  });

  it('finds compounds of exactly the selected elements', () => {
    expect(queryCloud(entries, [8, 26], 'only').items.map((entry) => entry.id)).toEqual(['Q103223']);
    expect(queryCloud(entries, [8], 'only').items.map((entry) => entry.id)).toEqual(['Q36933']);
  });

  it('filters the cloud by group and counts every group', () => {
    const result = queryCloud(entries, [1], 'contains', 'mineral');
    expect(result.items.map((entry) => entry.id)).toEqual(['Q189703']);
    expect(result.groups).toEqual({ all: 3, organic: 1, inorganic: 2, mineral: 1 });
    expect(queryCloud(entries, [1], 'contains', 'organic').items.map((entry) => entry.id)).toEqual(['Q2270']);
  });

  it('reads flags and treats old rows without them as non-minerals', () => {
    const byId = new Map(entries.map((entry) => [entry.id, entry]));
    expect(byId.get('Q103223')?.mineral).toBe(true);
    expect(byId.get('Q283')?.mineral).toBe(false);
    expect(inGroup(byId.get('Q2270')!, 'organic')).toBe(true);
    expect(inGroup(byId.get('Q283')!, 'inorganic')).toBe(true);
  });

  it('searches formulas and names in all languages', () => {
    expect(searchIndex(entries, 'h2o')[0]?.id).toBe('Q283');
    expect(searchIndex(entries, 'гетит')[0]?.id).toBe('Q189703');
    expect(searchIndex(entries, 'гем')[0]?.id).toBe('Q103223');
    expect(searchIndex(entries, '   ')).toEqual([]);
  });
});
