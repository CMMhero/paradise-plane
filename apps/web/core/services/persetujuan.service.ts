/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: antrean persetujuan penugasan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

// Bentuk balasan mengikuti `_serial` di
// `apps/api/plane/app/views/issue/persetujuan.py`. Kosakata status dipakai apa
// adanya ("menunggu" | "disetujui" | "ditolak") — label tampilannya ada di
// halaman, bukan di sini.
export type TStatusPersetujuan = "menunggu" | "disetujui" | "ditolak";

export type TPeranPersetujuan = "pemohon" | "penyetuju";

export type TPenyetujuRingkas = {
  id: string;
  tingkat: number | null;
};

export type TPersetujuanPenugasan = {
  id: string;
  peran_saya: TPeranPersetujuan;
  tugas: {
    id: string;
    nomor: string | null;
    judul: string | null;
  };
  pemohon: {
    id: string;
    email: string | null;
    nama: string | null;
  };
  status: TStatusPersetujuan;
  alasan: string | null;
  diputuskan_oleh: string | null;
  diputuskan_pada: string | null;
  boleh_saya_putuskan: boolean;
  penyetuju_di_divisi: TPenyetujuRingkas[];
  created_at: string;
};

export type TDaftarPersetujuan = {
  gerbang_aktif: boolean;
  tingkat_saya: number | null;
  jumlah: number;
  hasil: TPersetujuanPenugasan[];
};

export type TAksiPersetujuan = "setujui" | "tolak" | "ajukan-ulang";

// Balasan `bisa-ditugaskan/`: siapa boleh masuk dropdown assignee saya.
// mode "diri-sendiri" = staf (satu user: diri sendiri, auto-select).
// mode "rekan" = staf dengan rekan setingkat sedepartemen (diri wajib ikut).
// mode "bawahan" = atasan (diri + bawahan). mode "semua" = direktur/Super
// Admin atau gerbang mati (seluruh anggota project).
export type TBisaDitugaskan = {
  mode: "diri-sendiri" | "rekan" | "bawahan" | "semua";
  tingkat_saya: number | null;
  users?: { id: string; nama: string | null; email: string | null }[];
  user_ids?: string[];
};

export class PersetujuanService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private dasar(workspaceSlug: string, projectId: string): string {
    return `/api/workspaces/${workspaceSlug}/projects/${projectId}/persetujuan-penugasan/`;
  }

  async bisaDitugaskan(workspaceSlug: string, projectId: string): Promise<TBisaDitugaskan> {
    return this.get(`${this.dasar(workspaceSlug, projectId)}bisa-ditugaskan/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async daftar(
    workspaceSlug: string,
    projectId: string,
    params?: { peran?: "pemohon" | "penyetuju"; tugas?: string }
  ): Promise<TDaftarPersetujuan> {
    return this.get(this.dasar(workspaceSlug, projectId), { params })
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async putuskan(
    workspaceSlug: string,
    projectId: string,
    permintaanId: string,
    aksi: TAksiPersetujuan,
    alasan?: string
  ): Promise<TPersetujuanPenugasan> {
    return this.post(this.dasar(workspaceSlug, projectId) + `${permintaanId}/`, {
      aksi,
      alasan: alasan ?? "",
    })
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }
}
