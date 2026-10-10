import { describe, expect, it } from 'vitest';

import { formatCharge, formatCount, formatNumber, formulaOrder } from './format';

describe('format', () => {
  it('formats numbers in the interface language', () => {
    expect(formatNumber(55.845, 'en')).toBe('55.845');
    expect(formatNumber(1811, 'uk')).toMatch(/^1\s?811$/);
  });

  it('writes charges with a true minus sign', () => {
    expect(formatCharge(1)).toBe('+1');
    expect(formatCharge(-2)).toBe('−2');
  });

  it('keeps integer counts and rounds fractions', () => {
    expect(formatCount(3, 'en')).toBe('3');
    expect(formatCount(0.333333, 'en')).toBe('0.33');
  });

  it('orders elements as the formula names them', () => {
    expect(formulaOrder('Fe₂O₃', ['O', 'Fe'])).toEqual(['Fe', 'O']);
    expect(formulaOrder('FeO(OH)', ['H', 'O', 'Fe'])).toEqual(['Fe', 'O', 'H']);
    expect(formulaOrder('D₂O', ['H', 'O'])).toEqual(['O', 'H']);
  });
});
