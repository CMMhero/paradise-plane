/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pohon folder Wiki (KEP-94, KEP-97)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import useSWR from "swr";
// services
import { WikiService, type TWikiFolder } from "@/services/wiki.service";

const layanan = new WikiService();

export const kunciPohonWiki = (workspaceSlug: string) => `WIKI_TREE_${workspaceSlug}`;

/**
 * Satu panggilan `GET wiki/` membawa seluruh pohon folder berikut `can_upload`
 * dan `can_manage` per folder. Dipakai halaman Wiki dan tab Materials project
 * departemen dengan kunci SWR yang sama, jadi keduanya tidak mengambil dua kali.
 *
 * Sengaja ikut segar saat tab kembali difokus (bawaan SWR global): izin bisa
 * berubah dari luar halaman ini, misalnya penempatan di God Mode.
 */
export const usePohonWiki = (workspaceSlug?: string) => {
  const { data, isLoading, error, mutate } = useSWR(
    workspaceSlug ? kunciPohonWiki(workspaceSlug) : null,
    workspaceSlug ? () => layanan.fetchTree(workspaceSlug) : null
  );
  return {
    folder: data?.folders,
    adalahAdmin: !!data?.is_admin,
    sedangMemuat: isLoading,
    galat: error as { error?: string } | undefined,
    muatUlang: mutate,
  };
};

/**
 * Folder Wiki departemen milik project ini, atau undefined (project tanpa
 * departemen, modul Wiki mati, atau pohon belum datang).
 *
 * Untuk menu (tab header dan sidebar project): tidak menyegarkan sendiri saat
 * fokus atau saat menu dipasang ulang. Halaman Wiki dan tab Materials yang
 * memakai `usePohonWiki` tetap menyegarkannya.
 */
export const useFolderWikiProject = (
  workspaceSlug: string | undefined,
  projectId: string | undefined,
  aktif: boolean
): TWikiFolder | undefined => {
  const { data } = useSWR(
    aktif && workspaceSlug ? kunciPohonWiki(workspaceSlug) : null,
    workspaceSlug ? () => layanan.fetchTree(workspaceSlug) : null,
    { revalidateOnFocus: false, revalidateIfStale: false, revalidateOnMount: undefined }
  );
  if (!projectId) return undefined;
  return data?.folders.find((f) => f.project_id === projectId && !!f.departemen_id);
};
