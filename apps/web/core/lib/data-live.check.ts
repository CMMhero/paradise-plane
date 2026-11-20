/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: hitungan penarikan saat pindah tab/jendela
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Menghitung berapa kunci SWR dan penyegar terdaftar yang ditarik ulang pada
 * tiap skenario. Memakai `mutate` SWR yang asli; kunci "terpasang" didaftarkan
 * lewat `subscribeCallback` seperti yang dilakukan `useSWR`.
 *
 *   cd packages/i18n
 *   pnpm exec tsx ../../apps/web/core/lib/data-live.check.ts [./modul-lain]
 *
 * Argumen opsional: modul data-live yang diuji (untuk membandingkan dengan versi lama).
 */

import assert from "node:assert/strict";
import { cache, SWRGlobalState, subscribeCallback } from "swr/_internal";
import { WEB_SWR_CONFIG } from "@plane/constants";

// ---- DOM dan jam palsu -------------------------------------------------------
let sekarang = 1_700_000_000_000;
const pendengar = new Map<string, Set<() => void>>();
const doc = {
  visibilityState: "visible" as "visible" | "hidden",
  fokus: true,
  activeElement: null,
  hasFocus() {
    return this.fokus;
  },
  addEventListener(n: string, f: () => void) {
    pendengar.set(n, (pendengar.get(n) ?? new Set()).add(f));
  },
  removeEventListener(n: string, f: () => void) {
    pendengar.get(n)?.delete(f);
  },
};
(globalThis as unknown as { document: unknown }).document = doc;
Date.now = () => sekarang;
type Timer = { at: number; f: () => void; id: number };
let timers: Timer[] = [];
let nomorTimer = 0;
(globalThis as unknown as { setTimeout: unknown }).setTimeout = (f: () => void, ms = 0) => {
  timers.push({ at: sekarang + ms, f, id: ++nomorTimer });
  return nomorTimer;
};
(globalThis as unknown as { clearTimeout: unknown }).clearTimeout = (id: number) => {
  timers = timers.filter((t) => t.id !== id);
};
const maju = async (ms: number) => {
  const sampai = sekarang + ms;
  for (;;) {
    const berikut = timers.filter((t) => t.at <= sampai).sort((a, b) => a.at - b.at)[0];
    if (!berikut) break;
    timers = timers.filter((t) => t !== berikut);
    sekarang = Math.max(sekarang, berikut.at);
    berikut.f();
    await Promise.resolve();
  }
  sekarang = sampai;
  await new Promise((r) => setImmediate(r));
};
const picu = (n: string) => pendengar.get(n)?.forEach((f) => f());
const sembunyikan = () => {
  doc.visibilityState = "hidden";
  picu("visibilitychange");
};
const tampilkan = async () => {
  doc.visibilityState = "visible";
  picu("visibilitychange");
  await maju(1);
};

// ---- kunci SWR terpasang -------------------------------------------------------
const KUNCI = [
  "PROJECT_ISSUES_ws_p1",
  "WORKSPACE_GLOBAL_VIEW_ISSUES_ws_v1",
  "CHAT_ISI_ws_r1",
  "CHAT_PERCAKAPAN_ws",
  "HOME_ATTENTION_ws",
  ...Array.from({ length: 20 }, (_, i) => `LAIN_${i}`),
];
const tarikan: Record<string, number> = {};
const [EVENT_REVALIDATORS] = SWRGlobalState.get(cache) as unknown as [
  Record<string, Array<(t: number) => Promise<boolean>>>,
];
for (const k of KUNCI) {
  cache.set(k, { data: 1, _k: k } as never);
  subscribeCallback(k, EVENT_REVALIDATORS, () => {
    tarikan[k] = (tarikan[k] ?? 0) + 1;
    return Promise.resolve(true);
  });
}
let penyegarTugas = 0;
const total = () => Object.values(tarikan).reduce((a, b) => a + b, 0) + penyegarTugas;
const hitung = async (nama: string, kerja: () => Promise<void>): Promise<number> => {
  for (const k of Object.keys(tarikan)) delete tarikan[k];
  penyegarTugas = 0;
  await kerja();
  await maju(5000);
  const n = total();
  console.log(
    `${nama.padEnd(58)} ${String(n).padStart(3)} penarikan`,
    process.env.RINCI ? JSON.stringify({ ...tarikan, penyegarTugas }) : ""
  );
  return n;
};

