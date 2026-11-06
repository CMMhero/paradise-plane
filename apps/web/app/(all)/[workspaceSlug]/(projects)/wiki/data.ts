/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: data Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// services
import { WikiService, type TWikiFolder } from "@/services/wiki.service";

/**
 * Wiki berdiri sendiri (KEP-94): bukan project, jadi tidak ada store halaman
 * MobX dan tidak ada id project. Satu panggilan `GET wiki/` membawa seluruh
 * pohon folder berikut `can_upload` dan `can_manage` per folder, lalu klien
 * menurunkan anak, jejak, dan angka dari situ. Izin tidak pernah dihitung ulang
 * di sini.
 */
export const layananWiki = new WikiService();

// Pohonnya tinggal di core supaya tab Materials project departemen ikut memakai
// kunci SWR yang sama (KEP-97).
export { kunciPohonWiki, usePohonWiki } from "@/hooks/use-pohon-wiki";

/** Folder yang tidak diarsipkan, yaitu yang layak ditampilkan. */
export const folderTerlihat = (folder?: TWikiFolder[]): TWikiFolder[] => (folder ?? []).filter((f) => !f.archived_at);

/** Tipe data seretan sebuah kartu materi, dibaca area lepas folder untuk memindahkannya. Huruf kecil: peramban menurunkan semua tipe kustom. */
export const TIPE_SERET_MATERI = "application/x-paradise-wiki-materi";

/** Muatan seretan kartu materi. */
export type TSeretMateri = { id: string; folderId: string; judul: string };

export const adalahUnit =(folder: TWikiFolder | undefined): boolean => !!(folder?.divisi_id || folder?.departemen_id);

export const anakDari = (folder: TWikiFolder[], indukId: string | null | undefined): TWikiFolder[] =>
  folder
    .filter((f) => (f.parent_id ?? null) === (indukId ?? null))
    // oxlint-disable-next-line unicorn/no-array-sort -- filter already returned a copy
    .sort((a, b) => a.urutan - b.urutan || a.nama.localeCompare(b.nama));

/**
 * Sub-topik hanya satu tingkat: hanya divisi, departemen, dan folder tingkat
 * atas yang boleh punya sub-topik. Server menolak sisanya; ini hanya menyembunyikan tombolnya.
 */
export const bisaPunyaSubtopik = (folder: TWikiFolder | undefined): boolean =>
  !!folder && (adalahUnit(folder) || !folder.parent_id);

/** Folder ini beserta leluhurnya, dari akar sampai folder itu sendiri. */
export const jalurFolder = (folder: TWikiFolder[], id?: string | null): TWikiFolder[] => {
  const jalur: TWikiFolder[] = [];
  let sekarang = folderDenganId(folder, id);
  // Batas langkah menjaga dari siklus data yang rusak.
  for (let i = 0; sekarang && i < 20; i += 1) {
    jalur.unshift(sekarang);
    sekarang = folderDenganId(folder, sekarang.parent_id);
  }
  return jalur;
};

export const folderDenganId =(folder: TWikiFolder[], id?: string | null): TWikiFolder | undefined =>
  id ? folder.find((f) => f.id === id) : undefined;

/** Angka langsung sebuah folder dijumlahkan dengan seluruh sub-foldernya. `folder` harus sudah disaring `folderTerlihat`. */
const jumlahDalam = (
  folder: TWikiFolder[],
  folderId: string | undefined,
  angka: (f: TWikiFolder) => number
): number => {
  if (!folderId) return 0;
  const sendiri = folderDenganId(folder, folderId);
  return anakDari(folder, folderId).reduce(
    (total, anak) => total + jumlahDalam(folder, anak.id, angka),
    sendiri ? angka(sendiri) : 0
  );
};

/** Materi di sebuah folder berikut seluruh sub-foldernya. */
export const jumlahMateriDalam = (folder: TWikiFolder[], folderId: string | undefined): number =>
  jumlahDalam(folder, folderId, (f) => f.jumlah_materi);

/**
 * Halaman departemen di sebuah folder berikut seluruh sub-foldernya, dengan
 * aturan yang sama dengan angka materi: kartu divisi ikut menghitung halaman
 * departemen-departemennya. Angka per folder sudah disaring server (KEP-97).
 */
export const jumlahHalamanDalam = (folder: TWikiFolder[], folderId: string | undefined): number =>
  jumlahDalam(folder, folderId, (f) => f.jumlah_halaman ?? 0);

/** Ukuran berkas dengan basis 1024, supaya cocok dengan angka yang dilihat orang di Windows. */
export const ukuranTerbaca = (bytes: number): string => {
  if (!bytes) return "0 B";
  const satuan = ["B", "KB", "MB", "GB"];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), satuan.length - 1);
  const nilai = bytes / 1024 ** i;
  return `${nilai >= 10 || i === 0 ? Math.round(nilai) : nilai.toFixed(1)} ${satuan[i]}`;
};

/** Label pendek untuk tipe berkas, yang dibaca orang bukan mesin. */
export const labelTipe = (mime: string, t: (key: string) => string): string => {
  if (mime === "application/pdf") return "PDF";
  if (mime.startsWith("image/")) return t("wiki_ui.file_type.image");
  if (mime.startsWith("video/")) return t("wiki_ui.file_type.video");
  if (mime.startsWith("audio/")) return t("wiki_ui.file_type.audio");
  if (mime.includes("wordprocessingml") || mime === "application/msword") return "Word";
  if (mime.includes("spreadsheetml") || mime === "application/vnd.ms-excel") return "Excel";
  if (mime.includes("presentationml") || mime === "application/vnd.ms-powerpoint") return "PowerPoint";
  if (mime.startsWith("text/")) return t("wiki_ui.file_type.text");
  if (mime.includes("zip") || mime.includes("compressed") || mime.includes("rar"))
    return t("wiki_ui.file_type.archive");
  return t("wiki_ui.file_type.file");
};
