// Reports gzip sizes of the built assets and checks the initial-JS budget.
import { readdir, readFile, writeFile, mkdir } from 'node:fs/promises';
import { gzipSync } from 'node:zlib';

const BUDGET_KB = 400;
const dist = 'dist';
const html = await readFile(`${dist}/index.html`, 'utf8');

// Initial JS = scripts and modulepreloads referenced by index.html.
const initial = new Set(
  [...html.matchAll(/(?:src|href)="[^"]*?(assets\/[^"]+\.js)"/g)].map((match) => match[1]),
);

const files = (await readdir(`${dist}/assets`)).filter((name) => /\.(js|css)$/.test(name));
const rows = [];
for (const name of files) {
  const buffer = await readFile(`${dist}/assets/${name}`);
  rows.push({
    file: `assets/${name}`,
    kb: +(buffer.length / 1024).toFixed(1),
    gzipKb: +(gzipSync(buffer, { level: 9 }).length / 1024).toFixed(1),
    initial: initial.has(`assets/${name}`) || name.endsWith('.css'),
  });
}
rows.sort((a, b) => b.gzipKb - a.gzipKb);

const initialJs = rows.filter((row) => row.initial && row.file.endsWith('.js')).reduce((sum, row) => sum + row.gzipKb, 0);
const summary = { budgetKb: BUDGET_KB, initialJsGzipKb: +initialJs.toFixed(1), withinBudget: initialJs <= BUDGET_KB, rows };

await mkdir('out', { recursive: true });
await writeFile('out/size.json', JSON.stringify(summary, null, 2));
for (const row of rows) console.log(`${row.initial ? '*' : ' '} ${row.gzipKb.toString().padStart(7)} KB gz  ${row.file}`);
console.log(`initial JS (gzip): ${summary.initialJsGzipKb} KB / budget ${BUDGET_KB} KB`);
if (!summary.withinBudget) {
  console.error('Initial JS is over budget');
  process.exitCode = 1;
}
