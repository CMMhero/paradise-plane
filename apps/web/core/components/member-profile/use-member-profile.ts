/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kartu profil anggota
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import useSWR from "swr";
// services
import { memberProfileService, type TMemberProfile } from "@/services/member-profile.service";

/** Kunci SWR dipakai bersama kartu dan halaman profil, jadi satu orang = satu request. */
export const memberProfileKey = (workspaceSlug: string, userId: string) => `MEMBER_PROFILE_${workspaceSlug}_${userId}`;

/**
 * Profil satu anggota. `enabled=false` menunda request sampai kartunya benar-benar
 * dibuka: daftar 80 anggota tidak boleh memicu 80 request saat dirender.
 */
export function useMemberProfile(workspaceSlug: string | undefined, userId: string | undefined, enabled = true) {
  const { data, error, isLoading } = useSWR<TMemberProfile>(
    enabled && workspaceSlug && userId ? memberProfileKey(workspaceSlug, userId) : null,
    () => memberProfileService.fetchProfile(workspaceSlug as string, userId as string),
    { revalidateOnFocus: false, dedupingInterval: 60_000, shouldRetryOnError: false }
  );
  return { profile: data, error, isLoading };
}
