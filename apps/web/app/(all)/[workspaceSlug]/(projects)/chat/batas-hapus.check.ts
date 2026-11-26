/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Pemeriksaan bolehDihapus. Jalankan DARI packages/i18n (tsx terpasang di sana):
 *
 *   cd packages/i18n
 *   pnpm exec tsx "../../apps/web/app/(all)/[workspaceSlug]/(projects)/chat/batas-hapus.check.ts"
 */

import assert from "node:assert/strict";
import { batasHapusRuang, bolehDihapus } from "./batas-hapus";

const sekarang = Date.parse("2026-11-03T12:00:00Z");
const jamLalu = (n: number) => new Date(sekarang - n * 60 * 60 * 1000).toISOString();

assert.equal(bolehDihapus(jamLalu(1), 24, sekarang), true, "pesan sejam lalu boleh dihapus");
assert.equal(bolehDihapus(jamLalu(24), 24, sekarang), true, "tepat di batas masih boleh, sama dengan server");
assert.equal(bolehDihapus(jamLalu(25), 24, sekarang), false, "lewat batas tidak boleh");
assert.equal(bolehDihapus(jamLalu(24 * 365), 0, sekarang), true, "0 = tanpa batas");
assert.equal(bolehDihapus(jamLalu(24 * 365), undefined, sekarang), true, "server lama tanpa setelan = tanpa batas");

assert.equal(bolehDihapus(jamLalu(999), batasHapusRuang(24, "pengumuman"), sekarang), true, "pengumuman tanpa batas");
assert.equal(batasHapusRuang(24, "divisi:1"), 24, "kanal sistem lain tetap dibatasi");
assert.equal(batasHapusRuang(24, null), 24, "kanal biasa tetap dibatasi");
assert.equal(batasHapusRuang(24, undefined), 24, "DM tetap dibatasi");

console.log("batas-hapus: semua pemeriksaan lolos");
