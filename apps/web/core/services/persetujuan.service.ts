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
    /**
     * Status tugas SESUDAH keputusan (KEP-55: setujui -> Done, tolak -> In
     * Progress). Hanya ada di balasan POST keputusan; server lama tidak
     * mengirimnya, jadi `undefined` = ambil ulang tugasnya.
     */
    state_id?: string | null;
  };
  pemohon: {
    id: string;
    email: string | null;
    nama: string | null;
  };
  status: TStatusPersetujuan;
  alasan: string | null;
  diputuskan_oleh: string | null;
  diputuskan_oleh_nama: string | null;
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
/**
 * Aturan kerja God Mode (KEP-83) yang dicerminkan tampilan, cermin
 * `_aturan_tugas()` di `plane/app/views/issue/persetujuan.py`.
 *
 *   hapus_tugas              0 hari ini · 1 pembuat saja · 2 yang boleh mengubah
 *   ganti_tenggat            0 pembuat · 1 + admin project · 2 yang boleh mengubah
 *   persetujuan_di_bawah     jenjang DI BAWAH angka ini menunggu persetujuan (20/30/40)
 *   alasan_tolak_wajib       penolakan wajib beralasan
 *   tugaskan_ke_bawah_saja   atasan hanya boleh menugaskan ke jenjang lebih rendah
 */
export type TAturanTugas = {
  hapus_tugas: number;
  ganti_tenggat: number;
  persetujuan_di_bawah: number;
  alasan_tolak_wajib: boolean;
  tugaskan_ke_bawah_saja: boolean;
};

/** Bawaan server = perilaku sebelum KEP-83; dipakai selama `aturan` belum ada (server lama / belum dimuat). */
export const ATURAN_TUGAS_BAWAAN: TAturanTugas = {
  hapus_tugas: 0,
  ganti_tenggat: 0,
  persetujuan_di_bawah: 20,
  alasan_tolak_wajib: true,
  tugaskan_ke_bawah_saja: true,
};

export type TBisaDitugaskan = {
  /** Server lama tidak mengirim ini. */
  aturan?: Partial<TAturanTugas>;
  mode: "diri-sendiri" | "rekan" | "bawahan" | "semua";
  tingkat_saya: number | null;
  users?: { id: string; nama: string | null; email: string | null }[];
  user_ids?: string[];
  /** false = gerbang hierarki mati: server tidak mengunci edit berdasarkan kepemilikan. */
  gerbang_aktif?: boolean;
  /** Bawahan yang tugasnya boleh saya UBAH (cermin `_bawahan_ids` server). Staf: kosong. */
  bawahan_ids?: string[];
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
