/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: menu yang disembunyikan untuk Direktur
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { isDirektur } from "@plane/services";
// hooks
import { useMemberProfile } from "@/components/member-profile/use-member-profile";
import { useUser } from "@/hooks/store/user";

/**
 * Item sidebar yang tidak ditampilkan untuk Direktur (jenjang 40). Pekerjaan Anda
 * sudah dibuka lagi; yang tersisa Arsip. Analitik dan
 * Dasbor Divisi ikut tersembunyi lewat tab di halaman KPI (`kinerja/layout.tsx`).
 */
export const DIRECTOR_HIDDEN_NAV_KEYS: readonly string[] = ["archives"];

/**
 * Apakah penonton adalah Direktur, dibaca dari penempatan di profilnya sendiri
 * (kunci SWR yang sama dengan kartu profil, jadi tidak menambah request kalau
 * profilnya sudah dimuat). `isResolved=false` selama profil belum datang; menu
 * baru disembunyikan setelah terbukti direktur, supaya yang lain tidak melihat
 * sidebar-nya bergeser.
 */
export const useIsDirektur = (workspaceSlug: string | undefined) => {
  const { data: currentUser } = useUser();
  const { profile, error } = useMemberProfile(workspaceSlug, currentUser?.id);
  return {
    isDirektur: isDirektur(profile?.penempatan),
    isResolved: Boolean(profile) || Boolean(error),
  };
};
