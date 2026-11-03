/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: indikator kehadiran & volume suara
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Jalankan dari packages/i18n:
 *
 *   cd packages/i18n
 *   pnpm exec tsx ../../apps/web/core/lib/kehadiran.check.ts
 */

import assert from "node:assert/strict";
import { AMBANG_AWAY_MS, statusTab, terapkanPesanKehadiran } from "./kehadiran";
import { bacaSuara, SUARA_PABRIK, volumeAudio } from "./suara";

// --- status tab --------------------------------------------------------------
assert.equal(statusTab(1000, 1000 + AMBANG_AWAY_MS - 1, true), "online");
assert.equal(statusTab(1000, 1000 + AMBANG_AWAY_MS, true), "away");
// Tab tersembunyi = away walau baru saja digerakkan; tab lain orang yang sama bisa tetap online.
assert.equal(statusTab(1000, 1000, false), "away");

// --- pesan server ------------------------------------------------------------
{
  let peta = terapkanPesanKehadiran(new Map(), { tipe: "kehadiran_semua", peta: { a: "online", b: "away" } });
  assert.deepEqual(
    [...peta],
    [
      ["a", "online"],
      ["b", "away"],
    ]
  );
  const sebelum = peta;
  peta = terapkanPesanKehadiran(peta, { tipe: "kehadiran", user: "a", status: "offline" });
  assert.deepEqual([...peta], [["b", "away"]]);
  // Tidak memutasi peta lama: useSyncExternalStore butuh identitas baru.
  assert.equal(sebelum.has("a"), true);
  peta = terapkanPesanKehadiran(peta, { tipe: "kehadiran", user: "c", status: "online" });
  assert.equal(peta.get("c"), "online");
}

// --- volume suara ------------------------------------------------------------
assert.deepEqual(bacaSuara(undefined), SUARA_PABRIK);
assert.deepEqual(bacaSuara({ theme: "dark", volume_suara: 30, suara_bisu: true }), { volume: 30, bisu: true });
// Nilai rusak jatuh ke pabrik.
assert.equal(bacaSuara({ theme: "dark", volume_suara: 150 }).volume, SUARA_PABRIK.volume);
// Saklar lama per peramban dipakai hanya kalau akun belum pernah menyimpan bisu.
assert.equal(bacaSuara({ theme: "dark" }, true).bisu, true);
assert.equal(bacaSuara({ theme: "dark", suara_bisu: false }, true).bisu, false);
assert.equal(volumeAudio({ volume: 40, bisu: false }), 0.4);
assert.equal(volumeAudio({ volume: 40, bisu: true }), 0);

console.log("kehadiran & suara: semua pemeriksaan lulus");
