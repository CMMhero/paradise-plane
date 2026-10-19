/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: node berkas non-gambar
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { Editor } from "@tiptap/core";
// constants
import { CORE_EXTENSIONS } from "@/constants/extension";
// local imports
import type { CustomFileExtensionStorage } from "./types";

export const getFileComponentFileMap = (editor: Editor): CustomFileExtensionStorage["fileMap"] | undefined =>
  editor.storage[CORE_EXTENSIONS.CUSTOM_FILE]?.fileMap;

/**
 * Dibaca dari editor.storage, bukan extension.storage, mengikuti pola node
 * gambar. extension.storage tidak selalu terisi saat node view pertama render.
 */
export const getFileComponentMaxFileSize = (editor: Editor): number =>
  (editor.storage[CORE_EXTENSIONS.CUSTOM_FILE] as { maxFileSize?: number } | undefined)?.maxFileSize ?? 0;

/** bentuk pratinjau yang bisa dirender browser tanpa bantuan server */
export type TFilePreviewKind = "video" | "audio" | "pdf" | "image" | "text" | "none";

const EXTENSION_MIME_FALLBACK: Record<string, string> = {
  pdf: "application/pdf",
  mp4: "video/mp4",
  webm: "video/webm",
  ogv: "video/ogg",
  mov: "video/quicktime",
  mp3: "audio/mpeg",
  wav: "audio/wav",
  m4a: "audio/x-m4a",
  flac: "audio/flac",
  png: "image/png",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  gif: "image/gif",
  webp: "image/webp",
  svg: "image/svg+xml",
  txt: "text/plain",
  csv: "text/csv",
  md: "text/markdown",
  json: "application/json",
  xml: "text/xml",
};

/**
 * Node yang dibuat sebelum atribut `type` ada tidak menyimpan MIME-nya, jadi
 * ditebak dari ekstensi. Tanpa ini, lampiran lama selamanya tampil sebagai
 * kartu polos walau sebenarnya bisa dipratinjau.
 */
export const resolveFileMimeType = (type: string | null, name: string | null): string => {
  // parameter seperti "; charset=utf-8" dibuang supaya pencocokan di bawah tidak
  // meleset dan diam-diam menurunkan berkas yang sebenarnya bisa dipratinjau
  if (type) return type.split(";")[0].trim().toLowerCase();
  const ext = name?.includes(".") ? name.split(".").pop()?.toLowerCase() : undefined;
  return (ext && EXTENSION_MIME_FALLBACK[ext]) || "";
};

/**
 * Tipe teks yang benar-benar DIRENDER Chrome di dalam frame, bukan sekadar
 * "kelihatannya teks". `text/csv` dan `text/markdown` sengaja TIDAK ada di sini:
 * Chrome tak punya renderer untuk keduanya dan mengubah navigasi frame jadi
 * unduhan, jadi bingkainya cuma putih kosong. Diuji langsung dengan berkas
 * nyata: csv kosong di sandbox="", tanpa sandbox, maupun allow-downloads,
 * sementara txt render di semuanya. Tanpa sandbox ia malah mengunduh diam-diam
 * begitu halaman dibuka.
 *
 * Jangan diganti kembali jadi `startsWith("text/")`, itu justru asal masalahnya.
 */
const FRAMEABLE_TEXT_MIME_TYPES = new Set([
  "text/plain",
  "text/css",
  "text/javascript",
  "text/xml",
  "application/xml",
  "application/json",
]);

export const getFilePreviewKind = (mimeType: string): TFilePreviewKind => {
  // Matroska lolos `video/` tapi tidak ada peramban yang memutarnya. Tanpa
  // pengecualian ini pemakai melihat pemutar hitam yang diam saja, dan itu
  // lebih membingungkan daripada kartu unduh yang jujur.
  if (mimeType === "video/x-matroska") return "none";
  if (mimeType.startsWith("video/")) return "video";
  if (mimeType.startsWith("audio/")) return "audio";
  if (mimeType.startsWith("image/")) return "image";
  if (mimeType === "application/pdf") return "pdf";
  if (FRAMEABLE_TEXT_MIME_TYPES.has(mimeType)) return "text";
  // Office, zip, csv, markdown, biner: browser tidak punya renderer-nya
  // -> kartu unduh saja, dengan keterangan terus terang di kartunya
  return "none";
};

/**
 * URL untuk DITAMPILKAN, bukan diunduh. Endpoint aset default membalas
 * Content-Disposition: attachment; pada <iframe> itu memicu unduhan alih-alih
 * render, jadi pratinjau PDF wajib meminta disposition=inline.
 */
export const toInlineSrc = (src: string): string => `${src}${src.includes("?") ? "&" : "?"}disposition=inline`;

const FILE_SIZE_UNITS = ["B", "KB", "MB", "GB"];

/**
 * Ukuran berkas untuk ditampilkan di kartu. Pakai 1024 sebagai basis supaya
 * cocok dengan angka yang dilihat user di Windows Explorer.
 */
export const formatFileSize = (bytes: number | null): string => {
  if (bytes === null || !Number.isFinite(bytes) || bytes < 0) return "";
  let size = bytes;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < FILE_SIZE_UNITS.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  // byte selalu bulat; satuan lebih besar cukup satu desimal
  const rounded = unitIndex === 0 ? String(size) : size.toFixed(1);
  return `${rounded} ${FILE_SIZE_UNITS[unitIndex]}`;
};
