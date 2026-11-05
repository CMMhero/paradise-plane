/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Pemeriksaan reaksi.ts. Jalankan DARI packages/i18n (tsx terpasang di sana):
 *
 *   cd packages/i18n
 *   pnpm exec tsx "../../apps/web/app/(all)/[workspaceSlug]/(projects)/chat/reaksi.check.ts"
 */

import assert from "node:assert/strict";
import { JENDELA_GEMA_KLIK_MS, alihkanReaksi, buatPenyaringGanda } from "./reaksi";

// Penyaring: satu klik di menu konteks Windows memanggil onClick dua kali,
// beberapa milidetik terpisah. Yang kedua harus ditolak.
const boleh = buatPenyaringGanda();
assert.equal(boleh("reaksi:👍", 1000), true, "aktivasi pertama jalan");
assert.equal(boleh("reaksi:👍", 1004), false, "gema klik yang sama ditolak");
assert.equal(boleh("reaksi:❤️", 1006), true, "emoji lain di jendela yang sama tetap jalan");
assert.equal(boleh("reaksi:👍", 1000 + JENDELA_GEMA_KLIK_MS), true, "sesudah jendela, klik baru jalan lagi");
assert.equal(boleh("aksi:sematkan", 5000), true, "aksi menu ikut disaring per kunci");
assert.equal(boleh("aksi:sematkan", 5010), false, "sematkan tidak boleh bolak-balik dalam satu klik");

// alihkanReaksi meniru tombol bolak-balik server.
const awal = [{ emoji: "👍", orang: ["budi"] }];
assert.deepEqual(alihkanReaksi(awal, "👍", "aku"), [{ emoji: "👍", orang: ["budi", "aku"] }], "ikut emoji yang ada");
assert.deepEqual(alihkanReaksi(awal, "👍", "budi"), [], "klik kedua membatalkan, chip kosong dibuang");
assert.deepEqual(
  alihkanReaksi(awal, "❤️", "aku"),
  [
    { emoji: "👍", orang: ["budi"] },
    { emoji: "❤️", orang: ["aku"] },
  ],
  "emoji baru ditambah di ujung"
);
assert.deepEqual(
  alihkanReaksi([{ emoji: "👍", orang: ["budi", "aku"] }], "👍", "aku"),
  [{ emoji: "👍", orang: ["budi"] }],
  "batal tanpa membuang reaksi orang lain"
);
assert.deepEqual(awal, [{ emoji: "👍", orang: ["budi"] }], "masukan tidak diubah");

console.log("reaksi: semua pemeriksaan lolos");
