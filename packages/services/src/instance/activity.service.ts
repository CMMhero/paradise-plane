/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pemantauan sesi & aktivitas
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import { APIService } from "../api.service";

/**
 * Tiga keadaan yang terdengar mirip dan tidak sama:
 * - `masih_login`    ada sesi belum kedaluwarsa. Bertahan berhari-hari.
 * - `sedang_memakai` ada sesi hidup DAN ada request dalam beberapa menit terakhir.
 * - riwayat          pernah login, di `login-history`. Riwayat, bukan keadaan.
 */
export type TSesi = {
  session_key: string;
  expire_date: string;
  user_agent: string;
  ip_address: string;
  domain: string;
};

export type TMemberSession = {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  sedang_memakai: boolean;
  masih_login: boolean;
  last_active: string | null;
  last_login_time: string | null;
  last_logout_time: string | null;
  sesi: TSesi[];
};

export type TKickResponse = {
  sesi_diputus: number;
  dinonaktifkan: boolean;
  is_active: boolean;
};

export type TRetensi = {
  retensi_hari: number;
  ambang_peringatan_hari: number;
  tertua: string | null;
  sisa_hari: number | null;
  akan_dibuang: number;
  sudah_lewat: number;
  perlu_peringatan: boolean;
  peristiwa_tersimpan: number;
};

export type TActivitySummary = {
  rentang_hari: number;
  sejak: string;
  ambang_aktif_menit: number;
  ringkas: {
    total_user: number;
    sedang_memakai: number;
    masih_login: number;
    belum_pernah_login: number;
    total_login: number;
    user_yang_login: number;
    rata_login_per_user: number;
  };
  /** Sudah terurut naik menurut tanggal dari server, jangan diurutkan ulang. */
  harian: { tgl: string; orang: number; login: number }[];
  /** 10 terbanyak. Rata-rata menyembunyikan satu orang yang login 40x sehari
   *  karena sesinya terus putus, itu justru yang perlu terlihat. */
  teraktif: { user_id: string; email: string; login: number }[];
  retensi: TRetensi;
};

export type TLoginEvent = {
  id: string;
  user_id: string;
  email: string;
  display_name: string;
  jenis: "LOGIN" | "LOGOUT";
  terjadi_pada: string;
  ip: string;
  user_agent: string;
  medium: string;
  permukaan: string;
};

export type TLoginHistoryFilter = {
  user_id?: string;
  jenis?: "LOGIN" | "LOGOUT" | "";
  hari?: number;
  page?: number;
  per_page?: number;
};

export type TLoginHistoryResponse = {
  count: number;
  page: number;
  per_page: number;
  total_pages: number;
  results: TLoginEvent[];
};

export class InstanceActivityService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async summary(hari = 30): Promise<TActivitySummary> {
    return this.get("/api/instances/activity/", { params: { hari } })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data ?? error;
      });
  }

  async history(filter: TLoginHistoryFilter = {}): Promise<TLoginHistoryResponse> {
    // Buang nilai kosong, mengirim `?jenis=` membuat backend menyaring dengan
    // string kosong dan hasilnya selalu nol.
    const params = Object.fromEntries(
      Object.entries(filter).filter(([, v]) => v !== undefined && v !== null && v !== "")
    );
    return this.get("/api/instances/login-history/", { params })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data ?? error;
      });
  }

  async sessions(userId: string): Promise<TMemberSession> {
    return this.get(`/api/instances/members/${userId}/sessions/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data ?? error;
      });
  }

  /** Putuskan semua sesi. `nonaktifkan` sekalian mengunci akunnya. */
  async kick(userId: string, nonaktifkan = false): Promise<TKickResponse> {
    // APIService.delete(url, data, config), argumen KEDUA itu body, bukan
    // config. Menaruh `params` di sana membuat query string tak pernah terkirim
    // dan `nonaktifkan` diam-diam tidak berefek.
    return this.delete(
      `/api/instances/members/${userId}/sessions/`,
      undefined,
      nonaktifkan ? { params: { nonaktifkan: 1 } } : {}
    )
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data ?? error;
      });
  }
}
