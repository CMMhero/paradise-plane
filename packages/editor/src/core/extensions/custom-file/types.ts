/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: node berkas non-gambar
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { Node } from "@tiptap/core";
// types
import type { TFileHandler } from "@/types";

/**
 * Sengaja TIDAK ada atribut `status`. Node gambar punya satu karena ia melacak
 * duplikasi; di sini `src` sudah cukup jadi sumber kebenaran (ada = terunggah)
 * dan progres unggah dipegang state lokal useUploader. Atribut status akan jadi
 * state mati yang tetap ikut tersinkron ke semua kolaborator lewat Yjs.
 */
export enum ECustomFileAttributeNames {
  ID = "id",
  SOURCE = "src",
  NAME = "name",
  SIZE = "size",
  TYPE = "type",
}

export type TCustomFileAttributes = {
  [ECustomFileAttributeNames.ID]: string | null;
  [ECustomFileAttributeNames.SOURCE]: string | null;
  [ECustomFileAttributeNames.NAME]: string | null;
  /** ukuran dalam byte; disimpan supaya kartu tidak perlu memanggil server */
  [ECustomFileAttributeNames.SIZE]: number | null;
  /** MIME type; menentukan bentuk pratinjau. Boleh null - node lama tidak
   *  punya atribut ini, jadi tipenya ditebak dari ekstensi berkas. */
  [ECustomFileAttributeNames.TYPE]: string | null;
};

export type UploadEntity = ({ event: "insert" } | { event: "drop"; file: File }) & {
  hasOpenedFileInputOnce?: boolean;
};

export type InsertFileComponentProps = {
  file?: File;
  pos?: number;
  event: "insert" | "drop";
};

export type CustomFileExtensionOptions = {
  /** URL yang memaksa unduh - dipakai tombol Download */
  getFileDownloadSource: TFileHandler["getAssetDownloadSrc"];
  /** URL untuk ditampilkan di halaman - dipakai pemutar & pratinjau */
  getFileSource: TFileHandler["getAssetSrc"];
  uploadFile?: TFileHandler["upload"];
};

export type CustomFileExtensionStorage = {
  fileMap: Map<string, UploadEntity>;
  maxFileSize: number;
};

export type CustomFileExtensionType = Node<CustomFileExtensionOptions, CustomFileExtensionStorage>;
