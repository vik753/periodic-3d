import { describe, expect, it } from 'vitest';

import { atomColor, registerElementColors } from './chemistry';

describe('atomColor', () => {
  it('uses the softened oxygen and Jmol colours', () => {
    expect(atomColor('O')).toBe('#F0564A');
    expect(atomColor('Fe')).toBe('#E06633');
  });

  it('fills elements missing from the table with dataset colours', () => {
    expect(atomColor('Nd')).toBe('#C8D0E0');
    registerElementColors([
      { symbol: 'Nd', cpk: '#C7FFC7' },
      { symbol: 'Og', cpk: null },
    ]);
    expect(atomColor('Nd')).toBe('#C7FFC7');
    expect(atomColor('Og')).toBe('#C8D0E0');
  });

  it('prefers an explicit override', () => {
    expect(atomColor('Fe', '#123456')).toBe('#123456');
  });
});
