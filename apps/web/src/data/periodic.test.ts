import { describe, expect, it } from 'vitest';

import { ELEMENTS, SYMBOLS, categoryOf, configurationOf, elementBySymbol, groupOf, shellsOf } from './periodic';

describe('periodic table layout', () => {
  it('has 118 unique symbols', () => {
    expect(SYMBOLS).toHaveLength(118);
    expect(new Set(SYMBOLS).size).toBe(118);
  });

  it('places every element on a unique grid cell', () => {
    const cells = new Set(ELEMENTS.map((e) => `${e.col}:${e.row}`));
    expect(cells.size).toBe(118);
  });

  it('assigns IUPAC groups', () => {
    expect(groupOf(1)).toBe(1);
    expect(groupOf(2)).toBe(18);
    expect(groupOf(5)).toBe(13);
    expect(groupOf(26)).toBe(8);
    expect(groupOf(72)).toBe(4);
    expect(groupOf(86)).toBe(18);
    expect(groupOf(104)).toBe(4);
    expect(groupOf(118)).toBe(18);
    expect(groupOf(60)).toBeNull();
  });

  it('assigns categories', () => {
    expect(categoryOf(11)).toBe('alkali-metal');
    expect(categoryOf(26)).toBe('transition-metal');
    expect(categoryOf(14)).toBe('metalloid');
    expect(categoryOf(54)).toBe('noble-gas');
    expect(categoryOf(63)).toBe('lanthanide');
    expect(categoryOf(92)).toBe('actinide');
  });

  it('finds elements by symbol', () => {
    expect(elementBySymbol('Fe')?.z).toBe(26);
    expect(elementBySymbol('Xx')).toBeUndefined();
  });
});

describe('electron shells', () => {
  it('keeps the electron count equal to Z for every element', () => {
    for (const element of ELEMENTS) {
      const total = shellsOf(element.z).reduce((sum, n) => sum + n, 0);
      expect(total, element.symbol).toBe(element.z);
    }
  });

  it('matches known ground states', () => {
    expect(shellsOf(26)).toEqual([2, 8, 14, 2]); // Fe
    expect(shellsOf(24)).toEqual([2, 8, 13, 1]); // Cr
    expect(shellsOf(29)).toEqual([2, 8, 18, 1]); // Cu
    expect(shellsOf(46)).toEqual([2, 8, 18, 18]); // Pd
    expect(shellsOf(79)).toEqual([2, 8, 18, 32, 18, 1]); // Au
    expect(shellsOf(92)).toEqual([2, 8, 18, 32, 21, 9, 2]); // U
  });

  it('lists subshells with electrons', () => {
    expect(configurationOf(8)).toEqual([
      ['1s', 2],
      ['2s', 2],
      ['2p', 4],
    ]);
  });
});
