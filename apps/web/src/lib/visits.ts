const ABOUT_SEEN_KEY = 'p3d.aboutSeen';

/** Has this visitor opened the "How to use" page before? (Calms the button's glow.) */
export function wasAboutSeen(): boolean {
  try {
    return window.localStorage.getItem(ABOUT_SEEN_KEY) === '1';
  } catch {
    // Storage can be blocked (private mode): treat the visitor as new.
    return false;
  }
}

export function markAboutSeen(): void {
  try {
    window.localStorage.setItem(ABOUT_SEEN_KEY, '1');
  } catch {
    // Ignore: the glow simply stays bright.
  }
}
