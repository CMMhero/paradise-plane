/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: dashboard KPI
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Logika murni di balik halaman KPI. Tidak menyentuh React.
 */

import type { TKpiMetric, TKpiPeriod, TKpiScope, TKpiScopeKind, TKpiValues } from "@/services/kinerja.service";
import { KPI_PERIODS } from "@/services/kinerja.service";

export type TKpiTone = "good" | "bad" | "neutral";

const SCOPE_KINDS = new Set<string>(["saya", "orang", "departemen", "divisi", "organisasi"] satisfies TKpiScopeKind[]);

/** Lingkup dari query string; apa pun yang tidak dikenal jatuh ke "saya". */
export function scopeFromParams(params: URLSearchParams): TKpiScope {
  const raw = params.get("lingkup");
  const id = params.get("id") ?? undefined;
  if (!raw || !SCOPE_KINDS.has(raw)) return { kind: "saya" };
  const kind = raw as TKpiScopeKind;
  if (kind === "saya" || kind === "organisasi") return { kind };
  return id ? { kind, id } : { kind: "saya" };
}

export const scopeToParams = (scope: TKpiScope): Record<string, string> =>
  scope.kind === "saya" ? {} : { lingkup: scope.kind, ...(scope.id ? { id: scope.id } : {}) };

/** Kunci tunggal untuk pemilih lingkup dan cache SWR. */
export const scopeKey = (scope: TKpiScope): string => (scope.id ? `${scope.kind}:${scope.id}` : scope.kind);

export function scopeFromKey(key: string): TKpiScope {
  const [kind, id] = key.split(":");
  return scopeFromParams(new URLSearchParams(id ? { lingkup: kind, id } : { lingkup: kind }));
}

const DAY = /^\d{4}-\d{2}-\d{2}$/;

/** Periode tersimpan yang rusak atau rentang khusus yang belum lengkap jatuh ke bulan ini. */
export function sanitizePeriod(stored: unknown): TKpiPeriod {
  const fallback: TKpiPeriod = { key: "this_month" };
  if (typeof stored !== "object" || stored === null) return fallback;
  const { key, start, end } = stored as Partial<TKpiPeriod>;
  if (!key || !KPI_PERIODS.includes(key)) return fallback;
  if (key !== "custom") return { key };
  if (!start || !end || !DAY.test(start) || !DAY.test(end) || end < start) return fallback;
  return { key, start, end };
}

/** Selisih terhadap pembanding; null kalau salah satunya tidak ada. */
export function metricDelta(metric: TKpiMetric, values: TKpiValues, previous: TKpiValues): number | null {
  const now = values[metric.key];
  const before = previous[metric.key];
  if (now === null || now === undefined || before === null || before === undefined) return null;
  return Math.round((now - before) * 10) / 10;
}

export function deltaTone(metric: TKpiMetric, delta: number | null): TKpiTone {
  if (delta === null || delta === 0 || metric.direction === "neutral") return "neutral";
  return delta > 0 === (metric.direction === "up") ? "good" : "bad";
}

export type TSort = { key: string; descending: boolean };

/** Urutkan baris menurut satu metrik (atau nama); nilai kosong selalu paling bawah. */
export function sortRows<T extends { values: TKpiValues }>(rows: T[], sort: TSort, nameOf: (row: T) => string): T[] {
  const sign = sort.descending ? -1 : 1;
  // oxlint-disable-next-line unicorn/no-array-sort -- apps/web lib is ES2022 (no toSorted); sorts a copy
  return [...rows].sort((a, b) => {
    if (sort.key === "name") return sign * nameOf(a).localeCompare(nameOf(b));
    const x = a.values[sort.key] ?? null;
    const y = b.values[sort.key] ?? null;
    if (x === null || y === null) return x === y ? nameOf(a).localeCompare(nameOf(b)) : x === null ? 1 : -1;
    return x === y ? nameOf(a).localeCompare(nameOf(b)) : sign * (x - y);
  });
}

/** Metrik yang punya nilai di setidaknya satu baris (kolom yang seluruhnya kosong disembunyikan). */
export const metricsWithData = (metrics: TKpiMetric[], rows: { values: TKpiValues }[]): TKpiMetric[] =>
  metrics.filter((m) => rows.some((r) => r.values[m.key] !== null && r.values[m.key] !== undefined));
