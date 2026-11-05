/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: hierarki jabatan God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { API_BASE_URL } from "@plane/constants";
// api service
import { APIService } from "../api.service";

/** Tangga jenjang, sama dengan TINGKAT_* di `plane/db/models/hierarki.py`. */
export const TINGKAT_MEMBER = 10;
export const TINGKAT_SUPERVISOR = 20;
export const TINGKAT_MANAGER = 30;
export const TINGKAT_DIREKTUR = 40;

export type TTingkat =
  | typeof TINGKAT_MEMBER
  | typeof TINGKAT_SUPERVISOR
  | typeof TINGKAT_MANAGER
  | typeof TINGKAT_DIREKTUR;

export type TAnggotaHierarki = {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  /**
   * Sejak 4 Nov 2026 server tidak lagi mengirim null: orang tanpa baris jabatan
   * dilaporkan Staf (10) dengan `tingkat_bawaan: true`. Tipe tetap menerima null
   * untuk server lama.
   */
  tingkat: number | null;
  /** True = belum pernah ada yang menetapkan jenjangnya; dihitung Staf. */
  tingkat_bawaan?: boolean;
  tingkat_nama: string | null;
  sumber: string | null;
  /** Identifier divisi tempat ia anggota. */
  divisi: string[];
  /** Identifier divisi yang ia awasi (baris eksplisit). */
  divisi_diawasi: string[];
  punya_atasan: boolean;
  /** Penempatan KEP-29 (id record). Yang pertama dari daftar di bawah, untuk tampilan ringkas. */
  departemen_id?: string | null;
  divisi_id?: string | null;
  /** KEP-76: SEMUA departemen orang ini (jenjang apa pun boleh banyak). */
  departemen_ids?: string[];
  /** KEP-76: SEMUA divisi yang ia pimpin (manager ke atas). */
  divisi_ids?: string[];
  /** KEP-93: peran orang ini DI tiap departemennya (10 Staf / 20 Supervisor). */
  peran_departemen?: Record<string, number>;
};

export type TPilihanDepartemen = {
  id: string;
  kode: string;
  nama: string;
  divisi_id: string;
  /** Identifier project departemen ini (KEP-76). Boleh tidak ada di server lama. */
  projects?: string[];
};
export type TPilihanDivisi = { id: string; kode: string; nama: string };

/** Badan POST /api/instances/hierarki/. Kunci tidak dikirim = jangan sentuh; null = kosongkan. */
export type TSetJabatan = {
  member_id: string;
  tingkat?: number | null;
  sumber?: string;
  catatan?: string;
  pengawasan?: string[];
  /** Singkatan: TAMBAH satu departemen (tidak memindahkan); null = cabut semua departemen. */
  departemen_id?: string | null;
  /** Singkatan: TAMBAH satu divisi; null = cabut semua divisi. */
  divisi_id?: string | null;
  /** MENGGANTI seluruh departemen orang ini (tidak dikirim = jangan sentuh). */
  departemen_ids?: string[];
  /** MENGGANTI seluruh divisi yang dipimpin (tidak dikirim = jangan sentuh). */
  divisi_ids?: string[];
  /** KEP-93: peran per departemen, 10 (Staf) atau 20 (Supervisor). */
  peran_departemen?: Record<string, number>;
  /** KEP-93: `tingkat` tidak menyeragamkan peran departemen yang lain. */
  pertahankan_peran?: boolean;
};

export type THasilSetJabatan = {
  member: {
    id: string;
    tingkat: number | null;
    pengawasan: string[];
    departemen_ids: string[];
    divisi_ids: string[];
    /** Divisi yang dicabut otomatis karena jenjang turun di bawah Manager. */
    divisi_dilepas: string[];
    /** KEP-93: departemen yang tertelan divisi yang kini ia pimpin. */
    departemen_dilepas?: string[];
    peran_departemen?: Record<string, number>;
  };
};

export type TProjectOrganisasi = { id: string; identifier: string; name: string };
/** Orang yang ditempatkan: staf/supervisor di departemen, manager di divisi. */
export type TOrangOrganisasi = {
  id: string;
  nama: string;
  email: string;
  tingkat: number;
  tingkat_nama: string | null;
  /** KEP-32: true = supervisor tambahan (mengawasi tanpa ditempatkan di sini). */
  tambahan?: boolean;
};
export type TDepartemenOrganisasi = {
  id: string;
  kode: string;
  nama: string;
  jumlah_orang: number;
  anggota: TOrangOrganisasi[];
  projects: TProjectOrganisasi[];
};
export type TDivisiOrganisasi = {
  id: string;
  kode: string;
  nama: string;
  manager: TOrangOrganisasi[];
  departemen: TDepartemenOrganisasi[];
};
export type TPohonOrganisasi = { divisi: TDivisiOrganisasi[]; tanpa_departemen: TProjectOrganisasi[] };
/** Anggota aktif project lama, untuk impor jadi departemen. */
export type TAnggotaProjectLama = {
  id: string;
  nama: string;
  email: string;
  tingkat: number | null;
  tingkat_nama: string | null;
  /** "KODE Nama" departemen sekarang, null kalau belum ditempatkan. */
  departemen: string | null;
  /** False untuk manager/direktur: jangkauan mereka bukan departemen. */
  bisa_ditempatkan: boolean;
};

