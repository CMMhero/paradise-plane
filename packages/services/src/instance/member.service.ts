/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kelola member di God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { API_BASE_URL } from "@plane/constants";
// api service
import { APIService } from "../api.service";

export type TInstanceMember = {
  id: string;
  email: string;
  display_name: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_super_admin: boolean;
  /** 20 Admin · 15 Member · 5 Guest · null kalau belum jadi anggota workspace. */
  workspace_role: number | null;
  /** Slug workspace tempat ia anggota aktif · null kalau belum jadi anggota. */
  workspace_slug: string | null;
  last_active: string | null;
  last_login_time: string | null;
  last_logout_time: string | null;
  last_login_ip: string | null;
  last_login_medium: string | null;
  created_at: string;
  /** Ada sesi belum kedaluwarsa. Bisa bertahan berhari-hari sesudah orangnya pulang. */
  masih_login: boolean;
  /** Sesi hidup DAN ada request beberapa menit terakhir, benar-benar di depan layar. */
  sedang_memakai: boolean;
};

export type TInstanceMemberResponse = {
  count: number;
  total_pages: number;
  page: number;
  results: TInstanceMember[];
};

export type TMemberUpdate = {
  display_name?: string;
  /** Identitas login (`USERNAME_FIELD`), bukan sekadar kontak. Mengakhiri sesi. */
  email?: string;
  /** Reset oleh admin. Minimal 8 karakter. Mengakhiri sesi. */
  password?: string;
  /** 20 Admin · 15 Member · 5 Guest. */
  workspace_role?: number;
  /** Slug workspace yang perannya diatur. Kosong = workspace pertama. */
  workspace_slug?: string;
  is_active?: boolean;
  is_super_admin?: boolean;
  /**
   * Konfirmasi ketik-ulang, WAJIB saat `is_super_admin: true`:
   * "jadikan superadmin" atau "make superadmin" (server menormalisasi
   * huruf/spasi). Ini BUKAN rahasia — ini bukti niat eksplisit supaya
   * pemberian tidak bisa terjadi karena salah klik. Nilai yang diketik
   * pengguna dikirim apa adanya; tombol kirim aktif hanya kalau cocok.
   */
  grant_confirm?: string;
};

/** Balasan `PATCH`: member sesudah diubah + berapa sesi yang ikut diakhiri. */
export type TInstanceMemberUpdated = TInstanceMember & { sessions_ended: number };

export type TMemberFilter = {
  search?: string;
  status?: "active" | "inactive";
  sort?: "name" | "email" | "last_active" | "last_login" | "created";
  page?: number;
  per_page?: number;
};

/**
 * Kelola member dari God Mode. Hanya Super Admin.
 *
 * Ini satu-satunya pintu masuk akun: pendaftaran mandiri dimatikan dan undangan
 * email belum bisa dipakai selama SMTP patah.
 */
export class InstanceMemberService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async list(filter: TMemberFilter = {}): Promise<TInstanceMemberResponse> {
    const params = Object.fromEntries(
      Object.entries(filter).filter(([, v]) => v !== undefined && v !== null && v !== "")
    );
    return this.get("/api/instances/members/", { params })
      .then((r) => r?.data)
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }

  async create(data: { email: string; display_name: string; password: string }): Promise<TInstanceMember> {
    return this.post("/api/instances/members/", data)
      .then((r) => r?.data)
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }

  /**
   * Semua kolom opsional, kirim hanya yang berubah. Yang tidak dikirim tidak
   * disentuh, jadi form parsial tidak menimpa sisanya dengan nilai kosong.
   *
   * `password` dan `email` mengakhiri seluruh sesi orang itu (lihat
   * `sessions_ended` di balasan): reset password yang membiarkan tab lama tetap
   * sah bukan reset.
   */
  async update(id: string, data: TMemberUpdate): Promise<TInstanceMemberUpdated> {
    return this.patch(`/api/instances/members/${id}/`, data)
      .then((r) => r?.data)
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }

  /**
   * Hapus akun secara AMAN (soft-delete + anonimisasi di server): nonaktif,
   * email/nama digosok, sesi diakhiri, Super Admin dicabut. Rujukan (audit,
   * worklog, work item) tetap utuh. `konfirmasi` HARUS persis display_name
   * akun — server menolak tanpa itu.
   */
  async hapus(id: string, konfirmasi: string): Promise<{ id: string; sessions_ended: number }> {
    return this.delete(`/api/instances/members/${id}/`, { konfirmasi })
      .then((r) => r?.data)
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }
}
