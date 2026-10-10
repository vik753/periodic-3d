import { elementBySymbol } from '../data/periodic';

/** What the 3D world shows. Derived from the URL so every scene has its own address. */
export type SceneRoute =
  | { kind: 'table' }
  | { kind: 'element'; symbol: string }
  | { kind: 'compound'; id: string }
  | { kind: 'set'; symbols: string[] };

/**
 * Parse a router pathname (already relative to the app base):
 *   /            → table
 *   /e/Fe        → element
 *   /c/<id>      → compound
 *   /set/Fe-O-H  → set of elements
 */
export function parseSceneRoute(pathname: string): SceneRoute {
  const parts = pathname.split('/').filter(Boolean);
  const [head, value] = parts;
  if (head === 'e' && value && elementBySymbol(value)) return { kind: 'element', symbol: value };
  if (head === 'c' && value) return { kind: 'compound', id: decodeURIComponent(value) };
  if (head === 'set' && value) {
    const symbols = value.split('-').filter((symbol) => elementBySymbol(symbol));
    if (symbols.length > 0) return { kind: 'set', symbols };
  }
  return { kind: 'table' };
}

export function scenePath(route: SceneRoute): string {
  switch (route.kind) {
    case 'table':
      return '/';
    case 'element':
      return `/e/${route.symbol}`;
    case 'compound':
      return `/c/${encodeURIComponent(route.id)}`;
    case 'set':
      return `/set/${route.symbols.join('-')}`;
  }
}

export function sameScene(a: SceneRoute, b: SceneRoute): boolean {
  return scenePath(a) === scenePath(b);
}
