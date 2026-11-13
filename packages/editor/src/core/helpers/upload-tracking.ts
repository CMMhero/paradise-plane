/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pelacak unggahan editor
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { Editor } from "@tiptap/core";
// helpers
import { EFileError } from "@/helpers/file";

/**
 * Pencatat unggahan yang sedang jalan.
 *
 * Dulu setiap node view menulis `uploadInProgress = true/false` langsung. Dua
 * akibatnya: (1) dengan beberapa berkas sekaligus, unggahan pertama yang selesai
 * menurunkan bendera ke false padahal yang lain masih jalan, jadi tombol kirim
 * komentar menyala dan gambar yang belum selesai ikut hilang; (2) bendera itu
 * data biasa, bukan state, jadi tombol kirim/simpan yang membacanya saat render
 * tetap `disabled` (unggahan gagal) atau tetap menyala (unggahan berkas, yang
 * tidak mengubah dokumen) sampai ada hal lain yang memicu render. Penghitung
 * di sini menjaga yang pertama, dan transaksi kosong di akhir membangunkan
 * semua pelanggan `onStateChange` supaya yang kedua ikut benar.
 */
export const trackUploadProgress = (editor: Editor, isUploading: boolean): void => {
  const storage = editor.storage.utility;
  if (!storage) return;
  const next = Math.max(0, (storage.uploadsInFlight ?? 0) + (isUploading ? 1 : -1));
  storage.uploadsInFlight = next;
  storage.uploadInProgress = next > 0;
  if (editor.isDestroyed) return;
  try {
    editor.view.dispatch(editor.state.tr.setMeta("addToHistory", false));
  } catch {
    // the view is gone (the comment was sent while the upload was running); nothing to notify
  }
};

/**
 * Meneruskan kegagalan unggah ke aplikasi tuan rumah (toast), bukan hanya console.
 * Tanpa pengait dari tuan rumah, jatuh ke console supaya tetap terlihat saat debug.
 */
export const reportEditorUploadFailure = (editor: Editor, error: unknown, file: File): void => {
  const report = editor.storage.utility?.onUploadFailure;
  if (report) {
    report(error, file);
    return;
  }
  console.error("Editor upload failed:", file.name, error);
};

const INVALID_FILE_CODES: Record<EFileError, string> = {
  [EFileError.INVALID_FILE_TYPE]: "type_not_allowed",
  [EFileError.FILE_SIZE_TOO_LARGE]: "file_too_large",
  [EFileError.NO_FILE_SELECTED]: "unknown",
};

/**
 * Berkas ditolak sebelum dikirim (tipe atau ukuran). Lewat tuan rumah kalau ada, supaya
 * pesannya diterjemahkan; kalau tidak, `alert` seperti sebelumnya.
 */
export const reportInvalidEditorFile = (editor: Editor, error: EFileError, file: File, message: string): void => {
  const report = editor.storage.utility?.onUploadFailure;
  if (report) {
    report({ error: message, code: INVALID_FILE_CODES[error] }, file);
    return;
  }
  alert(message);
};
