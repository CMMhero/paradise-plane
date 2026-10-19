/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pemeriksaan teks pemberitahuan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Pemeriksaan penyusun teks pemberitahuan. Jalankan DARI packages/i18n, karena
 * di situlah tsx terpasang; dari root `pnpm exec tsx` menjawab
 * "Command not found":
 *
 *   cd packages/i18n
 *   pnpm exec tsx ../../apps/web/core/components/notifikasi/teks.check.ts
 *
 * Sengaja node:assert, bukan framework: apps/web tidak punya test runner, dan
 * menambah satu cuma untuk berkas ini lebih mahal daripada yang dijaganya.
 */

import assert from "node:assert/strict";
import { ringkasNotifikasi, ringkasPercakapan, teksPolos } from "./teks";

// --- HTML komentar jadi teks yang bisa dibaca --------------------------------

assert.equal(teksPolos("<p>sudah saya cek</p>"), "sudah saya cek");
assert.equal(teksPolos("<p>a</p><p>b</p>"), "a b");
assert.equal(teksPolos("harga &lt; 5 &amp; stok &gt; 0"), "harga < 5 & stok > 0");
assert.equal(teksPolos(""), "");
assert.equal(teksPolos(undefined), "");

// --- pemberitahuan pekerjaan ------------------------------------------------

const pemicu = { display_name: "andri", first_name: "Andri", is_bot: false };
const tugas = { name: "Printer lantai 2 macet", identifier: "IT", sequence_id: 42 };

{
  // Ditugaskan ke saya. Ini pemberitahuan yang paling sering muncul, dan judul
  // harus menyebut PEKERJAANNYA, bukan kata "Pemberitahuan".
  const r = ringkasNotifikasi({
    triggered_by_details: pemicu,
    data: { issue: tugas, issue_activity: { field: "assignees", new_value: "budi", verb: "updated" } },
  });
  assert.equal(r.judul, "IT-42 Printer lantai 2 macet");
  assert.equal(r.isi, "andri menugaskan pekerjaan ini kepada Anda");
}

{
  // Tugas baru yang langsung ditugaskan datang dengan field "None".
  const r = ringkasNotifikasi({
    triggered_by_details: pemicu,
    data: { issue: tugas, issue_activity: { field: "None", verb: "created" } },
  });
  assert.equal(r.isi, "andri memberi Anda tugas baru");
}

{
  const r = ringkasNotifikasi({
    triggered_by_details: pemicu,
    data: { issue: tugas, issue_activity: { field: "comment", new_value: "<p>tolong cek ya</p>", verb: "created" } },
  });
  assert.equal(r.isi, "andri berkomentar: tolong cek ya");
}

{
  // Penyebutan menang atas "berkomentar": itulah alasan pemberitahuan ini
  // sampai ke orangnya, dan menyembunyikannya membuat @-nya terasa tidak jalan.
  const r = ringkasNotifikasi({
    is_mentioned_notification: true,
    triggered_by_details: pemicu,
    data: { issue: tugas, issue_activity: { field: "comment", new_value: "<p>@budi bantu ya</p>", verb: "created" } },
  });
  assert.equal(r.isi, "andri menyebut Anda: @budi bantu ya");
}

{
  // Jenis aktivitas yang tidak terdaftar tidak boleh menghasilkan kalimat
  // kosong atau "undefined".
  const r = ringkasNotifikasi({
    triggered_by_details: pemicu,
    data: { issue: tugas, issue_activity: { field: "estimate_time", new_value: "120", verb: "updated" } },
  });
  assert.equal(r.isi, "andri memperbarui estimate time");
}

{
  // Tanpa pemicu dan tanpa tugas pun harus tetap terbaca sebagai kalimat.
  const r = ringkasNotifikasi({ title: "Ada yang baru" });
  assert.equal(r.judul, "Ada yang baru");
  assert.equal(r.isi, "Seseorang memperbarui pekerjaan ini");
}

