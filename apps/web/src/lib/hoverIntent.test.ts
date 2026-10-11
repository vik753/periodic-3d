import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { DWELL, HoverIntent, intends, LEAVE, PATIENCE, SLOW } from './hoverIntent';

describe('intends', () => {
  it('waits for a short dwell of a slow pointer, or for patience', () => {
    expect(intends(DWELL - 1, 0)).toBe(false);
    expect(intends(DWELL, 0)).toBe(true);
    expect(intends(DWELL, SLOW * 2)).toBe(false);
    expect(intends(PATIENCE, SLOW * 10)).toBe(true);
  });
});

describe('HoverIntent', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'performance'] });
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  function setup() {
    let shown: number | null = null;
    const commits: Array<number | null> = [];
    const intent = new HoverIntent<number>(
      (value) => {
        shown = value;
        commits.push(value);
      },
      () => shown,
    );
    return { intent, commits, shown: () => shown };
  }

  it('lights a target after the dwell and clears it after the grace', () => {
    const { intent, shown } = setup();
    intent.over(5);
    expect(shown()).toBe(null);
    vi.advanceTimersByTime(DWELL + 40);
    expect(shown()).toBe(5);
    intent.out();
    vi.advanceTimersByTime(LEAVE - 10);
    expect(shown()).toBe(5);
    vi.advanceTimersByTime(20);
    expect(shown()).toBe(null);
  });

  it('skips the targets that the pointer only crosses', () => {
    const { intent, commits } = setup();
    for (const z of [1, 2, 3, 4]) {
      intent.over(z);
      vi.advanceTimersByTime(20);
    }
    vi.advanceTimersByTime(DWELL + 40);
    expect(commits).toEqual([4]);
  });

  it('keeps the target while the pointer crosses a gap and comes back', () => {
    const { intent, commits } = setup();
    intent.over(7);
    vi.advanceTimersByTime(DWELL + 40);
    intent.out();
    vi.advanceTimersByTime(LEAVE / 2);
    intent.over(7);
    vi.advanceTimersByTime(LEAVE * 2);
    expect(commits).toEqual([7]);
  });

  it('switches at once for taps and keyboard focus', () => {
    const { intent, shown } = setup();
    intent.over(9, true);
    expect(shown()).toBe(9);
  });

  it('follows a value cleared elsewhere', () => {
    const { intent, commits } = setup();
    let external: number | null = null;
    const synced = new HoverIntent<number>(
      (value) => {
        external = value;
        commits.push(value);
      },
      () => external,
    );
    synced.over(3);
    vi.advanceTimersByTime(DWELL + 40);
    external = null; // Esc cleared the store
    synced.over(3);
    vi.advanceTimersByTime(DWELL + 40);
    expect(commits).toEqual([3, 3]);
    intent.dispose();
  });
});
