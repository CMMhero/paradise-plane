/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: permintaan tugas lintas divisi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

// Bentuk balasan endpoint mengikuti `serialize_permintaan`
// (apps/api/plane/app/serializers/cross_division.py). Medan yang sengaja TIDAK
// ada di sana -- assignee, tenggat, label, komentar, deskripsi versi divisi
// tujuan -- juga sengaja tidak dideklarasikan di sini supaya tidak ada yang
// tergoda menampilkannya.
export type TDivisiLintasDivisi = {
  id: string;
  identifier: string;
  name: string;
};

export type TStatusPermintaan = "menunggu" | "ditunda" | "ditolak" | "duplikat" | "diterima" | "dibatalkan";

export type TStatusTugas = "belum_diterima" | "terbuka" | "selesai" | "dibatalkan" | "tidak_dikerjakan";

export type TPermintaanLintasDivisi = {
  id: string;
  dibuat_pada: string;
  catatan: string;
  asal: TDivisiLintasDivisi;
  tujuan: TDivisiLintasDivisi;
  judul: string | null;
  nomor_tugas_tujuan: string | null;
  status_permintaan: TStatusPermintaan;
  status_tugas: TStatusTugas;
  /** Diisi departemen tujuan saat menolak. Server lama: tidak ada. */
  alasan_tolak?: string;
  /** Peminta anggota departemen tujuan, jadi `nomor_tugas_tujuan` boleh ditautkan. */
  boleh_dibuka?: boolean;
};

/** Status `IntakeIssue`: 1 diterima, -1 ditolak. */
export type TKeputusanPermintaan = 1 | -1;

export type TRingkasanDivisi = {
  masuk_menunggu: number;
  masuk_terbuka: number;
  keluar_menunggu: number;
  keluar_terbuka: number;
};

/** Dipetakan per `project_id`; hanya project tempat pemanggil menjadi anggota. */
export type TRingkasanLintasDivisi = Record<string, TRingkasanDivisi>;

export type TBuatPermintaanLintasDivisi = {
  judul: string;
  prioritas: string;
  catatan: string;
  /**
   * WAJIB HTML yang sudah disanitasi pemanggil. Halaman pengirim membungkus teks
   * textarea yang sudah di-escape jadi `<p>…</p>`; jangan pernah mengirim
   * masukan mentah ke sini (XSS di origin aplikasi).
   */
  deskripsi_html: string;
  asal_project: string;
  tujuan_project: string;
};

export class CrossDivisionService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private root(workspaceSlug: string): string {
    return `/api/workspaces/${workspaceSlug}/cross-division`;
  }

  async listTujuan(workspaceSlug: string): Promise<TDivisiLintasDivisi[]> {
    return this.get(`${this.root(workspaceSlug)}/tujuan/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async listPermintaan(workspaceSlug: string): Promise<TPermintaanLintasDivisi[]> {
    return this.get(`${this.root(workspaceSlug)}/permintaan/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async listRingkasan(workspaceSlug: string): Promise<TRingkasanLintasDivisi> {
    return this.get(`${this.root(workspaceSlug)}/ringkasan/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  /**
   * Terima/tolak lewat jalur Intake bawaan (`IntakeIssueViewSet.partial_update`),
   * jadi wewenangnya sama dengan tombol di halaman Intake. `issueId` = id work item.
   */
  async putuskanPermintaan(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    status: TKeputusanPermintaan,
    alasan = ""
  ): Promise<void> {
    return this.patch(`/api/workspaces/${workspaceSlug}/projects/${projectId}/intake-issues/${issueId}/`, {
      status,
      alasan,
    })
      .then(() => undefined)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async buatPermintaan(workspaceSlug: string, data: TBuatPermintaanLintasDivisi): Promise<TPermintaanLintasDivisi> {
    return this.post(`${this.root(workspaceSlug)}/permintaan/`, data)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }
}
