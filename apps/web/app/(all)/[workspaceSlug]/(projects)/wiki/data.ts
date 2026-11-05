/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: data Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import useSWR from "swr";
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

export const kunciPohonWiki = (workspaceSlug: string) => `WIKI_TREE_${workspaceSlug}`;

/**
 * Sengaja ikut segar saat tab kembali difokus (bawaan SWR global): izin bisa
 * berubah dari luar halaman ini, misalnya penempatan di God Mode.
 */
export const usePohonWiki = (workspaceSlug?: string) => {
  const { data, isLoading, error, mutate } = useSWR(
    workspaceSlug ? kunciPohonWiki(workspaceSlug) : null,
    workspaceSlug ? () => layananWiki.fetchTree(workspaceSlug) : null
  );
  return {
    folder: data?.folders,
    adalahAdmin: !!data?.is_admin,
    sedangMemuat: isLoading,
    galat: error as { error?: string } | undefined,
    muatUlang: mutate,
  };
};

/** Folder yang tidak diarsipkan, yaitu yang layak ditampilkan. */
export const folderTerlihat = (folder?: TWikiFolder[]): TWikiFolder[] => (folder ?? []).filter((f) => !f.archived_at);

export const adalahUnit = (folder: TWikiFolder | undefined): boolean => !!(folder?.divisi_id || folder?.departemen_id);

export const anakDari = (folder: TWikiFolder[], indukId: string | null | undefined): TWikiFolder[] =>
  folder
    .filter((f) => (f.parent_id ?? null) === (indukId ?? null))
    // oxlint-disable-next-line unicorn/no-array-sort -- filter already returned a copy
    .sort((a, b) => a.urutan - b.urutan || a.nama.localeCompare(b.nama));

export const folderDenganId = (folder: TWikiFolder[], id?: string | null): TWikiFolder | undefined =>
  id ? folder.find((f) => f.id === id) : undefined;

/** Materi di sebuah folder berikut seluruh sub-foldernya. `folder` harus sudah disaring `folderTerlihat`. */
export const jumlahMateriDalam = (folder: TWikiFolder[], folderId: string | undefined): number => {
  if (!folderId) return 0;
  return anakDari(folder, folderId).reduce(
    (total, anak) => total + jumlahMateriDalam(folder, anak.id),
    folderDenganId(folder, folderId)?.jumlah_materi ?? 0
  );
};

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
