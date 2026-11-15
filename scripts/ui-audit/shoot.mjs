#!/usr/bin/env node
/**
 * UI audit harness: screenshots + perf/overflow/console metrics for the local app.
 *
 *   UI_AUDIT_EMAIL=... UI_AUDIT_PASSWORD=... node shoot.mjs <label> [--only a,b] [--viewports mobile,desktop]
 *                                                           [--themes light,dark] [--full-page] [--skip-existing]
 *                                                           [--a11y] [--no-shots]
 *
 * Output: docs/ui-audit/<label>/<route>-<viewport>-<theme>.png and docs/ui-audit/<label>/metrics.json
 *
 * --a11y     run axe-core (WCAG 2.0/2.1/2.2 A+AA tags, no best-practice) per page and, on mobile, count touch
 *            targets under 24x24 CSS px (WCAG 2.2 2.5.8). Results land in metrics.json as `a11y` / `touchTargets`,
 *            plus an aggregated `a11ySummary` (rule x impact, ranked).
 * --no-shots skip PNG writes (metrics only).
 * --merge    keep the existing metrics.json results of this label and replace only the route/viewport/theme
 *            combinations measured now (for tablet-light add-on runs and --only re-runs).
 * --throttle realistic device: CPU 4x slowdown + DevTools "Fast 4G" (165 ms RTT, ~9 Mbps down, ~1.5 Mbps up) via CDP,
 *            and the HTTP cache disabled so every load is a cold first visit. Implies --runs 3. Settling also waits
 *            for a 2 s quiet window (no network event, no long task; max 60 s) so metrics cover the full load.
 * --runs N   load each route N times; numeric metrics are the median, raw values land in `samples`.
 *
 * Env: UI_AUDIT_EMAIL, UI_AUDIT_PASSWORD (required), UI_AUDIT_BASE (default http://localhost:4000),
 *      UI_AUDIT_MODE (free-text note stored in metrics.json, e.g. "production build"),
 *      UI_AUDIT_WORKSPACE (default pt-paradise-perkasa), UI_AUDIT_PROJECT (project identifier, default: the
 *      project with most work items), UI_AUDIT_STATE (storageState path, default $TMPDIR/ui-audit-auth.json).
 * Credentials are never written to disk (only the session cookie state, outside the repo).
 */
import { AxeBuilder } from "@axe-core/playwright";
import { chromium } from "playwright";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "../..");

// ---------- args / env ----------
const argv = process.argv.slice(2);
const flag = (n) => argv.includes(`--${n}`);
const opt = (n) => {
  const i = argv.indexOf(`--${n}`);
  return i >= 0 ? argv[i + 1] : undefined;
};
const VALUE_FLAGS = new Set(["--only", "--viewports", "--themes", "--runs"]);
const label = argv.find((a, i) => !a.startsWith("--") && !VALUE_FLAGS.has(argv[i - 1]));
if (!label) {
  console.error(
    "usage: node shoot.mjs <label> [--only a,b] [--viewports mobile,tablet,desktop] [--themes light,dark] [--full-page] [--skip-existing] [--a11y] [--no-shots] [--merge]"
  );
  process.exit(2);
}
const EMAIL = process.env.UI_AUDIT_EMAIL;
const PASSWORD = process.env.UI_AUDIT_PASSWORD;
if (!EMAIL || !PASSWORD) {
  console.error("Set UI_AUDIT_EMAIL and UI_AUDIT_PASSWORD");
  process.exit(2);
}
const BASE = (process.env.UI_AUDIT_BASE || "http://localhost:4000").replace(/\/$/, "");
const WS = process.env.UI_AUDIT_WORKSPACE || "pt-paradise-perkasa";
const STATE = process.env.UI_AUDIT_STATE || path.join(os.tmpdir(), "ui-audit-auth.json");
const outDir = path.join(repoRoot, "docs/ui-audit", label);
fs.mkdirSync(outDir, { recursive: true });

