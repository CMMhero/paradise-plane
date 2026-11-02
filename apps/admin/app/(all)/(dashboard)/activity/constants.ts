/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: dashboard aktivitas
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/* Dipisah dari berkas komponen: satu berkas yang mengekspor komponen DAN nilai
   biasa mematikan Fast Refresh, sama alasannya dengan members/constants.ts. */

/** Pilihan rentang. Yang melebihi retensi (God Mode > Features) disembunyikan halaman. */
export const RENTANG = [7, 30, 90, 180, 365];

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
  login: { terang: "#2a78d6", gelap: "#3987e5", label: "Sign-ins" },
  orang: { terang: "#eb6834", gelap: "#d95926", label: "Unique people" },
} as const;
