/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kelola member di God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { API_BASE_URL } from "@plane/constants";
import type { TNotificationPreferenceKey, TNotificationPreferences } from "@plane/types";
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

/** Pengaturan pribadi yang boleh diatur Super Admin atas nama member. */
export type TMemberTheme = "system" | "light" | "dark" | "light-contrast" | "dark-contrast" | "custom";

/** Isi `/api/timezones/` (endpoint publik yang sama dengan halaman Preferences pengguna). */
export type TZonaWaktu = { value: string; label: string; utc_offset: string; gmt_offset: string };

/** Item sidebar yang bisa disematkan. Cermin `NAV_KUNCI` di plane/utils/bawaan_member.py. */
export type TNavItemKey =
  | "your_work"
  | "stickies"
  | "drafts"
  | "quick_links"
  | "views"
  | "analytics"
  | "dashboard_divisi"
  | "initiatives"
  | "chat"
  | "wiki"
  | "archives";

/** Gaya daftar project di sidebar. */
export type TProjectNavMode = "ACCORDION" | "TABBED";

/** Navigasi sidebar: item tersemat, gaya daftar project, batas jumlah project (0 = semua). */
export type TMemberNavigation = {
  pinned: Record<TNavItemKey, boolean>;
  project_mode: TProjectNavMode;
  project_limit: number;
};

/** Tata letak daftar work item. "kanban" = Board. */
export type TWorkItemLayout = "kanban" | "list" | "calendar" | "spreadsheet";

export type TMemberPreferences = {
  profile: {
    /** Kode bahasa UI, mis. "en", "id". */
    language: string;
    /** Nama zona IANA, mis. "Asia/Jakarta". Disimpan di User. */
    timezone: string;
    /** Tema siap pakai. "custom" hanya terbaca, tak bisa dipilih dari God Mode. */
    theme: TMemberTheme;
    /** 0 Minggu · 1 Senin · ... · 6 Sabtu. */
    start_of_the_week: number;
  };
  /** Saklar notifikasi: email + inbox per jenis kabar, dan bagian ringkasan harian. */
  notifications: TNotificationPreferences & {
    /** Hidup = saklar di atas mengikuti bawaan jabatan, bukan pilihan tersimpan. */
    ikut_bawaan_jabatan: boolean;
  };
  /** Saklar yang dipaksa mati kebijakan direktur (baris direktur di bawaan). Kosong untuk selain direktur. */
  notifikasi_dikunci?: TNotificationPreferenceKey[];
  /** Dibaca dari workspace utama; disimpan ke semua workspace orangnya. */
  navigasi: TMemberNavigation;
  /** Tata letak terbanyak di project-projectnya; disimpan ke semua project. */
  work_items: {
    layout: TWorkItemLayout;
    /** true = orangnya memakai tata letak berbeda per project. */
    campuran: boolean;
    jumlah_project: number;
  };
};

/** Kirim hanya yang berubah; kunci yang tidak dikirim tidak disentuh. */
export type TMemberPreferencesUpdate = {
  profile?: Partial<TMemberPreferences["profile"]>;
  notifications?: Partial<TMemberPreferences["notifications"]>;
  navigasi?: Partial<Omit<TMemberNavigation, "pinned">> & { pinned?: Partial<TMemberNavigation["pinned"]> };
  work_items?: { layout?: TWorkItemLayout };
};

/** Semua saklar tanpa `ikut_bawaan_jabatan`: isi satu kolom tabel bawaan jabatan. */
export type TSaklarEmail = Omit<TMemberPreferences["notifications"], "ikut_bawaan_jabatan">;

/** Setelan akun baru di God Mode (KEP-44). Cermin `PABRIK` di plane/utils/bawaan_member.py. */
export type TMemberDefaults = {
  /** Ditulis sekali saat akun lahir; akun lama tidak berubah. */
  profile: TMemberPreferences["profile"];
  /** Berlaku seketika untuk semua yang masih ikut bawaan jabatan. */
  /** `pimpinan` = leader (supervisor, manager). `direktur` juga batas atas untuk setiap direktur. */
  email: { staf: TSaklarEmail; pimpinan: TSaklarEmail; direktur: TSaklarEmail };
  /** Dipakai saat akun dibuat dari God Mode. `tingkat: null` = jabatan belum diisi. */
  keanggotaan: { workspace_role: 5 | 15; tingkat: 10 | 20 | 30 | null };
  /** Ditulis saat baris preferensi sidebar orangnya lahir. */
  navigasi: TMemberNavigation;
  /** Bawaan kolom per project; berlaku untuk tiap member+project baru. */
  work_items: { layout: TWorkItemLayout };
};

