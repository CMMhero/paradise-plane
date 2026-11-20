/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: catatan rilis untuk widget Home
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

export type TJenisEntri = "Added" | "Changed" | "Fixed";

/** Satu rilis. Cermin `ChangelogEndpoint` di `plane/app/views/changelog.py`. */
export type TCatatanRilis = {
  id: string;
  versi: string;
  tanggal: string;
  entri: { type: TJenisEntri; text: string }[];
};

export class ChangelogService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  /** Rilis terbaru dulu, urut versi. */
  async getCatatanRilis(workspaceSlug: string, batas = 10): Promise<TCatatanRilis[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/changelog/`, { params: { batas } })
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }
}