const modul = await import(process.argv[2] ?? "./data-live");
const bersih = modul.pasangPenjagaData();
modul.daftarkanPenyegar({ jenis: ["tugas"], proyek: "p1", tarik: () => void (penyegarTugas += 1) });

const hasil: Record<string, number> = {};
console.log(`modul: ${process.argv[2] ?? "./data-live"}`);
console.log(`WEB_SWR_CONFIG.revalidateOnFocus = ${WEB_SWR_CONFIG.revalidateOnFocus}`);
console.log(
  `WEB_SWR_CONFIG.isVisible = ${"isVisible" in WEB_SWR_CONFIG ? "ada (polling berhenti saat blur)" : "tidak ada"}`
);

const tersembunyiSelama = (ms: number) => async () => {
  sembunyikan();
  await maju(ms);
  await tampilkan();
};
hasil.tab10 = await hitung("tab tersembunyi 10 dtk, kembali", tersembunyiSelama(10_000));
await maju(60_000);
hasil.tab30 = await hitung("tab tersembunyi 30 dtk, kembali", tersembunyiSelama(30_000));
await maju(60_000);
hasil.tab6m = await hitung("tab tersembunyi 6 mnt, kembali", tersembunyiSelama(6 * 60_000));
await maju(60_000);
hasil.blur = await hitung("jendela blur/fokus, tab tetap terlihat (alt-tab)", async () => {
  doc.fokus = false;
  picu("blur");
  await maju(20_000);
  doc.fokus = true;
  picu("focus");
});
await maju(60_000);
hasil.petunjuk = await hitung("tersembunyi 30 dtk + 3 petunjuk tugas p1 saat tersembunyi", async () => {
  sembunyikan();
  for (let i = 0; i < 3; i++) {
    modul.terimaSinyalData({ jenis: "tugas", proyek: "p1", tugas: `t${i}` });
    await maju(5000);
  }
  await maju(15_000);
  await tampilkan();
});
await maju(60_000);
hasil.petunjukAktif = await hitung("tab terlihat, 1 petunjuk tugas p1 (tujuan real-time)", async () => {
  modul.terimaSinyalData({ jenis: "tugas", proyek: "p1", tugas: "t9" });
  await maju(1000);
});
await maju(60_000);
const sambungUlang = (terputusMs: number) => async () => {
  if (modul.saatSoketTersambungUlang) modul.saatSoketTersambungUlang(terputusMs);
  else await modul.segarkanSemua();
};
hasil.putus3 = await hitung("soket tersambung ulang setelah putus 3 dtk", sambungUlang(3000));
await maju(60_000);
hasil.putus60 = await hitung("soket tersambung ulang setelah putus 60 dtk", sambungUlang(60_000));
await maju(60_000);
hasil.dobel = await hitung("kembali dari 6 mnt + soket sambung ulang bersamaan", async () => {
  sembunyikan();
  await maju(6 * 60_000);
  await sambungUlang(60_000)();
  await tampilkan();
});
bersih();

if (modul.jendelaAktif) {
  // Rancangan baru: perubahan fokus/tab singkat tidak menarik apa pun.
  assert.equal(hasil.tab10, 0);
  assert.equal(hasil.tab30, 0);
  assert.equal(hasil.blur, 0);
  assert.equal(hasil.putus3, 0);
  // Petunjuk tugas p1: kunci project, widget perhatian, dan penyegar daftar (3), digabung jadi satu putaran saat kembali.
  assert.equal(hasil.petunjuk, 3);
  assert.equal(hasil.petunjukAktif, 3);
  assert.equal(hasil.putus60, KUNCI.length + 1);
  assert.equal(hasil.tab6m, KUNCI.length + 1, "6 mnt: satu putaran menyeluruh");
  assert.equal(hasil.dobel, KUNCI.length + 1, "pemicu bersamaan menyatu jadi satu putaran");
  assert.equal(WEB_SWR_CONFIG.revalidateOnFocus, false);
  console.log("OK");
}
