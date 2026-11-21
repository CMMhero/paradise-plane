/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: cermin web registri aturan God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu berkas per area (area-<nama>.ts), cermin apps/api/plane/utils/aturan/area_<nama>.py.
 * Ketujuh area sudah terdaftar di sini, jadi menambah aturan web cukup menyunting
 * berkas areanya sendiri. apps/web membaca nilainya lewat `useAturan()`.
 */

import { ATURAN_WEB_KEAMANAN } from "./area-keamanan";
import { ATURAN_WEB_KEPUTUSAN } from "./area-keputusan";
import { ATURAN_WEB_NOTIFIKASI } from "./area-notifikasi";
import { ATURAN_WEB_OBROLAN } from "./area-obrolan";
import { ATURAN_WEB_TAMPILAN } from "./area-tampilan";
import { ATURAN_WEB_TUGAS } from "./area-tugas";
import { ATURAN_WEB_VISIBILITAS } from "./area-visibilitas";

export * from "./jenis";
export * from "./area-keamanan";
export * from "./area-keputusan";
export * from "./area-notifikasi";
export * from "./area-obrolan";
export * from "./area-tampilan";
export * from "./area-tugas";
export * from "./area-visibilitas";

/** Semua aturan web: kunci God Mode -> { default, choices? }. */
export const ATURAN_WEB = {
  ...ATURAN_WEB_VISIBILITAS,
  ...ATURAN_WEB_TUGAS,
  ...ATURAN_WEB_TAMPILAN,
  ...ATURAN_WEB_NOTIFIKASI,
  ...ATURAN_WEB_OBROLAN,
  ...ATURAN_WEB_KEAMANAN,
  ...ATURAN_WEB_KEPUTUSAN,
};

export type TKunciAturanWeb = keyof typeof ATURAN_WEB;

/** Nilai yang berlaku untuk satu aturan web, dengan tipe yang sama dengan bawaannya. */
export type TNilaiAturanWeb<K extends TKunciAturanWeb> = (typeof ATURAN_WEB)[K]["default"];

const samaJenis = (nilai: unknown, bawaan: unknown): boolean =>
  Array.isArray(bawaan) ? Array.isArray(nilai) : typeof nilai === typeof bawaan;

/**
 * Nilai aturan `kunci` dari `paradise_rules` server. Tidak ada, salah jenis, atau di
 * luar `choices` = bawaan, jadi web tidak pernah memakai nilai yang tidak dikenalnya.
 */
export const nilaiAturanWeb = <K extends TKunciAturanWeb>(
  dariServer: Record<string, unknown> | undefined,
  kunci: K
): TNilaiAturanWeb<K> => {
  const def = ATURAN_WEB[kunci] as { default: unknown; choices?: readonly unknown[] };
  const nilai = dariServer?.[kunci];
  if (nilai === undefined || !samaJenis(nilai, def.default)) return def.default as TNilaiAturanWeb<K>;
  const sah = def.choices;
  if (sah) {
    const butir = Array.isArray(nilai) ? nilai : [nilai];
    if (!butir.every((b) => sah.includes(b))) return def.default as TNilaiAturanWeb<K>;
  }
  return nilai as TNilaiAturanWeb<K>;
};
