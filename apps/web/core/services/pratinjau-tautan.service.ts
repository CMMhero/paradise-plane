/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pratinjau tautan Open Graph (KEP-88)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

/** Cermin respons `plane/utils/pratinjau_tautan.py`. */
export type TPratinjauTautan = {
  url: string;
  title: string | null;
  description: string | null;
  site_name: string | null;
  image: string | null;
  favicon: string | null;
  /** Situs tidak terjangkau / tanpa metadata: kartu tidak ditampilkan. */
  kosong?: boolean;
};

export class PratinjauTautanService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async ambil(workspaceSlug: string, url: string): Promise<TPratinjauTautan> {
    return this.get(`/api/workspaces/${workspaceSlug}/link-preview/`, { params: { url } })
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }
}
