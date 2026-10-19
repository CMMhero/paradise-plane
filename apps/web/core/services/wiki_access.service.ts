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

export type TWikiFolder = {
  id: string;
  name: string;
  divisions: TWikiDivision[];
};

export type TWikiAccessState = {
  is_governed: boolean;
  folders: TWikiFolder[];
  available_divisions: TWikiDivision[];
  /**
   * Id project Wiki itu sendiri. Menjadikannya "divisi pemilik" sebuah folder
   * berarti folder General: siapa pun anggota Wiki boleh mengunggah ke sana.
   * Tidak ada mode ketiga di model, dan memang tidak perlu ada.
   */
  general_division_id: string;
};

/** Bendera izin satu folder teratas, untuk pemakai yang sedang bertanya. */
export type TWikiFolderPermission = {
  id: string;
  /** Boleh menaruh Topik atau Materi baru di dalam folder ini. */
  can_upload: boolean;
  /** Kepala divisi pemilik: boleh membereskan materi orang lain di sini. */
  is_lead: boolean;
  /** Folder terbuka, semua anggota Wiki boleh mengunggah. */
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
  /** Hanya terisi untuk admin project. Dipakai panel Kelola. */
  general_division_id: string | null;
  available_divisions: TWikiDivision[];
};

export class WikiAccessService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async fetchState(workspaceSlug: string, projectId: string): Promise<TWikiAccessState> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/wiki-access/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
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

  async setGoverned(workspaceSlug: string, projectId: string, isGoverned: boolean): Promise<{ is_governed: boolean }> {
    return this.post(`/api/workspaces/${workspaceSlug}/projects/${projectId}/wiki-access/`, {
      is_governed: isGoverned,
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /** Mengganti seluruh daftar divisi pemilik folder (bukan menambah satu per satu). */
  async setFolderDivisions(
    workspaceSlug: string,
    projectId: string,
    folderId: string,
    divisionIds: string[]
  ): Promise<TWikiFolder> {
    return this.put(`/api/workspaces/${workspaceSlug}/projects/${projectId}/wiki-access/folders/${folderId}/`, {
      division_ids: divisionIds,
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
