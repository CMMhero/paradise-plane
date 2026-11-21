/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: bawaan tampilan dari aturan God Mode (area C)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Logika murni, tidak menyentuh React. Nilai aturan hanya dipakai selagi orang itu
 * belum punya pilihan sendiri di localStorage; pilihan tersimpan selalu menang.
 * Nilai aturan tidak pernah ditulis ke localStorage.
 */

import type { TActivityFilters } from "@plane/constants";
import { E_SORT_ORDER, defaultActivityFilters } from "@plane/constants";

/**
 * Filter aktivitas yang berlaku: daftar tersimpan kalau ada, kalau tidak nilai
 * aturan. Aturan kosong = keempat filter (bawaan lama).
 */
export const efektifFilterAktivitas = (tersimpan: unknown, aturan: readonly string[]): TActivityFilters[] => {
  if (Array.isArray(tersimpan) && tersimpan.length > 0) return tersimpan as TActivityFilters[];
  // Nilai aturan sudah divalidasi terhadap `choices` oleh nilaiAturanWeb; enum string
  // memakai nilai yang sama, jadi cukup disempitkan tipenya.
  return aturan.length > 0 ? (aturan as TActivityFilters[]) : defaultActivityFilters;
};

export type TPosisiKotakKomentar = "follow" | "top" | "bottom";

/** Di mana kotak komentar berada. "follow" = di atas saat terbaru di atas, di bawah saat terlama di atas. */
export const posisiKotakKomentar = (aturan: TPosisiKotakKomentar, urutan: E_SORT_ORDER): "top" | "bottom" =>
  aturan === "follow" ? (urutan === E_SORT_ORDER.DESC ? "top" : "bottom") : aturan;

/**
 * Urutan balasan dalam satu utas. "oldest" = selalu terlama dulu (bawaan lama);
 * "timeline" = ikut urutan linimasa (terbaru dulu saat linimasa DESC).
 */
export const urutkanBalasan = <T extends { created_at?: string | Date | null }>(
  balasan: readonly T[],
  aturan: "oldest" | "timeline",
  urutan: E_SORT_ORDER
): T[] => {
  const arah = aturan === "timeline" && urutan === E_SORT_ORDER.DESC ? -1 : 1;
  const waktu = (b: T) => new Date(b.created_at ?? 0).getTime();
  // oxlint-disable-next-line unicorn/no-array-sort -- apps/web lib is ES2022 (no toSorted); the copy is a fresh array
  return [...balasan].sort((a, b) => arah * (waktu(a) - waktu(b)));
};

/** Pilihan tersimpan kalau masih sah, kalau tidak nilai aturan. */
export const pilihanTersimpanAtauAturan = <T extends string>(tersimpan: unknown, sah: readonly T[], aturan: T): T =>
  sah.includes(tersimpan as T) ? (tersimpan as T) : aturan;
