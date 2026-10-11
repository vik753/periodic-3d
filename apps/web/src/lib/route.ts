import { elementBySymbol } from '../data/periodic';

/** What the 3D world shows. Derived from the URL so every scene has its own address. */
export type SceneRoute =
  | { kind: 'table' }
  | { kind: 'element'; symbol: string; partner?: string; predicted?: boolean }
  | { kind: 'compound'; id: string }
  | { kind: 'material'; id: string }
  | { kind: 'set'; symbols: string[] };

/**
 * Parse a router pathname (already relative to the app base):
 *   /            → table
 *   /e/Fe        → element with rays to its partners
 *   /e/Fe/O      → walk along the Fe–O ray
 *   /e/Fe/O/predicted → walk along the ray of predicted Fe–O materials (GNoME)
 *   /c/<id>      → compound
 *   /m/<id>      → predicted material (GNoME, 10 hex characters)
 *   /set/Fe-O-H  → set of elements
 */
export function parseSceneRoute(pathname: string): SceneRoute {
  const parts = pathname.split('/').filter(Boolean);
  const [head, value, extra, layer] = parts;
  if (head === 'e' && value && elementBySymbol(value)) {
    if (extra && extra !== value && elementBySymbol(extra)) {
      return layer === 'predicted'
        ? { kind: 'element', symbol: value, partner: extra, predicted: true }
        : { kind: 'element', symbol: value, partner: extra };
    }
    return { kind: 'element', symbol: value };
  }
  if (head === 'c' && value) return { kind: 'compound', id: decodeURIComponent(value) };
  if (head === 'm' && value && /^[0-9a-fA-F]{10}$/.test(value)) return { kind: 'material', id: value.toLowerCase() };
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
      if (!route.partner) return `/e/${route.symbol}`;
      return `/e/${route.symbol}/${route.partner}${route.predicted ? '/predicted' : ''}`;
    case 'compound':
      return `/c/${encodeURIComponent(route.id)}`;
    case 'material':
      return `/m/${route.id}`;
    case 'set':
      return `/set/${route.symbols.join('-')}`;
  }
}

export function sameScene(a: SceneRoute, b: SceneRoute): boolean {
  return scenePath(a) === scenePath(b);
}
