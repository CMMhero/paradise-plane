/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Trashbin & TPA
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { API_BASE_URL } from "@plane/constants";
// api service
import { APIService } from "../api.service";

export type TTrashType = "issue" | "page" | "cycle" | "module";

export type TTrashItem = {
  id: string;
  type: TTrashType;
  type_label: string;
  name: string;
  project_id: string | null;
  deleted_at: string;
  /** Sisa hari sebelum dibuang permanen oleh task harian. */
  days_left: number;
  /** null kalau dibuang lewat skrip, atau kalau modelnya tidak dipantau auditlog. */
  deleted_by: { email: string; display_name: string } | null;
};

export type TTrashResponse = {
  retention_days: number;
  results: TTrashItem[];
};

/**
 * Trashbin per project, dipakai admin project.
 *
 * Cakupannya dikunci server-side ke project di URL, jadi id dari project lain
 * ditolak walau ditebak.
 */
export class ProjectTrashService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async list(workspaceSlug: string, projectId: string, type?: TTrashType): Promise<TTrashResponse> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/trash/`, {
      params: type ? { type } : {},
    })
      .then((r) => r?.data)
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }

  async restore(workspaceSlug: string, projectId: string, type: TTrashType, id: string) {
    return this.post(`/api/workspaces/${workspaceSlug}/projects/${projectId}/trash/${type}/${id}/`)
      .then((r) => r?.data)
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }

  async purge(workspaceSlug: string, projectId: string, type: TTrashType, id: string) {
    return this.delete(`/api/workspaces/${workspaceSlug}/projects/${projectId}/trash/${type}/${id}/`)
      .then((r) => r?.data)
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }
}

/**
 * TPA, tong sampah lintas project di God Mode. Hanya Super Admin.
 *
 * Membaca data yang sama dengan `ProjectTrashService`; yang berbeda cakupannya.
 */
export class InstanceTrashService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async list(type?: TTrashType): Promise<TTrashResponse> {
    return this.get("/api/instances/trash/", { params: type ? { type } : {} })
      .then((r) => r?.data)
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }

  async restore(type: TTrashType, id: string) {
    return this.post(`/api/instances/trash/${type}/${id}/`)
      .then((r) => r?.data)
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }

  async purge(type: TTrashType, id: string) {
    return this.delete(`/api/instances/trash/${type}/${id}/`)
      .then((r) => r?.data)
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }
}
