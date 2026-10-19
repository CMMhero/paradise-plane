/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: jejak audit God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { API_BASE_URL } from "@plane/constants";
// api service
import { APIService } from "../api.service";

/** Model yang dipantau auditlog, sama dengan daftar di plane/db/audit.py. */
export type TAuditLogModel = "project" | "projectmember" | "workspacemember" | "issue" | "page";

export type TAuditLogAction = "create" | "update" | "delete";

export type TAuditLogActor = {
  id: string;
  email: string;
  display_name: string;
};

export type TAuditLogEntry = {
  id: number;
  timestamp: string;
  /** Sudah dalam bentuk terbaca dari backend ("Create"/"Update"/"Delete"). */
  action: string;
  model: TAuditLogModel | null;
  object_repr: string;
  object_id: string;
  /** Peta {field: [nilai_lama, nilai_baru]}. Bentuknya ditentukan django-auditlog. */
  changes: Record<string, [string, string]> | null;
  remote_addr: string | null;
  /** null untuk perubahan dari skrip shell, di situ memang tidak ada request. */
  actor: TAuditLogActor | null;
};

export type TAuditLogResponse = {
  count: number;
  total_pages: number;
  page: number;
  per_page: number;
  results: TAuditLogEntry[];
};

export type TAuditLogFilter = {
  model?: TAuditLogModel;
  action?: TAuditLogAction;
  actor?: string;
  /** YYYY-MM-DD. Batas atas sudah dinaikkan ke akhir hari di backend. */
  date_from?: string;
  date_to?: string;
  search?: string;
  page?: number;
  per_page?: number;
};

/**
 * Jejak audit tingkat instance. HANYA bisa dibaca instance admin (God Mode),
 * versi workspace-level yang lama sudah dibuang, jadi ini satu-satunya jalan.
 */
export class InstanceAuditLogService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async list(filter: TAuditLogFilter = {}): Promise<TAuditLogResponse> {
    // Buang nilai kosong supaya tidak mengirim `?model=&action=` yang bikin
    // backend memfilter dengan string kosong.
    const params = Object.fromEntries(
      Object.entries(filter).filter(([, v]) => v !== undefined && v !== null && v !== "")
    );

    return this.get("/api/instances/audit-logs/", { params })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data ?? error;
      });
  }
}
