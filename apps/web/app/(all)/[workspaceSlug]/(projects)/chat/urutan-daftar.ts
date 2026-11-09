/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: urutan daftar percakapan obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Aturan murni urutan daftar percakapan (orang dan kanal). Tanpa impor supaya
 * bisa diperiksa lewat tsx (urutan-daftar.check.ts).
 *
 * Tiga lapis, dari atas:
 *   0. ada pesan belum dibaca
 *   1. orangnya sedang online (online atau away; kanal tidak punya kehadiran)
 *   2. sisanya
 * Dalam satu lapis: pesan terakhir paling baru dulu. Yang belum pernah berisi
 * pesan menyusul di bawah lapisnya, urut menurut nama, lalu id supaya hasilnya
 * selalu sama untuk masukan yang sama.
 */

export type TButirUrut = {
  id: string;
  belumDibaca: boolean;
  online: boolean;
  /** ISO pesan terakhir; kosong = belum pernah berbalas pesan. */
  terakhir: string | null;
  nama: string;
};

const lapis = (b: TButirUrut): number => (b.belumDibaca ? 0 : b.online ? 1 : 2);

const waktu = (iso: string | null): number => {
  if (!iso) return Number.NEGATIVE_INFINITY;
  const ms = Date.parse(iso);
  return Number.isNaN(ms) ? Number.NEGATIVE_INFINITY : ms;
};

/**
 * Urutkan butir. `bekuId` = percakapan yang sedang dibuka: lapis "belum
 * dibaca"-nya ditahan (`bekuBelumDibaca`) supaya tidak melompat turun begitu
 * dibuka dan ditandai terbaca. Mengembalikan salinan.
 */
export function urutkanDaftar(
  butir: readonly TButirUrut[],
  beku?: { id: string | null; belumDibaca: boolean }
): TButirUrut[] {
  const efektif = (b: TButirUrut): TButirUrut =>
    beku && beku.id === b.id && beku.belumDibaca && !b.belumDibaca ? { ...b, belumDibaca: true } : b;
  const salinan = butir.map(efektif);
  // oxlint-disable-next-line unicorn/no-array-sort -- salinan baru; lib TS proyek belum punya toSorted
  return salinan.sort((a, b) => {
    const selisihLapis = lapis(a) - lapis(b);
    if (selisihLapis !== 0) return selisihLapis;
    const wa = waktu(a.terakhir);
    const wb = waktu(b.terakhir);
    if (wa !== wb) return wa > wb ? -1 : 1;
    return a.nama.localeCompare(b.nama) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
  });
}