{
  const r = ringkasNotifikasi({
    triggered_by_details: { first_name: "Paradise Bot", is_bot: true },
    data: { issue: tugas, issue_activity: { field: "state", new_value: "Done", verb: "updated" } },
  });
  assert.equal(r.isi, "Paradise Bot memindahkan statusnya ke Done");
}

// --- obrolan ----------------------------------------------------------------

const namaOrang = (id: string) => ({ "u-1": "Siti", "u-2": "Rendi" })[id];

assert.equal(ringkasPercakapan([], namaOrang), null);

{
  // Percakapan yang sudah dibaca tidak boleh memicu apa pun.
  const hasil = ringkasPercakapan(
    [{ id: "r1", lawan_bicara: "u-1", belum_dibaca: 0, isi: "halo", pesan_terakhir_pada: "2026-08-21T09:00:00Z" }],
    namaOrang
  );
  assert.equal(hasil, null);
}

{
  // Pesan SAYA SENDIRI, terkirim dari perangkat lain, tidak boleh
  // diberitahukan kembali kepada saya.
  const hasil = ringkasPercakapan(
    [
      {
        id: "r1",
        lawan_bicara: "u-1",
        belum_dibaca: 2,
        dari_saya: true,
        isi: "oke",
        pesan_terakhir_pada: "2026-08-21T09:00:00Z",
      },
    ],
    namaOrang
  );
  assert.equal(hasil, null);
}

{
  // Yang PALING BARU yang ditampilkan, bukan yang pertama di daftar.
  const hasil = ringkasPercakapan(
    [
      { id: "r1", lawan_bicara: "u-1", belum_dibaca: 1, isi: "lama", pesan_terakhir_pada: "2026-08-21T08:00:00Z" },
      { id: "r2", lawan_bicara: "u-2", belum_dibaca: 3, isi: "baru", pesan_terakhir_pada: "2026-08-21T10:00:00Z" },
    ],
    namaOrang
  );
  assert.equal(hasil?.judul, "Rendi");
  assert.equal(hasil?.isi, "baru (+1 percakapan lain)");
  assert.equal(hasil?.ruangId, "r2");
  assert.equal(hasil?.lawanBicara, "u-2");
}

{
  // Kanal punya nama sendiri; lawan bicaranya kosong dan itu wajar.
  const hasil = ringkasPercakapan(
    [{ id: "r9", nama: "it-support", lawan_bicara: null, belum_dibaca: 1, isi: "server lambat" }],
    namaOrang
  );
  assert.equal(hasil?.judul, "# it-support");
  assert.equal(hasil?.lawanBicara, null);
}

{
  // Ekor "(+N percakapan lain)" harus selamat walau pesannya panjang: bagian
  // itulah yang tidak bisa ditebak sendiri oleh yang membacanya.
  const panjang = "x".repeat(400);
  const hasil = ringkasPercakapan(
    [
      { id: "r1", lawan_bicara: "u-1", belum_dibaca: 1, isi: panjang, pesan_terakhir_pada: "2026-08-21T10:00:00Z" },
      { id: "r2", lawan_bicara: "u-2", belum_dibaca: 1, isi: "hai", pesan_terakhir_pada: "2026-08-21T09:00:00Z" },
    ],
    namaOrang
  );
  assert.ok(hasil?.isi.endsWith("(+1 percakapan lain)"), hasil?.isi);
  assert.ok((hasil?.isi.length ?? 0) <= 160);
}

{
  // Pesan yang isinya cuma lampiran tetap harus punya kalimat.
  const hasil = ringkasPercakapan([{ id: "r1", lawan_bicara: "u-1", belum_dibaca: 1, isi: "" }], namaOrang);
  assert.equal(hasil?.isi, "Mengirim lampiran");
}

console.log("teks pemberitahuan: semua pemeriksaan lolos");
