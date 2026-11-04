/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: aturan sinyal panggilan DM (murni)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Tanpa impor nilai supaya bisa diperiksa lewat tsx (sinyal-panggilan.check.ts).
 */

import type { TStatusPanggilan } from "./panggilan";

/**
 * KENAPA SINYAL DM PINDAH KE SOKET KEHADIRAN
 *
 * Dulu undangan panggilan lewat soket per ruang obrolan, yang hanya hidup
 * selama halaman Obrolan terbuka TEPAT di percakapan itu. Yang ditelepon
 * sedang membuka papan tugas, atau percakapan lain, tidak pernah berdering:
 * penelepon menunggu "Menunggu dijawab" selamanya tanpa satu galat pun. Soket
 * kehadiran hidup di lapisan workspace (satu per tab), jadi dering sampai ke
 * halaman mana pun.
 *
 * Server meneruskan sinyal ke SEMUA tab milik `ke`, dan ke tab LAIN milik
 * pengirim (`dari === saya`). Gema itu yang membuat tab kedua berhenti berdering
 * saat tab pertama sudah mengangkat atau menolak.
 */

export type TJenisSinyal = "panggil" | "batal" | "tolak" | "terima" | "tutup" | "sibuk";

export type TMuatanPanggilan = { jenis: TJenisSinyal; id: string; video?: boolean };

export type TSinyalPanggilan = { dari: string; ke: string; ruang: string; muatan: TMuatanPanggilan };

/** Penelepon menyerah sesudah ini: kirim `batal`, catat sebagai tak terjawab. */
export const BATAS_DERING_PENELEPON_MS = 45_000;
/** Jaring pengaman di sisi yang ditelepon, sedikit lebih panjang dari milik
 * penelepon. Kalau `batal` dari penelepon hilang di jalan (tabnya tertutup paksa,
 * soket putus), dering tetap berhenti sendiri alih-alih berbunyi tanpa ujung. */
export const BATAS_DERING_PENERIMA_MS = 50_000;

export type TPeran = "penelepon" | "penerima";

/** Panggilan DM yang sedang dipegang tab ini. `null` = tidak ada. */
export type TPanggilanAktif = {
  id: string;
  lawan: string;
  ruang: string;
  peran: TPeran;
  /** Lawan sudah mengirim `terima` (khusus penelepon). */
  terjawab: boolean;
};

export type TKeputusan =
  /** Sinyal basi, gema yang tak relevan, atau bentuknya rusak. */
  | "abaikan"
  /** Undangan baru saat diam: berdering. */
  | "dering"
  /** Undangan baru saat sedang dalam panggilan lain: balas `sibuk`. */
  | "balas_sibuk"
  /** Tab lain milik saya sudah mengangkat/menolak: berhenti diam-diam. */
  | "berhenti_senyap"
  /** Dua orang saling menelepon bersamaan di ruang yang sama: keduanya sudah
   * menuju ruang LiveKit yang sama, jadi biarkan bertemu di sana. */
  | "bertemu"
  /** Penelepon: lawan mengangkat. */
  | "terjawab"
  /** Penelepon: lawan menolak. */
  | "ditolak"
  /** Penelepon: lawan sedang di panggilan lain. */
  | "sibuk"
  /** Yang ditelepon: penelepon membatalkan sebelum diangkat. */
  | "terlewat"
  /** Lawan menutup panggilan yang sudah berjalan. */
  | "ditutup";

const JENIS_SAH: ReadonlySet<string> = new Set(["panggil", "batal", "tolak", "terima", "tutup", "sibuk"]);

/** Periksa bentuk pesan dari soket. Soket adalah batas sistem: isinya tidak dipercaya. */
export function bacaSinyalPanggilan(pesan: unknown): TSinyalPanggilan | null {
  if (!pesan || typeof pesan !== "object") return null;
  const { dari, ke, ruang, muatan } = pesan as Record<string, unknown>;
  if (typeof dari !== "string" || !dari || typeof ke !== "string" || !ke) return null;
  if (typeof ruang !== "string" || !ruang) return null;
  if (!muatan || typeof muatan !== "object") return null;
  const { jenis, id, video } = muatan as Record<string, unknown>;
  if (typeof jenis !== "string" || !JENIS_SAH.has(jenis)) return null;
  if (typeof id !== "string" || !id) return null;
  return {
    dari,
    ke,
    ruang,
    muatan: { jenis: jenis as TJenisSinyal, id, ...(typeof video === "boolean" ? { video } : {}) },
  };
}

