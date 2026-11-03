/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: sebutan @ di obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Logika murni sebutan `@nama`, tanpa DOM, supaya bisa diperiksa `sebut.check.ts`.
 *
 * Yang dikirim ke server adalah ID orang (`sebut: [...]`), bukan nama: nama
 * tampilan bisa kembar dan bisa berganti. Teks pesan tetap berisi `@nama` supaya
 * terbaca wajar di email, pencarian, dan peramban lama.
 */

/** Panjang maksimum kata kunci setelah `@` yang masih dianggap sedang menyebut. */
const MAKS_KUERI = 40;

export type TKueriSebut = { awal: number; kueri: string };

/**
 * `@kata` yang sedang diketik tepat sebelum kursor, atau null.
 *
 * `@` harus di awal teks atau sesudah spasi/baris baru, supaya alamat email
 * (`nama@kantor.com`) tidak membuka pemilih.
 */
export const cariKueriSebut = (teks: string, kursor: number): TKueriSebut | null => {
  const depan = teks.slice(0, kursor);
  const cocok = /(^|\s)@([^\s@]*)$/.exec(depan);
  if (!cocok) return null;
  const kueri = cocok[2] ?? "";
  if (kueri.length > MAKS_KUERI) return null;
  return { awal: depan.length - kueri.length - 1, kueri };
};

/** Ganti `@kueri` dengan `@nama ` dan kembalikan teks baru beserta posisi kursornya. */
export const sisipkanSebut = (
  teks: string,
  awal: number,
  kursor: number,
  nama: string
): { teks: string; kursor: number } => {
  const sisip = `@${nama} `;
  const belakang = teks.slice(kursor).replace(/^\s/, "");
  return { teks: `${teks.slice(0, awal)}${sisip}${belakang}`, kursor: awal + sisip.length };
};

/** Calon yang cocok dengan kueri: awalan nama dulu, lalu yang memuatnya. */
export const saringCalon = <T extends { nama: string }>(calon: T[], kueri: string, batas = 8): T[] => {
  const k = kueri.toLowerCase();
  if (!k) return calon.slice(0, batas);
  const awalan = calon.filter((c) => c.nama.toLowerCase().startsWith(k));
  const memuat = calon.filter((c) => !c.nama.toLowerCase().startsWith(k) && c.nama.toLowerCase().includes(k));
  return [...awalan, ...memuat].slice(0, batas);
};

/** ID yang `@nama`-nya masih ada di teks. Sebutan yang sudah dihapus dari draf tidak ikut terkirim. */
export const sebutanTersisa = (teks: string, dipilih: ReadonlyMap<string, string>): string[] =>
  [...dipilih.entries()].filter(([, nama]) => adaSebutan(teks, nama)).map(([id]) => id);

const lolosRegex = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** `@nama` berdiri sendiri: tidak menempel di huruf sebelum maupun sesudahnya. */
const polaSebutan = (nama: string, flags = "") =>
  new RegExp(`(^|[^\\p{L}\\p{N}_])@${lolosRegex(nama)}(?![\\p{L}\\p{N}_])`, `u${flags}`);

const adaSebutan = (teks: string, nama: string) => !!nama && polaSebutan(nama).test(teks);

export type TPotonganSebut = { jenis: "teks"; isi: string } | { jenis: "sebut"; isi: string; id: string };

/**
 * Pecah teks pesan jadi potongan biasa dan potongan `@nama`.
 *
 * Nama terpanjang dicocokkan dulu, supaya `@Budi Santoso` tidak terpotong jadi
 * `@Budi` + " Santoso" saat ada anggota lain bernama Budi.
 */
export const potongSebutan = (teks: string, orang: { id: string; nama: string }[]): TPotonganSebut[] => {
  // `filter` sudah menghasilkan larik baru, jadi `sort` tidak mengubah masukan.
  // `toSorted` tidak tersedia di target TS repo ini (lolos dev server, gagal check:types).
  // oxlint-disable-next-line unicorn/no-array-sort
  const sah = orang.filter((o) => o.nama).sort((a, b) => b.nama.length - a.nama.length);
  if (sah.length === 0 || !teks.includes("@")) return [{ jenis: "teks", isi: teks }];
  const pola = new RegExp(
    `(^|[^\\p{L}\\p{N}_])@(${sah.map((o) => lolosRegex(o.nama)).join("|")})(?![\\p{L}\\p{N}_])`,
    "gu"
  );
  const hasil: TPotonganSebut[] = [];
  let posisi = 0;
  for (const m of teks.matchAll(pola)) {
    const mulai = (m.index ?? 0) + (m[1] ?? "").length;
    if (mulai > posisi) hasil.push({ jenis: "teks", isi: teks.slice(posisi, mulai) });
    const nama = m[2] ?? "";
    const id = sah.find((o) => o.nama === nama)?.id ?? "";
    hasil.push({ jenis: "sebut", isi: `@${nama}`, id });
    posisi = mulai + nama.length + 1;
  }
  if (posisi < teks.length) hasil.push({ jenis: "teks", isi: teks.slice(posisi) });
  return hasil;
};
