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

/** @type {Array<{name: string, path: string, viewport: {width: number, height: number}, dpr?: number, wait?: number, quick?: boolean, lang?: string, act?: (page: import('@playwright/test').Page) => Promise<void>}>} */
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
  { name: 'element-u', path: 'e/U', viewport: desktop, wait: 3500 },
  { name: 'element-o-rays', path: 'e/O', viewport: desktop, quick: true, wait: 4500 },
  { name: 'walk-fe-o', path: 'e/Fe/O', viewport: desktop, quick: true, wait: 5000 },
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
  { name: 'set-o', path: 'set/O', viewport: desktop, wait: 4500 },
  { name: 'phone-set-fe-o', path: 'set/Fe-O', viewport: phone, dpr: 2, wait: 4500 },
  { name: 'compound-hematite', path: 'c/Q103223', viewport: desktop, quick: true, wait: 4000 },
  { name: 'compound-water', path: 'c/Q283', viewport: desktop, wait: 4000 },
  { name: 'compound-ozone-ru', path: 'c/Q36933', viewport: desktop, wait: 4000, lang: 'ru' },
  { name: 'molecule-benzene', path: 'c/demo-benzene', viewport: desktop, wait: 3500 },
  { name: 'crystal-nacl', path: 'c/demo-nacl', viewport: desktop, wait: 3500 },
  { name: 'phone-table', path: '', viewport: phone, dpr: 2 },
  { name: 'phone-element-fe', path: 'e/Fe', viewport: phone, dpr: 2, wait: 3500 },
  { name: 'phone-compound-hematite', path: 'c/Q103223', viewport: phone, dpr: 2, wait: 4000 },
];

await mkdir(outDir, { recursive: true });
const browser = await chromium.launch({
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
});

const report = { base, set, time: new Date().toISOString(), shots: [] };
let failures = 0;

for (const shot of shots) {
  if (set === 'quick' && !shot.quick) continue;
  const context = await browser.newContext({
    viewport: shot.viewport,
    deviceScaleFactor: shot.dpr ?? 1,
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
  try {
    await page.goto(base + shot.path, { waitUntil: 'load', timeout: 60_000 });
    await page.waitForFunction(() => window.__p3d?.ready === true, null, { timeout: 30_000 });
    await page.waitForTimeout(1200);
    if (shot.act) await shot.act(page);
    await page.waitForTimeout(shot.wait ?? 1800);
  } catch (error) {
    ok = false;
    messages.push(`[script] ${error instanceof Error ? error.message : String(error)}`);
  }
  const stats = await page.evaluate(() => ({ ...(window.__p3d ?? {}), project: undefined, url: location.pathname }));
  await page.screenshot({ path: `${outDir}/${shot.name}.png` });
  if (!ok || messages.some((line) => line.startsWith('[pageerror]'))) failures += 1;
  report.shots.push({ name: shot.name, path: shot.path, ok, ms: Date.now() - started, stats, console: messages });
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${shot.name} ${Date.now() - started}ms calls=${stats.calls} url=${stats.url}`);
  await context.close();
}

await browser.close();
await writeFile(`${outDir}/report.json`, JSON.stringify(report, null, 2));
if (failures > 0) {
  console.error(`${failures} screenshot(s) failed`);
  process.exitCode = 1;
}