const ALL_VIEWPORTS = {
  mobile: { width: 390, height: 844, isMobile: true, hasTouch: true, deviceScaleFactor: 2 },
  tablet: { width: 820, height: 1180, isMobile: true, hasTouch: true, deviceScaleFactor: 1 },
  desktop: { width: 1440, height: 900, isMobile: false, hasTouch: false, deviceScaleFactor: 1 },
};
const viewports = (opt("viewports") || "mobile,tablet,desktop").split(",").filter((v) => ALL_VIEWPORTS[v]);
const themes = (opt("themes") || "light,dark").split(",");
const only = opt("only")?.split(",");
const A11Y = flag("a11y");
const SHOTS = !flag("no-shots");
const THROTTLE = flag("throttle");
const RUNS = Math.max(1, Number(opt("runs") ?? (THROTTLE ? 3 : 1)) || 1);
// Preset "Fast 4G" DevTools (byte/detik, latensi sudah dikali faktor 2.75 seperti di DevTools).
const FAST_4G = {
  offline: false,
  latency: 60 * 2.75,
  downloadThroughput: ((9 * 1000 * 1000) / 8) * 0.9,
  uploadThroughput: ((1.5 * 1000 * 1000) / 8) * 0.9,
};
const CPU_SLOWDOWN = 4;
// Metrik numerik yang diambil mediannya bila --runs > 1.
const MEDIAN_KEYS = [
  "wallMs",
  "dcl",
  "load",
  "lcp",
  "cls",
  "tbt",
  "longTasks",
  "longestTask",
  "requests",
  "transferKB",
  "jsTransferKB",
];
const median = (xs) => {
  const v = xs.filter((x) => typeof x === "number").sort((a, b) => a - b);
  if (!v.length) return null;
  const m = v.length >> 1;
  return v.length % 2 ? v[m] : +((v[m - 1] + v[m]) / 2).toFixed(4);
};
const AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
// Pengecualian sempit untuk markup pihak ketiga yang tidak bisa kita ubah. Setiap baris WAJIB punya alasan.
const AXE_EXCLUDE = [
  // (kosong) tambahkan { selector, why } bila temuan terbukti berasal dari pustaka luar.
];

// ---------- init script: web-vitals collectors ----------
const INIT = `(() => {
  const w = window; w.__audit = { lcp: 0, cls: 0, tbt: 0, longTasks: 0, longest: 0, lastLongEnd: 0 };
  try { new PerformanceObserver((l) => { for (const e of l.getEntries()) w.__audit.lcp = e.startTime; }).observe({ type: "largest-contentful-paint", buffered: true }); } catch {}
  w.__audit.shifts = [];
  const desc = (n) => { if (!n || n.nodeType !== 1) return n ? n.nodeName : "?"; const c = (n.className && n.className.toString ? n.className.toString() : "").trim().split(" ").filter(Boolean).slice(0, 4).join("."); return n.tagName.toLowerCase() + (n.id ? "#" + n.id : "") + (c ? "." + c : ""); };
  try { new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) { w.__audit.cls += e.value; if (w.__audit.shifts.length < 20) w.__audit.shifts.push({ t: Math.round(e.startTime), v: +e.value.toFixed(4), nodes: (e.sources || []).slice(0, 3).map((s) => desc(s.node)) }); } }).observe({ type: "layout-shift", buffered: true }); } catch {}
  try { new PerformanceObserver((l) => { for (const e of l.getEntries()) { w.__audit.longTasks++; w.__audit.tbt += Math.max(0, e.duration - 50); w.__audit.longest = Math.max(w.__audit.longest, e.duration); w.__audit.lastLongEnd = Math.max(w.__audit.lastLongEnd, e.startTime + e.duration); } }).observe({ type: "longtask", buffered: true }); } catch {}
})();`;

// ---------- helpers ----------
const csrfPost = async (ctx, url, body) => {
  const cookies = await ctx.cookies(BASE);
  const csrf = cookies.find((c) => c.name === "csrftoken")?.value;
  return ctx.request.patch(url, { data: body, headers: { "X-CSRFToken": csrf ?? "", Referer: BASE } });
};

async function login(browser) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await page.goto(`${BASE}/`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("input#email", { timeout: 60000 });
  await page.fill("input#email", EMAIL);
  await page.keyboard.press("Enter");
  await page.waitForSelector('input[type="password"]', { timeout: 30000 });
  await page.fill('input[type="password"]', PASSWORD);
  await page.keyboard.press("Enter");
  await page.waitForURL((u) => !/^\/?$/.test(u.pathname) && !u.pathname.startsWith("/sign-up"), { timeout: 90000 });
  await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
  await ctx.storageState({ path: STATE });
  await ctx.close();
}

