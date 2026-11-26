/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

const MS_PER_JAM = 60 * 60 * 1000;

/**
 * Apakah pesan yang dikirim pada `dikirim` masih boleh dihapus pengirimnya.
 *
 * Cermin penjaga `CHAT_DELETE_WINDOW_HOURS` di `ChatPesanEndpoint.delete`.
 * Server tetap yang memutuskan; ini hanya supaya tombol hapus tidak ditawarkan
 * untuk aksi yang pasti ditolak. `batasJam` 0 atau tidak ada = tanpa batas.
 */
export const bolehDihapus = (dikirim: string, batasJam: number | undefined, sekarang = Date.now()): boolean =>
  !batasJam || sekarang - new Date(dikirim).getTime() <= batasJam * MS_PER_JAM;

/**
 * Batas yang berlaku di satu ruang: di kanal Announcements tidak ada, karena
 * penulis boleh menghapus pengumumannya kapan pun (`ChatPesanEndpoint._batas_jam`).
 * Hapus dan sunting tetap hanya ditawarkan untuk pesan sendiri.
 */
export const batasHapusRuang = (
  batasJam: number | undefined,
  kunciSistem: string | null | undefined
): number | undefined => (kunciSistem === "pengumuman" ? 0 : batasJam);
