/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pesan langsung antar-karyawan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

export type TTipeRuang = "dm" | "kanal" | "privat";

export type TRuang = {
  id: string;
  tipe: TTipeRuang;
  /** Kosong untuk DM: namanya adalah lawan bicaranya, dan itu berbeda
   * tergantung siapa yang melihat. */
  nama: string | null;
  topik: string;
  /** Hanya terisi untuk DM. Dipertahankan supaya bagian UI yang sudah ada
   * tidak perlu tahu apa pun tentang ruang untuk membuka percakapan. */
  lawan_bicara: string | null;
  pesan_terakhir_pada: string | null;
  belum_dibaca: number;
  /** Apakah saya berlangganan. Selalu true di daftar percakapan; berguna di
   * daftar jelajah kanal, tempat kanal yang belum diikuti ikut ditampilkan. */
  ikut: boolean;
};

export type TPercakapan = TRuang & {
  isi: string;
  dari_saya: boolean;
  created_at: string;
};

export type TLampiran = {
  id: string;
  nama: string;
  tipe: string;
  ukuran: number;
  /** URL berpenjaga; hanya pengirim, penerima, dan pemilik workspace. */
  url: string;
};

export type TReaksi = { emoji: string; orang: string[] };

export type TKutipan = { id: string; pengirim: string; isi: string };

export type TPesan = {
  id: string;
  pengirim: string;
  isi: string;
  created_at: string;
  lampiran: TLampiran[];
  disunting: boolean;
  /** Hanya berarti untuk pesan keluar. */
  sudah_dibaca: boolean;
  balasan_ke: TKutipan | null;
  reaksi: TReaksi[];
  /** Belum dibaca saat percakapan ini dimuat. Dihitung server SEBELUM menandai
   * terbaca, jadi hanya benar pada muatan pertama sesudah pesan itu masuk. */
  baru: boolean;
};

/** Kunci SWR untuk jumlah belum dibaca.
 *
 * Dipakai di DUA tempat: lencana di sidebar yang menariknya berkala, dan halaman
 * Obrolan yang memanggil `mutate` pada kunci ini begitu percakapan dibaca. Tanpa
 * kunci bersama, lencana baru turun pada tarikan berikutnya dan orang melihat
 * angka yang sudah tidak benar selama setengah menit. */
export const KUNCI_BELUM_DIBACA = "CHAT_BELUM_DIBACA";

export type TStatusObrolan = {
  jumlah: number;
};

/** Satu pesan hasil pencarian, berikut lawan bicaranya supaya UI bisa langsung
 * membuka percakapan yang benar. */
export type THasilCari = {
  id: string;
  isi: string;
  created_at: string;
  dari_saya: boolean;
  /** Ruang tempat pesan ini berada. Selalu ada, termasuk untuk kanal. */
  ruang: string;
  /** Kosong untuk pesan kanal, karena tidak ada lawan tunggal. */
  lawan_bicara: string | null;
};

