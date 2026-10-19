/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: data Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import useSWR from "swr";
import type { TPage } from "@plane/types";
// hooks
import { useProject } from "@/hooks/store/use-project";
// services
import { ProjectPageService } from "@/services/page";
import { WikiAccessService, type TWikiFolderPermission } from "@/services/wiki_access.service";

/**
 * Wiki berdiri sendiri, jadi datanya juga.
 *
 * Store halaman MobX sengaja TIDAK dipakai di sini. Ia membaca
 * `router.projectId`, dan rute `/wiki` tidak punya parameter itu; menumpanginya
 * berarti Wiki harus hidup di dalam rute project, dan itu persis yang membuat
 * tombol "buat halaman" serta chrome work item ikut terbawa. Jadi datanya
 * diambil langsung lewat service, dan project Wiki diresolusi dari
 * identifiernya saat runtime karena UUID-nya berbeda di tiap instance.
 */
const layananHalaman = new ProjectPageService();
const layananAkses = new WikiAccessService();

const IDENTIFIER_WIKI = "WIKI";

export const useProjectWiki = () => {
  const { getProjectByIdentifier, loader } = useProject();
  const project = getProjectByIdentifier(IDENTIFIER_WIKI);
  return { projectId: project?.id, sedangMemuat: loader === "init-loader", project };
};

export const usePohonWiki = (workspaceSlug?: string, projectId?: string) => {
  const { data, isLoading, mutate } = useSWR(
    workspaceSlug && projectId ? `WIKI_TREE_${projectId}` : null,
    workspaceSlug && projectId ? () => layananHalaman.fetchAll(workspaceSlug, projectId) : null,
    { revalidateOnFocus: false }
  );
  return { halaman: data, sedangMemuat: isLoading, muatUlang: mutate };
};

export const useIzinWiki = (workspaceSlug?: string, projectId?: string) => {
  const { data, mutate } = useSWR(
    workspaceSlug && projectId ? `WIKI_PERMISSIONS_${projectId}` : null,
    workspaceSlug && projectId ? () => layananAkses.fetchPermissions(workspaceSlug, projectId) : null,
    { revalidateOnFocus: false }
  );
  return { izin: data, muatUlangIzin: mutate };
};

/** Halaman yang tidak diarsipkan dan tidak dihapus, yaitu yang layak ditampilkan. */
export const halamanTerlihat = (halaman?: TPage[]): TPage[] =>
  (halaman ?? []).filter((h) => !h.archived_at && !h.deleted_at);

export const anakDari = (halaman: TPage[], indukId: string | null | undefined): TPage[] =>
  halaman.filter((h) => (h.parent ?? null) === (indukId ?? null));

export const halamanDenganId = (halaman: TPage[], id?: string | null): TPage | undefined =>
  id ? halaman.find((h) => h.id === id) : undefined;

/** Naik ke folder Divisi. Di situlah izin dan nama divisinya menempel. */
export const divisiDari = (halaman: TPage[], id: string | undefined): TPage | undefined => {
  let kini = halamanDenganId(halaman, id);
  for (let i = 0; i < 20 && kini; i++) {
    if (!kini.parent) return kini;
    kini = halamanDenganId(halaman, kini.parent);
  }
  return kini;
};

export const izinFolderDari = (
  izin: { folders: TWikiFolderPermission[] } | undefined,
  folderId?: string
): TWikiFolderPermission | undefined => (folderId ? izin?.folders.find((f) => f.id === folderId) : undefined);

/** Ukuran berkas dengan basis 1024, supaya cocok dengan angka yang dilihat orang di Windows. */
export const ukuranTerbaca = (bytes: number): string => {
  if (!bytes) return "0 B";
  const satuan = ["B", "KB", "MB", "GB"];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), satuan.length - 1);
  const nilai = bytes / 1024 ** i;
  return `${nilai >= 10 || i === 0 ? Math.round(nilai) : nilai.toFixed(1)} ${satuan[i]}`;
};

/** Label pendek untuk tipe berkas, yang dibaca orang bukan mesin. */
export const labelTipe = (mime: string): string => {
  if (mime === "application/pdf") return "PDF";
  if (mime.startsWith("image/")) return "Gambar";
  if (mime.startsWith("video/")) return "Video";
  if (mime.startsWith("audio/")) return "Audio";
  if (mime.includes("wordprocessingml") || mime === "application/msword") return "Word";
  if (mime.includes("spreadsheetml") || mime === "application/vnd.ms-excel") return "Excel";
  if (mime.includes("presentationml") || mime === "application/vnd.ms-powerpoint") return "PowerPoint";
  if (mime.startsWith("text/")) return "Teks";
  if (mime.includes("zip") || mime.includes("compressed") || mime.includes("rar")) return "Arsip";
  return "Berkas";
};
