/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Dashboard Divisi ringkas (KEP-60)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Logika murni di balik tampilan ringkas: kalimat utama dan daftar "yang perlu
 * Anda lihat". Tidak menyentuh React supaya mudah dibaca dan diuji.
 */

import type {
  TDashboardHealth,
  TDivisionDashboard,
  TDivisionGroup,
  TDivisionStats,
} from "@/services/workspace_dashboard.service";

/** Batas daftar "yang perlu Anda lihat". Lebih dari ini berhenti jadi ringkasan. */
export const MAX_ATTENTION_ITEMS = 5;

export type TAttentionItem =
  | { kind: "approvals"; key: string; project: TDivisionStats; count: number }
  | { kind: "overdue"; key: string; project: TDivisionStats; count: number; oldestDays: number | null };

export type THeadline =
  | { kind: "empty" }
  | { kind: "all_ok"; total: number }
  | { kind: "some"; ok: number; total: number; worst: TDivisionGroup };

/** Ringkasan satu kalimat: berapa divisi lancar, dan mana yang paling butuh perhatian. */
export function buildHeadline(divisions: TDivisionGroup[]): THeadline {
  if (divisions.length === 0) return { kind: "empty" };
  const ok = divisions.filter((d) => d.health === "lancar").length;
  if (ok === divisions.length) return { kind: "all_ok", total: divisions.length };
  // Server sudah mengurutkan dari yang paling bermasalah.
  return { kind: "some", ok, total: divisions.length, worst: divisions[0] };
}

/**
 * Persetujuan yang menunggu keputusan dulu (hanya pimpinan yang bisa
 * menyelesaikannya), lalu project bermasalah. Project lancar tidak masuk.
 */
export function buildAttentionItems(data: TDivisionDashboard, max = MAX_ATTENTION_ITEMS): TAttentionItem[] {
  const approvals: TAttentionItem[] = data.projects
    // Urutan server: project paling bermasalah lebih dulu.
    .filter((p) => p.pending_approvals > 0)
    .map((p) => ({ kind: "approvals", key: `approvals-${p.id}`, project: p, count: p.pending_approvals }));

  const overdue: TAttentionItem[] = data.projects
    .filter((p) => p.health !== "lancar" && p.issues_overdue > 0)
    .map((p) => ({
      kind: "overdue",
      key: `overdue-${p.id}`,
      project: p,
      count: p.issues_overdue,
      oldestDays: p.overdue_oldest_days,
    }));

  return [...approvals, ...overdue].slice(0, max);
}

/** Selisih terhadap 7 hari sebelumnya; null kalau keduanya nol (tidak ada yang dibandingkan). */
export function weeklyDelta(current: number, previous: number): number | null {
  if (current === 0 && previous === 0) return null;
  return current - previous;
}

/** Naik itu baik atau buruk? Untuk keterlambatan, naik = buruk. */
export type TTrendTone = "good" | "bad" | "neutral";

export function trendTone(delta: number | null, isHigherBetter: boolean): TTrendTone {
  if (delta === null || delta === 0) return "neutral";
  return delta > 0 === isHigherBetter ? "good" : "bad";
}

const HEALTH_ORDER: Record<TDashboardHealth, number> = { kritis: 0, perhatian: 1, lancar: 2 };

/** Project milik satu divisi, dalam urutan yang dikirim server. */
export function projectsOfDivision(division: TDivisionGroup, projects: TDivisionStats[]): TDivisionStats[] {
  const byId = new Map(projects.map((p) => [p.id, p]));
  return division.project_ids.flatMap((id) => byId.get(id) ?? []);
}

/** Divisi yang perlu tindakan dibuka otomatis di tampilan rinci. */
export function isExpandedByDefault(division: TDivisionGroup): boolean {
  return HEALTH_ORDER[division.health] < HEALTH_ORDER.lancar;
}