export type TRingkasanHierarki = {
  anggota_workspace: number;
  punya_jenjang: number;
  belum_diisi: number;
  pengawasan_eksplisit: number;
  tanpa_atasan: number;
  tanpa_atasan_tanpa_akun_uji: number;
  divisi_berpenyetuju: number;
  divisi_total: number;
};

export type THierarkiResponse = {
  workspace: { id: string; slug: string; name: string };
  gerbang_aktif: boolean;
  flag_gerbang: string;
  tingkat: Record<string, string>;
  ringkasan: TRingkasanHierarki;
  admin_lintas_divisi: { id: string; email: string | null; jumlah_divisi: number }[];
  /** Peta identifier → UUID project. POST `pengawasan` meminta UUID. */
  projects: Record<string, string>;
  /** Nama tampil divisi ({identifier: name}). Aditif, boleh kosong di server lama. */
  project_names?: Record<string, string>;
  departemen_pilihan?: TPilihanDepartemen[];
  divisi_pilihan?: TPilihanDivisi[];
  anggota: TAnggotaHierarki[];
};

/**
 * Jenjang organisasi + "divisi yang dia bawahi", dari God Mode. Hanya Super Admin.
 * Satu-satunya jalan menulis hierarki (keputusan user 2026-10-15).
 */
export class InstanceHierarkiService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async ringkasan(params?: {
    workspace?: string;
    hanya_tanpa_atasan?: boolean;
    divisi?: string;
  }): Promise<THierarkiResponse> {
    const query: Record<string, string> = {};
    if (params?.workspace) query.workspace = params.workspace;
    if (params?.hanya_tanpa_atasan) query.hanya_tanpa_atasan = "1";
    if (params?.divisi) query.divisi = params.divisi;
    return this.get("/api/instances/hierarki/", { params: query })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data ?? error;
      });
  }

  async setel(data: TSetJabatan): Promise<THasilSetJabatan> {
    return this.post("/api/instances/hierarki/", data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data ?? error;
      });
  }
}

/** Struktur divisi -> departemen -> project (KEP-29). Hanya Super Admin. */
export class InstanceOrganisasiService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private kirim(janji: Promise<{ data: TPohonOrganisasi }>): Promise<TPohonOrganisasi> {
    return janji
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data ?? error;
      });
  }

  pohon(): Promise<TPohonOrganisasi> {
    return this.kirim(this.get("/api/instances/organisasi/"));
  }

  buatDivisi(data: { kode: string; nama: string }): Promise<TPohonOrganisasi> {
    return this.kirim(this.post("/api/instances/organisasi/divisi/", data));
  }

  ubahDivisi(id: string, data: { kode?: string; nama?: string }): Promise<TPohonOrganisasi> {
    return this.kirim(this.patch(`/api/instances/organisasi/divisi/${id}/`, data));
  }

  hapusDivisi(id: string): Promise<TPohonOrganisasi> {
    return this.kirim(this.delete(`/api/instances/organisasi/divisi/${id}/`));
  }

  buatDepartemen(data: { divisi_id: string; kode: string; nama: string }): Promise<TPohonOrganisasi> {
    return this.kirim(this.post("/api/instances/organisasi/departemen/", data));
  }

  ubahDepartemen(
    id: string,
    data: { divisi_id?: string; kode?: string; nama?: string; project_ids?: string[] }
  ): Promise<TPohonOrganisasi> {
    return this.kirim(this.patch(`/api/instances/organisasi/departemen/${id}/`, data));
  }

  anggotaProject(projectId: string): Promise<{ project: TProjectOrganisasi; anggota: TAnggotaProjectLama[] }> {
    return this.get("/api/instances/organisasi/departemen/dari-project/", { params: { project_id: projectId } })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data ?? error;
      });
  }

  jadikanDepartemen(data: {
    project_id: string;
    divisi_id: string;
    kode?: string;
    nama?: string;
    member_ids: string[];
  }): Promise<{ pohon: TPohonOrganisasi; ditempatkan: number; dilewati: number }> {
    return this.post("/api/instances/organisasi/departemen/dari-project/", data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data ?? error;
      });
  }

  hapusDepartemen(id: string): Promise<TPohonOrganisasi> {
    return this.kirim(this.delete(`/api/instances/organisasi/departemen/${id}/`));
  }
}
