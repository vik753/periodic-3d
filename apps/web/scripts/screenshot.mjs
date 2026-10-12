// Renders the app in headless Chromium (software WebGL) and saves screenshots,
// console errors and render stats. Used by CI; results go to the ci-results branch.
//
// Env:
//   SCREENSHOT_BASE  app URL (default http://localhost:4173/)
//   SCREENSHOT_OUT   output directory (default out/screenshots)
//   SCREENSHOT_SET   "full" (default) or "quick"
import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';

const base = (process.env.SCREENSHOT_BASE ?? 'http://localhost:4173/').replace(/\/?$/, '/');
const outDir = process.env.SCREENSHOT_OUT ?? 'out/screenshots';
const set = process.env.SCREENSHOT_SET ?? 'full';

const desktop = { width: 1440, height: 900 };
const phone = { width: 390, height: 844 };

/** @type {Array<{name: string, path: string, viewport: {width: number, height: number}, dpr?: number, wait?: number, quick?: boolean, lang?: string, touch?: boolean, act?: (page: import('@playwright/test').Page) => Promise<void>}>} */
const shots = [
  { name: 'table', path: '', viewport: desktop, quick: true },
  {
    name: 'table-hover-fe',
    path: '',
    viewport: desktop,
    act: async (page) => {
      const point = await page.evaluate(() => window.__p3d?.project?.('Fe') ?? null);
      if (point) await page.mouse.move(point.x, point.y, { steps: 4 });
    },
  },
  {
    name: 'table-zoom-fe',
    path: '',
    viewport: desktop,
    wait: 1500,
    act: async (page) => {
      const point = await page.evaluate(() => window.__p3d?.project?.('Fe') ?? null);
      if (!point) return;
      await page.mouse.move(point.x, point.y, { steps: 4 });
      await page.mouse.wheel(0, -400); // one firm scroll towards Fe
    },
  },
  {
    // The closest zoom: the letters must stay sharp (distance-field labels).
    name: 'table-closeup-pm',
    path: '',
    viewport: desktop,
    dpr: 2,
    wait: 3000,
    act: async (page) => {
      await page.waitForTimeout(2500); // the distance field builds in a worker
      for (let step = 0; step < 6; step += 1) {
        const point = await page.evaluate(() => window.__p3d?.project?.('Pm') ?? null);
        if (!point) return;
        await page.mouse.move(point.x, point.y, { steps: 2 });
        await page.mouse.wheel(0, -400);
        await page.waitForTimeout(350);
      }
    },
  },
  {
    // Three chosen elements, then the pointer on another tile: the bar stays at the bottom.
    name: 'table-selection-hover',
    path: '',
    viewport: desktop,
    wait: 1200,
    act: async (page) => {
      await page.getByRole('button', { name: 'Вибрати кілька' }).click();
      for (const symbol of ['Ta', 'S', 'Pd']) {
        const point = await page.evaluate((s) => window.__p3d?.project?.(s) ?? null, symbol);
        if (point) await page.mouse.click(point.x, point.y);
        await page.waitForTimeout(250);
      }
      const point = await page.evaluate(() => window.__p3d?.project?.('Fe') ?? null);
      if (point) await page.mouse.move(point.x, point.y, { steps: 4 });
    },
  },
  {
    name: 'phone-table-tap-fe',
    path: '',
    viewport: phone,
    dpr: 2,
    touch: true,
    act: async (page) => {
      const point = await page.evaluate(() => window.__p3d?.project?.('Fe') ?? null);
      if (point) await page.touchscreen.tap(point.x, point.y);
    },
  },
  {
    name: 'click-fe-flight',
    path: '',
    viewport: desktop,
    act: async (page) => {
      const point = await page.evaluate(() => window.__p3d?.project?.('Fe') ?? null);
      if (point) await page.mouse.click(point.x, point.y);
    },
    wait: 3500,
  },
  {
    name: 'search-fe',
    path: '',
    viewport: desktop,
    wait: 1500,
    act: async (page) => {
      await page.keyboard.press('/');
      await page.keyboard.type('fe', { delay: 60 });
    },
  },
  { name: 'element-fe', path: 'e/Fe', viewport: desktop, quick: true, wait: 3500 },
  {
    // A click on empty space leads home: the report's stats must say scene=table.
    name: 'element-fe-empty-click',
    path: 'e/Fe',
    viewport: desktop,
    wait: 2500,
    act: async (page) => {
      await page.waitForTimeout(2500);
      await page.mouse.click(120, 820);
    },
  },
  { name: 'element-u', path: 'e/U', viewport: desktop, wait: 3500 },
  {
    name: 'element-fe-substance',
    path: 'e/Fe',
    viewport: desktop,
    wait: 3500,
    act: async (page) => {
      await page.waitForTimeout(1500);
      await page.getByRole('radio', { name: 'Речовина в 3D' }).click();
    },
  },
  {
    name: 'element-c-substance',
    path: 'e/C',
    viewport: desktop,
    wait: 3500,
    act: async (page) => {
      await page.waitForTimeout(1500);
      await page.getByRole('radio', { name: 'Речовина в 3D' }).click();
    },
  },
  { name: 'element-o-rays', path: 'e/O', viewport: desktop, quick: true, wait: 4500 },
  { name: 'walk-fe-o', path: 'e/Fe/O', viewport: desktop, quick: true, wait: 5000 },
  {
    // Violet rays of predicted materials (GNoME) next to the red ones.
    name: 'element-fe-predicted',
    path: 'e/Fe',
    viewport: desktop,
    wait: 4500,
    act: async (page) => {
      await page.getByRole('button', { name: 'Показати фіолетові промені' }).click({ timeout: 15_000 });
    },
  },
  { name: 'walk-fe-o-predicted', path: 'e/Fe/O/predicted', viewport: desktop, quick: true, wait: 6000 },
  { name: 'phone-walk-fe-o-predicted', path: 'e/Fe/O/predicted', viewport: phone, dpr: 2, wait: 6000 },
  {
    name: 'walk-fe-o-step3',
    path: 'e/Fe/O',
    viewport: desktop,
    wait: 4000,
    act: async (page) => {
      await page.waitForTimeout(2500);
      for (let i = 0; i < 3; i += 1) {
        await page.keyboard.press('ArrowRight');
        await page.waitForTimeout(400);
      }
    },
  },
  { name: 'phone-walk-fe-o', path: 'e/Fe/O', viewport: phone, dpr: 2, wait: 5000 },
  { name: 'phone-element-o-rays', path: 'e/O', viewport: phone, dpr: 2, wait: 4500 },
  { name: 'set-fe-o', path: 'set/Fe-O', viewport: desktop, quick: true, wait: 4500 },
  {
    // Predicted materials join the cloud as violet orbs around the known compounds.
    name: 'set-fe-o-predicted',
    path: 'set/Fe-O',
    viewport: desktop,
    wait: 5500,
    act: async (page) => {
      await page.getByRole('button', { name: '+ передбачені матеріали' }).click({ timeout: 15_000 });
    },
  },
  { name: 'set-o', path: 'set/O', viewport: desktop, wait: 4500 },
  { name: 'phone-set-fe-o', path: 'set/Fe-O', viewport: phone, dpr: 2, wait: 4500 },
  { name: 'compound-hematite', path: 'c/Q103223', viewport: desktop, quick: true, wait: 4000 },
  // Predicted materials (GNoME): a fluoride with a wide band gap and an intermetallic.
  { name: 'material-gdy3f12', path: 'm/df6697e2c1', viewport: desktop, quick: true, wait: 4000 },
  { name: 'material-laal3zn', path: 'm/1f3b0ccd3c', viewport: desktop, wait: 4000 },
  { name: 'phone-material-gdy3f12', path: 'm/df6697e2c1', viewport: phone, dpr: 2, wait: 4000 },
  { name: 'compound-water', path: 'c/Q283', viewport: desktop, wait: 4000 },
  { name: 'compound-ozone-ru', path: 'c/Q36933', viewport: desktop, wait: 4000, lang: 'ru' },
  { name: 'compound-glucose', path: 'c/Q37525', viewport: desktop, wait: 4000 },
  { name: 'compound-sodium-acetate', path: 'c/Q339940', viewport: desktop, wait: 4000 },
  { name: 'compound-no-3d', path: 'c/Q483269', viewport: desktop, wait: 4000 },
  // Source check (Q.1): Wikidata wrote "KCIO₃"; the card shows the fixed formula and a note.
  { name: 'compound-chlorate-fixed', path: 'c/Q309328', viewport: desktop, wait: 4000 },
  { name: 'about', path: 'about', viewport: desktop, wait: 2000 },
  {
    name: 'keyboard-index',
    path: '',
    viewport: desktop,
    act: async (page) => {
      await page.getByRole('navigation', { name: 'Елементи таблиці' }).getByRole('link').nth(25).focus();
    },
  },
  { name: 'phone-about', path: 'about', viewport: phone, dpr: 2, wait: 2000 },
  { name: 'molecule-benzene', path: 'c/demo-benzene', viewport: desktop, wait: 3500 },
  { name: 'crystal-nacl', path: 'c/demo-nacl', viewport: desktop, wait: 3500 },
  { name: 'phone-table', path: '', viewport: phone, dpr: 2 },
  { name: 'phone-element-fe', path: 'e/Fe', viewport: phone, dpr: 2, wait: 3500 },
  { name: 'phone-compound-hematite', path: 'c/Q103223', viewport: phone, dpr: 2, wait: 4000 },
  // "Where it is used" (U.4): scroll the card to the section; open the first chip.
  { name: 'uses-element-li', path: 'e/Li', viewport: desktop, wait: 3500, act: showUses() },
  { name: 'uses-element-he', path: 'e/He', viewport: desktop, wait: 3500, act: showUses(true) },
  { name: 'uses-element-nd-ru', path: 'e/Nd', viewport: desktop, wait: 3500, lang: 'ru', act: showUses() },
  { name: 'uses-compound-caffeine', path: 'c/Q60235', viewport: desktop, wait: 4000, act: showUses(true) },
  { name: 'uses-compound-aspirin-en', path: 'c/Q18216', viewport: desktop, wait: 4000, lang: 'en', act: showUses() },
  { name: 'uses-compound-salt', path: 'c/Q2314', viewport: desktop, wait: 4000, act: showUses() },
  { name: 'phone-uses-element-cu', path: 'e/Cu', viewport: phone, dpr: 2, wait: 3500, act: showUses() },
];

