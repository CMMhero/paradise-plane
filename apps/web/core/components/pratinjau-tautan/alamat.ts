/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: alamat yang layak dipratinjau (KEP-88)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/** Batas kartu per blok teks: lebih dari ini, deskripsi berubah jadi galeri tautan. */
export const MAKS_KARTU = 3;

const POLA_TEKS = /https?:\/\/[^\s<>"']+/g;
const EKOR = /[.,;:!?)\]}]+$/;

const layak = (alamat: string): boolean => {
  try {
    const url = new URL(alamat);
    if (url.protocol !== "http:" && url.protocol !== "https:") return false;
    // Tautan ke aplikasi ini sendiri (work item, aset) sudah punya tampilannya sendiri.
    return typeof window === "undefined" || url.origin !== window.location.origin;
  } catch {
    return false;
  }
};

const unik = (daftar: string[], maks: number): string[] => [...new Set(daftar.filter(layak))].slice(0, maks);

/** Alamat dari teks biasa (chat), tanda baca penutup kalimat dibuang. */
export const alamatDariTeks = (teks: string, maks = MAKS_KARTU): string[] =>
  unik(
    (teks.match(POLA_TEKS) ?? []).map((a) => a.replace(EKOR, "")),
    maks
  );

/** Alamat dari `<a href>` di HTML editor (deskripsi, komentar). */
export const alamatDariHtml = (html: string | null | undefined, maks = MAKS_KARTU): string[] => {
  if (!html || typeof DOMParser === "undefined") return [];
  const dok = new DOMParser().parseFromString(html, "text/html");
  const tertaut = Array.from(dok.querySelectorAll("a[href]"), (a) => a.getAttribute("href")?.trim() ?? "");
  // URL polos di teks (belum diberi mark tautan oleh editor) ikut, sama seperti turunan di backend.
  const polos: string[] = [];
  const penjelajah = dok.createTreeWalker(dok.body, NodeFilter.SHOW_TEXT);
  for (let simpul = penjelajah.nextNode(); simpul; simpul = penjelajah.nextNode()) {
    if (simpul.parentElement?.closest("a, code, pre")) continue;
    polos.push(...alamatDariTeks(simpul.textContent ?? "", Number.MAX_SAFE_INTEGER));
  }
  return unik([...tertaut, ...polos], maks);
};
