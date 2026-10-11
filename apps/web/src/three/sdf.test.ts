import { describe, expect, it } from 'vitest';

import { cellSdf, SDF_SCALE, sdfScratch } from './sdf';

/** A filled square with an antialiased left edge at x = edge (source pixels). */
function square(size: number, edge: number): Uint8Array {
  const alpha = new Uint8Array(size * size);
  for (let y = size / 4; y < (size * 3) / 4; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const coverage = Math.min(Math.max(x + 1 - edge, 0), 1);
      alpha[y * size + x] = x < (size * 3) / 4 ? Math.round(coverage * 255) : 0;
    }
  }
  return alpha;
}

describe('cellSdf', () => {
  const size = 64;
  const cell = size / SDF_SCALE;
  const read = (alpha: Uint8Array) => {
    const out = new Uint8Array(cell * cell);
    cellSdf(alpha, 0, size, out, 0, cell, sdfScratch(size));
    return out;
  };

  /** Where the row through the middle crosses the edge value, in atlas texels. */
  const crossing = (out: Uint8Array) => {
    const row = (cell / 2) * cell;
    for (let x = 0; x < cell / 2; x += 1) {
      const a = out[row + x]!;
      const b = out[row + x + 1]!;
      if (a < 127.5 && b >= 127.5) return x + 0.5 + (127.5 - a) / (b - a);
    }
    return Number.NaN;
  };

  it('is 0 far outside and 255 deep inside', () => {
    const out = read(square(size, 16.5));
    const row = (cell / 2) * cell;
    expect(out[row]).toBe(0);
    expect(out[row + cell / 2]).toBe(255);
    expect(out[0]).toBe(0);
  });

  it('puts the edge where the letters end, to a tenth of a texel', () => {
    for (const edge of [16.25, 16.5, 16.75]) {
      expect(Math.abs(crossing(read(square(size, edge))) - edge / SDF_SCALE)).toBeLessThan(0.1);
    }
  });

  it('writes into a cell of a larger atlas', () => {
    const out = new Uint8Array(cell * 2 * cell);
    cellSdf(square(size, 16.5), 0, size, out, cell, cell * 2, sdfScratch(size));
    expect(out[0]).toBe(0);
    expect(out[(cell / 2) * cell * 2 + cell + cell / 2]).toBe(255);
  });
});
