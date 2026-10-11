import { describe, expect, it } from 'vitest';

import { isChunkError } from './lazyChunk';

describe('isChunkError', () => {
  it('knows how browsers report a missing chunk', () => {
    expect(isChunkError(new TypeError('Failed to fetch dynamically imported module: https://x/assets/Rays-1a2b.js'))).toBe(true);
    expect(isChunkError(new TypeError('error loading dynamically imported module: https://x/a.js'))).toBe(true);
    expect(isChunkError(new TypeError('Importing a module script failed.'))).toBe(true);
    expect(isChunkError(new Error('Unable to preload CSS for /assets/index.css'))).toBe(true);
  });

  it('leaves other errors to the error boundary', () => {
    expect(isChunkError(new TypeError("Cannot read properties of undefined (reading 'x')"))).toBe(false);
    expect(isChunkError('not found')).toBe(false);
  });
});