/**
 * Apa yang harus dilakukan tab ini terhadap satu sinyal masuk.
 *
 * Aturan yang paling mudah terlewat, dan tiap satunya pernah atau akan jadi
 * bug yang senyap:
 * - Sinyal yang `id`-nya bukan milik panggilan sekarang DIABAIKAN. `batal` dari
 *   panggilan menit lalu yang datang terlambat tidak boleh memutus panggilan
 *   baru dengan orang yang sama.
 * - Gema `panggil` dari tab saya sendiri tidak boleh membuat saya berdering.
 * - Gema `terima`/`tolak`/`sibuk` dari tab saya sendiri menghentikan dering di
 *   tab ini TANPA melapor ke log: tab yang mengangkat sedang menyambung, dan
 *   laporan "selesai" dari tab ini akan menutup log-nya sebagai tak terjawab.
 */
export function putuskanSinyal(
  aktif: TPanggilanAktif | null,
  status: TStatusPanggilan,
  sinyal: TSinyalPanggilan,
  saya: string
): TKeputusan {
  const { dari, muatan } = sinyal;

  if (dari === saya) {
    if (!aktif || muatan.id !== aktif.id || status !== "berdering") return "abaikan";
    return muatan.jenis === "terima" || muatan.jenis === "tolak" || muatan.jenis === "sibuk"
      ? "berhenti_senyap"
      : "abaikan";
  }

  // Sinyal yang ditujukan ke orang lain tidak pernah sampai ke sini dari server
  // yang benar, tapi menolaknya di sini murah dan menutup satu kelas kesalahan.
  if (sinyal.ke !== saya) return "abaikan";

  if (muatan.jenis === "panggil") {
    if (!aktif && status === "diam") return "dering";
    if (aktif?.id === muatan.id) return "abaikan";
    if (
      aktif?.peran === "penelepon" &&
      aktif.lawan === dari &&
      aktif.ruang === sinyal.ruang &&
      (status === "memanggil" || status === "menyambungkan")
    )
      return "bertemu";
    return "balas_sibuk";
  }

  if (!aktif || muatan.id !== aktif.id || dari !== aktif.lawan) return "abaikan";

  switch (muatan.jenis) {
    case "batal":
      if (aktif.peran !== "penerima") return "abaikan";
      return status === "berdering" ? "terlewat" : "ditutup";
    case "terima":
      return aktif.peran === "penelepon" ? "terjawab" : "abaikan";
    case "tolak":
      return aktif.peran === "penelepon" ? "ditolak" : "abaikan";
    case "sibuk":
      return aktif.peran === "penelepon" ? "sibuk" : "abaikan";
    case "tutup":
      return "ditutup";
    default:
      return "abaikan";
  }
}

export type TAkibatWaktuHabis = "abaikan" | "tak_terjawab" | "terlewat";

/**
 * Jam dering habis. Penelepon yang belum dijawab menyerah (`tak_terjawab`);
 * yang ditelepon dan masih berdering berhenti (`terlewat`). Jam yang ternyata
 * milik panggilan lain (id beda) tidak boleh menyentuh panggilan sekarang.
 */
export function akibatWaktuHabis(
  aktif: TPanggilanAktif | null,
  status: TStatusPanggilan,
  idJam: string
): TAkibatWaktuHabis {
  if (!aktif || aktif.id !== idJam) return "abaikan";
  if (aktif.peran === "penelepon")
    return !aktif.terjawab && (status === "memanggil" || status === "menyambungkan") ? "tak_terjawab" : "abaikan";
  return status === "berdering" ? "terlewat" : "abaikan";
}

/**
 * Sinyal yang dikirim saat orang ini menutup panggilan, menurut keadaannya.
 * Penelepon yang belum dijawab `batal` (yang ditelepon mencatatnya sebagai
 * terlewat), yang ditelepon dan belum mengangkat `tolak`, sisanya `tutup`.
 */
export function sinyalTutup(aktif: TPanggilanAktif, status: TStatusPanggilan): TJenisSinyal {
  if (aktif.peran === "penerima") return status === "berdering" ? "tolak" : "tutup";
  return !aktif.terjawab && status !== "tersambung" ? "batal" : "tutup";
}
