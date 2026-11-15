#!/usr/bin/env node
/**
 * Bandingkan median metrik beberapa label shoot.mjs (mis. perf-before perf-after perf-opt) per rute x viewport.
 *
 *   node perf-compare.mjs perf-before perf-after [perf-opt] [--md]
 *
 * Kolom: LCP ms, TBT ms, CLS, JS transfer KB, jumlah request. --md mencetak tabel Markdown.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const md = argv.includes("--md");
const labels = argv.filter((a) => !a.startsWith("--"));
if (labels.length < 2) {
  console.error("usage: node perf-compare.mjs <label> <label> [label...] [--md]");
  process.exit(2);
}
const load = (l) => JSON.parse(fs.readFileSync(path.resolve(here, "../../docs/ui-audit", l, "metrics.json"), "utf8"));
const sets = labels.map(load);
const key = (e) => `${e.route}|${e.viewport}`;
const maps = sets.map((s) => new Map(s.results.map((e) => [key(e), e])));
const order = sets[0].results.map(key);
const cols = [
  ["lcp", "LCP"],
  ["tbt", "TBT"],
  ["cls", "CLS"],
  ["jsTransferKB", "JS KB"],
  ["requests", "req"],
];
const fmt = (k, v) => (v == null ? "-" : k === "cls" ? Number(v).toFixed(3) : String(Math.round(v)));
const rows = order.map((k) => {
  const [route, vp] = k.split("|");
  const cells = cols.map(([c]) => maps.map((m) => fmt(c, m.get(k)?.[c])).join(" / "));
  const ok = maps.every((m) => m.get(k)?.ok);
  return [route, vp, ...cells, ok ? "" : "!"];
});
const head = ["route", "viewport", ...cols.map(([, h]) => `${h} (${labels.join(" / ")})`), ""];
if (md) {
  console.log(`| ${head.join(" | ")} |`);
  console.log(`|${head.map(() => "---").join("|")}|`);
  for (const r of rows) console.log(`| ${r.join(" | ")} |`);
} else {
  for (const r of [head, ...rows]) console.log(r.map((c, i) => String(c).padEnd(i < 2 ? 18 : 24)).join(""));
}
