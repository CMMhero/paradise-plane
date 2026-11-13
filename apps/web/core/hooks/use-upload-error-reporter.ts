/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: satu pintu pesan galat unggah
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback } from "react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { getUploadErrorI18nKey, normalizeUploadError } from "@plane/services";
// hooks
import { useFileSize } from "@/hooks/use-file-size";

export type TUploadFailureContext = {
  /** nama berkas untuk judul toast */
  name?: string;
  /** batas ukuran yang dipakai di pesan; bawaannya batas instance */
  maxFileSize?: number;
};

export type TUploadFailureText = {
  /** true bila pengguna sendiri yang membatalkan; tidak perlu ditampilkan */
  isCancelled: boolean;
  title: string;
  message: string;
};

const BYTES_PER_MB = 1024 * 1024;

/**
 * Mengubah galat unggah apa pun menjadi teks siap tampil (diterjemahkan), tanpa
 * menampilkannya. Dipakai langsung oleh toast promise lampiran, dan oleh
 * `useUploadErrorReporter` di bawah.
 */
export const useUploadFailureText = () => {
  const { t } = useTranslation();
  const { maxFileSize: instanceMaxFileSize } = useFileSize();

  return useCallback(
    (raw: unknown, context: TUploadFailureContext = {}): TUploadFailureText => {
      // host wrappers rethrow a generic Error with the real failure as `cause`
      const error = normalizeUploadError(raw instanceof Error && raw.cause ? raw.cause : raw);
      const key = getUploadErrorI18nKey(error.code);
      const size = Math.floor((context.maxFileSize ?? instanceMaxFileSize) / BYTES_PER_MB);
      return {
        isCancelled: error.code === "cancelled",
        title: context.name ? t("unggah_ui.failed_title", { name: context.name }) : t("unggah_ui.failed_generic_title"),
        // kuota dan penolakan membawa alasan spesifik dari API; sisanya memakai terjemahan
        message: key ? t(key, { size }) : error.error || t("unggah_ui.generic"),
      };
    },
    [t, instanceMaxFileSize]
  );
};

/**
 * Menampilkan toast galat unggah dari galat apa pun yang tertangkap.
 *
 * Semua pintu unggah (tombol, seret-lepas, tempel; komentar, obrolan, deskripsi,
 * lampiran) memakai ini, jadi kegagalan tidak pernah lagi hanya berakhir di
 * console.error. Pembatalan oleh pengguna sengaja diam.
 */
export const useUploadErrorReporter = () => {
  const describe = useUploadFailureText();

  return useCallback(
    (raw: unknown, context: TUploadFailureContext = {}) => {
      const text = describe(raw, context);
      if (text.isCancelled) return;
      setToast({ type: TOAST_TYPE.ERROR, title: text.title, message: text.message });
    },
    [describe]
  );
};
