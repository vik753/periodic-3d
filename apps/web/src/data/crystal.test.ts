import { describe, expect, it } from 'vitest';

import { crystalBonds, crystalFromCell, decodeSites, latticeVectors, supercellRepeats } from './crystal';

// Encoded like the API does (apps/api/src/p3d_api/repository.py, encode_sites).
const BCC_IRON = 'GgAAAAAAABqIE4gTiBM='; // Fe (0, 0, 0) and Fe (½, ½, ½)
const ROCK_PAIR = 'CwAAAAAAABGIE4gTiBM='; // Na (0, 0, 0) and Cl (½, ½, ½)

describe('compact crystal cells', () => {
  it('decodes 7-byte site records', () => {
    expect(decodeSites(BCC_IRON)).toEqual([
      { el: 'Fe', frac: [0, 0, 0] },
      { el: 'Fe', frac: [0.5, 0.5, 0.5] },
    ]);
    expect(decodeSites('GgAADyeIEw==')).toEqual([{ el: 'Fe', frac: [0, 0.9999, 0.5] }]);
    expect(decodeSites('not base64!')).toEqual([]);
  });

  it('turns cell parameters into lattice vectors', () => {
    const cubic = latticeVectors([3, 3, 3, 90, 90, 90]);
    cubic.flat().forEach((value, index) => expect(value).toBeCloseTo([3, 0, 0, 0, 3, 0, 0, 0, 3][index]!, 9));
    const [a, b, c] = latticeVectors([2.5, 2.5, 4, 90, 90, 120]);
    expect(Math.hypot(...a)).toBeCloseTo(2.5);
    expect(Math.hypot(...b)).toBeCloseTo(2.5);
    expect(Math.hypot(...c)).toBeCloseTo(4);
    const angle = (Math.acos((a[0] * b[0] + a[1] * b[1]) / (2.5 * 2.5)) * 180) / Math.PI;
    expect(angle).toBeCloseTo(120);
  });

  it('repeats only tiny cells into a block', () => {
    expect(supercellRepeats(latticeVectors([2.87, 2.87, 2.87, 90, 90, 90]), 2)).toEqual([2, 2, 2]);
    expect(supercellRepeats(latticeVectors([9, 9, 9, 90, 90, 90]), 24)).toEqual([1, 1, 1]);
  });

  it('builds a closed cell with bonds', () => {
    const iron = crystalFromCell({ cell: [2.87, 2.87, 2.87, 90, 90, 90], sites: BCC_IRON });
    expect(iron?.kind).toBe('crystal');
    // 2×2×2 block of 2-atom cells, closed with atoms on the far faces: 27 corners + 8 centres.
    expect(iron?.atoms).toHaveLength(35);
    // Metals keep only the nearest shell: each centre bonds to its 8 corners.
    expect(iron?.bonds).toHaveLength(64);
    expect(iron?.cell?.[0]?.[0]).toBeCloseTo(2.87);
  });

  it('skips metal–metal bonds when anions are present', () => {
    const salt = crystalFromCell({ cell: [3.2, 3.2, 3.2, 90, 90, 90], sites: ROCK_PAIR });
    const atoms = salt?.atoms ?? [];
    const bonds = crystalBonds(atoms);
    expect(bonds.length).toBeGreaterThan(0);
    for (const [i, j] of bonds) expect(new Set([atoms[i]?.el, atoms[j]?.el])).toEqual(new Set(['Na', 'Cl']));
  });
});
