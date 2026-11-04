/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: izin per sumber (KEP-85)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

/** Aturan isi: sesuatu yang punya pemilik. Cermin `IZIN_ISI` di `saklar_instance.py`. */
export type TKunciIzinIsi =
  | "PERM_MODULE_EDIT"
  | "PERM_MODULE_ARCHIVE"
  | "PERM_MODULE_DELETE"
  | "PERM_PAGE_EDIT"
  | "PERM_PAGE_ARCHIVE"
  | "PERM_PAGE_DELETE"
  | "PERM_VIEW_EDIT"
  | "PERM_VIEW_DELETE"
  | "PERM_COMMENT_EDIT"
  | "PERM_COMMENT_DELETE"
  | "PERM_WIKI_EDIT"
  | "PERM_WIKI_DELETE";

/** Aturan struktur: milik project. Cermin `IZIN_STRUKTUR`; jawabannya sudah dari server. */
export type TKunciIzinStruktur =
  | "PERM_PROJECT_EDIT"
  | "PERM_PROJECT_WORKFLOW"
  | "PERM_PROJECT_ARCHIVE"
  | "PERM_PROJECT_DELETE"
  | "PERM_TRASH_RESTORE"
  | "PERM_TRASH_PURGE";

/** Balasan `GET workspaces/<slug>/izin-saya/`, bentuk `ringkasan_izin()` di `plane/utils/izin_sumber.py`. */
export type TIzinSaya = {
  admin: boolean;
  tingkat: number | null;
  aturan: Partial<Record<TKunciIzinIsi | TKunciIzinStruktur, number>>;
  bawahan_ids: string[];
  anggota: boolean;
  mengawasi_project?: boolean;
  struktur: Partial<Record<TKunciIzinStruktur, boolean>>;
};

export class IzinSumberService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async izinSaya(workspaceSlug: string, projectId?: string | null): Promise<TIzinSaya> {
    return this.get(`/api/workspaces/${workspaceSlug}/izin-saya/`, {
      params: projectId ? { project_id: projectId } : {},
    })
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }
}
