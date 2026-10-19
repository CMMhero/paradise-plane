/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pemeriksaan tata layar panggilan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Jalankan DARI packages/i18n, karena tsx hanya terpasang di situ:
 *   pnpm exec tsx "../../apps/web/app/(all)/[workspaceSlug]/(projects)/chat/tata-panggilan.check.ts"
 *
 * Urutan argumen: (status, pakaiVideo, adaStreamLokal, jumlahPeserta)
 *
 * Catatan: aturan "elemen media lawan SELALU terpasang walau hanya audio" tidak
 * lagi diuji di sini karena sekarang dijamin oleh struktur komponen `Peserta`,
 * yang selalu merender `Media` dan hanya menyembunyikannya lewat CSS. Aturan itu
 * pernah dilanggar dan membuat panggilan sunyi total.
 */

import assert from "node:assert/strict";
import { statusSesudahPeristiwa, tataPanggilan } from "./tata-panggilan";

// Diam: tidak ada apa pun di layar.
{
  const t = tataPanggilan("diam", true, true, 3);
  assert.equal(t.tampil, false, "status diam tidak boleh menampilkan layar panggilan");
}

// PERNAH SALAH: peserta dianggap ada berdasarkan NIAT memakai video, bukan
// media yang benar-benar tiba. Akibatnya layar menampilkan kotak hitam kosong
// yang terlihat seperti kerusakan padahal panggilannya hidup.
{
  const t = tataPanggilan("tersambung", true, true, 0);
  assert.equal(t.adaPeserta, false, "tersambung tapi belum ada peserta: jangan tampilkan kisi kosong");
  assert.equal(t.tampil, true, "layarnya tetap tampil, cuma isinya belum ada");
}

// Belum tersambung: peserta belum ditampilkan walau datanya sudah ada.
for (const status of ["memanggil", "berdering", "menyambungkan"] as const) {
  const t = tataPanggilan(status, true, true, 2);
  assert.equal(t.adaPeserta, false, `belum tersambung (${status}), peserta belum ditampilkan`);
}

{
  const t = tataPanggilan("tersambung", true, true, 1);
  assert.equal(t.adaPeserta, true, "satu peserta sudah cukup untuk menampilkan");
}

// Cacah jalur kisi TIDAK lagi dihitung di sini, dan pemeriksaannya sengaja
// dihapus bersama kodenya. Sejak 19 Agt 2026 kisinya diserahkan ke CSS
// `auto-fit minmax(240px, 1fr)`, yang mengikuti ruang yang benar-benar ada.
// Menghitungnya di JS memaksa dua peserta di HP 375px berbagi dua jalur selebar
// 160px, dan tidak ada nilai `jumlahPeserta` yang bisa membedakan HP dari
// laptop. Aturan yang tidak bisa dijawab dengan benar lebih baik tidak ada.

// Pratinjau diri tampil SEJAK MEMANGGIL, bukan menunggu tersambung.
{
  const t = tataPanggilan("memanggil", true, true, 0);
  assert.equal(t.pratinjauDiriTerlihat, true, "pratinjau diri tampil sejak memanggil");
}

// Tanpa stream lokal tidak ada yang bisa dipratinjau.
{
  const t = tataPanggilan("memanggil", true, false, 0);
  assert.equal(t.pratinjauDiriTerlihat, false, "tanpa stream lokal, pratinjau tidak dipaksakan");
}

// Panggilan suara tidak menampilkan pratinjau kamera sama sekali.
{
  const t = tataPanggilan("tersambung", false, true, 1);
  assert.equal(t.pratinjauDiriTerlihat, false, "panggilan suara tidak butuh pratinjau kamera");
}

// --- statusSesudahPeristiwa -------------------------------------------------

// PERNAH SALAH, DAN INI YANG PALING MAHAL. Penelepon masuk ruangan duluan dan
// SENDIRIAN, lalu layarnya macet di "Menunggu dijawab" selamanya walau lawannya
// sudah menjawab dan medianya mengalir. Ia tidak melihat dan tidak mendengar
// apa pun, karena kisi peserta hanya dirender saat "tersambung".
{
  assert.equal(
    statusSesudahPeristiwa("memanggil", true),
    "tersambung",
    "lawan masuk ruangan: penelepon WAJIB pindah dari memanggil ke tersambung"
  );
}

// Sendirian di ruangan bukan tersambung. Ini yang dulu keliru diambil dari
// `RoomEvent.Connected`, yang cuma berarti "saya sampai ke server".
{
  assert.equal(statusSesudahPeristiwa("memanggil", false), "memanggil", "sendirian di ruangan belum tersambung");
  assert.equal(
    statusSesudahPeristiwa("menyambungkan", false),
    "menyambungkan",
    "menyambungkan tanpa lawan tetap apa adanya"
  );
}

// Yang mengangkat: lawannya sudah ada sejak sebelum ia masuk.
{
  assert.equal(statusSesudahPeristiwa("menyambungkan", true), "tersambung", "yang mengangkat langsung tersambung");
}

// Peristiwa yang menyusul sesudah panggilan dibereskan tidak boleh
// menghidupkannya lagi. Tanpa penjaga ini, layar panggilan bisa muncul sendiri
// di halaman yang sudah ditutup penggunanya.
{
  assert.equal(statusSesudahPeristiwa("diam", true), "diam", "panggilan yang sudah dibereskan tidak boleh hidup lagi");
}

// Sudah tersambung tetap tersambung, tidak turun lagi.
{
  assert.equal(statusSesudahPeristiwa("tersambung", true), "tersambung", "tersambung bertahan");
}

// eslint-disable-next-line no-console
console.log("tataPanggilan: semua pemeriksaan lulus");
