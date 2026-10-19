/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Pemeriksaan potongTautan. Jalankan DARI packages/i18n, karena di situlah tsx
 * terpasang; dari root `pnpm exec tsx` menjawab "Command not found":
 *
 *   cd packages/i18n
 *   pnpm exec tsx "../../apps/web/app/(all)/[workspaceSlug]/(projects)/chat/tautan.check.ts"
 *
 * Yang dijaga bukan kerapiannya, melainkan skema apa saja yang boleh berubah
 * jadi sesuatu yang bisa diklik. Kotak obrolan adalah tempat paling mudah
 * menitipkan kalimat kepada orang lain.
 */

import assert from "node:assert/strict";
import { potongTautan } from "./tautan";

const tautan = (teks: string) => potongTautan(teks).filter((p) => p.jenis === "tautan");

// --- yang memang alamat ------------------------------------------------------

{
  const hasil = potongTautan("buka https://tugas.contoh/a/b ya");
  assert.deepEqual(hasil, [
    { jenis: "teks", isi: "buka " },
    { jenis: "tautan", alamat: "https://tugas.contoh/a/b", ekor: "" },
    { jenis: "teks", isi: " ya" },
  ]);
}

{
  // Pesan penugasan otomatis: tautannya di baris terakhir, sesudah baris kosong.
  const isi = "📋 Tugas baru untuk Anda\n\nIT-42 · Printer macet\n\nhttps://p.contoh/ws/projects/p1/issues/i1";
  const alamat = tautan(isi);
  assert.equal(alamat.length, 1);
  assert.equal(alamat[0].jenis === "tautan" ? alamat[0].alamat : "", "https://p.contoh/ws/projects/p1/issues/i1");
}

{
  // Dua alamat dalam satu pesan, keduanya kena.
  assert.equal(tautan("http://a.co dan https://b.co").length, 2);
}

// --- 🔴 yang TIDAK BOLEH jadi tautan ----------------------------------------

{
  // Kalau yang ini pernah lolos, satu kalimat di kotak obrolan jadi jalan
  // menjalankan kode di peramban rekan sekantor.
  assert.equal(tautan("javascript:alert(1)").length, 0);
  assert.equal(tautan("JavaScript:alert(1)").length, 0);
  assert.equal(tautan("data:text/html,<script>alert(1)</script>").length, 0);
  assert.equal(tautan("file:///etc/passwd").length, 0);
  assert.equal(tautan("ftp://a.co/x").length, 0);
  // Menyelipkannya sesudah alamat yang sah pun tidak menolongnya.
  assert.equal(tautan("https://a.co javascript:alert(1)").length, 1);
}

// --- ujung kalimat -----------------------------------------------------------

{
  // Titik penutup kalimat bukan bagian alamat: sebagian server menjawab 404
  // untuk path yang berakhir titik, dan orangnya akan mengira tugasnya hilang.
  const hasil = potongTautan("cek https://a.co/x.");
  assert.deepEqual(hasil[1], { jenis: "tautan", alamat: "https://a.co/x", ekor: "." });
}

{
  const hasil = potongTautan("lihat (https://a.co/x), lalu balas");
  assert.deepEqual(hasil[1], { jenis: "tautan", alamat: "https://a.co/x", ekor: ")," });
}

{
  // Titik DI TENGAH alamat tetap milik alamatnya.
  const hasil = tautan("https://a.co/v1.2/x");
  assert.equal(hasil[0].jenis === "tautan" ? hasil[0].alamat : "", "https://a.co/v1.2/x");
}

// --- teks biasa --------------------------------------------------------------

assert.deepEqual(potongTautan("halo, tolong cek printer"), [{ jenis: "teks", isi: "halo, tolong cek printer" }]);
assert.deepEqual(potongTautan(""), []);

{
  // Pesan yang isinya HANYA alamat tidak boleh menyisakan potongan kosong,
  // karena potongan kosong itu jadi elemen React tanpa isi di dalam gelembung.
  const hasil = potongTautan("https://a.co");
  assert.equal(hasil.length, 1);
  assert.deepEqual(hasil[0], { jenis: "tautan", alamat: "https://a.co", ekor: "" });
}

console.log("tautan pesan: semua pemeriksaan lolos");
