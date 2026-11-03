/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: laporan tugas selesai (KEP-62)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Logika murni di balik tampilan Laporan. Tidak menyentuh React.
 */

import type { TCompletedItem, TCompletedReport, TReportDivision } from "@/services/workspace_dashboard.service";

/** {project_id: tugas selesai}, urutan server (terbaru dulu) dipertahankan. */
export function itemsByProject(items: TCompletedItem[]): Map<string, TCompletedItem[]> {
  const map = new Map<string, TCompletedItem[]>();
  for (const item of items) map.set(item.project_id, [...(map.get(item.project_id) ?? []), item]);
  return map;
}

/** Lebar bilah divisi relatif terhadap divisi dengan selesai terbanyak, 0-100. */
export function barPercent(division: TReportDivision, divisions: TReportDivision[]): number {
  const max = Math.max(0, ...divisions.map((d) => d.completed));
  return max > 0 ? Math.round((division.completed * 100) / max) : 0;
}

/** Selisih selesai terhadap periode pembanding; null kalau keduanya nol. */
export function completedDelta(report: TCompletedReport): number | null {
  const { completed } = report.totals;
  const previous = report.previous.completed;
  if (completed === 0 && previous === 0) return null;
  return completed - previous;
}

/** "2026-11-03" -> Date tengah malam lokal (bukan UTC, supaya tanggalnya tidak bergeser). */
export const parseDay = (day: string): Date => new Date(`${day}T00:00:00`);

export const formatDay = (day: string, withYear = false): string =>
  parseDay(day).toLocaleDateString([], { day: "numeric", month: "short", ...(withYear ? { year: "numeric" } : {}) });
