/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: lampiran Obrolan (aturan murni)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Tanpa impor apa pun supaya bisa diperiksa lewat tsx (berkas-lampiran.check.ts).
 */

/** Bawaan; batas hidup dibaca dari `paradise_limits.chat_attachments_max` instance. */
export const BATAS_LAMPIRAN = 5;

export type TPenolakan = { jenis: "terlalu-besar" | "terlalu-banyak"; nama: string };

/** Pilah berkas: mana yang boleh naik, mana yang ditolak dan kenapa. Murni, diuji. */
export function pilahBerkas(
  berkas: File[],
  sudahAda: number,
  maksUkuran: number,
  maksJumlah: number = BATAS_LAMPIRAN
): { terima: File[]; tolak: TPenolakan[] } {
  const terima: File[] = [];
  const tolak: TPenolakan[] = [];
  for (const f of berkas) {
    if (f.size > maksUkuran) tolak.push({ jenis: "terlalu-besar", nama: f.name });
    else if (sudahAda + terima.length >= maksJumlah) tolak.push({ jenis: "terlalu-banyak", nama: f.name });
    else terima.push(f);
  }
  return { terima, tolak };
}

const NAMA_GAMBAR_PAPAN_KLIP = /^image.(png|jpe?g|gif|webp)$/i;

/**
 * Berkas dari peristiwa tempel. Gambar tempelan tak bernama diberi nama berwaktu.
 *
 * Dua jalan baca: `items` (bisa memberi `null` dari getAsFile) lalu `files`, yang
 * kadang satu-satunya yang terisi. Salin sel Excel atau Word menyertakan GAMBAR
 * "image.png" di samping teksnya; kalau gambar itu diambil, teksnya hilang
 * dan tempel terasa rusak. Jadi gambar generik yang datang bersama teks biasa
 * dibiarkan, dan tempel teks berjalan normal.
 */
export function berkasDariTempel(data: DataTransfer | null): File[] {
  if (!data) return [];
  let mentah: File[] = Array.from(data.items ?? [])
    .filter((item) => item.kind === "file")
    .flatMap((item) => item.getAsFile() ?? []);
  if (mentah.length === 0) mentah = Array.from(data.files ?? []);
  if (mentah.length === 0) return [];

  const teks = data.getData?.("text/plain")?.trim() ?? "";
  if (teks && mentah.every((f) => NAMA_GAMBAR_PAPAN_KLIP.test(f.name))) return [];

  return mentah.map((f, indeks) => {
    // Tangkapan layar dari papan klip bernama "image.png" di semua peramban;
    // lima tempelan berturut-turut jadi lima "image.png" yang tidak bisa dibedakan.
    if (!NAMA_GAMBAR_PAPAN_KLIP.test(f.name)) return f;
    const ekstensi = f.name.split(".").pop();
    const cap = new Date().toISOString().replace(/[:.]/g, "-");
    return new File([f], `tempelan-${cap}-${indeks + 1}.${ekstensi}`, { type: f.type });
  });
}

/** Peristiwa seret membawa berkas (bukan teks atau tautan yang diseret). */
export const seretBerkas = (data: DataTransfer | null): boolean => !!data && Array.from(data.types).includes("Files");
