/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: ACL folder Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

export type TWikiDivision = {
  id: string;
  identifier: string;
  name: string;
};

/** Bendera izin satu folder teratas, untuk pemakai yang sedang bertanya. */
export type TWikiFolderPermission = {
  id: string;
  /** Admin atau anggota departemen pemilik folder: boleh menaruh Materi baru. */
  can_upload: boolean;
  /** Admin: boleh membereskan materi orang lain di sini. */
  is_lead: boolean;
  /** Folder General (bawaan untuk folder non-divisi): semua anggota Wiki boleh mengunggah. */
  is_general: boolean;
  divisions: TWikiDivision[];
};

export type TWikiPermissions = {
  is_governed: boolean;
  is_super_admin: boolean;
  is_project_admin: boolean;
  user_id: string;
  folders: TWikiFolderPermission[];
  /**
   * Halaman yang boleh dikelola orang ini: ganti nama, ganti ikon, hapus.
   * Dihitung server supaya aturan izin tidak hidup di dua bahasa sekaligus.
   */
  manageable_page_ids: string[];
};

export class WikiAccessService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  /**
   * Izin seluruh folder teratas sekaligus.
   *
   * Sengaja borongan: `can-edit/` menjawab satu halaman per permintaan, dan
   * halaman daftar berisi belasan kartu. Bendera dikembalikan per folder
   * TERATAS karena resolver izin di server memang selalu naik ke sana, jadi
   * klien tidak perlu menyalin satu pun aturan izin ke TypeScript.
   */
  async fetchPermissions(workspaceSlug: string, projectId: string): Promise<TWikiPermissions> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/wiki-permissions/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
