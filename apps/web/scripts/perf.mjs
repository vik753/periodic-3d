// Loads the app under a throttled 4G network and measures what the plan budgets:
// LCP (≤ 2.5 s on 4G), JavaScript transferred before the first 3D frame (≤ 400 KB),
// and the time until the 3D table is ready. Runs in CI against the live demo
// (GitHub Pages serves gzip like a real CDN). Results: <out>/report.json.
//
// Env:
//   PERF_BASE  app URL (default https://vik753.github.io/periodic-3d/)
//   PERF_OUT   output directory (default out/perf)
//   PERF_RUNS  runs per profile (default 3; the median is reported)
import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';

const base = (process.env.PERF_BASE ?? 'https://vik753.github.io/periodic-3d/').replace(/\/?$/, '/');
const outDir = process.env.PERF_OUT ?? 'out/perf';
const runs = Number(process.env.PERF_RUNS ?? 3);

// WebPageTest "4G": 9 Mbit/s down, 9 Mbit/s up, 170 ms round trip.
const FOUR_G = { offline: false, latency: 170, downloadThroughput: (9e6 / 8) * 0.9, uploadThroughput: (9e6 / 8) * 0.9 };

const profiles = [
  { name: 'desktop-4g', viewport: { width: 1440, height: 900 }, dpr: 1, cpu: 1 },
  { name: 'phone-4g', viewport: { width: 390, height: 844 }, dpr: 2, cpu: 4, mobile: true },
];

function median(values) {
  const sorted = values.filter((value) => Number.isFinite(value)).sort((a, b) => a - b);
  return sorted.length ? sorted[Math.floor(sorted.length / 2)] : null;
}

async function measure(browser, profile) {
  const context = await browser.newContext({
    viewport: profile.viewport,
    deviceScaleFactor: profile.dpr,
    isMobile: profile.mobile ?? false,
    hasTouch: profile.mobile ?? false,
    locale: 'uk-UA',
  });
  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  await cdp.send('Network.enable');
  await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
  await cdp.send('Network.emulateNetworkConditions', FOUR_G);
  if (profile.cpu > 1) await cdp.send('Emulation.setCPUThrottlingRate', { rate: profile.cpu });

  // Encoded (on-the-wire) bytes per request, until the 3D table is ready.
  const sizes = new Map();
  const types = new Map();
  let counting = true;
  cdp.on('Network.responseReceived', (event) => types.set(event.requestId, event.type));
  cdp.on('Network.loadingFinished', (event) => {
    if (counting) sizes.set(event.requestId, event.encodedDataLength);
  });

  await page.addInitScript(() => {
    window.__lcp = 0;
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) window.__lcp = entry.startTime;
    }).observe({ type: 'largest-contentful-paint', buffered: true });
  });

  const started = Date.now();
  await page.goto(base, { waitUntil: 'load', timeout: 120_000 });
  await page.waitForFunction(() => window.__p3d?.ready === true, null, { timeout: 120_000 });
  const ready = Date.now() - started;
  counting = false;
  await page.waitForTimeout(1500);
  // LCP is final after the first input; a key press is the least intrusive one.
  await page.keyboard.press('Shift');
  const metrics = await page.evaluate(() => {
    const navigation = performance.getEntriesByType('navigation')[0];
    return {
      lcp: window.__lcp,
      domContentLoaded: navigation ? navigation.domContentLoadedEventEnd : null,
      load: navigation ? navigation.loadEventEnd : null,
      calls: window.__p3d?.calls ?? null,
    };
  });
  let script = 0;
  let total = 0;
  for (const [id, bytes] of sizes) {
    total += bytes;
    if (types.get(id) === 'Script') script += bytes;
  }
  await context.close();
  return { ...metrics, ready, scriptKB: Math.round(script / 1024), totalKB: Math.round(total / 1024) };
}

await mkdir(outDir, { recursive: true });
const browser = await chromium.launch({
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
});
const report = { base, time: new Date().toISOString(), network: '4G 9 Mbit/s, 170 ms RTT', profiles: [] };
for (const profile of profiles) {
  const samples = [];
  for (let run = 0; run < runs; run += 1) {
    try {
      samples.push(await measure(browser, profile));
    } catch (error) {
      samples.push({ error: error instanceof Error ? error.message : String(error) });
    }
  }
  const ok = samples.filter((sample) => !sample.error);
  const summary = {
    name: profile.name,
    cpuSlowdown: profile.cpu,
    lcpMs: median(ok.map((sample) => sample.lcp)),
    readyMs: median(ok.map((sample) => sample.ready)),
    scriptKB: median(ok.map((sample) => sample.scriptKB)),
    totalKB: median(ok.map((sample) => sample.totalKB)),
    samples,
  };
  report.profiles.push(summary);
  console.log(
    `${profile.name}: LCP ${summary.lcpMs?.toFixed(0)} ms, 3D ready ${summary.readyMs} ms, ` +
      `JS ${summary.scriptKB} KB, all ${summary.totalKB} KB (median of ${ok.length})`,
  );
}
await browser.close();
await writeFile(`${outDir}/report.json`, JSON.stringify(report, null, 2));
process.exit(0);
