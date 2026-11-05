/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pemeriksaan sebutan @
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Jalankan dari packages/i18n (tsx terpasang di sana):
 *   pnpm exec tsx "../../apps/web/app/(all)/[workspaceSlug]/(projects)/chat/sebut.check.ts"
 */

import assert from "node:assert/strict";
import {
  cariKueri,
  cariKueriSebut,
  cocokSemua,
  potongRujukan,
  potongSebutan,
  rujukanTersisa,
  saringCalon,
  sebutanTersisa,
  semuaTersisa,
  sisipkanRujukan,
  sisipkanSebut,
} from "./sebut";

// Kueri yang sedang diketik
assert.deepEqual(cariKueriSebut("halo @an", 8), { awal: 5, kueri: "an" });
assert.deepEqual(cariKueriSebut("@", 1), { awal: 0, kueri: "" });
assert.deepEqual(cariKueriSebut("baris\n@bu", 9), { awal: 6, kueri: "bu" });
assert.equal(cariKueriSebut("kirim ke ani@kantor.com", 23), null, "alamat email bukan sebutan");
assert.equal(cariKueriSebut("@ani sudah", 10), null, "spasi sesudah nama menutup pemilih");
assert.deepEqual(cariKueriSebut("@ani sudah", 4), { awal: 0, kueri: "ani" }, "kursor di tengah tetap terbaca");

// Sisipan
assert.deepEqual(sisipkanSebut("halo @an", 5, 8, "Ani"), { teks: "halo @Ani ", kursor: 10 });
assert.deepEqual(sisipkanSebut("@b tolong", 0, 2, "Budi"), { teks: "@Budi tolong", kursor: 6 });

// Saring calon: awalan dulu
const calon = [{ nama: "Sani" }, { nama: "Ani" }, { nama: "Budi" }];
assert.deepEqual(
  saringCalon(calon, "an").map((c) => c.nama),
  ["Ani", "Sani"]
);
assert.equal(saringCalon(calon, "").length, 3);

// Sebutan yang dihapus dari draf tidak terkirim
const dipilih = new Map([
  ["1", "Ani"],
  ["2", "Budi"],
]);
assert.deepEqual(sebutanTersisa("@Ani tolong cek", dipilih), ["1"]);
assert.deepEqual(sebutanTersisa("@Anita bukan Ani", dipilih), [], "awalan nama lain bukan sebutan");
assert.deepEqual(sebutanTersisa("(@Budi)", dipilih), ["2"]);

// Potongan render: nama terpanjang menang
const orang = [
  { id: "1", nama: "Budi" },
  { id: "2", nama: "Budi Santoso" },
];
assert.deepEqual(potongSebutan("hai @Budi Santoso dan @Budi.", orang), [
  { jenis: "teks", isi: "hai " },
  { jenis: "sebut", isi: "@Budi Santoso", id: "2" },
  { jenis: "teks", isi: " dan " },
  { jenis: "sebut", isi: "@Budi", id: "1" },
  { jenis: "teks", isi: "." },
]);
assert.deepEqual(potongSebutan("email budi@Budi.com", orang), [{ jenis: "teks", isi: "email budi@Budi.com" }]);
assert.deepEqual(potongSebutan("tanpa sebutan", []), [{ jenis: "teks", isi: "tanpa sebutan" }]);
assert.deepEqual(potongSebutan("nama [x]+ aneh @a.b", [{ id: "9", nama: "a.b" }]).at(-1), {
  jenis: "sebut",
  isi: "@a.b",
  id: "9",
});

// Kueri # (kanal dan work item)
assert.deepEqual(cariKueri("lihat #PRJ-1", 12, "#"), { awal: 6, kueri: "PRJ-1" });
assert.deepEqual(cariKueri("#", 1, "#"), { awal: 0, kueri: "" });
assert.equal(cariKueri("halaman#bagian", 14, "#"), null, "fragmen URL bukan rujukan");
assert.equal(cariKueri("#a sudah", 8, "#"), null);
assert.equal(cariKueri("@ani", 4, "#"), null, "pemicu @ tidak membuka #");
assert.equal(cariKueri("#ab@cd", 6, "#"), null, "@ memutus kueri #");
assert.deepEqual(sisipkanRujukan("cek #pr", 4, 7, "PRJ-12", "#"), { teks: "cek #PRJ-12 ", kursor: 12 });

// @all hanya muncul untuk kueri yang mengawali all/everyone/semua
assert.equal(cocokSemua(""), true);
assert.equal(cocokSemua("al"), true);
assert.equal(cocokSemua("Every"), true);
assert.equal(cocokSemua("sem"), true);
assert.equal(cocokSemua("ani"), false);

// Rujukan # yang dihapus dari draf tidak terkirim
const kanalDipilih = new Map([
  ["k1", "umum"],
  ["k2", "tim-it"],
]);
assert.deepEqual(rujukanTersisa("lihat #umum ya", kanalDipilih, "#"), ["k1"]);
assert.deepEqual(rujukanTersisa("#umumnya bukan", kanalDipilih, "#"), []);
assert.deepEqual(rujukanTersisa("umum tanpa pagar", kanalDipilih, "#"), []);

// @all: hanya yang dipilih dari daftar dan masih ada di teks
assert.equal(semuaTersisa("halo @all semua", true), true);
assert.equal(semuaTersisa("halo @all semua", false), false, "diketik sendiri bukan pemberitahuan");
assert.equal(semuaTersisa("halo @allan", true), false);
assert.equal(semuaTersisa("sudah dihapus", true), false);

// Potongan render dengan semua jenis
const sumber = {
  orang: [{ id: "1", nama: "Ani" }],
  kanal: [
    { id: "k1", nama: "umum" },
    { id: "k2", nama: "umum-it" },
  ],
  tugas: [{ id: "w1", nomor: "PRJ-12" }],
  semua: true,
};
assert.deepEqual(potongRujukan("@all cek #PRJ-12 di #umum-it, @Ani", sumber), [
  { jenis: "semua", isi: "@all" },
  { jenis: "teks", isi: " cek " },
  { jenis: "tugas", isi: "#PRJ-12", id: "w1" },
  { jenis: "teks", isi: " di " },
  { jenis: "kanal", isi: "#umum-it", id: "k2" },
  { jenis: "teks", isi: ", " },
  { jenis: "sebut", isi: "@Ani", id: "1" },
]);
assert.deepEqual(
  potongRujukan("@all", { ...sumber, semua: false }),
  [{ jenis: "teks", isi: "@all" }],
  "@all polos tanpa muatan semua"
);
assert.deepEqual(potongRujukan("#PRJ-123 dan x#umum", sumber), [{ jenis: "teks", isi: "#PRJ-123 dan x#umum" }]);
assert.deepEqual(potongRujukan("#private-channel", { kanal: [{ id: "k9", nama: "private-channel" }] }), [
  { jenis: "kanal", isi: "#private-channel", id: "k9" },
]);

console.log("sebut.check: semua lolos");
