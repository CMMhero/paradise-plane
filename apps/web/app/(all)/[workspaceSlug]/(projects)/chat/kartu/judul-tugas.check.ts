/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Pemeriksaan judulTugas. Jalankan DARI packages/i18n:
 *
 *   cd packages/i18n
 *   pnpm exec tsx "../../apps/web/app/(all)/[workspaceSlug]/(projects)/chat/kartu/judul-tugas.check.ts"
 */

import assert from "node:assert/strict";
import { judulTugas } from "./judul-tugas";

const AKU = "aku";
const DIA = "dia";

// Orang lain menugaskan saya.
assert.deepEqual(judulTugas({ aktor: DIA, penerima: AKU, assignees: [AKU], sayaId: AKU }), { kunci: "assigned" });
// Saya menugaskan orang lain (bug awal: terbaca "You assigned you").
assert.deepEqual(judulTugas({ aktor: AKU, penerima: DIA, assignees: [DIA], sayaId: AKU }), {
  kunci: "assigned_other",
  idPenerima: DIA,
});
// Saya menugaskan diri sendiri.
assert.deepEqual(judulTugas({ aktor: AKU, penerima: AKU, assignees: [AKU], sayaId: AKU }), { kunci: "assigned_self" });
// Kartu lama tanpa penerima: ditebak dari daftar penerima tugas.
assert.deepEqual(judulTugas({ aktor: AKU, penerima: "", assignees: [DIA], sayaId: AKU }), {
  kunci: "assigned_other",
  idPenerima: DIA,
});
assert.deepEqual(judulTugas({ aktor: AKU, penerima: "", assignees: [AKU], sayaId: AKU }), { kunci: "assigned_self" });
assert.deepEqual(judulTugas({ aktor: AKU, penerima: "", assignees: [], sayaId: AKU }), {
  kunci: "assigned_other",
  idPenerima: null,
});
// Pengguna belum dikenal atau aktor kosong: kalimat bawaan.
assert.deepEqual(judulTugas({ aktor: DIA, penerima: AKU, assignees: [], sayaId: undefined }), { kunci: "assigned" });
assert.deepEqual(judulTugas({ aktor: "", penerima: AKU, assignees: [], sayaId: AKU }), { kunci: "assigned" });

console.log("judul-tugas.check: ok");
