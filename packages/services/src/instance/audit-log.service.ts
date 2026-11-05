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
export type TAuditLogModel =
  | "project"
  | "projectmember"
  | "workspacemember"
  | "issue"
  | "page"
  | "instanceconfiguration"
  | "divisi"
  | "departemen"
  | "departemenproject"
  | "jabatanorganisasi"
  | "pengawasandivisi";

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
  /** Jenis objek terbaca dari backend, tidak pernah kosong (dipakai bila `model` tak dikenal UI). */
  model_label?: string;
  /** Nama objek terbaca dari backend, tidak pernah kosong. */
  object_label?: string;
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

/** Kunci `actor` khusus untuk entri tanpa aktor (skrip server). */
export const AUDIT_SYSTEM_ACTOR = "system";

export type TAuditLogSort = "-timestamp" | "timestamp" | `${"" | "-"}${"actor" | "action" | "model" | "object" | "ip"}`;

/** Nilai ganda dipisah koma (`model=issue,page`); `*_not` = kebalikannya. */
export type TAuditLogFilter = {
  model?: string;
  model_not?: string;
  action?: string;
  action_not?: string;
  /** Id user, atau `AUDIT_SYSTEM_ACTOR`. */
  actor?: string;
  actor_not?: string;
  /** Nama kolom yang berubah (`changes`), mis. `state,target_date`. */
  field?: string;
  field_not?: string;
  /** Sebagian alamat IP. */
  ip?: string;
  sort?: TAuditLogSort;
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
