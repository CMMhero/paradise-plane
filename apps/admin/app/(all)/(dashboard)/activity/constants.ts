/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: dashboard aktivitas
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/* Dipisah dari berkas komponen: satu berkas yang mengekspor komponen DAN nilai
   biasa mematikan Fast Refresh, sama alasannya dengan members/constants.ts. */

/** Sama persis dengan halaman Member & Jejak audit, jangan dibuat sendiri. */
export const selectClass =
  "rounded border border-subtle bg-layer-1 px-2 py-1.5 text-body-sm-regular text-primary outline-none focus:border-accent-primary";

export const RENTANG = [
  { value: 7, label: "7 hari" },
  { value: 30, label: "30 hari" },
  { value: 90, label: "90 hari (maks)" },
];

export const SKELETON_ROWS = ["s1", "s2", "s3", "s4", "s5", "s6"];

/**
 * Dua warna seri grafik. Diambil dari palet kategorikal baku dan sudah
 * DIVALIDASI, bukan dipilih dengan mata: lightness band, chroma floor, pemisahan
 * buta warna (protan ΔE 24.7 terang / 26.8 gelap), dan kontras terhadap
 * permukaan, semuanya lulus di mode terang maupun gelap.
 *
 * Warna gelap BUKAN pembalikan otomatis dari yang terang; keduanya dilangkahkan
 * terpisah untuk permukaannya masing-masing.
 */
export const SERI = {
  login: { terang: "#2a78d6", gelap: "#3987e5", label: "Login" },
  orang: { terang: "#eb6834", gelap: "#d95926", label: "Orang unik" },
} as const;