async function sessionValid(browser) {
  if (!fs.existsSync(STATE)) return false;
  const ctx = await browser.newContext({ storageState: STATE });
  try {
    const r = await ctx.request.get(`${process.env.UI_AUDIT_API || "http://localhost:8000"}/api/users/me/`);
    return r.ok();
  } finally {
    await ctx.close();
  }
}

async function discover(browser) {
  const api = process.env.UI_AUDIT_API || "http://localhost:8000";
  const ctx = await browser.newContext({ storageState: STATE });
  const get = async (p) => {
    const r = await ctx.request.get(`${api}${p}`);
    return r.ok() ? r.json() : null;
  };
  const me = await get("/api/users/me/");
  const projects = (await get(`/api/workspaces/${WS}/projects/`)) ?? [];
  const list = Array.isArray(projects) ? projects : (projects.results ?? []);
  if (!list.length) throw new Error("No projects visible to this user in workspace " + WS);
  let project = list.find((p) => p.identifier === process.env.UI_AUDIT_PROJECT);
  if (!project) project = [...list].sort((a, b) => (b.total_issues ?? 0) - (a.total_issues ?? 0))[0];
  const pid = project.id;
  const issuesRes = await get(`/api/workspaces/${WS}/projects/${pid}/issues/?per_page=50&order_by=-created_at`);
  const flat = (() => {
    const r = issuesRes?.results ?? issuesRes ?? [];
    if (Array.isArray(r)) return r;
    return Object.values(r).flatMap((g) => g?.results ?? (Array.isArray(g) ? g : []));
  })();
  const issue = flat.find((i) => !i.parent_id && (i.sub_issues_count ?? 0) > 0) ?? flat[0];
  const modules = (await get(`/api/workspaces/${WS}/projects/${pid}/modules/`)) ?? [];
  const mod = (Array.isArray(modules) ? modules : (modules.results ?? []))[0];
  const pages = (await get(`/api/workspaces/${WS}/projects/${pid}/pages/`)) ?? [];
  const page = (Array.isArray(pages) ? pages : (pages.results ?? []))[0];
  await ctx.close();
  return {
    me,
    project,
    pid,
    issueKey: issue ? `${project.identifier}-${issue.sequence_id}` : null,
    moduleId: mod?.id,
    pageId: page?.id,
  };
}

/** Set the saved layout (list/kanban/...) for the project, as the layout switcher does. */
async function setLayout(ctx, pid, layout) {
  const api = process.env.UI_AUDIT_API || "http://localhost:8000";
  const cur = await ctx.request.get(`${api}/api/workspaces/${WS}/projects/${pid}/user-properties/`);
  const body = cur.ok() ? await cur.json() : {};
  const display_filters = { ...(body.display_filters ?? {}), layout };
  const cookies = await ctx.cookies(api);
  const csrf = cookies.find((c) => c.name === "csrftoken")?.value ?? "";
  const r = await ctx.request.patch(`${api}/api/workspaces/${WS}/projects/${pid}/user-properties/`, {
    data: { display_filters },
    headers: { "X-CSRFToken": csrf, Referer: BASE, "Content-Type": "application/json" },
  });
  if (!r.ok()) console.warn(`  ! layout ${layout}: PATCH ${r.status()}`);
}