export class ChatService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async getPercakapan(workspaceSlug: string): Promise<TPercakapan[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/chat/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async getStatus(workspaceSlug: string): Promise<TStatusObrolan> {
    return this.get(`/api/workspaces/${workspaceSlug}/chat/belum-dibaca/`)
      .then((res) => ({ jumlah: res?.data?.jumlah ?? 0 }))
      .catch((e) => {
        // Dilempar, bukan ditelan jadi 0. SWR menyimpannya di `error` dan
        // lencana cukup tidak tampil; menelannya berarti "tidak ada pesan baru"
        // dan "endpointnya rusak" terlihat persis sama.
        throw e?.response?.data;
      });
  }

  /** Pesan lebih lama dari `sebelum`. Kursor waktu, bukan nomor halaman:
   * pesan baru terus berdatangan di ujung lain dan nomor halaman akan bergeser
   * di bawah jari orang yang sedang menggulung. */
  async cariPesan(workspaceSlug: string, q: string): Promise<THasilCari[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/chat/cari/`, { params: { q } })
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async getPesanLama(workspaceSlug: string, userId: string, sebelum: string): Promise<TPesan[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/chat/${userId}/`, { params: { sebelum } })
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async suntingPesan(workspaceSlug: string, pesanId: string, isi: string): Promise<TPesan> {
    return this.patch(`/api/workspaces/${workspaceSlug}/chat/pesan/${pesanId}/`, { isi })
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async hapusPesan(workspaceSlug: string, pesanId: string): Promise<void> {
    return this.delete(`/api/workspaces/${workspaceSlug}/chat/pesan/${pesanId}/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async toggleReaksi(workspaceSlug: string, pesanId: string, emoji: string): Promise<{ aktif: boolean }> {
    return this.post(`/api/workspaces/${workspaceSlug}/chat/pesan/${pesanId}/reaksi/`, { emoji })
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async getPesan(workspaceSlug: string, userId: string): Promise<TPesan[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/chat/${userId}/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async kirimPesan(
    workspaceSlug: string,
    userId: string,
    isi: string,
    lampiran: string[] = [],
    balasanKe?: string
  ): Promise<TPesan> {
    return this.post(`/api/workspaces/${workspaceSlug}/chat/${userId}/`, {
      isi,
      lampiran,
      balasan_ke: balasanKe ?? null,
    })
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  // ------------------------------------------------------------------
  // Kanal
  //
  // Jalur `ruang/<id>/` melayani DM MAUPUN kanal, jadi begitu UI tahu id
  // ruangnya ia tidak perlu lagi peduli jenisnya. Metode berbasis userId di
  // atas tetap ada untuk percakapan yang ruangnya belum pernah dibuat.
  // ------------------------------------------------------------------

  /** Server ICE untuk panggilan, berikut kredensial TURN berumur pendek.
   *
   * Diambil saat panggilan dimulai, BUKAN ditanam saat build: kredensialnya
   * kedaluwarsa dan alamat TURN-nya bisa berubah tanpa perlu build ulang.
   */
  async getIceServers(workspaceSlug: string): Promise<RTCIceServer[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/chat/ice/`)
      .then((res) => res?.data?.iceServers ?? [])
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  /** Izin masuk ruang panggilan LiveKit.
   *
   * POST, bukan GET: ia menerbitkan kredensial berumur pendek, dan kredensial
   * tidak boleh tersimpan di riwayat peramban maupun cache proxy.
   */
  async getTokenPanggilan(workspaceSlug: string, ruangId: string): Promise<{ url: string; token: string }> {
    return this.post(`/api/workspaces/${workspaceSlug}/chat/ruang/${ruangId}/panggilan/`, {})
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async getDaftarRuang(workspaceSlug: string): Promise<TRuang[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/chat/ruang/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async buatRuang(workspaceSlug: string, nama: string, tipe: TTipeRuang, topik = ""): Promise<TRuang> {
    return this.post(`/api/workspaces/${workspaceSlug}/chat/ruang/`, { nama, tipe, topik })
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async gabungRuang(workspaceSlug: string, ruangId: string): Promise<{ ikut: boolean }> {
    return this.post(`/api/workspaces/${workspaceSlug}/chat/ruang/${ruangId}/gabung/`, {})
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async keluarRuang(workspaceSlug: string, ruangId: string): Promise<void> {
    return this.delete(`/api/workspaces/${workspaceSlug}/chat/ruang/${ruangId}/gabung/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async getAnggotaRuang(workspaceSlug: string, ruangId: string): Promise<string[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/chat/ruang/${ruangId}/anggota/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async tambahAnggotaRuang(workspaceSlug: string, ruangId: string, userId: string): Promise<void> {
    return this.post(`/api/workspaces/${workspaceSlug}/chat/ruang/${ruangId}/anggota/`, { user: userId })
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async getPesanRuang(workspaceSlug: string, ruangId: string): Promise<TPesan[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/chat/ruang/${ruangId}/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async getPesanLamaRuang(workspaceSlug: string, ruangId: string, sebelum: string): Promise<TPesan[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/chat/ruang/${ruangId}/`, { params: { sebelum } })
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async kirimPesanRuang(
    workspaceSlug: string,
    ruangId: string,
    isi: string,
    lampiran: string[] = [],
    balasanKe?: string
  ): Promise<TPesan> {
    return this.post(`/api/workspaces/${workspaceSlug}/chat/ruang/${ruangId}/`, {
      isi,
      lampiran,
      balasan_ke: balasanKe ?? null,
    })
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }
}
