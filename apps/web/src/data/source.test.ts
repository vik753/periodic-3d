import { describe, expect, it } from 'vitest';

import { metaUrl, pairPath, resourceUrl } from './source';

describe('data source paths', () => {
  it('mirrors API paths in the static export', () => {
    expect(metaUrl('static')).toMatch(/data\/meta\.json$/);
    expect(resourceUrl('2026.10.10-r3', 'elements/Fe', 'static')).toMatch(/data\/2026\.10\.10-r3\/elements\/Fe\.json$/);
    expect(resourceUrl('2026.10.10-r3', 'elements/Fe', 'api')).toBe('/api/v1/elements/Fe');
  });

  it('orders pair paths by atomic number', () => {
    expect(pairPath({ z: 26, symbol: 'Fe' }, { z: 8, symbol: 'O' })).toBe('pairs/O-Fe');
    expect(pairPath({ z: 1, symbol: 'H' }, { z: 8, symbol: 'O' })).toBe('pairs/H-O');
  });
});
