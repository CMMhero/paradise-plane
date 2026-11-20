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
  /** Kunci kartu, unik di dalam kelompok: id persetujuan, id komentar, atau id tugas. */
  key: string;
  /** Id tugas. */
  id: string;
  sequence_id: number;
  /** Nomor tugas, mis. WH-12. */
  identifier: string;
  name: string;
  project_id: string;
  project_name: string;
  target_date: string | null;
  state_id: string | null;
  state_name: string | null;
  state_group: string | null;
  created_by: string | null;
  /** Untuk aturan hak ubah di web (`useBolehUbahTugas`). */
  assignee_ids: string[];
  /** Hanya kelompok `rejected`. */
  reason?: string;
  decided_at?: string;
  /** `decide` dan `waiting_mine`. */
  requested_at?: string;
  /** Hanya kelompok `decide`. */
  requester?: string | null;
  /** Hanya `decide`: id baris persetujuan untuk setujui/tolak. */
  approval_id?: string;
  /** Hanya `mentioned`. */
  mentioned_at?: string;
  /** Id komentar yang menyebut saya; null = sebutan di deskripsi. */
  comment_id?: string | null;
  /** Teks polos komentar dengan `@Nama`, tanpa HTML. */
  snippet?: string | null;
  mentioned_by?: string | null;
  /** Notifikasi inbox yang belum dibaca untuk sebutan ini, kalau ada. */
  notification_id?: string | null;
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
