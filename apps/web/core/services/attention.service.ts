/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: widget "Needs attention" di Home
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

/** Cermin `URUTAN` di `plane/utils/perhatian.py`. */
export type TAttentionGroupKey =
  | "decide"
  | "overdue_mine"
  | "rejected"
  | "team_overdue"
  | "due_soon"
  | "waiting_mine"
  | "mentioned";

export type TAttentionItem = {
  id: string;
  sequence_id: number;
  /** Nomor tugas, mis. WH-12. */
  identifier: string;
  name: string;
  project_id: string;
  project_name: string;
  target_date: string | null;
  /** Hanya kelompok `rejected`. */
  reason?: string;
  /** Hanya kelompok `decide`. */
  requester?: string | null;
};

export type TAttentionGroup = {
  key: TAttentionGroupKey;
  /** Jumlah seluruhnya; `items` dipotong server. */
  count: number;
  items: TAttentionItem[];
  /** Hanya `decide`: project dengan antrean terpanjang, tujuan tautan "lihat semua". */
  top_project_id?: string | null;
};

export type TAttention = {
  generated_at: string;
  is_supervisor: boolean;
  /** Jendela `due_soon` dalam hari (God Mode DIGEST_LOOKAHEAD_DAYS). Server lama: tidak ada. */
  lookahead_days?: number;
  total: number;
  groups: TAttentionGroup[];
};

export class AttentionService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async getAttention(workspaceSlug: string): Promise<TAttention> {
    return this.get(`/api/workspaces/${workspaceSlug}/paradise/attention/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }
}