function buildRoutes(d) {
  const p = `/${WS}/projects/${d.pid}`;
  const R = [
    { name: "login", path: "/", anon: true },
    { name: "workspace-home", path: `/${WS}` },
    { name: "projects-list", path: `/${WS}/projects` },
    { name: "issues-list", path: `${p}/issues`, layout: "list" },
    { name: "issues-kanban", path: `${p}/issues`, layout: "kanban" },
    { name: "issues-spreadsheet", path: `${p}/issues`, layout: "spreadsheet" },
    { name: "issues-calendar", path: `${p}/issues`, layout: "calendar" },
    { name: "issues-gantt", path: `${p}/issues`, layout: "gantt_chart" },
    d.issueKey && { name: "work-item-detail", path: `/${WS}/browse/${d.issueKey}`, layout: "list" },
    { name: "modules", path: `${p}/modules` },
    d.moduleId && { name: "module-detail", path: `${p}/modules/${d.moduleId}` },
    { name: "views", path: `${p}/views` },
    { name: "pages", path: `${p}/pages` },
    d.pageId && { name: "page-detail", path: `${p}/pages/${d.pageId}` },
    { name: "intake", path: `${p}/intake` },
    { name: "approvals", path: `${p}/persetujuan` },
    { name: "analytics", path: `/${WS}/analytics/overview` },
    { name: "dashboard-divisi", path: `/${WS}/dashboard-divisi` },
    { name: "chat", path: `/${WS}/chat` },
    { name: "wiki", path: `/${WS}/wiki` },
    { name: "notifications", path: `/${WS}/notifications` },
    { name: "drafts", path: `/${WS}/drafts` },
    { name: "workspace-views", path: `/${WS}/workspace-views/all-issues` },
    d.me?.id && { name: "profile", path: `/${WS}/profile/${d.me.id}` },
    d.me?.id && { name: "profile-assigned", path: `/${WS}/profile/${d.me.id}/assigned` },
    { name: "settings-workspace", path: `/${WS}/settings` },
    { name: "settings-members", path: `/${WS}/settings/members` },
    { name: "settings-projects", path: `/${WS}/settings/projects` },
    { name: "settings-project", path: `/${WS}/settings/projects/${d.pid}` },
    { name: "settings-project-states", path: `/${WS}/settings/projects/${d.pid}/states` },
    { name: "settings-account", path: `/settings/profile/general` },
  ].filter(Boolean);
  return only ? R.filter((r) => only.includes(r.name)) : R;
}

// Jendela tenang (mirip heuristik TTI Lighthouse): tidak ada peristiwa jaringan dan tidak ada long task selama
// QUIET_MS. Dipakai saat --throttle: CPU 4x membuat parse JS memakan > 500 ms tanpa lalu lintas jaringan, jadi
// "networkidle" Playwright terpicu di tengah pemuatan (aplikasi belum termuat, JS & LCP terhitung separuh).
const QUIET_MS = 2000;
const QUIET_MAX_MS = 60000;
async function waitQuiet(page, lastNetAt) {
  const t0 = Date.now();
  while (Date.now() - t0 < QUIET_MAX_MS) {
    const sinceLong = await page.evaluate(() => performance.now() - (window.__audit?.lastLongEnd ?? 0)).catch(() => 0);
    if (Date.now() - lastNetAt() >= QUIET_MS && sinceLong >= QUIET_MS) return true;
    await page.waitForTimeout(250);
  }
  return false;
}

async function settle(page, lastNetAt) {
  await page.waitForLoadState("domcontentloaded").catch(() => {});
  if (lastNetAt) await waitQuiet(page, lastNetAt);
  await page.waitForLoadState("networkidle", { timeout: 20000 }).catch(() => {});
  // wait for spinners / skeletons to disappear (bounded)
  await page
    .waitForFunction(
      () => {
        const sel = '[role="progressbar"], .animate-spin, [data-loading="true"], .animate-pulse';
        return ![...document.querySelectorAll(sel)].some((el) => {
          const r = el.getBoundingClientRect();
          const cs = getComputedStyle(el);
          return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none";
        });
      },
      undefined,
      { timeout: 15000 }
    )
    .catch(() => {});
  await page.evaluate(() => document.fonts?.ready).catch(() => {});
  if (lastNetAt) await waitQuiet(page, lastNetAt);
  else await page.waitForTimeout(700);
}

