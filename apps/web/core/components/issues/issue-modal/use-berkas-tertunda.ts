/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: berkas yang ditempel/diseret ke dialog "buat work item"
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useState } from "react";
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { useFileSize } from "@/hooks/use-file-size";

const BYTES_PER_MB = 1024 * 1024;

const kunciBerkas = (file: File) => `${file.name}:${file.size}:${file.lastModified}`;

/**
 * Work item yang sedang dibuat belum punya id, jadi berkas non-gambar yang
 * ditempel atau diseret ke dialog tidak bisa langsung jadi lampiran. Berkas
 * ditampung di sini dan diunggah sebagai lampiran sesudah work item berhasil dibuat
 * (`IssueModalBase.handleCreateIssue`).
 *
 * Berkas yang melewati batas ukuran ditolak SAAT ditambahkan, bukan sesudah
 * work item dibuat: orang yang menunggu unggahan gagal baru tahu setelah
 * dialognya tertutup.
 */
export const useBerkasTertunda = () => {
  const { t } = useTranslation();
  const { maxFileSize } = useFileSize();
  const [berkas, setBerkas] = useState<File[]>([]);

  const tambah = useCallback(
    (files: File[]) => {
      const layak = files.filter((file) => {
        if (file.size <= maxFileSize) return true;
        setToast({
          type: TOAST_TYPE.ERROR,
          title: t("navigasi_lampiran_ui.too_large", {
            name: file.name,
            size: Math.round(maxFileSize / BYTES_PER_MB),
          }),
        });
        return false;
      });
      if (layak.length === 0) return;
      setBerkas((sebelumnya) => {
        const ada = new Set(sebelumnya.map(kunciBerkas));
        return [...sebelumnya, ...layak.filter((file) => !ada.has(kunciBerkas(file)))];
      });
    },
    [maxFileSize, t]
  );

  const hapus = useCallback((file: File) => setBerkas((sebelumnya) => sebelumnya.filter((item) => item !== file)), []);
  const kosongkan = useCallback(() => setBerkas([]), []);

  return { berkas, tambah, hapus, kosongkan };
};
