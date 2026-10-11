// Records the "How to use" video: a scripted tour of the site, frame by frame.
//
// The page runs on a frozen fake clock (Playwright clock): each video frame advances it
// by exactly 1/FPS s, steps the CSS animations (guide-overlay.js) and takes a
// screenshot. Software WebGL in CI is slow, but the video plays at full speed and is the
// same on every run. ffmpeg then joins the frames (tools/ci/guide-encode.sh).
//
// Env:
//   GUIDE_BASE   site URL (default https://vik753.github.io/periodic-3d/)
//   GUIDE_LANG   uk | ru | en (default uk)
//   GUIDE_OUT    output directory (default out/guide/<lang>): frames/, timeline.json
//   GUIDE_FPS    frames per second (default 30)
//   GUIDE_SCALE  device pixel ratio: 1280×720 × scale (default 1.5 → 1920×1080)
//   GUIDE_ONLY   comma-separated scene names to record (default: all), for quick tries
import { chromium } from '@playwright/test';
import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const base = (process.env.GUIDE_BASE ?? 'https://vik753.github.io/periodic-3d/').replace(/\/?$/, '/');
const lang = process.env.GUIDE_LANG ?? 'uk';
const outDir = process.env.GUIDE_OUT ?? `out/guide/${lang}`;
const FPS = Number(process.env.GUIDE_FPS ?? 30);
const SCALE = Number(process.env.GUIDE_SCALE ?? 1.5);
const only = new Set((process.env.GUIDE_ONLY ?? '').split(',').filter(Boolean));
const viewport = { width: 1280, height: 720 };
const DT = 1000 / FPS;

