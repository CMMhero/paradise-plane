/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: tata letak & status layar panggilan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TStatusPanggilan } from "./panggilan";

export type TTataPanggilan = {
  /** Layar panggilan ditampilkan sama sekali. */
  tampil: boolean;
  /** Ada peserta lain yang medianya sudah tiba. */
  adaPeserta: boolean;
  pratinjauDiriTerlihat: boolean;
};

/**
 * Apa yang tampil di layar panggilan, sebagai fungsi murni.
 *
 * Dipisahkan dari komponennya supaya bisa diuji tanpa DOM. Dua aturan di sini
 * pernah salah dan menghasilkan panggilan yang terasa rusak tanpa error apa pun:
 * elemen media yang dirender bersyarat sehingga audionya tidak punya tempat
 * keluar, dan gambar lawan yang digantungkan pada NIAT memakai video alih-alih
 * pada media yang benar-benar tiba.
 */
export function tataPanggilan(
  status: TStatusPanggilan,
  pakaiVideo: boolean,
  adaStreamLokal: boolean,
  jumlahPeserta: number
): TTataPanggilan {
  if (status === "diam") {
    return { tampil: false, adaPeserta: false, pratinjauDiriTerlihat: false };
  }

  // Peserta hanya dianggap ada kalau medianya sudah tiba, bukan kalau kita
  // sedang berniat menelepon. Menggantungkannya pada niat membuat layar
  // menampilkan kotak kosong yang terlihat seperti kerusakan.
  const adaPeserta = status === "tersambung" && jumlahPeserta > 0;

  return {
    tampil: true,
    adaPeserta,
    // Sejak memanggil, bukan setelah tersambung: kalau kameranya bermasalah,
    // orang tahu sejak detik pertama.
    pratinjauDiriTerlihat: pakaiVideo && adaStreamLokal,
  };
}

/**
 * Status panggilan sesudah sebuah peristiwa ruang, sebagai fungsi murni.
 *
 * PERNAH SALAH, DAN INI YANG PALING MAHAL. `"tersambung"` dulu diturunkan dari
 * `RoomEvent.Connected`, padahal peristiwa itu berarti "SAYA sampai ke server",
 * bukan "lawan bicara sudah ada di ruangan". Untuk yang MENGANGKAT dua hal itu
 * terjadi bersamaan, jadi layarnya benar. Untuk yang MENELEPON tidak: ia masuk
 * ruangan lebih dulu, sendirian, dan `Connected` dipancarkan DI DALAM
 * `room.connect()` sebelum promise-nya selesai. Baris `setStatus("memanggil")`
 * sesudah `await` lalu menimpanya, dan `Connected` tidak pernah datang dua kali.
 *
 * Akibatnya penelepon macet di "Menunggu dijawab" selamanya walau lawannya
 * sudah menjawab: kisi peserta tidak dirender, jadi ia tidak melihat DAN tidak
 * mendengar apa pun, sementara pengukur byte ikut mati karena hanya berjalan
 * saat `"tersambung"`. Di sisi lawan semuanya tampak normal. Dua tangkapan
 * layar dari HP dan PC pada panggilan yang SAMA yang akhirnya membongkarnya:
 * satu menulis "Tersambung, masuk 225 KB audio", satu menulis "Menunggu
 * dijawab, masuk 0 KB", pada detik yang sama.
 *
 * `diam` sengaja tidak bisa dinaikkan lagi: peristiwa yang menyusul sesudah
 * panggilan dibereskan tidak boleh menghidupkannya kembali.
 */
export function statusSesudahPeristiwa(sekarang: TStatusPanggilan, adaPesertaJauh: boolean): TStatusPanggilan {
  if (sekarang === "diam") return "diam";
  return adaPesertaJauh ? "tersambung" : sekarang;
}
