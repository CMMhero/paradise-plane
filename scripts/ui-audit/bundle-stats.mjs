#!/usr/bin/env node
/**
 * Ringkasan ukuran bundel produksi web (apps/web/build/client).
 *
 *   node bundle-stats.mjs <dir build/client> [out.json] [--top 15]
 *
 * Mencetak total JS/CSS (mentah + gzip level 6, sama dengan kompresi `serve`), N chunk terbesar, dan "JS awal"
 * per rute: entry + modul rute beserta impor statisnya, dibaca dari manifest React Router di build.
 */
import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";

const argv = process.argv.slice(2);
const dir = argv[0];
if (!dir) {
  console.error("usage: node bundle-stats.mjs <build/client> [out.json] [--top 15]");
  process.exit(2);
}
const ti = argv.indexOf("--top");
const TOP = ti >= 0 ? Number(argv[ti + 1]) : 15;
const outJson = argv.find((a, i) => i > 0 && a.endsWith(".json") && argv[i - 1] !== "--top");

const walk = (d) =>
  fs
    .readdirSync(d, { withFileTypes: true })
    .flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));
const files = walk(dir).map((f) => {
  const buf = fs.readFileSync(f);
  return {
    file: path.relative(dir, f),
    raw: buf.length,
    gzip: zlib.gzipSync(buf, { level: 6 }).length,
    ext: path.extname(f),
  };
});
const sum = (xs, k) => xs.reduce((a, x) => a + x[k], 0);
const js = files.filter((f) => f.ext === ".js");
const css = files.filter((f) => f.ext === ".css");
const other = files.filter((f) => f.ext !== ".js" && f.ext !== ".css");
const byFile = new Map(files.map((f) => [`/${f.file}`, f]));

// Manifest React Router: window.__reactRouterManifest={...} di assets/manifest-*.js
let initial = null;
const mf = js.find((f) => /assets\/manifest-[^/]+\.js$/.test(f.file));
if (mf) {
  const src = fs.readFileSync(path.join(dir, mf.file), "utf8");
  const json = src.slice(src.indexOf("{"), src.lastIndexOf("}") + 1);
  const m = JSON.parse(json);
  const set = (mods) => {
    const s = new Set(mods.filter(Boolean));
    const list = [...s].map((p) => byFile.get(p)).filter(Boolean);
    return { files: list.length, raw: sum(list, "raw"), gzip: sum(list, "gzip") };
  };
  const chain = (id) => {
    const out = [];
    for (let r = m.routes[id]; r; r = m.routes[r.parentId]) out.unshift(r);
    return out;
  };
  const forRoute = (id) =>
    set([
      m.entry.module,
      ...m.entry.imports,
      ...chain(id).flatMap((r) => [r.module, ...(r.imports ?? [])]),
      mf ? `/${mf.file}` : null,
    ]);
  const shell = set([
    m.entry.module,
    ...m.entry.imports,
    ...chain("root").flatMap((r) => [r.module, ...(r.imports ?? [])]),
    `/${mf.file}`,
  ]);
  const routes = Object.keys(m.routes)
    .map((id) => ({
      id,
      path: chain(id)
        .map((r) => r.path)
        .filter(Boolean)
        .join("/"),
      ...forRoute(id),
    }))
    .sort((a, b) => b.gzip - a.gzip);
  initial = { shell, routes };
}

const kb = (n) => (n / 1024).toFixed(1).padStart(8);
const result = {
  dir,
  totals: {
    js: { files: js.length, raw: sum(js, "raw"), gzip: sum(js, "gzip") },
    css: { files: css.length, raw: sum(css, "raw"), gzip: sum(css, "gzip") },
    other: { files: other.length, raw: sum(other, "raw") },
  },
  largestJs: [...js].sort((a, b) => b.raw - a.raw).slice(0, TOP),
  largestCss: [...css].sort((a, b) => b.raw - a.raw).slice(0, 5),
  initial,
};

const lines = [];
lines.push(`build: ${dir}`);
lines.push(
  `JS   ${String(js.length).padStart(5)} files  raw ${kb(result.totals.js.raw)} KB  gzip ${kb(result.totals.js.gzip)} KB`
);
lines.push(
  `CSS  ${String(css.length).padStart(5)} files  raw ${kb(result.totals.css.raw)} KB  gzip ${kb(result.totals.css.gzip)} KB`
);
lines.push(`other ${String(other.length).padStart(4)} files  raw ${kb(result.totals.other.raw)} KB`);
if (initial) {
  lines.push(
    `\ninitial JS, shell (entry + root): ${initial.shell.files} files, raw ${kb(initial.shell.raw)} KB, gzip ${kb(initial.shell.gzip)} KB`
  );
  lines.push(`initial JS per route, heaviest 12 (entry + route chain + static imports):`);
  for (const r of initial.routes.slice(0, 12))
    lines.push(`  ${kb(r.gzip)} KB gz ${kb(r.raw)} KB raw ${String(r.files).padStart(4)} files  ${r.path || r.id}`);
}
lines.push(`\nlargest ${TOP} JS chunks (raw / gzip KB):`);
for (const f of result.largestJs) lines.push(`  ${kb(f.raw)} ${kb(f.gzip)}  ${f.file}`);
lines.push(`\nlargest CSS (raw / gzip KB):`);
for (const f of result.largestCss) lines.push(`  ${kb(f.raw)} ${kb(f.gzip)}  ${f.file}`);
console.log(lines.join("\n"));
if (outJson) fs.writeFileSync(outJson, JSON.stringify(result, null, 2));
