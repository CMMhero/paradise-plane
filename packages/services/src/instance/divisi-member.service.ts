/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: keanggotaan divisi dari God Mode 
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { API_BASE_URL } from "@plane/constants";
// api service
import { APIService } from "../api.service";

export type TDivisiAnggota = {
  project_id: string;
  identifier: string;
  role: number;
};

/**
 * Tambah/hapus/ubah-peran orang di divisi, dari God Mode. Hanya Super Admin.
 *
 * Sengaja TIDAK memakai endpoint project biasa (`POST .../projects/<id>/
 * members/`): endpoint itu memeriksa keanggotaan PEMANGGIL di tiap divisi,
 * jadi dari God Mode ia 403 di tengah simpan bertahap dengan keadaan setengah
 * jadi. Endpoint ini atomik (satu transaksi): daftar yang dikirim MENGGANTI
 * seluruh keanggotaan.
 *
 * Peran divisi DITURUNKAN dari jabatan, bukan dipilih: manager/supervisor =
 * Admin divisi (20), member = Member (15). Keputusan user 2026-10-16.
 */
export class InstanceDivisiMemberService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async daftar(memberId: string): Promise<{ member_id: string; divisi: TDivisiAnggota[] }> {
    return this.get("/api/instances/divisi-anggota/", { params: { member_id: memberId } })
      .then((r) => r?.data)
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }

  async ganti(memberId: string, divisi: { project_id: string; role: number }[]): Promise<void> {
    return this.post("/api/instances/divisi-anggota/", { member_id: memberId, divisi })
      .then((r) => r?.data)
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }
}
