# UI audit: before and after

Screenshots and metrics from an audit of appearance, layout, accessibility, and
performance (version 2.7.1). The screenshots cover 31 pages, 3 screen sizes, and
light and dark themes: 186 PNGs per folder, plus `metrics.json`.

| Folder                                     | Contents                                                                                      |
| ------------------------------------------ | --------------------------------------------------------------------------------------------- |
| `before/`                                  | State before the audit (2.6.1 baseline)                                                       |
| `final/`                                   | State after all the fixes                                                                     |
| `a11y-before/`, `a11y-after/`              | axe-core results per page (no PNGs)                                                           |
| `perf-before/`, `perf-after/`, `perf-opt/` | Production build performance: baseline, visual fixes only, visual fixes plus bundle size work |

File names: `<page>-<mobile|tablet|desktop>-<light|dark>.png`.
Screen sizes: mobile 390x844, tablet 820x1180, desktop 1440x900.

The `before/` and `final/` screenshots were taken before this branch was merged
with 2.7.0 (the Secretary tier, chat replies, and so on). The chat page in
`final/` doesn't show those features yet. The axe and performance metrics were
also measured on the old baseline.

## Results

| Measurement                                                | Before       | After                   |
| ---------------------------------------------------------- | ------------ | ----------------------- |
| Serious or critical axe violations (page loads out of 155) | 151          | 0                       |
| axe violations at all levels (186 final screenshots)       | not measured | 0                       |
| Pages (route x size) with CLS above 0.1                    | 28           | 1 (0.1045, tablet dark) |
| Median tablet CLS                                          | 0.20         | 0                       |
| `pageerror: undefined` errors                              | 42           | 0                       |
| Console errors                                             | 54           | 0                       |
| React warnings (dev mode, some from libraries)             | 316          | 288                     |
| Pages that failed to render or were thrown back to login   | 0            | 0                       |

### Production build performance

Measured on a production build, CPU throttled 4x, Fast 4G network, median of 3
cold loads, light theme. The Vite dev server wasn't used for these numbers.

| Route (mobile)   | First-load JS (KB, gzip), before / after | LCP (seconds) | TBT (seconds) | CLS           |
| ---------------- | ---------------------------------------- | ------------- | ------------- | ------------- |
| workspace-home   | 2104 / 1526                              | 15.2 / 11.9   | 4.1 / 3.6     | 0.535 / 0     |
| issues-list      | 2136 / 1550                              | 19.6 / 18.4   | 8.1 / 7.7     | 0.557 / 0     |
| chat             | 2021 / 1439                              | 11.8 / 11.3   | 4.1 / 3.4     | 0.285 / 0     |
| approvals        | 1999 / 1415                              | 16.0 / 14.8   | 4.7 / 4.2     | 0 / 0         |
| dashboard-divisi | 1997 / 1410                              | 13.9 / 12.4   | 3.6 / 3.0     | 0.001 / 0.001 |

First-load JS dropped by about 28 percent on every workspace route. Full table:
`node scripts/ui-audit/perf-compare.mjs perf-before perf-after
perf-opt --md` from this folder.

An honest note on the numbers:

- Absolute LCP is high because of the aggressive throttling and the homemade
  HTTP/1.1 static server (`serve-static.mjs`). Comparing builds against each
  other is fair, but the absolute values don't represent production behind
  Caddy.
- `issues-kanban` mobile LCP rose from 13.3 to 18.3 seconds, consistently across
  three runs, while TBT and wall time didn't change. Guess: the CLS fix changed
  which element is counted as the LCP. Not verified.
- The login page is slightly slower (about 0.3 seconds of LCP, 4 more requests)
  because the bundler splits some small chunks together.

## Still open

- `workspace-views` tablet dark has a CLS of 0.1045, just above the limit.
- `page-detail` shows the skeleton forever because the collaboration server
  (`:3100`) isn't part of the local stack. That is an environment artifact. The
  element reported as "clipped" in notifications is the empty detail panel,
  deliberately parked off-screen on narrow screens.
- Not done because they change behavior: one request per chat message for work
  item references and link previews, chat polling that could be replaced by
  socket events, virtualizing the message list, the cross-division and trash
  tables as cards on phones, empty-state illustrations (202 KB gzip on every
  page) that could be lazy loaded, and splitting `@plane/utils` and
  `@plane/ui`.
- Not manually tested: dragging kanban cards on a touch screen, click and
  keyboard behavior on the breadcrumb, member chips, and reaction picker whose
  structure changed, and the rich editor that is now lazy loaded (its ref is
  empty until the code arrives; callers already use `ref.current?.`).

## Re-running

```bash
scripts/ui-audit/stack.sh up        # docker + dev server
set -a; . <env-file-with-UI_AUDIT_EMAIL-and-PASSWORD>; set +a
cd scripts/ui-audit
node shoot.mjs <label>                     # screenshots + metrics
node shoot.mjs <label> --a11y --no-shots   # axe and touch targets
node shoot.mjs <label> --throttle --runs 3 --no-shots   # performance (production build)
```

The password isn't stored in the repo. The script reads it from environment
variables.

## Accessibility (axe and touch targets)

Rules, the number of pages affected before the audit, and the final result of 0
for all of them:

| Rule                        | Level    | Pages affected before |
| --------------------------- | -------- | --------------------- |
| button-name                 | critical | 146                   |
| aria-required-attr          | critical | 116                   |
| label                       | critical | 16                    |
| nested-interactive          | serious  | 141                   |
| label-content-name-mismatch | serious  | 141                   |
| color-contrast              | serious  | 109                   |
| aria-command-name           | serious  | 64                    |
| target-size                 | serious  | 53                    |
| link-name                   | serious  | 8                     |
| scrollable-region-focusable | serious  | 5                     |
| svg-img-alt                 | serious  | 5                     |
| aria-input-field-name       | serious  | 2                     |
| document-title              | serious  | 1                     |

No rule was turned off and no element was hidden with `aria-hidden`. Touch
targets on mobile (at least 24x24 pixels, WCAG 2.2 AA 2.5.8) fell from 1,561
elements to 460 in the intermediate run. That figure still counted disabled
buttons, and a `:disabled` filter was added afterward. One submit button in
`settings-projects` was sometimes flagged for contrast while mid-transition and
passed on the next run.
