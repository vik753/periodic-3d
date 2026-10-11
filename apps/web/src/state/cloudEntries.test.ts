import { describe, expect, it } from 'vitest';

import type { IndexEntry } from '../data/compoundIndex';
import { CLOUD_MAX } from '../three/cloudLimits';
import { cloudEntries, predictedEntry } from './useCloud';

function known(count: number): IndexEntry[] {
  return Array.from({ length: count }, (_, index) => ({
    id: `Q${index}`,
    formula: 'X',
    zs: [8],
    fame: count - index,
    kind: null,
    names: {},
    haystack: '',
    plainFormula: '',
    mineral: false,
  }));
}

const predicted = Array.from({ length: 40 }, (_, index) =>
  predictedEntry({ id: `aaaa0000${String(index).padStart(2, '0')}`, formula: 'Fe2O3', names: {}, elements: ['Fe', 'O'], fame: 0, kind: 'crystal' }),
);

describe('cloud entries', () => {
  it('turns a predicted material into a violet cloud entry', () => {
    expect(predicted[0]).toMatchObject({ zs: [8, 26], predicted: true, kind: 'crystal' });
  });

  it('keeps known compounds in the core and fills the rest with predicted ones', () => {
    const mixed = cloudEntries(known(200), predicted);
    expect(mixed).toHaveLength(CLOUD_MAX);
    expect(mixed.filter((entry) => !entry.predicted)).toHaveLength(55);
    expect(mixed[0]?.predicted).toBeUndefined();
    expect(mixed.at(-1)?.predicted).toBe(true);
  });

  it('gives a small set all the room it needs', () => {
    expect(cloudEntries(known(10), predicted)).toHaveLength(50);
    expect(cloudEntries(known(200), [])).toHaveLength(CLOUD_MAX);
  });
});
