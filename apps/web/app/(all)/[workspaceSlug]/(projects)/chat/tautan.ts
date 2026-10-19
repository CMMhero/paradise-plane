/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pemisah tautan di dalam pesan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Pecah teks pesan jadi potongan teks biasa dan potongan alamat.
 *
 * Dipisah dari komponennya supaya bagian yang menentukan APA yang jadi tautan
 * bisa diuji tanpa merender React. Bagian itulah yang penting: ia yang memutuskan
 * kalimat mana di kotak obrolan boleh berubah jadi sesuatu yang bisa diklik.
 *
 * 🔴 Yang dikenali HANYA http dan https, dan itu bukan kerapian melainkan
 * penjagaan. Skema lain (`javascript:`, `data:`) menjadikan sebuah kalimat di
 * kotak obrolan sebagai jalan menjalankan kode di peramban orang lain, dan kotak
 * obrolan justru tempat paling mudah menitipkan kalimat kepada orang lain.
 * Karena pengenalannya lewat pola di bawah, skema lain tidak pernah sampai ke
 * atribut `href`.
 */

export type TPotongan = { jenis: "teks"; isi: string } | { jenis: "tautan"; alamat: string; ekor: string };

const POLA = /(https?:\/\/[^\s<>"']+)/g;
const ALAMAT = /^https?:\/\//;

/** Tanda baca di ujung kalimat bukan bagian dari alamatnya. "buka https://a/b."
 * tidak boleh menghasilkan tautan yang berakhir dengan titik, karena sebagian
 * server memperlakukannya sebagai path yang berbeda lalu menjawab 404. */
const EKOR = /[.,;:!?)\]}]+$/;

export const potongTautan = (teks: string): TPotongan[] =>
  (teks ?? "")
    .split(POLA)
    .filter((bagian) => bagian !== "")
    .map((bagian): TPotongan => {
      // Tiap potongan diperiksa ulang, bukan ditebak dari posisinya. `split`
      // dengan pola bertanda kurung memang menyelipkan hasil tangkapan di antara
      // potongan biasa, tapi begitu potongan kosong dibuang urutan ganjil-genap
      // tidak bisa lagi dipercaya.
      if (!ALAMAT.test(bagian)) return { jenis: "teks", isi: bagian };

      const ekor = EKOR.exec(bagian)?.[0] ?? "";
      return { jenis: "tautan", alamat: ekor ? bagian.slice(0, -ekor.length) : bagian, ekor };
    });