const OVERFLOW = () => {
  const iw = window.innerWidth;
  const doc = document.documentElement;
  const res = {
    scrollWidth: doc.scrollWidth,
    innerWidth: iw,
    bodyScrollWidth: document.body.scrollWidth,
    overflow: doc.scrollWidth > iw + 1 || document.body.scrollWidth > iw + 1,
    offenders: [],
  };
  if (res.overflow) {
    const seen = [];
    for (const el of document.querySelectorAll("body *")) {
      const r = el.getBoundingClientRect();
      if (r.width && r.right > iw + 1) {
        let anc = el.parentElement,
          clipped = false;
        while (anc && anc !== document.body) {
          const o = getComputedStyle(anc).overflowX;
          if (o === "auto" || o === "scroll" || o === "hidden") {
            clipped = true;
            break;
          }
          anc = anc.parentElement;
        }
        if (!clipped)
          seen.push({
            tag: el.tagName.toLowerCase(),
            cls: (el.className?.toString?.() || "").slice(0, 80),
            right: Math.round(r.right),
            w: Math.round(r.width),
          });
      }
      if (seen.length >= 6) break;
    }
    res.offenders = seen;
  }
  // Content that runs off the right edge of the viewport and is cut by an overflow:hidden/clip ancestor
  // (no scrollbar, so users cannot reach it). Document-level overflow above misses this because the app
  // scrolls inside its own containers.
  const clipped = [];
  for (const el of document.querySelectorAll("body *")) {
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4 || r.right <= iw + 2 || r.left >= iw) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === "hidden" || cs.display === "none" || cs.position === "fixed" || cs.opacity === "0") continue;
    let anc = el.parentElement,
      how = null;
    while (anc && anc !== document.documentElement) {
      const o = getComputedStyle(anc).overflowX;
      if (o === "auto" || o === "scroll") {
        how = null;
        break;
      }
      if (o === "hidden" || o === "clip") {
        how = how || "hidden";
      }
      anc = anc.parentElement;
    }
    if (how && r.left < iw - 8)
      clipped.push({
        tag: el.tagName.toLowerCase(),
        cls: (el.className?.toString?.() || "").slice(0, 70),
        text: (el.innerText || "").trim().slice(0, 30),
        left: Math.round(r.left),
        right: Math.round(r.right),
      });
    if (clipped.length >= 5) break;
  }
  res.clippedRight = clipped;
  return res;
};

/** Elemen interaktif terlihat yang area sentuhnya < 24x24 CSS px (WCAG 2.2 AA 2.5.8). */
const TOUCH_TARGETS = () => {
  const MIN = 24;
  const sel =
    'a[href], button, input:not([type="hidden"]), select, textarea, [role="button"], [role="tab"], [role="menuitem"]';
  const cssPath = (el) => {
    const parts = [];
    for (let n = el; n && n.nodeType === 1 && parts.length < 4; n = n.parentElement) {
      if (n.id && /^[A-Za-z][\w-]*$/.test(n.id)) {
        parts.unshift(`#${n.id}`);
        break;
      }
      let p = n.tagName.toLowerCase();
      const al = n.getAttribute("aria-label");
      if (al) p += `[aria-label="${al.slice(0, 40)}"]`;
      else {
        const cls = [...n.classList].filter((c) => /^[a-z][\w-]*$/i.test(c)).slice(0, 2);
        if (cls.length) p += "." + cls.join(".");
      }
      parts.unshift(p);
    }
    return parts.join(" > ");
  };
  const out = [];
  for (const el of document.querySelectorAll(sel)) {
    if (el.closest('[aria-hidden="true"], [inert]')) continue;
    // kontrol nonaktif bukan sasaran sentuh (WCAG 2.5.8 hanya untuk sasaran yang bisa dipakai)
    if (el.matches(":disabled, [aria-disabled='true']")) continue;
    if (el.checkVisibility && !el.checkVisibility({ opacityProperty: true, visibilityProperty: true })) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    // label yang membungkus checkbox/radio kecil adalah area sentuh yang sah
    if (el.tagName === "INPUT" && /checkbox|radio/.test(el.type)) {
      const lab = el.closest("label") || (el.id && document.querySelector(`label[for="${CSS.escape(el.id)}"]`));
      if (lab) {
        const lr = lab.getBoundingClientRect();
        if (lr.width >= MIN && lr.height >= MIN) continue;
      }
    }
    let w = r.width,
      h = r.height;
    if (el.hasAttribute("data-sentuh-lega")) {
      const a = getComputedStyle(el, "::after");
      if (a.content && a.content !== "none") {
        w = Math.max(w, parseFloat(a.width) || 0);
        h = Math.max(h, parseFloat(a.height) || 0);
      }
    }
    if (w < MIN || h < MIN)
      out.push({
        selector: cssPath(el),
        w: Math.round(w),
        h: Math.round(h),
        text: (el.getAttribute("aria-label") || el.innerText || el.value || "").trim().slice(0, 30),
      });
  }
  return { count: out.length, items: out.slice(0, 15) };
};

