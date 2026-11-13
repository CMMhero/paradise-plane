/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: penentuan tipe MIME unggahan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Fungsi murni, tanpa impor selain konstanta: diperiksa lewat tsx
 * (file-type.check.ts) dan dipakai bersama oleh editor, layanan unggah, dan web.
 */

import { DANGEROUS_EXTENSIONS } from "./file";

/**
 * Tipe tebakan dari ekstensi. Semua nilainya HARUS ada di
 * `ATTACHMENT_MIME_TYPES` server (apps/api/plane/settings/common.py).
 *
 * Kenapa perlu: `File.type` dari peramban diisi dari registri sistem operasi,
 * jadi `.md`, `.csv`, `.mkv`, `.7z`, `.log` bisa kosong di satu komputer dan
 * terisi di komputer lain. Pembacaan tanda tangan biner (file-type) tidak
 * mengenali berkas teks sama sekali dan menjawab `application/x-cfb` untuk
 * .doc/.xls/.ppt. Tanpa tabel ini, berkas yang sama bisa naik di satu mesin
 * dan ditolak di mesin lain.
 */
export const EXTENSION_MIME_TYPES: Readonly<Record<string, string>> = {
  // teks
  txt: "text/plain",
  log: "text/plain",
  md: "text/markdown",
  markdown: "text/markdown",
  csv: "text/csv",
  json: "application/json",
  xml: "application/xml",
  css: "text/css",
  js: "text/javascript",
  sql: "application/x-sql",
  rtf: "application/rtf",
  // dokumen
  pdf: "application/pdf",
  doc: "application/msword",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  xls: "application/vnd.ms-excel",
  xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  ppt: "application/vnd.ms-powerpoint",
  pptx: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  odt: "application/vnd.oasis.opendocument.text",
  ods: "application/vnd.oasis.opendocument.spreadsheet",
  odp: "application/vnd.oasis.opendocument.presentation",
  // gambar
  png: "image/png",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  gif: "image/gif",
  webp: "image/webp",
  bmp: "image/bmp",
  tif: "image/tiff",
  tiff: "image/tiff",
  svg: "image/svg+xml",
  // audio
  mp3: "audio/mpeg",
  wav: "audio/wav",
  ogg: "audio/ogg",
  flac: "audio/flac",
  aac: "audio/aac",
  m4a: "audio/x-m4a",
  mid: "audio/midi",
  midi: "audio/midi",
  // video
  mp4: "video/mp4",
  mpeg: "video/mpeg",
  mpg: "video/mpeg",
  webm: "video/webm",
  mov: "video/quicktime",
  avi: "video/x-msvideo",
  wmv: "video/x-ms-wmv",
  mkv: "video/x-matroska",
  // arsip
  zip: "application/zip",
  rar: "application/x-rar-compressed",
  "7z": "application/x-7z-compressed",
  tar: "application/x-tar",
  gz: "application/gzip",
  tgz: "application/gzip",
  // model 3D dan font
  glb: "model/gltf-binary",
  gltf: "model/gltf+json",
  ttf: "font/ttf",
  otf: "font/otf",
  woff: "font/woff",
  woff2: "font/woff2",
};

/**
 * Jawaban pembaca tanda tangan yang terlalu umum untuk dipercaya: wadah ZIP
 * bisa .docx/.xlsx/.jar, wadah CFB bisa .doc/.xls/.ppt/.msg. Untuk ini
 * ekstensi yang menentukan.
 */
const GENERIC_SNIFFED_TYPES: ReadonlySet<string> = new Set([
  "application/x-cfb",
  "application/zip",
  "application/octet-stream",
]);

/** Tipe terakhir bila tidak ada petunjuk sama sekali; server menerimanya. */
export const FALLBACK_UPLOAD_MIME_TYPE = "application/octet-stream";

/** Ekstensi huruf kecil tanpa titik, "" kalau tidak ada. */
export const getFileExtensionLower = (filename: string): string => {
  const dot = filename.lastIndexOf(".");
  if (dot <= 0 || dot === filename.length - 1) return "";
  return filename.slice(dot + 1).toLowerCase();
};

const cleanMime = (value: string | null | undefined): string => (value ?? "").split(";")[0].trim().toLowerCase();

type TResolveArgs = {
  /** nama berkas apa adanya */
  name: string;
  /** `File.type` dari peramban, boleh kosong */
  browserType?: string | null | undefined;
  /** hasil pembacaan tanda tangan biner, boleh kosong */
  sniffedType?: string | null | undefined;
};

/**
 * Menentukan satu tipe MIME untuk sebuah unggahan, dari tiga sumber yang
 * masing-masing bisa kosong atau salah. Urutan: tanda tangan biner yang
 * spesifik, ekstensi, tipe peramban, tanda tangan umum, lalu
 * `application/octet-stream`. Ekstensi berbahaya tidak pernah dapat tipe
 * cadangan: hasilnya dibiarkan apa adanya supaya server yang menolaknya.
 */
export const resolveFileMimeType = ({ name, browserType, sniffedType }: TResolveArgs): string => {
  const sniffed = cleanMime(sniffedType);
  const browser = cleanMime(browserType);
  const extension = getFileExtensionLower(name);

  if (sniffed && !GENERIC_SNIFFED_TYPES.has(sniffed)) return sniffed;

  const byExtension = EXTENSION_MIME_TYPES[extension];
  if (byExtension) return byExtension;

  if (browser && browser !== FALLBACK_UPLOAD_MIME_TYPE) return browser;
  if (sniffed) return sniffed;
  if (DANGEROUS_EXTENSIONS.includes(extension)) return browser;
  return FALLBACK_UPLOAD_MIME_TYPE;
};
