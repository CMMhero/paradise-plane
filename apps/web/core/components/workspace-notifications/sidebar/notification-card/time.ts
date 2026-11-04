/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: waktu ringkas di baris pemberitahuan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

const MENIT = 60;
const JAM = 60 * MENIT;
const HARI = 24 * JAM;
const MINGGU = 7 * HARI;
const BULAN = 30 * HARI;
const TAHUN = 365 * HARI;

const SATUAN: ReadonlyArray<[Intl.RelativeTimeFormatUnit, number]> = [
  ["year", TAHUN],
  ["month", BULAN],
  ["week", MINGGU],
  ["day", HARI],
  ["hour", JAM],
  ["minute", MENIT],
];

const parse = (value: string | undefined): Date | undefined => {
  if (!value) return undefined;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? undefined : date;
};

/**
 * "5 min. ago" / "5 mnt lalu", mengikuti bahasa antarmuka. `calculateTimeAgo`
 * di @plane/utils selalu berbahasa Inggris, jadi baris berbahasa Indonesia
 * dulu berakhiran "about 2 hours ago".
 *
 * Kode bahasa yang tidak dikenal Intl (mis. "ua") jatuh ke bahasa bawaan
 * peramban, bukan melempar.
 */
export const formatRelativeTime = (value: string | undefined, locale: string, now: number = Date.now()): string => {
  const date = parse(value);
  if (!date) return "";
  const selisih = Math.round((date.getTime() - now) / 1000);
  const format = new Intl.RelativeTimeFormat(locale, { numeric: "auto", style: "short" });
  for (const [satuan, detik] of SATUAN) {
    if (Math.abs(selisih) >= detik) return format.format(Math.trunc(selisih / detik), satuan);
  }
  return format.format(0, "minute");
};

/** Tanggal + jam lengkap untuk `title` dan "ditunda sampai". */
export const formatFullDateTime = (value: string | undefined, locale: string): string => {
  const date = parse(value);
  if (!date) return "";
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(date);
};
