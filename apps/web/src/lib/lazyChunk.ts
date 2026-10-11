import type { ComponentType, LazyExoticComponent } from 'react';
import { lazy } from 'react';

/**
 * Pages and 3D parts load in separate files (chunks) whose names change with every
 * deploy. A page opened before a deploy still asks for the old names; the server no
 * longer has them, the import fails and React used to unmount everything: a blank
 * screen until the visitor reloaded. Now such a failure reloads the page once, and the
 * new page loads the new files. A guard in sessionStorage stops reload loops.
 */

const KEY = 'p3d-reloaded-at';
/** No second automatic reload within this time. */
const GUARD_MS = 30_000;

export function isChunkError(error: unknown): boolean {
  const text = error instanceof Error ? `${error.name} ${error.message}` : String(error);
  return /dynamically imported module|Importing a module script failed|error loading dynamically|ChunkLoadError|Unable to preload CSS/i.test(
    text,
  );
}

/** Reload the page for a newer deploy; false when it was done moments ago (or impossible). */
export function reloadForNewVersion(): boolean {
  try {
    const last = Number(window.sessionStorage.getItem(KEY) ?? 0);
    if (Date.now() - last < GUARD_MS) return false;
    window.sessionStorage.setItem(KEY, String(Date.now()));
  } catch {
    return false; // no storage: no guard, so no automatic reload
  }
  window.location.reload();
  return true;
}

/** React.lazy that reloads the page once when the chunk is gone after a deploy. */
export function lazyChunk<P extends object>(
  load: () => Promise<{ default: ComponentType<P> }>,
): LazyExoticComponent<ComponentType<P>> {
  return lazy(() =>
    load().catch((error: unknown) => {
      if (isChunkError(error) && reloadForNewVersion()) {
        return new Promise<never>(() => undefined); // the page is reloading
      }
      throw error;
    }),
  );
}
