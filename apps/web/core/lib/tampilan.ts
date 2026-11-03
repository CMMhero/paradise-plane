/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: preferensi tampilan (KEP-64)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Tiga pilihan per orang (skema warna, font, gerak) disimpan di
 * `profile.theme` (JSONField, tanpa migrasi) dan diterapkan sebagai atribut
 * `data-*` di <html>. Semua efeknya hidup di
 * `packages/tailwind-config/paradise-tampilan.css`; di sini hanya menulis
 * atributnya.
 *
 * Nilai bawaan pabrik TIDAK ditulis sebagai atribut, jadi CSS-nya cukup
 * menangani penyimpangan. Cermin `GAYA_SAH` di plane/utils/bawaan_member.py:
 * pilihan pertama tiap daftar = bawaan pabrik.
 */

import type { IUserTheme, TTampilanFont, TTampilanGerak, TTampilanSkema } from "@plane/types";

export type TTampilan = {
  skema: TTampilanSkema;
  font: TTampilanFont;
  gerak: TTampilanGerak;
};

export const TAMPILAN_SAH: { [K in keyof TTampilan]: readonly TTampilan[K][] } = {
  skema: ["bara", "senja", "sumi", "hutan", "netral"],
  font: [
    "jakarta",
    "inter",
    "geist",
    "figtree",
    "bricolage",
    "archivo",
    "sora",
    "shantell",
    "jetbrains",
    "serif",
    "sistem",
  ],
  gerak: ["halus", "kurangi"],
};

const KUNCI = Object.keys(TAMPILAN_SAH) as (keyof TTampilan)[];

export const TAMPILAN_PABRIK: TTampilan = {
  skema: "bara",
  font: "jakarta",
  gerak: "halus",
};

/** Baca preferensi dari profil; nilai kosong atau tak dikenal jatuh ke pabrik. */
export function bacaTampilan(theme: Partial<IUserTheme> | undefined): TTampilan {
  const pilih = <K extends keyof TTampilan>(kunci: K): TTampilan[K] => {
    const nilai = theme?.[kunci];
    return (TAMPILAN_SAH[kunci] as readonly unknown[]).includes(nilai)
      ? (nilai as TTampilan[K])
      : TAMPILAN_PABRIK[kunci];
  };
  return {
    skema: pilih("skema"),
    font: pilih("font"),
    gerak: pilih("gerak"),
  };
}

/** Tulis atribut `data-skema`, `data-font`, `data-gerak` di <html>. */
export function terapkanTampilan(tampilan: TTampilan, root: HTMLElement = document.documentElement): void {
  KUNCI.forEach((kunci) => {
    if (tampilan[kunci] === TAMPILAN_PABRIK[kunci]) root.removeAttribute(`data-${kunci}`);
    else root.setAttribute(`data-${kunci}`, tampilan[kunci]);
  });
}
