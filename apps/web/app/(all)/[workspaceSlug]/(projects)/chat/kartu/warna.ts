/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: warna isi kartu obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Warna isi kartu. `terang` = kartu yang SAYA picu, digambar di atas aksen
 * gelembung keluar saya, jadi teks dan kotaknya pindah ke putih transparan.
 * Chip status (berhasil/gagal) dan tombol tetap pejal: keduanya terbaca di atas
 * warna apa pun.
 */
export const warnaKartu = (terang: boolean) =>
  terang
    ? {
        utama: "text-on-color",
        sekunder: "text-on-color/85",
        redup: "text-on-color/70",
        kotak: "border-white/25 bg-white/15",
        chip: "bg-white/20 text-on-color",
        garis: "border-white/40",
        ikon: "bg-white/20 text-on-color",
      }
    : {
        utama: "text-primary",
        sekunder: "text-secondary",
        redup: "text-tertiary",
        kotak: "border-subtle bg-layer-2",
        chip: "bg-layer-3 text-secondary",
        garis: "border-subtle",
        ikon: "bg-accent-subtle text-accent-primary",
      };
