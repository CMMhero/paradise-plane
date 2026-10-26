/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pilih departemen sendiri
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

// Bentuk balasan mengikuti `apps/api/plane/app/views/penempatan_saya.py`.
export type TPilihanDepartemen = { id: string; kode: string; nama: string; divisi: string };
export type TPenempatanSaya = { perlu_pilih: boolean; departemen: TPilihanDepartemen[] };

export class PenempatanService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async saya(workspaceSlug: string): Promise<TPenempatanSaya> {
    return this.get(`/api/workspaces/${workspaceSlug}/penempatan-saya/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async pilih(workspaceSlug: string, departemenId: string): Promise<TPenempatanSaya> {
    return this.post(`/api/workspaces/${workspaceSlug}/penempatan-saya/`, { departemen_id: departemenId })
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }
}

export const penempatanService = new PenempatanService();
