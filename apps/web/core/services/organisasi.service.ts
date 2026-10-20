/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: struktur divisi -> departemen untuk sidebar (KEP-29)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

export type TDepartemenSidebar = {
  id: string;
  kode: string;
  nama: string;
  /** Hanya project tempat pemanggil anggota aktif. */
  project_ids: string[];
};

export type TDivisiSidebar = {
  id: string;
  kode: string;
  nama: string;
  departemen: TDepartemenSidebar[];
};

export type TStrukturOrganisasi = {
  /** False = workspace belum memakai struktur; sidebar tetap daftar datar. */
  aktif: boolean;
  divisi: TDivisiSidebar[];
};

export class OrganisasiService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async getStruktur(workspaceSlug: string): Promise<TStrukturOrganisasi> {
    return this.get(`/api/workspaces/${workspaceSlug}/struktur-organisasi/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }
}
