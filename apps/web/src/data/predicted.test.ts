import { describe, expect, it } from 'vitest';

import type { MaterialList, MaterialPairs } from './api';
import {
  filterMaterials,
  formulaElements,
  materialSummary,
  predictedCount,
  predictedPairCount,
  predictedPartners,
  rarestElement,
} from './predicted';

const PAIRS: MaterialPairs = {
  version: 'gnome-test',
  elements: [
    [1, 2],
    [8, 4],
    [26, 3],
  ],
  pairs: [
    [1, 8, 2],
    [1, 26, 1],
    [8, 26, 3],
  ],
};

const OXYGEN: MaterialList = {
  version: 'gnome-test',
  symbol: 'O',
  total: 4,
  fields: ['id', 'formula', 'decompositionEnergy'],
  rows: [
    ['bbbb000003', 'Fe3O4', -0.031],
    ['aaaa000001', 'Fe2O3', -0.012],
    ['cccc000004', 'H2O2', null],
    ['aaaa000002', 'FeHO2', 0],
  ],
};

describe('predicted materials', () => {
  it('reads elements from a formula, brackets included', () => {
    expect(formulaElements('PrNdPa(InPd)3')).toEqual(['Pr', 'Nd', 'Pa', 'In', 'Pd']);
    expect(formulaElements('Fe2O3')).toEqual(['Fe', 'O']);
  });

  it('lists partners with the most materials first', () => {
    expect(predictedPartners(PAIRS, 8)).toEqual([
      { z: 26, symbol: 'Fe', count: 3 },
      { z: 1, symbol: 'H', count: 2 },
    ]);
    expect(predictedCount(PAIRS, 26)).toBe(3);
    expect(predictedPairCount(PAIRS, 26, 8)).toBe(3);
    expect(predictedPairCount(PAIRS, 26, 2)).toBe(0);
  });

  it('picks the element with the smallest list', () => {
    expect(rarestElement(PAIRS, [8, 26, 1])).toBe(1);
  });

  it('filters a list by elements, keeping its order', () => {
    expect(filterMaterials(OXYGEN, ['O', 'Fe']).map((row) => row[0])).toEqual([
      'bbbb000003',
      'aaaa000001',
      'aaaa000002',
    ]);
    expect(filterMaterials(OXYGEN, ['O', 'Fe'], 'only').map((row) => row[0])).toEqual(['bbbb000003', 'aaaa000001']);
  });

  it('shapes a row like a compound summary', () => {
    expect(materialSummary(['aaaa000001', 'Fe2O3', -0.012])).toEqual({
      id: 'aaaa000001',
      formula: 'Fe2O3',
      names: {},
      elements: ['Fe', 'O'],
      fame: 0,
      kind: 'crystal',
    });
  });
});
