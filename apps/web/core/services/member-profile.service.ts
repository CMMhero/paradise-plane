/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kartu profil anggota
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

// Bentuk balasan mengikuti `apps/api/plane/app/views/workspace/profil_anggota.py`.
export type TOrgUnit = { id: string; kode: string; nama: string };

export type TMemberPlacement = {
  /** 10 staf · 20 supervisor · 30 manager · 40 direktur (KEP-29). */
  tingkat: number;
  departemen: TOrgUnit | null;
  divisi: TOrgUnit | null;
};

export type TMemberProfile = {
  id: string;
  display_name: string;
  first_name: string;
  last_name: string;
  avatar_url: string | null;
  is_active: boolean;
  user_timezone: string;
  workspace_role: number;
  job_title: string;
  /** null = peminta Guest, kontak tidak dikirim. */
  email: string | null;
  /** null = peminta Guest, kontak tidak dikirim. */
  phone_extension: string | null;
  penempatan: TMemberPlacement[];
};

export class MemberProfileService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async fetchProfile(workspaceSlug: string, userId: string): Promise<TMemberProfile> {
    return this.get(`/api/workspaces/${workspaceSlug}/member-profile/${userId}/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }
}

export const memberProfileService = new MemberProfileService();
