/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pemeriksaan aturan sinyal panggilan DM
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Jalankan DARI packages/i18n, karena tsx hanya terpasang di situ:
 *   pnpm exec tsx "../../apps/web/app/(all)/[workspaceSlug]/(projects)/chat/sinyal-panggilan.check.ts"
 */

import assert from "node:assert/strict";
import {
  akibatWaktuHabis,
  BATAS_DERING_PENELEPON_MS,
  BATAS_DERING_PENERIMA_MS,
  bacaSinyalPanggilan,
  putuskanSinyal,
  sinyalTutup,
  type TJenisSinyal,
  type TPanggilanAktif,
  type TSinyalPanggilan,
} from "./sinyal-panggilan";

const SAYA = "saya";
const LAWAN = "lawan";
const RUANG = "ruang-1";

const sinyal = (jenis: TJenisSinyal, id: string, dari = LAWAN, ke = SAYA, ruang = RUANG): TSinyalPanggilan => ({
  dari,
  ke,
  ruang,
  muatan: { jenis, id },
});

const penelepon = (id = "c1", terjawab = false): TPanggilanAktif => ({
  id,
  lawan: LAWAN,
  ruang: RUANG,
  peran: "penelepon",
  terjawab,
});
const penerima = (id = "c1"): TPanggilanAktif => ({
  id,
  lawan: LAWAN,
  ruang: RUANG,
  peran: "penerima",
  terjawab: false,
});

// --- bentuk pesan dari soket --------------------------------------------------
assert.equal(bacaSinyalPanggilan(null), null);
assert.equal(bacaSinyalPanggilan({ dari: "a", ke: "b", ruang: "r", muatan: { jenis: "nyanyi", id: "x" } }), null);
assert.equal(bacaSinyalPanggilan({ dari: "a", ke: "b", ruang: "r", muatan: { jenis: "panggil" } }), null, "tanpa id");
assert.equal(bacaSinyalPanggilan({ dari: "", ke: "b", ruang: "r", muatan: { jenis: "panggil", id: "x" } }), null);
assert.deepEqual(
  bacaSinyalPanggilan({
    tipe: "panggilan",
    dari: "a",
    ke: "b",
    ruang: "r",
    muatan: { jenis: "panggil", id: "x", video: true, lain: 1 },
  }),
  { dari: "a", ke: "b", ruang: "r", muatan: { jenis: "panggil", id: "x", video: true } },
  "bidang tak dikenal dibuang"
);

// --- undangan ------------------------------------------------------------------
assert.equal(putuskanSinyal(null, "diam", sinyal("panggil", "c1"), SAYA), "dering");
// Sedang di panggilan lain: balas sibuk, jangan menimpa.
assert.equal(
  putuskanSinyal(penerima("c0"), "tersambung", sinyal("panggil", "c1", "orang-ketiga"), SAYA),
  "balas_sibuk"
);
assert.equal(putuskanSinyal(penerima("c0"), "berdering", sinyal("panggil", "c1", "orang-ketiga"), SAYA), "balas_sibuk");
// Undangan ganda dengan id yang sama tidak berdering dua kali.
assert.equal(putuskanSinyal(penerima("c1"), "berdering", sinyal("panggil", "c1"), SAYA), "abaikan");
// Saling menelepon bersamaan di ruang yang sama: bertemu di LiveKit, bukan saling sibuk.
assert.equal(putuskanSinyal(penelepon("c1"), "memanggil", sinyal("panggil", "c2"), SAYA), "bertemu");
assert.equal(
  putuskanSinyal(penelepon("c1"), "memanggil", sinyal("panggil", "c2", LAWAN, SAYA, "ruang-lain"), SAYA),
  "balas_sibuk",
  "ruang beda = panggilan lain"
);

// --- gema dari tab saya sendiri -------------------------------------------------
// PERNAH JADI MASALAH di desain: tab kedua penelepon ikut berdering untuk
// panggilannya sendiri.
assert.equal(putuskanSinyal(null, "diam", sinyal("panggil", "c1", SAYA, LAWAN), SAYA), "abaikan");
for (const jenis of ["terima", "tolak", "sibuk"] as const) {
  assert.equal(
    putuskanSinyal(penerima("c1"), "berdering", sinyal(jenis, "c1", SAYA, LAWAN), SAYA),
    "berhenti_senyap",
    `gema ${jenis} dari tab lain menghentikan dering di sini`
  );
}
// Gema milik panggilan lain tidak menyentuh dering sekarang.
assert.equal(putuskanSinyal(penerima("c1"), "berdering", sinyal("terima", "c0", SAYA, LAWAN), SAYA), "abaikan");
// Tab yang sudah mengangkat tidak berhenti karena gemanya sendiri yang memantul.
assert.equal(putuskanSinyal(penerima("c1"), "tersambung", sinyal("terima", "c1", SAYA, LAWAN), SAYA), "abaikan");

