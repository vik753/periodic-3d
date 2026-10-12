/** The site's version (SemVer from package.json), commit and build time: vite.config.ts. */
export const APP_VERSION = __APP_VERSION__;
export const APP_COMMIT = __APP_COMMIT__;
export const APP_BUILT = __APP_BUILT__;

const REPOSITORY = 'https://github.com/vik753/periodic-3d';

/** "What's new": the changelog in the interface language. */
export function changelogUrl(language: string): string {
  const file = language === 'uk' ? 'CHANGELOG.uk.md' : language === 'ru' ? 'CHANGELOG.ru.md' : 'CHANGELOG.md';
  return `${REPOSITORY}/blob/main/${file}`;
}

/** The commit of this build on GitHub; null for a local build. */
export function commitUrl(): string | null {
  return /^[0-9a-f]{7}$/.test(APP_COMMIT) ? `${REPOSITORY}/commit/${APP_COMMIT}` : null;
}