async function runAxe(page) {
  let b = new AxeBuilder({ page }).withTags(AXE_TAGS);
  for (const x of AXE_EXCLUDE) b = b.exclude(x.selector);
  const res = await b.analyze();
  return res.violations.map((v) => ({
    id: v.id,
    impact: v.impact,
    nodes: v.nodes.length,
    help: v.help,
    samples: v.nodes.slice(0, 3).map((n) => ({
      target: n.target.join(" "),
      html: n.html.slice(0, 200),
      summary: (n.failureSummary || "").slice(0, 240),
    })),
  }));
}

// ---------- main ----------
const browser = await chromium.launch({ args: ["--disable-dev-shm-usage"] });
if (!(await sessionValid(browser))) {
  console.log("logging in ...");
  await login(browser);
}
const d = await discover(browser);
console.log(`project ${d.project.identifier} (${d.pid}), issue ${d.issueKey}, user ${d.me?.email}`);
const routes = buildRoutes(d);
const metrics = {
  label,
  generatedAt: new Date().toISOString(),
  base: BASE,
  workspace: WS,
  project: d.project.identifier,
  mode: process.env.UI_AUDIT_MODE || "dev-server numbers are not production numbers; compare before/after only",
  throttle: THROTTLE ? { cpuSlowdown: CPU_SLOWDOWN, network: "Fast 4G", ...FAST_4G, cacheDisabled: true } : null,
  runs: RUNS,
  results: [],
};
let shots = 0;

