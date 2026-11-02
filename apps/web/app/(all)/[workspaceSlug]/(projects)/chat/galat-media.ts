/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: sebab gagalnya mikrofon & kamera
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Menerjemahkan kegagalan mengambil mikrofon atau kamera menjadi kalimat yang
 * menyebut apa yang harus dilakukan orangnya.
 *
 * KENAPA INI ADA. Panggilan 18 Agt gagal berulang kali dan layar selalu menulis
 * "Gagal menyambung ke server panggilan. Periksa jaringan kantor." Kalimat itu
 * SALAH: sambungan ke server sudah berhasil, log LiveKit mencatat peserta masuk
 * lalu keluar sendiri dalam 40 milidetik tanpa pernah menerbitkan satu track pun.
 * Yang gagal adalah getUserMedia di komputer orang itu, dan penyebabnya tidak
 * pernah sampai ke layar karena satu blok catch menelan dua kegagalan yang sangat
 * berbeda. Berjam-jam habis untuk mencari bug jaringan yang tidak pernah ada.
 *
 * `konteksAman` = `window.isSecureContext`. Diminta sebagai argumen, bukan dibaca
 * di dalam, supaya fungsinya murni dan bisa diperiksa tanpa DOM.
 */
export type TTerjemah = (key: string, params?: Record<string, unknown>) => string;

export function pesanGalatMedia(galat: unknown, konteksAman: boolean, t: TTerjemah): string {
  // Didahulukan dari nama galat apa pun. Di halaman http:// peramban tidak
  // menolak izinnya, ia meniadakan `navigator.mediaDevices` sama sekali,
  // sehingga galatnya TypeError yang tidak menyebut-nyebut mikrofon. Server
  // masih melayani http di IP lama, jadi jalur ini benar-benar bisa dilalui.
  if (!konteksAman) return t("chat_ui.media_error.insecure");

  switch ((galat as { name?: string })?.name) {
    case "NotAllowedError":
    case "SecurityError":
      return t("chat_ui.media_error.denied");
    case "NotFoundError":
    case "OverconstrainedError":
      return t("chat_ui.media_error.not_found");
    case "NotReadableError":
      return t("chat_ui.media_error.in_use");
    default:
      return t("chat_ui.media_error.unknown", {
        reason: (galat as { name?: string })?.name ?? t("chat_ui.media_error.unknown_reason"),
      });
  }
}
