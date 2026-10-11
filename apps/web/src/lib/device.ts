/** Touch-first screens (no hover): the first tap magnifies a tile, the second opens it. */
export function isTouchFirst(): boolean {
  return typeof window !== 'undefined' && window.matchMedia?.('(hover: none)').matches === true;
}
