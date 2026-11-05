/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: sebutan @ dan rujukan # di obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Logika murni sebutan `@nama` dan rujukan `#kanal` / `#PRJ-12`, tanpa DOM,
 * supaya bisa diperiksa `sebut.check.ts`.
 *
 * Yang dikirim ke server adalah ID (`sebut`, `kanal`, `tugas`), bukan nama: nama
 * tampilan bisa kembar dan bisa berganti. Teks pesan tetap berisi `@nama` /
 * `#nama` supaya terbaca wajar di email, pencarian, dan peramban lama.
 */

/** Panjang maksimum kata kunci setelah pemicu yang masih dianggap sedang mengetik rujukan. */
const MAKS_KUERI = 40;

/** Pemicu yang dikenal pemilih: `@` untuk orang, `#` untuk kanal dan work item. */
export type TPemicu = "@" | "#";

export type TKueriSebut = { awal: number; kueri: string };

/**
 * `<pemicu>kata` yang sedang diketik tepat sebelum kursor, atau null.
 *
 * Pemicu harus di awal teks atau sesudah spasi/baris baru, supaya alamat email
 * (`nama@kantor.com`) dan tautan berfragmen (`halaman#bagian`) tidak membuka
 * pemilih. `awal` menunjuk ke pemicunya.
 */
export const cariKueri = (teks: string, kursor: number, pemicu: TPemicu): TKueriSebut | null => {
  const depan = teks.slice(0, kursor);
  const cocok = new RegExp(`(^|\\s)${pemicu}([^\\s@#]*)$`).exec(depan);
  if (!cocok) return null;
  const kueri = cocok[2] ?? "";
  if (kueri.length > MAKS_KUERI) return null;
  return { awal: depan.length - kueri.length - 1, kueri };
};

/** `@kata` yang sedang diketik tepat sebelum kursor, atau null. */
export const cariKueriSebut = (teks: string, kursor: number): TKueriSebut | null => cariKueri(teks, kursor, "@");

/** Kata yang memunculkan `@all` di pemilih: kueri kosong atau awalan salah satunya. */
const KATA_SEMUA = ["all", "everyone", "semua"];
export const cocokSemua = (kueri: string): boolean => {
  const k = kueri.toLowerCase();
  return KATA_SEMUA.some((kata) => kata.startsWith(k));
};

/** Ganti `<pemicu>kueri` dengan `<pemicu>nama ` dan kembalikan teks baru beserta posisi kursornya. */
export const sisipkanRujukan = (
  teks: string,
  awal: number,
  kursor: number,
  nama: string,
  pemicu: TPemicu = "@"
): { teks: string; kursor: number } => {
  const sisip = `${pemicu}${nama} `;
  const belakang = teks.slice(kursor).replace(/^\s/, "");
  return { teks: `${teks.slice(0, awal)}${sisip}${belakang}`, kursor: awal + sisip.length };
};

/** Ganti `@kueri` dengan `@nama `. */
export const sisipkanSebut = (teks: string, awal: number, kursor: number, nama: string) =>
  sisipkanRujukan(teks, awal, kursor, nama, "@");

/** Calon yang cocok dengan kueri: awalan nama dulu, lalu yang memuatnya. */
export const saringCalon = <T extends { nama: string }>(calon: T[], kueri: string, batas = 8): T[] => {
  const k = kueri.toLowerCase();
  if (!k) return calon.slice(0, batas);
  const awalan = calon.filter((c) => c.nama.toLowerCase().startsWith(k));
  const memuat = calon.filter((c) => !c.nama.toLowerCase().startsWith(k) && c.nama.toLowerCase().includes(k));
  return [...awalan, ...memuat].slice(0, batas);
};

const lolosRegex = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** `<pemicu>nama` berdiri sendiri: tidak menempel di huruf sebelum maupun sesudahnya. */
const polaRujukan = (nama: string, pemicu: TPemicu) =>
  new RegExp(`(^|[^\\p{L}\\p{N}_])${pemicu}${lolosRegex(nama)}(?![\\p{L}\\p{N}_])`, "u");

const adaRujukan = (teks: string, nama: string, pemicu: TPemicu) => !!nama && polaRujukan(nama, pemicu).test(teks);

/** ID yang `<pemicu>nama`-nya masih ada di teks. Rujukan yang sudah dihapus dari draf tidak ikut terkirim. */
export const rujukanTersisa = (teks: string, dipilih: ReadonlyMap<string, string>, pemicu: TPemicu): string[] =>
  [...dipilih.entries()].filter(([, nama]) => adaRujukan(teks, nama, pemicu)).map(([id]) => id);