/** Scroll the card to "Where it is used" (any language); optionally open the first term chip. */
function showUses(openChip = false) {
  return async (page) => {
    const heading = page.getByRole('heading', { name: /^(Де використовується|Где используется|Where it is used)$/ });
    await heading.waitFor({ timeout: 15_000 });
    await heading.scrollIntoViewIfNeeded();
    await page.evaluate(() => {
      const panel = document.querySelector('aside');
      const title = [...document.querySelectorAll('aside h2')].find((node) =>
        /використовується|используется|is used/.test(node.textContent ?? ''),
      );
      if (panel && title) panel.scrollTop += title.getBoundingClientRect().top - panel.getBoundingClientRect().top - 12;
    });
    if (openChip) {
      await page.locator('section', { has: heading }).locator('button[aria-expanded]').first().click();
    }
    await page.waitForTimeout(400);
  };
}

await mkdir(outDir, { recursive: true });
const launch = () =>
  chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
let browser = await launch();

/** Rejects after `ms`: a stuck page (software GPU) must not stall the whole job. */
function within(promise, ms, label) {
  let timer;
  const limit = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`timed out: ${label} (${ms} ms)`)), ms);
  });
  return Promise.race([promise, limit]).finally(() => clearTimeout(timer));
}

const report = { base, set, time: new Date().toISOString(), shots: [] };
let failures = 0;

