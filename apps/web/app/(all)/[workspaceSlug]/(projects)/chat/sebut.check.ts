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
import { cariKueriSebut, potongSebutan, saringCalon, sebutanTersisa, sisipkanSebut } from "./sebut";

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

console.log("sebut.check: semua lolos");
