/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: notifikasi peramban (sistem operasi)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { getValueFromLocalStorage } from "@/hooks/use-local-storage";

/**
 * Pemberitahuan lewat peramban: kartu Windows/macOS/Android di luar halaman.
 *
 * Berlaku SELAMA TAB PARADISE TERBUKA (boleh di belakang, diminimalkan, atau di
 * tab lain). Peramban yang ditutup butuh Web Push + service worker, dan itu
 * pekerjaan lain (lihat catatan "notifikasi-popup" di vault).
 *
 * Saklarnya per PERAMBAN, bukan per akun, karena izinnya pun per peramban:
 * menyalakan di PC kantor tidak berarti HP ikut mengizinkan.
 */

export const KUNCI_NOTIF_PERAMBAN = "notif_peramban_nyala";

/** Penolakan spanduk izin disimpan, karena menawarkan hal yang sama tiap kali
 * halaman dibuka adalah cara membuat orang membenci fiturnya. Saklar di popup
 * suara ikut menulisnya, supaya spanduk hilang begitu izin diurus dari sana. */
export const KUNCI_SPANDUK = "spanduk_izin_notifikasi_ditutup";

export type TIzinPeramban = NotificationPermission | "tidak-didukung";

export const izinPeramban = (): TIzinPeramban =>
  typeof window !== "undefined" && "Notification" in window ? Notification.permission : "tidak-didukung";

/** Saklar milik orang ini di peramban ini. Bawaan menyala; izin tetap harus diberikan. */
export const notifPerambanNyala = (): boolean => getValueFromLocalStorage(KUNCI_NOTIF_PERAMBAN, true) !== false;

/** Siap mengirim: didukung, diizinkan, dan saklarnya tidak dimatikan. */
export const bisaNotifPeramban = (): boolean => izinPeramban() === "granted" && notifPerambanNyala();

type TIsi = {
  judul: string;
  isi: string;
  /** Pemberitahuan bertag sama MENGGANTI yang lama, bukan menumpuk di Pusat Tindakan. */
  tag: string;
  onKlik?: () => void;
};

/**
 * Tampilkan satu kartu sistem operasi. Mengembalikan `false` kalau gagal.
 *
 * Gagal itu nyata dan diam: Chrome Android MELEMPAR `TypeError: Illegal
 * constructor` untuk `new Notification()` (di sana hanya service worker yang
 * boleh). Pemanggil memakai `false` untuk jatuh ke kartu di dalam aplikasi,
 * supaya pemberitahuannya tetap sampai lewat jalan lain.
 */
export const tampilkanNotifPeramban = ({ judul, isi, tag, onKlik }: TIsi): boolean => {
  if (!bisaNotifPeramban()) return false;
  try {
    const kartu = new Notification(judul, {
      body: isi,
      icon: "/favicon/android-chrome-192x192.png",
      badge: "/favicon/android-chrome-192x192.png",
      tag,
    });
    kartu.addEventListener("click", () => {
      window.focus();
      onKlik?.();
      kartu.close();
    });
    return true;
  } catch {
    return false;
  }
};
