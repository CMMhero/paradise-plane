/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: lampiran Obrolan (aturan murni)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Tanpa impor apa pun supaya bisa diperiksa lewat tsx (berkas-lampiran.check.ts).
 */

/** Cermin `BATAS_LAMPIRAN` di apps/api/plane/app/views/chat.py. */
export const BATAS_LAMPIRAN = 5;

export type TPenolakan = { jenis: "terlalu-besar" | "terlalu-banyak"; nama: string };

/** Pilah berkas: mana yang boleh naik, mana yang ditolak dan kenapa. Murni, diuji. */
export function pilahBerkas(
  berkas: File[],
  sudahAda: number,
  maksUkuran: number
): { terima: File[]; tolak: TPenolakan[] } {
  const terima: File[] = [];
  const tolak: TPenolakan[] = [];
  for (const f of berkas) {
    if (f.size > maksUkuran) tolak.push({ jenis: "terlalu-besar", nama: f.name });
    else if (sudahAda + terima.length >= BATAS_LAMPIRAN) tolak.push({ jenis: "terlalu-banyak", nama: f.name });
    else terima.push(f);
  }
  return { terima, tolak };
}

/** Berkas dari peristiwa tempel. Gambar tempelan tak bernama diberi nama berwaktu. */
export function berkasDariTempel(data: DataTransfer | null): File[] {
  if (!data) return [];
  const hasil: File[] = [];
  for (const item of Array.from(data.items ?? [])) {
    if (item.kind !== "file") continue;
    const f = item.getAsFile();
    if (!f) continue;
    // Tangkapan layar dari papan klip bernama "image.png" di semua peramban;
    // lima tempelan berturut-turut jadi lima "image.png" yang tidak bisa dibedakan.
    if (/^image\.(png|jpe?g|gif|webp)$/i.test(f.name)) {
      const ekstensi = f.name.split(".").pop();
      const cap = new Date().toISOString().replace(/[:.]/g, "-");
      hasil.push(new File([f], `tempelan-${cap}-${hasil.length + 1}.${ekstensi}`, { type: f.type }));
    } else hasil.push(f);
  }
  return hasil;
}

/** Peristiwa seret membawa berkas (bukan teks atau tautan yang diseret). */
export const seretBerkas = (data: DataTransfer | null): boolean => !!data && Array.from(data.types).includes("Files");