// --- id basi ---------------------------------------------------------------------
// `batal` milik panggilan menit lalu tidak boleh memutus panggilan baru.
assert.equal(putuskanSinyal(penerima("c2"), "berdering", sinyal("batal", "c1"), SAYA), "abaikan");
assert.equal(putuskanSinyal(penelepon("c2"), "tersambung", sinyal("tutup", "c1"), SAYA), "abaikan");
assert.equal(putuskanSinyal(null, "diam", sinyal("tutup", "c1"), SAYA), "abaikan");
// Id cocok tapi pengirimnya bukan lawan.
assert.equal(putuskanSinyal(penerima("c1"), "berdering", sinyal("batal", "c1", "orang-ketiga"), SAYA), "abaikan");

// --- alur penelepon -----------------------------------------------------------
assert.equal(putuskanSinyal(penelepon(), "memanggil", sinyal("terima", "c1"), SAYA), "terjawab");
assert.equal(putuskanSinyal(penelepon(), "memanggil", sinyal("tolak", "c1"), SAYA), "ditolak");
assert.equal(putuskanSinyal(penelepon(), "memanggil", sinyal("sibuk", "c1"), SAYA), "sibuk");
assert.equal(putuskanSinyal(penelepon(), "tersambung", sinyal("tutup", "c1"), SAYA), "ditutup");
assert.equal(
  putuskanSinyal(penelepon(), "memanggil", sinyal("batal", "c1"), SAYA),
  "abaikan",
  "batal hanya untuk penerima"
);

// --- alur yang ditelepon -----------------------------------------------------
assert.equal(putuskanSinyal(penerima(), "berdering", sinyal("batal", "c1"), SAYA), "terlewat");
// Penelepon membatalkan tepat saat kita mengangkat: tutup, bukan "terlewat".
assert.equal(putuskanSinyal(penerima(), "menyambungkan", sinyal("batal", "c1"), SAYA), "ditutup");
assert.equal(putuskanSinyal(penerima(), "tersambung", sinyal("tutup", "c1"), SAYA), "ditutup");
assert.equal(putuskanSinyal(penerima(), "berdering", sinyal("terima", "c1"), SAYA), "abaikan");

// --- waktu habis -----------------------------------------------------------------
assert.ok(BATAS_DERING_PENERIMA_MS > BATAS_DERING_PENELEPON_MS, "penerima menyerah SESUDAH penelepon");
assert.equal(akibatWaktuHabis(penelepon(), "memanggil", "c1"), "tak_terjawab");
assert.equal(akibatWaktuHabis(penelepon(), "menyambungkan", "c1"), "tak_terjawab");
assert.equal(
  akibatWaktuHabis(penelepon("c1", true), "menyambungkan", "c1"),
  "abaikan",
  "sudah dijawab, sedang menyambung"
);
assert.equal(akibatWaktuHabis(penelepon(), "tersambung", "c1"), "abaikan");
assert.equal(akibatWaktuHabis(penelepon("c2"), "memanggil", "c1"), "abaikan", "jam milik panggilan lama");
assert.equal(akibatWaktuHabis(null, "diam", "c1"), "abaikan");
assert.equal(akibatWaktuHabis(penerima(), "berdering", "c1"), "terlewat");
assert.equal(akibatWaktuHabis(penerima(), "tersambung", "c1"), "abaikan");

// --- sinyal saat menutup ---------------------------------------------------------
assert.equal(sinyalTutup(penelepon(), "memanggil"), "batal");
assert.equal(sinyalTutup(penelepon(), "menyambungkan"), "batal");
assert.equal(sinyalTutup(penelepon("c1", true), "menyambungkan"), "tutup");
assert.equal(sinyalTutup(penelepon(), "tersambung"), "tutup");
assert.equal(sinyalTutup(penerima(), "berdering"), "tolak");
assert.equal(sinyalTutup(penerima(), "tersambung"), "tutup");

console.info("sinyal-panggilan: semua pemeriksaan lulus");
