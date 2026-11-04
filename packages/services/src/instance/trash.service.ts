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

export type TTrashType =
  | "issue"
  | "page"
  | "wiki_material"
  | "cycle"
  | "module"
  | "view"
  | "label"
  | "template"
  // Hanya di Trash God Mode, tidak pernah dikembalikan Trashbin project.
  | "project"
  | "initiative"
  | "account";

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
  deleted_by: { id: string; email: string; display_name: string } | null;
};

export type TTrashResponse = {
  retention_days: number;
  results: TTrashItem[];
};

/**
 * Jenis yang benar-benar ada di `items`, urut sesuai kemunculan, dengan jumlahnya.
 * Dipakai filter jenis di kedua halaman Trash: opsi yang ditawarkan selalu
 * isi tong sampahnya, bukan daftar tetap yang bisa basi (mis. cycle yang dicabut).
 */
export const countTrashTypes = (items: TTrashItem[]): { type: TTrashType; label: string; count: number }[] => {
  const peta = new Map<TTrashType, { type: TTrashType; label: string; count: number }>();
  for (const item of items) {
    const ada = peta.get(item.type);
    peta.set(item.type, { type: item.type, label: item.type_label, count: (ada?.count ?? 0) + 1 });
  }
  return [...peta.values()];
};

/** Saring tong sampah per jenis dan teks (nama atau nama/email penghapus), tanpa membedakan huruf besar. */
export const filterTrashItems = (items: TTrashItem[], type: TTrashType | "", search: string): TTrashItem[] => {
  const kata = search.trim().toLowerCase();
  return items.filter((item) => {
    if (type && item.type !== type) return false;
    if (!kata) return true;
    const penghapus = item.deleted_by ? `${item.deleted_by.display_name} ${item.deleted_by.email}` : "";
    return `${item.name} ${penghapus}`.toLowerCase().includes(kata);
  });
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