/** Captions in the language of the interface. <kbd> draws a key cap, <b> a button name. */
const TEXT = {
  uk: {
    title: '<h1>Періодична таблиця 3D</h1><p>Як користуватися сайтом</p>',
    hover: 'Наведіть курсор на елемент: плитка збільшується, а внизу з’являється картка.',
    zoom: 'Коліщатко миші наближає таблицю до елемента під курсором.',
    sharp: 'Навіть зблизька написи на плитках лишаються чіткими.',
    open: 'Натисніть на елемент: камера влітає всередину.',
    substance: 'Перемикач <b>Речовина в 3D</b> показує просту речовину: кристал заліза.',
    rays: 'Червоні промені ведуть до елементів, з якими утворюються сполуки. Товстий промінь — багато сполук.',
    walk: 'Натисніть на промінь або плитку партнера: сполуки пари стають у ряд, найвідоміші — першими.',
    walkMove: 'Крутіть коліщатко або тягніть уздовж променя: від сполуки до сполуки.',
    card: 'Картка сполуки: 3D-модель, формула, склад, маса, опис і джерела.',
    rotate: 'Тягніть модель, щоб обернути її.',
    back: '<b>До таблиці</b>, клавіша <kbd>Esc</kbd> або клік по порожньому місцю — назад до таблиці.',
    select: '<kbd>Shift</kbd> + клік вибирає кілька елементів. На телефоні — кнопка <b>Вибрати кілька</b>.',
    cloud: '<b>Показати сполуки</b>: хмара сполук, у яких є всі вибрані елементи. Одна куля — одна сполука.',
    filter: 'Фільтр залишає лише органічні, неорганічні речовини або мінерали.',
    predicted: 'Фіолетові кулі — передбачені матеріали GNoME. Їх знайшов розрахунок, не експеримент.',
    violetRays: 'Усередині елемента кнопка <b>Показати фіолетові промені</b> відкриває передбачені матеріали.',
    material: 'Картка передбаченого матеріалу: елементарна комірка в 3D і розрахункові властивості.',
    search: 'Пошук: клавіша <kbd>/</kbd>, потім символ, формула або назва трьома мовами.',
    about: 'Кнопка <b>Як користуватися</b> — коротка інструкція, джерела даних і це відео.',
    end: '<h1>Періодична таблиця 3D</h1><p>vik753.github.io/periodic-3d</p><small>Безкоштовно · без реклами · українська, російська, англійська</small>',
    query: 'кварц',
  },
  ru: {
    title: '<h1>Периодическая таблица 3D</h1><p>Как пользоваться сайтом</p>',
    hover: 'Наведите курсор на элемент: плитка увеличивается, а внизу появляется карточка.',
    zoom: 'Колесо мыши приближает таблицу к элементу под курсором.',
    sharp: 'Даже вблизи надписи на плитках остаются чёткими.',
    open: 'Нажмите на элемент: камера влетает внутрь.',
    substance: 'Переключатель <b>Вещество в 3D</b> показывает простое вещество: кристалл железа.',
    rays: 'Красные лучи ведут к элементам, с которыми образуются соединения. Толстый луч — много соединений.',
    walk: 'Нажмите на луч или плитку партнёра: соединения пары встают в ряд, самые известные — первыми.',
    walkMove: 'Крутите колесо или тяните вдоль луча: от соединения к соединению.',
    card: 'Карточка соединения: 3D-модель, формула, состав, масса, описание и источники.',
    rotate: 'Тяните модель, чтобы повернуть её.',
    back: '<b>К таблице</b>, клавиша <kbd>Esc</kbd> или клик по пустому месту — назад к таблице.',
    select: '<kbd>Shift</kbd> + клик выбирает несколько элементов. На телефоне — кнопка <b>Выбрать несколько</b>.',
    cloud: '<b>Показать соединения</b>: облако соединений, в которых есть все выбранные элементы. Один шар — одно соединение.',
    filter: 'Фильтр оставляет только органические, неорганические вещества или минералы.',
    predicted: 'Фиолетовые шары — предсказанные материалы GNoME. Их нашёл расчёт, не эксперимент.',
    violetRays: 'Внутри элемента кнопка <b>Показать фиолетовые лучи</b> открывает предсказанные материалы.',
    material: 'Карточка предсказанного материала: элементарная ячейка в 3D и расчётные свойства.',
    search: 'Поиск: клавиша <kbd>/</kbd>, затем символ, формула или название на трёх языках.',
    about: 'Кнопка <b>Как пользоваться</b> — краткая инструкция, источники данных и это видео.',
    end: '<h1>Периодическая таблица 3D</h1><p>vik753.github.io/periodic-3d</p><small>Бесплатно · без рекламы · украинский, русский, английский</small>',
    query: 'кварц',
  },
  en: {
    title: '<h1>Periodic Table 3D</h1><p>How to use the site</p>',
    hover: 'Point at an element: the tile grows and a card appears at the bottom.',
    zoom: 'The mouse wheel zooms towards the element under the pointer.',
    sharp: 'Even close up, the letters on the tiles stay sharp.',
    open: 'Click an element: the camera flies inside.',
    substance: 'The <b>Substance in 3D</b> switch shows the simple substance: the iron crystal.',
    rays: 'Red rays lead to the elements it forms compounds with. A thick ray means many compounds.',
    walk: 'Click a ray or a partner tile: the compounds of the pair line up, the best known first.',
    walkMove: 'Scroll or drag along the ray to move from compound to compound.',
    card: 'The compound card: 3D model, formula, composition, mass, description and sources.',
    rotate: 'Drag the model to turn it.',
    back: '<b>To the table</b>, the <kbd>Esc</kbd> key or a click on empty space takes you back.',
    select: '<kbd>Shift</kbd> + click picks several elements. On a phone, use <b>Select several</b>.',
    cloud: '<b>Show compounds</b>: a cloud of compounds that contain all chosen elements. One orb is one compound.',
    filter: 'The filter keeps organic, inorganic substances or minerals only.',
    predicted: 'Violet orbs are materials predicted by GNoME: found by computation, not by experiment.',
    violetRays: 'Inside an element, <b>Show the violet rays</b> opens the predicted materials.',
    material: 'A predicted material: its unit cell in 3D and its computed properties.',
    search: 'Search: press <kbd>/</kbd>, then type a symbol, a formula or a name in any of three languages.',
    about: 'The <b>How to use</b> button opens a short guide, the data sources and this video.',
    end: '<h1>Periodic Table 3D</h1><p>vik753.github.io/periodic-3d</p><small>Free · no ads · Ukrainian, Russian, English</small>',
    query: 'quartz',
  },
}[lang];

