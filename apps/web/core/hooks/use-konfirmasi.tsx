/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: konfirmasi sebelum aksi yang merusak
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
import { useCallback, useState } from "react";
import { useTranslation } from "@plane/i18n";
import { AlertModalCore } from "@plane/ui";

export type TOpsiKonfirmasi = {
  judul: string;
  isi: ReactNode;
  /** Teks tombol utama; bawaan "Delete". */
  tombol?: string;
  /** Teks tombol utama selama aksi berjalan; bawaan "Deleting". */
  tombolProses?: string;
};

type TPermintaan = TOpsiKonfirmasi & { aksi: () => Promise<unknown> | void };

/**
 * Satu dialog konfirmasi yang bisa dipakai banyak tombol di satu layar.
 *
 * Di layar sentuh, tombol hapus yang kecil gampang tersentuh tanpa sengaja,
 * dan beberapa yang dihapus (pesan chat) tidak masuk Trash. Pemanggil cukup
 * membungkus aksinya: `minta({ judul, isi }, () => hapus(x))`, lalu
 * merender `dialog` sekali di mana saja dalam pohonnya.
 *
 * Dialog tertutup sesudah aksi selesai, berhasil atau gagal. Menangani galat
 * (toast) tetap tugas aksinya sendiri, sama seperti tanpa konfirmasi.
 */
export function useKonfirmasi(): {
  minta: (opsi: TOpsiKonfirmasi, aksi: () => Promise<unknown> | void) => void;
  dialog: ReactNode;
} {
  const { t } = useTranslation();
  const [permintaan, setPermintaan] = useState<TPermintaan | null>(null);
  const [terbuka, setTerbuka] = useState(false);
  const [berjalan, setBerjalan] = useState(false);

  const minta = useCallback((opsi: TOpsiKonfirmasi, aksi: () => Promise<unknown> | void) => {
    setPermintaan({ ...opsi, aksi });
    setTerbuka(true);
  }, []);

  const tutup = () => {
    if (!berjalan) setTerbuka(false);
  };

  const jalankan = async () => {
    if (!permintaan || berjalan) return;
    setBerjalan(true);
    try {
      await permintaan.aksi();
    } finally {
      setBerjalan(false);
      setTerbuka(false);
    }
  };

  // `permintaan` sengaja tidak dikosongkan saat ditutup: judul dan isinya
  // tetap dibutuhkan selama animasi keluar modal.
  const dialog = (
    <AlertModalCore
      isOpen={terbuka}
      handleClose={tutup}
      handleSubmit={() => void jalankan()}
      isSubmitting={berjalan}
      title={permintaan?.judul ?? ""}
      content={permintaan?.isi ?? null}
      primaryButtonText={{
        default: permintaan?.tombol ?? t("delete"),
        loading: permintaan?.tombolProses ?? t("deleting"),
      }}
      secondaryButtonText={t("cancel")}
    />
  );

  return { minta, dialog };
}
