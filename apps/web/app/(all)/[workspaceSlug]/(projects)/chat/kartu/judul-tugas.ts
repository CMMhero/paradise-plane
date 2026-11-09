/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kalimat judul kartu penugasan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Kalimat penugasan bergantung pada siapa yang membaca. Kartu yang sama dibaca
 * dua orang (pemberi dan penerima), dan "{aktor} assigned you" hanya benar
 * untuk penerima. Tanpa ini pemberi tugas membaca "You assigned you".
 *
 * Murni dan tanpa impor supaya bisa diperiksa lewat tsx (judul-tugas.check.ts).
 */

export type TJudulTugas =
  /** Orang lain menugaskan saya: "{name} assigned you a work item". */
  | { kunci: "assigned" }
  /** Saya menugaskan orang lain: "{name} assigned {assignee} a work item". */
  | { kunci: "assigned_other"; idPenerima: string | null }
  /** Saya menugaskan diri sendiri: "You assigned yourself a work item". */
  | { kunci: "assigned_self" };

export function judulTugas(opsi: {
  aktor: string;
  /** Penerima tugas yang dicatat server (kartu lama tidak punya). */
  penerima: string;
  assignees: readonly string[];
  sayaId: string | undefined;
}): TJudulTugas {
  const { aktor, penerima, assignees, sayaId } = opsi;
  if (!sayaId || !aktor || aktor !== sayaId) return { kunci: "assigned" };
  // Kartu lama tanpa `penerima`: tebak dari daftar penerima tugas. Orang lain
  // lebih dulu, karena kartu ke diri sendiri jarang dan kartu ke DM umum.
  const tujuan = penerima || assignees.find((id) => id !== aktor) || (assignees.includes(aktor) ? aktor : "");
  if (tujuan === aktor) return { kunci: "assigned_self" };
  return { kunci: "assigned_other", idPenerima: tujuan || null };
}
