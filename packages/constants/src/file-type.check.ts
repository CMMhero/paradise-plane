/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: penentuan tipe MIME unggahan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Pemeriksaan resolveFileMimeType. Jalankan dari packages/i18n:
 *
 *   cd packages/i18n
 *   pnpm exec tsx ../constants/src/file-type.check.ts
 */

import assert from "node:assert/strict";
import { EXTENSION_MIME_TYPES, getFileExtensionLower, resolveFileMimeType } from "./file-type";

// --- ekstensi ------------------------------------------------------------------
assert.equal(getFileExtensionLower("Laporan.FINAL.XLSX"), "xlsx");
assert.equal(getFileExtensionLower("catatan"), "");
assert.equal(getFileExtensionLower(".env"), "");
assert.equal(getFileExtensionLower("akhir."), "");

// --- tanda tangan biner yang spesifik menang -----------------------------------
assert.equal(resolveFileMimeType({ name: "foto.png", browserType: "", sniffedType: "image/jpeg" }), "image/jpeg");

// --- teks tidak punya tanda tangan: ekstensi menyelamatkan ---------------------
assert.equal(resolveFileMimeType({ name: "catatan.md", browserType: "", sniffedType: "" }), "text/markdown");
assert.equal(resolveFileMimeType({ name: "data.csv", browserType: "", sniffedType: "" }), "text/csv");
assert.equal(resolveFileMimeType({ name: "rekaman.MKV", browserType: "", sniffedType: "" }), "video/x-matroska");

// --- wadah umum: ekstensi menentukan -------------------------------------------
assert.equal(
  resolveFileMimeType({ name: "angka.xlsx", browserType: "", sniffedType: "application/zip" }),
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
);
assert.equal(
  resolveFileMimeType({ name: "lama.xls", browserType: "", sniffedType: "application/x-cfb" }),
  "application/vnd.ms-excel"
);
assert.equal(
  resolveFileMimeType({ name: "arsip.zip", browserType: "", sniffedType: "application/zip" }),
  "application/zip"
);

// --- peramban hanya dipakai bila ekstensi tidak dikenal ------------------------
assert.equal(resolveFileMimeType({ name: "model.step", browserType: "model/step", sniffedType: "" }), "model/step");
assert.equal(
  resolveFileMimeType({ name: "angka.xlsx", browserType: "application/octet-stream", sniffedType: "" }),
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
);

// --- tanpa petunjuk sama sekali ------------------------------------------------
assert.equal(
  resolveFileMimeType({ name: "tanpa-ekstensi", browserType: "", sniffedType: "" }),
  "application/octet-stream"
);
assert.equal(
  resolveFileMimeType({ name: "aneh.xyz", browserType: null, sniffedType: undefined }),
  "application/octet-stream"
);

// --- parameter tipe dibuang, huruf dinormalkan ---------------------------------
assert.equal(
  resolveFileMimeType({ name: "x.bin", browserType: "Text/Plain; charset=utf-8", sniffedType: "" }),
  "text/plain"
);

// --- ekstensi berbahaya tidak diberi tipe cadangan (server yang menolak) -------
assert.equal(resolveFileMimeType({ name: "pasang.exe", browserType: "", sniffedType: "" }), "");
assert.equal(
  resolveFileMimeType({ name: "pasang.exe", browserType: "application/x-msdownload", sniffedType: "" }),
  "application/x-msdownload"
);

// --- kontrol negatif: tabel tidak boleh memuat tipe yang tak dikenal server ----
const TIPE_SERVER_DIKENAL = /^(text|image|audio|video|font|model|application)\/[\w.+-]+$/;
for (const [ekstensi, tipe] of Object.entries(EXTENSION_MIME_TYPES)) {
  assert.match(tipe, TIPE_SERVER_DIKENAL, `tipe untuk .${ekstensi} tidak valid`);
}

console.log("file-type.check.ts: semua lolos");