await rm(outDir, { recursive: true, force: true });
const framesDir = join(outDir, 'frames');
await mkdir(framesDir, { recursive: true });

const browser = await chromium.launch({
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
});
const context = await browser.newContext({
  viewport,
  deviceScaleFactor: SCALE,
  locale: lang === 'ru' ? 'ru-RU' : lang === 'en' ? 'en-US' : 'uk-UA',
  reducedMotion: 'no-preference',
});
const page = await context.newPage();
const errors = [];
page.on('pageerror', (error) => errors.push(String(error)));
page.on('console', (message) => {
  if (message.type() === 'error') errors.push(message.text());
});
await page.addInitScript({ content: await readFile(join(here, 'guide-overlay.js'), 'utf8') });
// A frozen clock: time moves only when the script says so (one video frame at a time).
await page.clock.install({ time: new Date('2026-10-11T12:00:00Z') });
await page.clock.pauseAt(new Date('2026-10-11T12:00:01Z'));

let frame = 0;
let recording = true;
const timeline = [];
let pointer = { x: viewport.width / 2, y: viewport.height / 2 };

async function capture() {
  const image = await page.screenshot({ type: 'jpeg', quality: 92 });
  await writeFile(join(framesDir, `${String(frame).padStart(6, '0')}.jpg`), image);
  frame += 1;
}

/** One video frame: advance time, step CSS animations, take the picture. */
async function tick() {
  await page.clock.runFor(DT);
  await page.evaluate((dt) => window.__guide?.tick(dt), DT);
  if (recording) await capture();
}

async function hold(seconds) {
  const frames = Math.max(1, Math.round(seconds * FPS));
  for (let i = 0; i < frames; i += 1) await tick();
}

/** Let the page work (network, workers) while its clock runs, without recording. */
async function settle(seconds) {
  const was = recording;
  recording = false;
  const steps = Math.round(seconds * 10);
  for (let i = 0; i < steps; i += 1) {
    await page.clock.runFor(100);
    await page.waitForTimeout(40);
  }
  recording = was;
}

const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

async function moveTo(x, y, seconds = 0.7) {
  const frames = Math.max(1, Math.round(seconds * FPS));
  const from = { ...pointer };
  for (let i = 1; i <= frames; i += 1) {
    const k = ease(i / frames);
    pointer = { x: from.x + (x - from.x) * k, y: from.y + (y - from.y) * k };
    await page.mouse.move(pointer.x, pointer.y);
    await tick();
  }
}

async function click() {
  await page.mouse.down();
  await tick();
  await tick();
  await page.mouse.up();
  await tick();
}

async function drag(dx, dy, seconds = 1) {
  await page.mouse.down();
  await tick();
  const frames = Math.max(1, Math.round(seconds * FPS));
  const from = { ...pointer };
  for (let i = 1; i <= frames; i += 1) {
    const k = ease(i / frames);
    pointer = { x: from.x + dx * k, y: from.y + dy * k };
    await page.mouse.move(pointer.x, pointer.y);
    await tick();
  }
  await page.mouse.up();
  await tick();
}

async function wheel(deltaY, after = 0.45) {
  await page.mouse.wheel(0, deltaY);
  await hold(after);
}

async function caption(html, fade = 0.35) {
  await page.evaluate(() => window.__guide?.caption(null));
  await hold(fade);
  if (html) {
    await page.evaluate((text) => window.__guide?.caption(text), html);
    timeline.push({ at: frame / FPS, caption: html });
  }
}

