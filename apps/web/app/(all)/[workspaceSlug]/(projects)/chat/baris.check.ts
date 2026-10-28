/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Pemeriksaan susunBaris. Jalankan DARI packages/i18n, karena di situlah tsx
 * terpasang; dari root `pnpm exec tsx` menjawab "Command not found":
 *
 *   cd packages/i18n
 *   pnpm exec tsx "../../apps/web/app/(all)/[workspaceSlug]/(projects)/chat/baris.check.ts"
 *
 * Sengaja node:assert, bukan framework: apps/web tidak punya test runner, dan
 * menambah satu cuma untuk fungsi ini lebih mahal daripada yang dijaganya.
 */

import assert from "node:assert/strict";
import { susunBaris } from "./baris";

const AKU = "aku";
const DIA = "dia";

const pesan = (id: string, pengirim: string, waktu: string, baru = false) => ({
  id,
  pengirim,
  isi: id,
  created_at: waktu,
  baru,
  lampiran: [],
  disunting: false,
  sudah_dibaca: false,
  balasan_ke: null,
  reaksi: [],
});

const sekarang = new Date("2026-08-13T10:00:00");

// Dua pesan berdekatan dari orang yang sama = satu kelompok: avatar sekali di
// atas, jam sekali di bawah.
{
  const baris = susunBaris(
    [pesan("a", DIA, "2026-08-13T09:00:00"), pesan("b", DIA, "2026-08-13T09:01:00")],
    AKU,
    sekarang
  );
  const pesanSaja = baris.filter((b) => b.jenis === "pesan");
  assert.equal(baris.filter((b) => b.jenis === "tanggal").length, 1, "satu pemisah tanggal");
  assert.equal(pesanSaja.length, 2);
  assert.deepEqual(
    pesanSaja.map((b) => (b.jenis === "pesan" ? [b.awalKelompok, b.akhirKelompok] : [])),
    [
      [true, false],
      [false, true],
    ],
    "kelompok dibuka pesan pertama dan ditutup pesan terakhir"
  );
}

// Jeda lebih dari 5 menit memutus kelompok walau pengirimnya sama.
{
  const baris = susunBaris(
    [pesan("a", DIA, "2026-08-13T09:00:00"), pesan("b", DIA, "2026-08-13T09:30:00")],
    AKU,
    sekarang
  );
  const pesanSaja = baris.filter((b) => b.jenis === "pesan");
  assert.equal(
    pesanSaja.every((b) => b.jenis === "pesan" && b.awalKelompok),
    true,
    "keduanya awal kelompok"
  );
}

// Ganti hari memunculkan pemisah tanggal DAN memutus kelompok, jadi gelembung
// pertama hari ini tidak menempel ke kelompok kemarin.
{
  const baris = susunBaris(
    [pesan("a", DIA, "2026-08-12T23:59:00"), pesan("b", DIA, "2026-08-13T00:01:00")],
    AKU,
    sekarang
  );
  const tanggal = baris.filter((b) => b.jenis === "tanggal");
  assert.equal(tanggal.length, 2, "dua pemisah tanggal");
  assert.deepEqual(
    tanggal.map((b) => (b.jenis === "tanggal" ? (b.relatif ?? "") : "")),
    ["kemarin", "hari-ini"]
  );
  const kedua = baris.filter((b) => b.jenis === "pesan")[1];
  assert.equal(kedua.jenis === "pesan" && kedua.awalKelompok, true, "ganti hari memutus kelompok");
}

// Garis "belum dibaca" hanya SEKALI, di pesan baru yang pertama.
{
  const baris = susunBaris(
    [
      pesan("a", DIA, "2026-08-13T09:00:00"),
      pesan("b", DIA, "2026-08-13T09:01:00", true),
      pesan("c", DIA, "2026-08-13T09:02:00", true),
    ],
    AKU,
    sekarang
  );
  const batas = baris.filter((b) => b.jenis === "belum-dibaca");
  assert.equal(batas.length, 1, "satu garis saja");
  assert.equal(baris.indexOf(batas[0]), 2, "tepat sebelum pesan baru pertama");
}

// Pesan sendiri tidak pernah dianggap masuk.
{
  const baris = susunBaris([pesan("a", AKU, "2026-08-13T09:00:00")], AKU, sekarang);
  const p = baris.find((b) => b.jenis === "pesan");
  assert.equal(p?.jenis === "pesan" && p.dariSaya, true);
}

console.log("susunBaris: semua pemeriksaan lulus");