for (const vpName of viewports) {
  for (const theme of themes) {
    const vp = ALL_VIEWPORTS[vpName];
    const mk = async (anon) => {
      const ctx = await browser.newContext({
        viewport: { width: vp.width, height: vp.height },
        isMobile: vp.isMobile,
        hasTouch: vp.hasTouch,
        deviceScaleFactor: vp.deviceScaleFactor,
        colorScheme: theme,
        locale: "id-ID",
        storageState: anon ? undefined : STATE,
      });
      await ctx.addInitScript(INIT);
      await ctx.addInitScript((t) => {
        try {
          localStorage.setItem("theme", t);
        } catch {}
      }, theme);
      return ctx;
    };
    const authed = await mk(false);
    const anon = await mk(true);
    for (const r of routes) {
      const file = `${r.name}-${vpName}-${theme}.png`;
      const target = path.join(outDir, file);
      if (SHOTS && flag("skip-existing") && fs.existsSync(target)) continue;
      const runsOut = [];
      for (let run = 0; run < RUNS; run++) {
        const ctx = r.anon ? anon : authed;
        const entry = { route: r.name, path: r.path, viewport: vpName, theme, file, ok: false, run };
        const page = await ctx.newPage();
        const consoleErrors = [];
        const failedRequests = [];
        page.on("console", (m) => {
          if (m.type() === "error") consoleErrors.push(m.text().slice(0, 300));
        });
        page.on("pageerror", (e) => consoleErrors.push(`pageerror: ${String(e.message).slice(0, 300)}`));
        page.on("response", (res) => {
          if (res.status() >= 400)
            failedRequests.push(
              `${res.status()} ${res.request().method()} ${res.url().replace(BASE, "").slice(0, 120)}`
            );
        });
        const cdp = await ctx.newCDPSession(page);
        await cdp.send("Network.enable");
        if (THROTTLE) {
          await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
          await cdp.send("Network.emulateNetworkConditions", FAST_4G);
          await cdp.send("Emulation.setCPUThrottlingRate", { rate: CPU_SLOWDOWN });
        }
        const reqs = new Map();
        let bytes = 0,
          jsBytes = 0,
          count = 0;
        let lastNet = Date.now();
        cdp.on("Network.requestWillBeSent", (e) => {
          reqs.set(e.requestId, e.type);
          count++;
          lastNet = Date.now();
        });
        cdp.on("Network.loadingFinished", (e) => {
          bytes += e.encodedDataLength;
          if (reqs.get(e.requestId) === "Script") jsBytes += e.encodedDataLength;
          lastNet = Date.now();
        });
        cdp.on("Network.loadingFailed", () => {
          lastNet = Date.now();
        });
        try {
          if (r.layout) await setLayout(ctx, d.pid, r.layout);
          const t0 = Date.now();
          const resp = await page.goto(`${BASE}${r.path}`, { waitUntil: "domcontentloaded", timeout: 90000 });
          await settle(page, THROTTLE ? () => lastNet : undefined);
          entry.status = resp?.status();
          entry.finalUrl = page.url().replace(BASE, "");
          entry.wallMs = Date.now() - t0;
          const nav = await page.evaluate(() => {
            const n = performance.getEntriesByType("navigation")[0];
            const a = window.__audit || {};
            return {
              clsShifts: (a.shifts || []).filter((x) => x.v >= 0.001).slice(0, 8),
              dcl: n ? Math.round(n.domContentLoadedEventEnd) : null,
              load: n ? Math.round(n.loadEventEnd) : null,
              lcp: Math.round(a.lcp || 0),
              cls: +(a.cls || 0).toFixed(4),
              tbt: Math.round(a.tbt || 0),
              longTasks: a.longTasks || 0,
              longestTask: Math.round(a.longest || 0),
            };
          });
          Object.assign(entry, nav);
          entry.requests = count;
          entry.transferKB = Math.round(bytes / 1024);
          entry.jsTransferKB = Math.round(jsBytes / 1024);
          entry.overflow = await page.evaluate(OVERFLOW);
          entry.title = (await page.title()).slice(0, 80);
          // real-page sanity: authed routes must not bounce to login or show a hard error
          const body = (await page.evaluate(() => document.body.innerText || "")).slice(0, 4000);
          entry.bounceToLogin =
            !r.anon && (/^\/(\?.*)?$/.test(entry.finalUrl) || /sign-in|sign-up/.test(entry.finalUrl));
          entry.looksLikeError =
            /404|tidak ditemukan|not found|something went wrong|terjadi kesalahan|Application Error/i.test(
              body.slice(0, 600)
            ) && body.length < 600;
          // Server dev yang gagal memuat modul (mis. dist paket sedang dibangun ulang) menampilkan overlay Vite; hasil
          // halaman itu tidak mewakili aplikasi, jadi ditandai gagal supaya tidak ikut dihitung.
          entry.viteOverlay = (await page.locator("vite-error-overlay").count()) > 0 || entry.status >= 500;
          if (A11Y) {
            try {
              entry.a11y = await runAxe(page);
            } catch (e) {
              entry.a11yError = String(e.message).split("\n")[0].slice(0, 300);
            }
            if (vpName === "mobile") entry.touchTargets = await page.evaluate(TOUCH_TARGETS);
          }
          if (SHOTS && run === 0) {
            await page.screenshot({ path: target, fullPage: flag("full-page") });
            shots++;
          }
          entry.ok = !entry.bounceToLogin && !entry.looksLikeError && !entry.viteOverlay;
        } catch (e) {
          entry.error = String(e.message).split("\n")[0].slice(0, 300);
          if (SHOTS && run === 0)
            try {
              await page.screenshot({ path: target.replace(/\.png$/, "-FAILED.png") });
            } catch {}
        }
        // Split noise from signal: React dev warnings, the optional live-collab server (:3100, not part of this
        // stack) and the expected 401 on the login page are reported separately from real errors.
        const isNoise = (m) => /^Warning:/.test(m) || /localhost:3100/.test(m) || (r.anon && /401/.test(m));
        const real = consoleErrors.filter((m) => !isNoise(m));
        entry.consoleErrors = [...new Set(real)].slice(0, 10);
        entry.consoleErrorCount = real.length;
        entry.reactWarningCount = consoleErrors.filter((m) => /^Warning:/.test(m)).length;
        entry.liveServerRefused = consoleErrors.some((m) => /localhost:3100/.test(m));
        entry.failedRequests = [...new Set(failedRequests)].slice(0, 10);
        runsOut.push(entry);
        console.log(
          `${RUNS > 1 ? `#${run + 1} ` : ""}${entry.ok ? "ok  " : "FAIL"} ${r.name.padEnd(24)} ${vpName.padEnd(8)} ${theme.padEnd(5)} lcp=${entry.lcp ?? "-"} cls=${entry.cls ?? "-"} tbt=${entry.tbt ?? "-"} js=${entry.jsTransferKB ?? "-"}KB req=${entry.requests ?? "-"} ovf=${entry.overflow?.overflow ? "YES" : "no"} err=${entry.consoleErrorCount} warn=${entry.reactWarningCount}${A11Y ? ` axe=${(entry.a11y ?? []).filter((v) => v.impact === "serious" || v.impact === "critical").length}s/c${entry.touchTargets ? ` tt=${entry.touchTargets.count}` : ""}` : ""}${entry.error ? " :: " + entry.error : ""}`
        );
        await page.close();
      }
      if (RUNS === 1) metrics.results.push(runsOut[0]);
      else {
        // Median per metrik dari run yang berhasil; run gagal tetap tercatat di samples.
        const good = runsOut.filter((e) => e.ok);
        const base = { ...(good[0] ?? runsOut[0]) };
        delete base.run;
        for (const k of MEDIAN_KEYS) base[k] = median((good.length ? good : runsOut).map((e) => e[k]));
        base.ok = good.length === runsOut.length;
        base.okRuns = good.length;
        base.samples = Object.fromEntries(MEDIAN_KEYS.map((k) => [k, runsOut.map((e) => e[k] ?? null)]));
        metrics.results.push(base);
        console.log(
          `  median ${r.name.padEnd(24)} ${vpName.padEnd(8)} lcp=${base.lcp} cls=${base.cls} tbt=${base.tbt} js=${base.jsTransferKB}KB req=${base.requests} (${good.length}/${runsOut.length} ok)`
        );
      }
    }
    await authed.close();
    await anon.close();
  }
}
// restore project layout to list so repeated runs are stable
{
  const ctx = await browser.newContext({ storageState: STATE });
  await setLayout(ctx, d.pid, "list").catch(() => {});
  await ctx.close();
}
await browser.close();
metrics.screenshots = shots;
const metricsFile = path.join(outDir, "metrics.json");
if (flag("merge") && fs.existsSync(metricsFile)) {
  const prev = JSON.parse(fs.readFileSync(metricsFile, "utf8"));
  const key = (e) => `${e.route}|${e.viewport}|${e.theme}`;
  const fresh = new Set(metrics.results.map(key));
  metrics.results = [...(prev.results ?? []).filter((e) => !fresh.has(key(e))), ...metrics.results];
  metrics.screenshots = (prev.screenshots ?? 0) + shots;
}
if (A11Y) {
  // Ringkasan: aturan x dampak, dijumlah lintas rute/ukuran/tema, diurutkan berat -> ringan lalu banyaknya halaman.
  const rank = { critical: 0, serious: 1, moderate: 2, minor: 3 };
  metrics.a11yTags = AXE_TAGS;
  metrics.a11yExcluded = AXE_EXCLUDE;
  const agg = new Map();
  for (const e of metrics.results)
    for (const v of e.a11y ?? []) {
      const k = `${v.id}|${v.impact}`;
      const a = agg.get(k) ?? { id: v.id, impact: v.impact, pages: 0, nodes: 0, routes: new Set() };
      a.pages++;
      a.nodes += v.nodes;
      a.routes.add(e.route);
      agg.set(k, a);
    }
  metrics.a11ySummary = [...agg.values()]
    .map((a) => ({ ...a, routes: [...a.routes] }))
    .sort((x, y) => (rank[x.impact] ?? 9) - (rank[y.impact] ?? 9) || y.pages - x.pages);
  metrics.touchTargetSummary = metrics.results
    .filter((e) => e.touchTargets)
    .map((e) => ({ route: e.route, theme: e.theme, count: e.touchTargets.count }));
  console.log("\naxe summary (rule impact pages nodes):");
  for (const a of metrics.a11ySummary)
    console.log(
      `  ${a.impact.padEnd(9)} ${a.id.padEnd(32)} ${String(a.pages).padStart(4)} ${String(a.nodes).padStart(6)}`
    );
}
fs.writeFileSync(metricsFile, JSON.stringify(metrics, null, 2));
console.log(`\n${shots} screenshots -> ${path.relative(repoRoot, outDir)}  (metrics.json written)`);
