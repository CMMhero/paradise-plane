/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pemeriksaan perubahan lokal kartu "Needs attention"
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Jalankan dari packages/i18n. apps/web tidak punya
 * test runner, jadi mengikuti `notifikasi/teks.check.ts`:
 *
 *   cd packages/i18n
 *   pnpm dlx tsx ../../apps/web/core/components/home/widgets/attention/data.check.ts
 */

import assert from "node:assert/strict";
import type { TAttention, TAttentionItem } from "@/services/attention.service";
import { removeItem, removeItems, updateItem } from "./data";

const item = (key: string): TAttentionItem => ({
  key,
  id: `issue-${key}`,
  sequence_id: 1,
  identifier: "WH-1",
  name: "Tugas",
  project_id: "p1",
  project_name: "Gudang",
  target_date: null,
  state_id: "s1",
  state_name: "Todo",
  state_group: "unstarted",
  created_by: null,
  assignee_ids: [],
});

const data: TAttention = {
  generated_at: "2026-11-20T00:00:00Z",
  is_supervisor: true,
  total: 3,
  groups: [
    { key: "decide", count: 2, items: [item("a"), item("b")] },
    { key: "mentioned", count: 1, items: [item("a")] },
  ],
};

const tanpaA = removeItem("decide", "a")(data);
assert.deepEqual(
  tanpaA.groups[0].items.map((i) => i.key),
  ["b"]
);
assert.equal(tanpaA.groups[0].count, 1);
assert.equal(tanpaA.total, 2);
// Kunci yang sama di kelompok lain (satu tugas, dua kartu) tidak ikut hilang.
assert.equal(tanpaA.groups[1].items.length, 1);
// Data asli tidak diubah: SWR membutuhkannya untuk rollback.
assert.equal(data.groups[0].items.length, 2);

const pindah = updateItem("mentioned", "a", { state_id: "s2", state_name: "Doing" })(data);
assert.equal(pindah.groups[1].items[0].state_name, "Doing");
assert.equal(pindah.groups[0].items[0].state_name, "Todo");

// Banyak kartu sekaligus: kunci yang sama di kelompok lain tidak ikut hilang.
const semua = removeItems([
  { group: "decide", key: "a" },
  { group: "decide", key: "b" },
])(data);
assert.equal(semua.groups[0].items.length, 0);
assert.equal(semua.groups[0].count, 0);
assert.equal(semua.groups[1].items.length, 1);
assert.equal(semua.total, 1);
// Kunci yang tidak ada tidak mengubah apa pun, dan data asli tetap utuh.
assert.equal(removeItems([{ group: "decide", key: "zzz" }])(data).total, 3);
assert.equal(data.groups[0].items.length, 2);

console.log("data.check.ts: ok");
