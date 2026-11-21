/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: menu yang disembunyikan untuk Direktur
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { DIRECTOR_SIDEBAR_HIDDEN_KEYS } from "@plane/constants";
import { isDirektur } from "@plane/services";
// hooks
import { useMemberProfile } from "@/components/member-profile/use-member-profile";
import { useAturan } from "@/hooks/use-aturan";
import { useUser } from "@/hooks/store/user";

/**
 * Apakah penonton adalah Direktur, dibaca dari penempatan di profilnya sendiri
 * (kunci SWR yang sama dengan kartu profil, jadi tidak menambah request kalau
 * profilnya sudah dimuat). `isResolved=false` selama profil belum datang; menu
 * baru disembunyikan setelah terbukti direktur, supaya yang lain tidak melihat
 * sidebar-nya bergeser.
 *
 * `hiddenNavKeys`: kunci menu sidebar yang disembunyikan dari penonton ini. Kosong
 * kecuali Direktur; untuk Direktur dari aturan God Mode DIRECTOR_SIDEBAR_HIDES
 * (bawaan: Arsip saja). Referensinya stabil, aman dipakai sebagai dependensi
 * `useMemo`. Analitik dan Dasbor Divisi tersembunyi lewat tab di halaman KPI
 * (`kinerja/layout.tsx`), bukan di sini.
 */
const TANPA_MENU_TERSEMBUNYI: readonly string[] = [];

export const useIsDirektur = (workspaceSlug: string | undefined) => {
  const { data: currentUser } = useUser();
  const { profile, error } = useMemberProfile(workspaceSlug, currentUser?.id);
  const { get } = useAturan();
  const direktur = isDirektur(profile?.penempatan);
  return {
    isDirektur: direktur,
    isResolved: Boolean(profile) || Boolean(error),
    hiddenNavKeys: direktur ? DIRECTOR_SIDEBAR_HIDDEN_KEYS[get("DIRECTOR_SIDEBAR_HIDES")] : TANPA_MENU_TERSEMBUNYI,
  };
};
