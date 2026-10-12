/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** static (default): JSON files next to the site; api: the live API. */
  readonly VITE_DATA_MODE?: 'static' | 'api';
  /** Base URL of the live API, e.g. https://api.example.com/api/v1 */
  readonly VITE_API_URL?: string;
  /** Base path of the site, e.g. /periodic-3d/ on GitHub Pages. */
  readonly VITE_BASE?: string;
}

/** Site version from package.json (SemVer), set at build time (vite.config.ts). */
declare const __APP_VERSION__: string;
/** Short commit hash of the build. */
declare const __APP_COMMIT__: string;
/** Build time, ISO 8601. */
declare const __APP_BUILT__: string;