for (const shot of shots) {
  if (set === 'quick' && !shot.quick) continue;
  const context = await browser.newContext({
    viewport: shot.viewport,
    deviceScaleFactor: shot.dpr ?? 1,
    hasTouch: shot.touch ?? false,
    isMobile: shot.touch ?? false,
    locale: shot.lang === 'ru' ? 'ru-RU' : shot.lang === 'en' ? 'en-US' : 'uk-UA',
  });
  const page = await context.newPage();
  const messages = [];
  page.on('console', (message) => {
    if (message.type() === 'error' || message.type() === 'warning') messages.push(`[${message.type()}] ${message.text()}`);
  });
  page.on('pageerror', (error) => messages.push(`[pageerror] ${error.message}`));
  const started = Date.now();
  let ok = true;
  let stats = {};
  try {
    await page.goto(base + shot.path, { waitUntil: 'load', timeout: 60_000 });
    await page.waitForFunction(() => window.__p3d?.ready === true, null, { timeout: 30_000 });
    await page.waitForTimeout(1200);
    if (shot.act) await within(shot.act(page), 30_000, 'act');
    await page.waitForTimeout(shot.wait ?? 1800);
    stats = await within(
      page.evaluate(() => ({ ...(window.__p3d ?? {}), project: undefined, url: location.pathname })),
      15_000,
      'evaluate',
    );
    await within(page.screenshot({ path: `${outDir}/${shot.name}.png`, timeout: 30_000 }), 35_000, 'screenshot');
  } catch (error) {
    ok = false;
    messages.push(`[script] ${error instanceof Error ? error.message : String(error)}`);
  }
  if (!ok || messages.some((line) => line.startsWith('[pageerror]'))) failures += 1;
  report.shots.push({ name: shot.name, path: shot.path, ok, ms: Date.now() - started, stats, console: messages });
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${shot.name} ${Date.now() - started}ms calls=${stats.calls} url=${stats.url}`);
  try {
    await within(context.close(), 10_000, 'close');
  } catch {
    // The renderer is stuck: start a fresh browser for the next shots.
    await within(browser.close(), 10_000, 'browser close').catch(() => undefined);
    browser = await launch();
  }
}

await within(browser.close(), 10_000, 'browser close').catch(() => undefined);
await writeFile(`${outDir}/report.json`, JSON.stringify(report, null, 2));
if (failures > 0) {
  console.error(`${failures} screenshot(s) failed`);
  process.exitCode = 1;
}
process.exit();
