/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: indikator kehadiran obrolan (aturan murni)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Tanpa impor supaya bisa diperiksa lewat tsx (kehadiran.check.ts). Dipakai
 * `hooks/use-kehadiran.ts`.
 */

export type TStatusKehadiran = "online" | "away" | "offline";
export type TPetaKehadiran = Map<string, "online" | "away">;

/** Tanpa gerakan selama ini = away. */
export const AMBANG_AWAY_MS = 5 * 60_000;

export type TPesanKehadiran =
  | { tipe: "kehadiran_semua"; peta: Record<string, "online" | "away"> }
  | { tipe: "kehadiran"; user: string; status: TStatusKehadiran };

/** Terapkan pesan dari server: potret lengkap mengganti semua, perubahan satu orang menimpa satu. */
export function terapkanPesanKehadiran(lama: TPetaKehadiran, pesan: TPesanKehadiran): TPetaKehadiran {
  if (pesan.tipe === "kehadiran_semua") return new Map(Object.entries(pesan.peta ?? {}));
  const baru = new Map(lama);
  if (pesan.status === "offline") baru.delete(pesan.user);
  else baru.set(pesan.user, pesan.status);
  return baru;
}

/** Status tab ini: online kalau terlihat dan ada gerakan dalam AMBANG_AWAY_MS. */
export function statusTab(gerakTerakhir: number, sekarang: number, terlihat: boolean): "online" | "away" {
  return terlihat && sekarang - gerakTerakhir < AMBANG_AWAY_MS ? "online" : "away";
}

const URUTAN_STATUS: Record<TStatusKehadiran, number> = { online: 0, away: 1, offline: 2 };

/**
 * Urutkan id orang: online dulu, lalu away, lalu offline; dalam satu kelompok
 * menurut nama. Mengembalikan salinan, daftar asli tidak disentuh. Sort bawaan
 * JS stabil, jadi nama kembar tetap dalam urutan semula.
 */
export function urutkanMenurutKehadiran(
  ids: readonly string[],
  peta: TPetaKehadiran,
  namaDari: (id: string) => string
): string[] {
  const peringkat = (id: string) => URUTAN_STATUS[peta.get(id) ?? "offline"];
  // oxlint-disable-next-line unicorn/no-array-sort -- salinan baru; lib TS proyek belum punya toSorted
  return [...ids].sort((a, b) => peringkat(a) - peringkat(b) || namaDari(a).localeCompare(namaDari(b)));
}