async function title(html, seconds) {
  await page.evaluate((text) => window.__guide?.title(text), html);
  await hold(seconds);
  await page.evaluate(() => window.__guide?.title(null));
  await hold(0.6);
}

async function tile(symbol) {
  const point = await page.evaluate((s) => window.__p3d?.project?.(s) ?? null, symbol);
  if (!point) throw new Error(`no tile for ${symbol}`);
  return point;
}

async function moveToTile(symbol, seconds) {
  const point = await tile(symbol);
  await moveTo(point.x, point.y, seconds);
}

/** Move the pointer onto an element of the page and click it. */
async function press(locator, seconds = 0.7) {
  await locator.waitFor({ state: 'visible', timeout: 20_000 });
  const box = await locator.boundingBox();
  if (!box) throw new Error('no box');
  await moveTo(box.x + box.width / 2, box.y + box.height / 2, seconds);
  await click();
}

const t = (key) => page.evaluate((k) => window.__p3d?.t?.(k) ?? k, key);

async function waitReady() {
  for (let i = 0; i < 300; i += 1) {
    if (await page.evaluate(() => Boolean(window.__p3d?.ready))) return;
    await page.clock.runFor(100);
    await page.waitForTimeout(50);
  }
  throw new Error('the page did not get ready');
}

// ---------------------------------------------------------------------------------
// The tour. Each scene starts where the previous one ended.
// ---------------------------------------------------------------------------------

