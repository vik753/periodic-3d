import { describe, expect, it } from 'vitest';

import { magnifyScale } from './layout';

describe('tile magnification', () => {
  it('grows small tiles to a readable size and keeps big ones almost as they are', () => {
    expect(magnifyScale(20)).toBe(3.4); // a phone showing the whole table: capped
    expect(magnifyScale(66)).toBeCloseTo(2); // a laptop: twice as tall
    expect(magnifyScale(400)).toBe(1.2); // zoomed in: only a small lift
  });
});
