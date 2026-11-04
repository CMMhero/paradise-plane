/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: lampiran Obrolan (pilih, tempel, seret)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu pintu untuk ketiga cara menambah lampiran: tombol klip, tempel (Ctrl+V)
 * gambar/berkas di kotak tulis, dan seret berkas ke area percakapan. Ketiganya
 * lewat `tambah(files)`, jadi batas jumlah, batas ukuran, dan kemajuan unggah
 * cuma ditulis di sini.
 *
 * Batasnya cermin server: maksimal BATAS_LAMPIRAN berkas per pesan
 * (`BATAS_LAMPIRAN` di views/chat.py) dan ukuran `file_size_limit` instance.
 * Tipe berkas TIDAK dicek di sini: daftar tipe sah hidup di server
 * (`ATTACHMENT_MIME_TYPES`), dan pesan galatnya diteruskan apa adanya.
 */

import { useCallback, useRef, useState } from "react";
import { EFileAssetType } from "@plane/types";
import { useFileSize } from "@/hooks/use-file-size";
import { DEFAULT_CHAT_ATTACHMENTS_MAX, useParadiseLimits } from "@/hooks/use-paradise-limits";
import { FileService } from "@/services/file.service";
import { pilahBerkas, type TPenolakan } from "./berkas-lampiran";

const fileService = new FileService();

export { BATAS_LAMPIRAN, berkasDariTempel, seretBerkas } from "./berkas-lampiran";
export type { TPenolakan } from "./berkas-lampiran";

export type TLampiranSiap = { id: string; nama: string; ukuran: number };
export type TLampiranNaik = { kunci: string; nama: string; ukuran: number; persen: number };

type Opsi = {
  slug: string | undefined;
  onTolak: (penolakan: TPenolakan[], maksUkuran: number) => void;
  onGagal: (gagal: number, total: number, pesan?: string) => void;
};

export function useUnggahLampiran({ slug, onTolak, onGagal }: Opsi) {
  const { maxFileSize } = useFileSize();
  const maksJumlah = useParadiseLimits().chat_attachments_max ?? DEFAULT_CHAT_ATTACHMENTS_MAX;
  const [siap, setSiap] = useState<TLampiranSiap[]>([]);
  const [naik, setNaik] = useState<TLampiranNaik[]>([]);
  const urutRef = useRef(0);
  // Jumlah terkini dibaca lewat ref: tempel cepat dua kali terjadi sebelum render.
  const jumlahRef = useRef(0);
  // oxlint-disable-next-line react/refs -- latest-count ref read by async paste/drop handlers
  jumlahRef.current = siap.length + naik.length;

  const tambah = useCallback(
    async (masuk: File[] | FileList | null) => {
      if (!slug || !masuk) return;
      const { terima, tolak } = pilahBerkas(Array.from(masuk), jumlahRef.current, maxFileSize, maksJumlah);
      if (tolak.length > 0) onTolak(tolak, maxFileSize);
      if (terima.length === 0) return;
      jumlahRef.current += terima.length;

      const tugas = terima.map((f) => ({ f, kunci: `naik-${(urutRef.current += 1)}` }));
      setNaik((lama) => [
        ...lama,
        ...tugas.map(({ f, kunci }) => ({ kunci, nama: f.name, ukuran: f.size, persen: 0 })),
      ]);

      const hasil = await Promise.allSettled(
        tugas.map(async ({ f, kunci }) => {
          try {
            // entity_identifier kosong: pesannya belum ada. Server menempelkannya
            // saat pesan terkirim, dan hanya menerima berkas milik pengunggahnya.
            const res = await fileService.uploadWorkspaceAsset(
              slug,
              { entity_identifier: "", entity_type: EFileAssetType.CHAT_ATTACHMENT },
              f,
              (ev) => {
                const persen = ev.total ? Math.round((ev.loaded / ev.total) * 100) : 0;
                setNaik((lama) => lama.map((n) => (n.kunci === kunci ? { ...n, persen } : n)));
              }
            );
            setSiap((lama) => [...lama, { id: res.asset_id, nama: f.name, ukuran: f.size }]);
          } finally {
            setNaik((lama) => lama.filter((n) => n.kunci !== kunci));
          }
        })
      );
      const gagal = hasil.filter((h): h is PromiseRejectedResult => h.status === "rejected");
      if (gagal.length > 0) {
        const alasan = (gagal[0].reason as { error?: string } | undefined)?.error;
        onGagal(gagal.length, hasil.length, alasan);
      }
    },
    [slug, maxFileSize, maksJumlah, onTolak, onGagal]
  );

  const buang = useCallback((id: string) => setSiap((lama) => lama.filter((l) => l.id !== id)), []);
  const kosongkan = useCallback(() => setSiap([]), []);

  return { siap, naik, mengunggah: naik.length > 0, tambah, buang, kosongkan, maxFileSize, maksJumlah };
}
