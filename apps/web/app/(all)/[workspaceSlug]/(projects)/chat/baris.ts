/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TPesan } from "@/services/chat.service";

/** Jarak maksimum antar pesan yang masih dianggap satu kelompok. Lewat dari ini
 * orang membaca dua pesan itu sebagai dua momen berbeda, bukan satu napas. */
const JEDA_KELOMPOK_MS = 5 * 60 * 1000;

export type TBaris =
  | { jenis: "tanggal"; kunci: string; label: string; relatif?: "hari-ini" | "kemarin" }
  | { jenis: "belum-dibaca"; kunci: string }
  | {
      jenis: "pesan";
      kunci: string;
      pesan: TPesan;
      dariSaya: boolean;
      /** Pesan pertama dalam kelompok: yang memasang avatar dan jarak atas. */
      awalKelompok: boolean;
      /** Pesan terakhir dalam kelompok: satu-satunya yang memasang jam. */
      akhirKelompok: boolean;
    };

const HARI_MS = 24 * 60 * 60 * 1000;

/** Tengah malam lokal. Membandingkan cap waktu mentah membuat pesan pukul 23.50
 * dan 00.10 terhitung "selisih nol hari" padahal beda tanggal. */
const tanpaJam = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();

// Kata "hari ini"/"kemarin" sengaja tidak ditulis di sini: modul ini murni dan
// tidak tahu bahasa. Yang dikembalikan penandanya, komponen yang menerjemahkan.
const relatifDari = (waktu: Date, hariIni: Date): "hari-ini" | "kemarin" | undefined => {
  const selisih = (tanpaJam(hariIni) - tanpaJam(waktu)) / HARI_MS;
  if (selisih === 0) return "hari-ini";
  if (selisih === 1) return "kemarin";
  return undefined;
};

const labelTanggal = (waktu: Date, lokal: string): string =>
  waktu.toLocaleDateString(lokal, { day: "numeric", month: "long", year: "numeric" });

/** Ubah daftar pesan mentah jadi daftar baris siap render.
 *
 * Dipisah dari komponen supaya bisa diuji tanpa merender apa pun, dan supaya
 * JSX-nya tinggal memetakan, bukan menghitung sambil menggambar.
 */
export const susunBaris = (
  pesan: TPesan[],
  sayaId: string | undefined,
  sekarang = new Date(),
  lokal = "id-ID"
): TBaris[] => {
  const baris: TBaris[] = [];
  let pembatasSudahDipasang = false;

  pesan.forEach((p, i) => {
    const waktu = new Date(p.created_at);
    const sebelumnya = pesan[i - 1];
    const waktuSebelumnya = sebelumnya ? new Date(sebelumnya.created_at) : undefined;
    const gantiHari = !waktuSebelumnya || waktuSebelumnya.toDateString() !== waktu.toDateString();

    if (gantiHari) {
      baris.push({
        jenis: "tanggal",
        kunci: `tgl-${p.id}`,
        label: labelTanggal(waktu, lokal),
        relatif: relatifDari(waktu, sekarang),
      });
    }

    // Garis "belum dibaca" hanya sekali, di pesan baru yang pertama. Beberapa
    // garis akan membuat orang mengira ada beberapa kelompok pesan baru.
    if (p.baru && !pembatasSudahDipasang) {
      baris.push({ jenis: "belum-dibaca", kunci: `batas-${p.id}` });
      pembatasSudahDipasang = true;
    }

    const dariSaya = p.pengirim === sayaId;
    const dekatSebelumnya = !!waktuSebelumnya && waktu.getTime() - waktuSebelumnya.getTime() <= JEDA_KELOMPOK_MS;
    // Pemisah tanggal dan garis belum-dibaca memutus kelompok. Tanpa ini,
    // gelembung pertama sesudah pemisah menempel ke pemisahnya dan terbaca
    // seolah bagian dari kelompok kemarin.
    const awalKelompok = gantiHari || !sebelumnya || sebelumnya.pengirim !== p.pengirim || !dekatSebelumnya;

    const berikutnya = pesan[i + 1];
    const waktuBerikutnya = berikutnya ? new Date(berikutnya.created_at) : undefined;
    const akhirKelompok =
      !berikutnya ||
      berikutnya.pengirim !== p.pengirim ||
      (!!waktuBerikutnya && waktuBerikutnya.toDateString() !== waktu.toDateString()) ||
      (!!waktuBerikutnya && waktuBerikutnya.getTime() - waktu.getTime() > JEDA_KELOMPOK_MS);

    baris.push({ jenis: "pesan", kunci: p.id, pesan: p, dariSaya, awalKelompok, akhirKelompok });
  });

  return baris;
};