/** ID yang `@nama`-nya masih ada di teks. */
export const sebutanTersisa = (teks: string, dipilih: ReadonlyMap<string, string>): string[] =>
  rujukanTersisa(teks, dipilih, "@");

/**
 * `@all` yang dipilih dari daftar dan masih ada di teks.
 *
 * Sengaja HANYA lewat pemilih: mengetik `@all` sendiri tetap teks biasa, supaya
 * tidak ada yang memberi tahu seluruh ruang tanpa sengaja.
 */
export const semuaTersisa = (teks: string, dipilih: boolean): boolean => dipilih && adaRujukan(teks, "all", "@");

export type TPotonganRujukan =
  | { jenis: "teks"; isi: string }
  | { jenis: "sebut"; isi: string; id: string }
  | { jenis: "semua"; isi: string }
  | { jenis: "kanal"; isi: string; id: string }
  | { jenis: "tugas"; isi: string; id: string };

export type TPotonganSebut = Extract<TPotonganRujukan, { jenis: "teks" | "sebut" }>;

export type TSumberRujukan = {
  orang?: { id: string; nama: string }[];
  kanal?: { id: string; nama: string }[];
  tugas?: { id: string; nomor: string }[];
  /** Pesan ini memang menyapa semua orang (`muatan.semua`). */
  semua?: boolean;
};

/**
 * Pecah teks pesan jadi potongan biasa, `@nama`, `@all`, `#kanal`, dan `#PRJ-12`.
 *
 * Yang terpanjang dicocokkan dulu, supaya `@Budi Santoso` tidak terpotong jadi
 * `@Budi` + " Santoso" saat ada anggota lain bernama Budi. Hanya nama yang
 * diberikan di `sumber` yang jadi potongan; sisanya tetap teks biasa.
 */
export const potongRujukan = (teks: string, sumber: TSumberRujukan): TPotonganRujukan[] => {
  const kamus = new Map<string, TPotonganRujukan>();
  const tambah = (kunci: string, potongan: TPotonganRujukan) => {
    if (!kamus.has(kunci)) kamus.set(kunci, potongan);
  };
  if (sumber.semua) tambah("@all", { jenis: "semua", isi: "@all" });
  for (const o of sumber.orang ?? []) if (o.nama) tambah(`@${o.nama}`, { jenis: "sebut", isi: `@${o.nama}`, id: o.id });
  for (const k of sumber.kanal ?? []) if (k.nama) tambah(`#${k.nama}`, { jenis: "kanal", isi: `#${k.nama}`, id: k.id });
  for (const w of sumber.tugas ?? [])
    if (w.nomor) tambah(`#${w.nomor}`, { jenis: "tugas", isi: `#${w.nomor}`, id: w.id });
  if (kamus.size === 0 || !/[@#]/.test(teks)) return [{ jenis: "teks", isi: teks }];

  // `toSorted` tidak tersedia di target TS repo ini (lolos dev server, gagal check:types).
  // Larik dari `keys()` baru, jadi `sort` tidak mengubah masukan siapa pun.
  // oxlint-disable-next-line unicorn/no-array-sort
  const kunci = [...kamus.keys()].sort((a, b) => b.length - a.length);
  const pola = new RegExp(`(^|[^\\p{L}\\p{N}_])(${kunci.map(lolosRegex).join("|")})(?![\\p{L}\\p{N}_])`, "gu");
  const hasil: TPotonganRujukan[] = [];
  let posisi = 0;
  for (const m of teks.matchAll(pola)) {
    const mulai = (m.index ?? 0) + (m[1] ?? "").length;
    const potongan = kamus.get(m[2] ?? "");
    if (!potongan) continue;
    if (mulai > posisi) hasil.push({ jenis: "teks", isi: teks.slice(posisi, mulai) });
    hasil.push(potongan);
    posisi = mulai + (m[2] ?? "").length;
  }
  if (posisi < teks.length) hasil.push({ jenis: "teks", isi: teks.slice(posisi) });
  return hasil;
};

/** Seperti `potongRujukan`, tapi hanya `@nama`. */
export const potongSebutan = (teks: string, orang: { id: string; nama: string }[]): TPotonganSebut[] =>
  potongRujukan(teks, { orang }) as TPotonganSebut[];
