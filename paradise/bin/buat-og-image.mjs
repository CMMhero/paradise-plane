#!/usr/bin/env node
// Copyright (c) 2023-present Plane Software, Inc. and contributors
// SPDX-License-Identifier: AGPL-3.0-only
// See the LICENSE file for details.
/**
 * Potret gambar pratinjau tautan (Open Graph) dari paradise/bin/og-image.html.
 *
 * Gambar ini muncul tiap kali tautan aplikasi dibagikan di WhatsApp, Slack,
 * Teams, atau Discord. Ia digambar dari HTML, bukan Pillow, supaya memakai font
 * dan token warna yang SAMA dengan aplikasi (Plus Jakarta Sans, Geist Mono,
 * skema Bara) dan dirender oleh mesin yang sama dengan peramban.
 *
 * Pakai:  node paradise/bin/buat-og-image.mjs
 * Hasil:  apps/web/app/assets/og-image.png (1200x630)
 *
 * Butuh Chrome, Edge, atau Chromium. Lokasinya dicari otomatis, atau setel
 * CHROME_PATH. Font diambil dari node_modules apps/web, jadi jalankan
 * `pnpm install` dulu.
 */

import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const AKAR = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const WEB = join(AKAR, "apps/web");
const KELUAR = join(WEB, "app/assets/og-image.png");

// 1200x630 adalah ukuran Open Graph yang dipakai WhatsApp, Slack, Teams, dan
// X. Rasio yang meleset akan dipotong sembarangan oleh mereka.
const LEBAR = 1200;
const TINGGI = 630;

const ASET = {
  FONT_UI: join(
    WEB,
    "node_modules/@fontsource-variable/plus-jakarta-sans/files/plus-jakarta-sans-latin-wght-normal.woff2"
  ),
  FONT_MONO: join(WEB, "node_modules/@fontsource-variable/geist-mono/files/geist-mono-latin-wght-normal.woff2"),
  LOGO: join(WEB, "app/assets/images/paradise-logo.png"),
};

const CALON_CHROME = [
  process.env.CHROME_PATH,
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
];

function gagal(pesan) {
  console.error(pesan);
  process.exit(1);
}

function cariChrome() {
  const ketemu = CALON_CHROME.find((p) => p && existsSync(p));
  if (!ketemu) gagal("Chrome/Edge/Chromium tidak ditemukan. Setel CHROME_PATH.");
  return ketemu;
}

/** Lebar dan tinggi dari kepala IHDR PNG, untuk memastikan potretnya tidak meleset. */
function ukuranPng(berkas) {
  const b = readFileSync(berkas);
  return { lebar: b.readUInt32BE(16), tinggi: b.readUInt32BE(20) };
}

function main() {
  // Gagal terang-terangan kalau font hilang: peramban diam-diam jatuh ke font
  // sistem dan gambarnya tampak hampir benar, itu lebih buruk dari error.
  for (const [nama, berkas] of Object.entries(ASET)) {
    if (!existsSync(berkas)) gagal(`${nama} tidak ditemukan: ${berkas}\nJalankan pnpm install dulu.`);
  }

  let html = readFileSync(join(AKAR, "paradise/bin/og-image.html"), "utf8");
  for (const [nama, berkas] of Object.entries(ASET)) {
    html = html.replaceAll(`{{${nama}}}`, pathToFileURL(berkas).href);
  }

  const kerja = mkdtempSync(join(tmpdir(), "og-image-"));
  try {
    const halaman = join(kerja, "og-image.html");
    writeFileSync(halaman, html);
    execFileSync(
      cariChrome(),
      [
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        "--allow-file-access-from-files",
        // Beri waktu font selesai dimuat sebelum dipotret.
        "--virtual-time-budget=3000",
        `--user-data-dir=${join(kerja, "profil")}`,
        `--window-size=${LEBAR},${TINGGI}`,
        `--screenshot=${KELUAR}`,
        pathToFileURL(halaman).href,
      ],
      { stdio: "pipe" }
    );
  } finally {
    rmSync(kerja, { recursive: true, force: true });
  }

  const { lebar, tinggi } = ukuranPng(KELUAR);
  if (lebar !== LEBAR || tinggi !== TINGGI) gagal(`ukuran meleset: ${lebar}x${tinggi}, seharusnya ${LEBAR}x${TINGGI}`);
  console.log(`ditulis: ${relative(AKAR, KELUAR)} (${statSync(KELUAR).size} byte, ${lebar}x${tinggi})`);
}

main();
