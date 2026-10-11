import { describe, expect, it } from 'vitest';

import { parseSceneRoute, scenePath } from './route';

describe('scene routes', () => {
  it('parses every scene and builds the same path back', () => {
    const paths = ['/', '/e/Fe', '/e/Fe/O', '/c/Q283', '/m/df6697e2c1', '/set/Fe-O'];
    for (const path of paths) expect(scenePath(parseSceneRoute(path))).toBe(path);
  });

  it('accepts only GNoME ids for materials', () => {
    expect(parseSceneRoute('/m/DF6697E2C1')).toEqual({ kind: 'material', id: 'df6697e2c1' });
    expect(parseSceneRoute('/m/xyz')).toEqual({ kind: 'table' });
    expect(parseSceneRoute('/m/df6697e2c')).toEqual({ kind: 'table' });
  });
});
