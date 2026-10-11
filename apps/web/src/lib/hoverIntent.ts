import { useEffect, useLayoutEffect, useMemo, useRef } from 'react';

/**
 * Hover intent: react to what the pointer rests on, not to everything it crosses.
 *
 * A fast sweep across the table used to magnify every tile on the way. Now a target
 * becomes "hovered" only when the pointer has been over it for a moment (DWELL) and
 * moves slowly, or when it stays inside one target for longer (PATIENCE: a big tile
 * read up close). Leaving a target clears it after a short grace (LEAVE), so crossing
 * the gap between two tiles does not blink. The same rule serves tiles, rays, cloud
 * orbs and atoms. Touch has no hover: taps go straight through.
 */

/** Pointer speed below which the visitor is aiming, px per ms (≈ 450 px/s). */
export const SLOW = 0.45;
/** Time over one target before it may light up, ms. */
export const DWELL = 60;
/** Light up anyway after this long over one target, however the pointer moves, ms. */
export const PATIENCE = 220;
/** Grace before a left target goes dark, ms. */
export const LEAVE = 110;
const TICK = 30;

let speed = 0;
let lastX = 0;
let lastY = 0;
let lastT = -Infinity;
let tracking = false;

function track(): void {
  if (tracking || typeof window === 'undefined') return;
  tracking = true;
  window.addEventListener(
    'pointermove',
    (event) => {
      // performance.now(), not event.timeStamp: one clock for the speed and the timers.
      const now = performance.now();
      const dt = now - lastT;
      if (dt > 0 && dt < 200) {
        const v = Math.hypot(event.clientX - lastX, event.clientY - lastY) / dt;
        // Exponential smoothing with a ~40 ms time constant.
        speed += (v - speed) * Math.min(1, dt / 40);
      } else if (dt >= 200) {
        speed = 0;
      }
      lastX = event.clientX;
      lastY = event.clientY;
      lastT = now;
    },
    { capture: true, passive: true },
  );
}

/** Smoothed pointer speed in px per ms; 0 once the pointer has stopped. */
export function pointerSpeed(now = performance.now()): number {
  return now - lastT > 60 ? 0 : speed;
}

/** May a target that the pointer has been over for `dwell` ms light up now? */
export function intends(dwell: number, currentSpeed: number): boolean {
  return (dwell >= DWELL && currentSpeed < SLOW) || dwell >= PATIENCE;
}

export class HoverIntent<T> {
  private pending: T | null = null;
  private since = 0;
  private timer: ReturnType<typeof setTimeout> | undefined;
  private leaveTimer: ReturnType<typeof setTimeout> | undefined;

  /**
   * commit: show the new hovered value (null: nothing).
   * read: the value shown now (a store may change it elsewhere, for example on Esc).
   */
  constructor(
    private readonly commit: (value: T | null) => void,
    private readonly read: () => T | null,
  ) {
    track();
  }

  /** The pointer is over `value`. immediate: no waiting (touch, keyboard). */
  over(value: T, immediate = false): void {
    const current = this.read();
    if (value === current) {
      this.pending = null;
      this.cancelLeave();
      return;
    }
    if (immediate) {
      this.set(value);
      return;
    }
    if (current !== null) this.startLeave();
    if (value !== this.pending) {
      this.pending = value;
      this.since = performance.now();
    }
    this.schedule();
  }

  /** The pointer is over none of the targets. */
  out(): void {
    this.pending = null;
    if (this.read() !== null) this.startLeave();
  }

  /** Forget the pending target and timers (unmount, scene change). */
  dispose(): void {
    clearTimeout(this.timer);
    clearTimeout(this.leaveTimer);
    this.timer = undefined;
    this.leaveTimer = undefined;
    this.pending = null;
  }

  private schedule(): void {
    if (this.timer !== undefined) return;
    this.timer = setTimeout(() => {
      this.timer = undefined;
      this.check();
    }, TICK);
  }

  private check(): void {
    if (this.pending === null) return;
    const now = performance.now();
    if (intends(now - this.since, pointerSpeed(now))) this.set(this.pending);
    else this.schedule();
  }

  private startLeave(): void {
    if (this.leaveTimer !== undefined) return;
    // A new target that lights up in time (set) cancels this; otherwise the old one goes dark.
    this.leaveTimer = setTimeout(() => {
      this.leaveTimer = undefined;
      this.commit(null);
    }, LEAVE);
  }

  private cancelLeave(): void {
    clearTimeout(this.leaveTimer);
    this.leaveTimer = undefined;
  }

  private set(value: T): void {
    this.pending = null;
    this.cancelLeave();
    if (value !== this.read()) this.commit(value);
  }
}

/** A HoverIntent for a component; commit and read may change between renders. */
export function useHoverIntent<T>(commit: (value: T | null) => void, read: () => T | null): HoverIntent<T> {
  const commitRef = useRef(commit);
  const readRef = useRef(read);
  useLayoutEffect(() => {
    commitRef.current = commit;
    readRef.current = read;
  });
  const intent = useMemo(
    () =>
      new HoverIntent<T>(
        (value) => commitRef.current(value),
        () => readRef.current(),
      ),
    [],
  );
  useEffect(() => () => intent.dispose(), [intent]);
  return intent;
}