const scenes = [
  [
    'intro',
    async () => {
      await page.evaluate(() => window.__guide?.hidePointer(true));
      await title(TEXT.title, 3);
      await page.evaluate(() => window.__guide?.hidePointer(false));
    },
  ],
  [
    'hover',
    async () => {
      await caption(TEXT.hover);
      await moveToTile('Na', 1.1);
      await hold(1.1);
      await moveToTile('Fe', 1.1);
      await hold(1.4);
      await moveToTile('Au', 0.9);
      await hold(1.3);
    },
  ],
  [
    'zoom',
    async () => {
      await caption(TEXT.zoom);
      await moveToTile('Fe', 0.8);
      await wheel(-300, 0.6);
      await moveToTile('Fe', 0.3);
      await wheel(-300, 1.2);
      await caption(TEXT.sharp);
      await hold(2.2);
      await wheel(400, 0.5);
      await wheel(400, 0.5);
      await wheel(400, 1);
    },
  ],
  [
    'element',
    async () => {
      await caption(TEXT.open);
      await moveToTile('Fe', 0.8);
      await click();
      await hold(3.2);
      await caption(TEXT.substance);
      await press(page.getByRole('radio', { name: await t('element.viewSubstance') }));
      await hold(2.6);
      await press(page.getByRole('radio', { name: await t('element.viewAtom') }), 0.5);
      await hold(1);
    },
  ],
  [
    'rays',
    async () => {
      await caption(TEXT.rays);
      await moveToTile('O', 1.2);
      await hold(2.2);
      await moveToTile('S', 0.8);
      await hold(1.6);
    },
  ],
  [
    'walk',
    async () => {
      await caption(TEXT.walk);
      await moveToTile('O', 0.9);
      await click();
      await hold(3);
      await caption(TEXT.walkMove);
      await moveTo(viewport.width * 0.4, viewport.height * 0.5, 0.6);
      await wheel(120, 1);
      await wheel(120, 1);
      await wheel(120, 1.2);
    },
  ],
  [
    'card',
    async () => {
      await caption(TEXT.card);
      await press(page.getByRole('button', { name: await t('rays.open') }).or(page.getByRole('link', { name: await t('rays.open') })).first());
      await hold(3);
      await caption(TEXT.rotate);
      await moveTo(viewport.width * 0.33, viewport.height * 0.5, 0.6);
      await drag(220, 40, 1.4);
      await hold(1.4);
    },
  ],
  [
    'back',
    async () => {
      await caption(TEXT.back);
      await press(page.getByRole('link', { name: await t('nav.toTable') }).or(page.getByRole('button', { name: await t('nav.toTable') })).first());
      await hold(3);
    },
  ],
  [
    'select',
    async () => {
      await caption(TEXT.select);
      await page.keyboard.down('Shift');
      for (const symbol of ['Fe', 'O']) {
        await moveToTile(symbol, 0.8);
        await click();
        await hold(0.5);
      }
      await page.keyboard.up('Shift');
      await hold(1);
      await caption(TEXT.cloud);
      await press(page.getByRole('link', { name: await t('selection.show') }));
      await hold(3.5);
      await moveTo(viewport.width * 0.38, viewport.height * 0.45, 1);
      await hold(1.5);
      await caption(TEXT.filter);
      await press(page.getByRole('radio', { name: await t('cloud.group_mineral') }));
      await hold(2.2);
      await press(page.getByRole('radio', { name: await t('cloud.group_all') }), 0.5);
      await hold(0.8);
      await caption(TEXT.predicted);
      await press(page.getByRole('button', { name: await t('cloud.showPredicted') }));
      await hold(3);
    },
  ],
  [
    'violet',
    async () => {
      await caption(TEXT.violetRays);
      await press(page.getByRole('link', { name: await t('nav.toTable') }).or(page.getByRole('button', { name: await t('nav.toTable') })).first());
      await hold(2);
      await moveToTile('Li', 0.9);
      await click();
      await hold(3);
      await press(page.getByRole('button', { name: await t('predicted.show') }));
      await hold(2.5);
      const partner = page.locator('a[href$="/predicted"]').first();
      await press(partner);
      await hold(3);
      await caption(TEXT.material);
      await press(page.getByRole('button', { name: await t('rays.open') }).or(page.getByRole('link', { name: await t('rays.open') })).first());
      await hold(3.5);
    },
  ],
  [
    'search',
    async () => {
      await caption(TEXT.search);
      await moveTo(viewport.width * 0.5, viewport.height * 0.62, 0.6);
      await hold(0.4);
      await page.keyboard.press('/');
      await hold(0.5);
      for (const letter of TEXT.query) {
        await page.keyboard.type(letter);
        await hold(0.13);
      }
      await hold(1.2);
      await page.keyboard.press('Enter');
      await hold(3.2);
    },
  ],
  [
    'about',
    async () => {
      await caption(TEXT.about);
      await press(page.getByRole('link', { name: await t('about.button') }).or(page.getByRole('button', { name: await t('about.button') })).first());
      await hold(3.5);
      await caption(null);
    },
  ],
  [
    'outro',
    async () => {
      await page.evaluate(() => window.__guide?.hidePointer(true));
      await title(TEXT.end, 3.2);
    },
  ],
];

const started = Date.now();
await page.goto(base, { waitUntil: 'domcontentloaded' });
await waitReady();
await settle(4); // fonts, label atlas, distance field (worker), dataset
await page.mouse.move(pointer.x, pointer.y);

for (const [name, run] of scenes) {
  if (only.size && !only.has(name)) continue;
  const from = frame;
  const sceneStarted = Date.now();
  try {
    await run();
  } catch (error) {
    errors.push(`scene ${name}: ${error instanceof Error ? error.message : String(error)}`);
    await capture();
  }
  timeline.push({ scene: name, from: from / FPS, to: frame / FPS, seconds: Math.round((Date.now() - sceneStarted) / 1000) });
  console.log(`${name}: ${((frame - from) / FPS).toFixed(1)} s of video, ${Math.round((Date.now() - sceneStarted) / 1000)} s to record`);
}

await writeFile(
  join(outDir, 'timeline.json'),
  JSON.stringify({ lang, fps: FPS, frames: frame, seconds: frame / FPS, recordSeconds: Math.round((Date.now() - started) / 1000), errors, timeline }, null, 2),
);
console.log(`${frame} frames (${(frame / FPS).toFixed(1)} s), ${errors.length} errors`);
for (const error of errors) console.log(`  ${error}`);
await browser.close();
