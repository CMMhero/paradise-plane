/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Pemeriksaan urutkanDaftar. Jalankan DARI packages/i18n:
 *
 *   cd packages/i18n
 *   pnpm exec tsx "../../apps/web/app/(all)/[workspaceSlug]/(projects)/chat/urutan-daftar.check.ts"
 */

import assert from "node:assert/strict";
import { urutkanDaftar } from "./urutan-daftar";
import type { TButirUrut } from "./urutan-daftar";

const b = (id: string, o: Partial<TButirUrut> = {}): TButirUrut => ({
  id,
  belumDibaca: false,
  online: false,
  terakhir: null,
  nama: id,
  ...o,
});
const ids = (l: TButirUrut[]) => l.map((x) => x.id);

// Belum dibaca di atas online, online di atas sisanya.
assert.deepEqual(
  ids(
    urutkanDaftar([
      b("off", { terakhir: "2026-11-06T10:00:00Z" }),
      b("on", { online: true, terakhir: "2026-11-01T10:00:00Z" }),
      b("baru", { belumDibaca: true, terakhir: "2026-10-01T10:00:00Z" }),
    ])
  ),
  ["baru", "on", "off"]
);

// Dalam satu lapis: terbaru dulu; yang tanpa pesan di bawah, urut nama.
assert.deepEqual(
  ids(
    urutkanDaftar([
      b("z-kosong"),
      b("lama", { terakhir: "2026-11-01T10:00:00Z" }),
      b("a-kosong"),
      b("baru", { terakhir: "2026-11-05T10:00:00Z" }),
    ])
  ),
  ["baru", "lama", "a-kosong", "z-kosong"]
);

// Belum dibaca juga diurut menurut kekinian, online tidak mengalahkannya.
assert.deepEqual(
  ids(
    urutkanDaftar([
      b("u-lama", { belumDibaca: true, online: true, terakhir: "2026-11-01T10:00:00Z" }),
      b("u-baru", { belumDibaca: true, terakhir: "2026-11-05T10:00:00Z" }),
    ])
  ),
  ["u-baru", "u-lama"]
);

// Percakapan terbuka: lapis belum-dibaca ditahan walau server sudah menandai terbaca.
const dibuka = [
  b("terbuka", { belumDibaca: false, terakhir: "2026-11-01T10:00:00Z" }),
  b("on", { online: true, terakhir: "2026-11-05T10:00:00Z" }),
];
assert.deepEqual(ids(urutkanDaftar(dibuka, { id: "terbuka", belumDibaca: true })), ["terbuka", "on"]);
assert.deepEqual(ids(urutkanDaftar(dibuka, { id: "terbuka", belumDibaca: false })), ["on", "terbuka"]);
assert.deepEqual(ids(urutkanDaftar(dibuka)), ["on", "terbuka"]);

// Masukan tidak diubah, hasil deterministik.
const asli = [b("b"), b("a")];
const hasil = urutkanDaftar(asli);
assert.deepEqual(ids(asli), ["b", "a"]);
assert.deepEqual(ids(hasil), ["a", "b"]);

// Waktu rusak diperlakukan sebagai kosong, bukan membuat urutan acak.
assert.deepEqual(
  ids(urutkanDaftar([b("x", { terakhir: "bukan-tanggal" }), b("y", { terakhir: "2026-11-01T00:00:00Z" })])),
  ["y", "x"]
);

console.log("urutan-daftar.check: ok");