/** Bagian yang bisa diterapkan ke member LAMA sekaligus. */
export type TMemberDefaultsSection = "navigasi" | "work_items";

/** Setelan project baru. Cermin `PABRIK` di plane/utils/bawaan_project.py. */
export type TProjectDefaults = {
  /** 2 = Public, 0 = Private. */
  network: 0 | 2;
  timezone: string;
  /** Bulan sebelum work item selesai diarsipkan otomatis. 0 = mati. */
  archive_in: number;
  /** Bulan sebelum work item tak tersentuh ditutup otomatis. 0 = mati. */
  close_in: number;
  guest_view_all_features: boolean;
};

export type TProjectDefaultsResponse = TProjectDefaults & { pabrik: TProjectDefaults };

export type TMemberDefaultsResponse = TMemberDefaults & { pabrik: TMemberDefaults };

export type TMemberDefaultsUpdate = {
  profile?: Partial<TMemberDefaults["profile"]>;
  email?: { staf?: Partial<TSaklarEmail>; pimpinan?: Partial<TSaklarEmail>; direktur?: Partial<TSaklarEmail> };
  keanggotaan?: Partial<TMemberDefaults["keanggotaan"]>;
  navigasi?: TMemberPreferencesUpdate["navigasi"];
  work_items?: { layout?: TWorkItemLayout };
};

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

  /**
   * Semua akun sekaligus (halaman 200, diambil paralel sesudah halaman pertama).
   * Dipakai daftar Accounts God Mode yang menyaring dan mengurutkan di klien.
   */
  async listAll(): Promise<TInstanceMember[]> {
    const per_page = 200;
    const pertama = await this.list({ page: 1, per_page, sort: "name" });
    if (pertama.total_pages <= 1) return pertama.results;
    const sisa = await Promise.all(
      Array.from({ length: pertama.total_pages - 1 }, (_, i) => this.list({ page: i + 2, per_page, sort: "name" }))
    );
    return [...pertama.results, ...sisa.flatMap((r) => r.results)];
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

  async preferensi(id: string): Promise<TMemberPreferences> {
    return this.get(`/api/instances/members/${id}/preferences/`)
      .then((r) => r?.data)
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }

  /** Daftar zona waktu yang sama dengan pilihan di Preferences milik pengguna. */
  async daftarZonaWaktu(): Promise<TZonaWaktu[]> {
    return this.get("/api/timezones/")
      .then((r) => r?.data?.timezones ?? [])
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }

  /** Tidak mengakhiri sesi: ini preferensi tampilan, bukan kredensial. */
  async ubahPreferensi(id: string, data: TMemberPreferencesUpdate): Promise<TMemberPreferences> {
    return this.patch(`/api/instances/members/${id}/preferences/`, data)
      .then((r) => r?.data)
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }

  async bawaan(): Promise<TMemberDefaultsResponse> {
    return this.get("/api/instances/members/defaults/")
      .then((r) => r?.data)
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }

  /** Parsial per bagian; server mengecek semuanya sebelum menulis. */
  async ubahBawaan(data: TMemberDefaultsUpdate): Promise<TMemberDefaultsResponse> {
    return this.patch("/api/instances/members/defaults/", data)
      .then((r) => r?.data)
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }

  /** Samakan member LAMA dengan bawaan sekarang (hanya navigasi & tata letak). */
  async terapkanBawaan(sections: TMemberDefaultsSection[]): Promise<{ updated: Record<string, number> }> {
    return this.post("/api/instances/members/defaults/apply/", { sections })
      .then((r) => r?.data)
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }

  async bawaanProject(): Promise<TProjectDefaultsResponse> {
    return this.get("/api/instances/projects/defaults/")
      .then((r) => r?.data)
      .catch((e) => {
        throw e?.response?.data ?? e;
      });
  }

  async ubahBawaanProject(data: Partial<TProjectDefaults>): Promise<TProjectDefaultsResponse> {
    return this.patch("/api/instances/projects/defaults/", data)
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
