/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: lampiran Obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { useTranslation } from "@plane/i18n";
import { FileText } from "lucide-react";
import { API_BASE_URL } from "@plane/constants";
import { ImageFullScreenModal } from "@plane/editor";
import type { TLampiran } from "@/services/chat.service";

/** Ubah byte jadi angka yang bisa dibaca orang. */
export const ukuranTerbaca = (byte: number): string => {
  if (byte >= 1024 * 1024) return `${(byte / (1024 * 1024)).toFixed(1)} MB`;
  if (byte >= 1024) return `${Math.round(byte / 1024)} KB`;
  return `${byte} B`;
};

type Props = { lampiran: TLampiran[]; terang?: boolean };

/** Layar sentuh: tombol unduh & tab baru disembunyikan, sama seperti di work item. */
const layarSentuh = () => typeof window !== "undefined" && window.matchMedia("(pointer: coarse)").matches;

/**
 * Gambar lampiran yang dibuka di penampil layar penuh milik work item (zoom,
 * geser, Esc/Back untuk menutup), bukan tab baru. Satu penampil untuk seluruh
 * aplikasi, supaya cara melihat gambar tidak perlu dipelajari dua kali.
 */
function GambarLampiran({ url, nama }: { url: string; nama: string }) {
  const [terbuka, setTerbuka] = useState(false);
  const [ukuran, setUkuran] = useState<{ lebar: number; rasio: number }>({ lebar: 0, rasio: 1 });

  return (
    <>
      <button
        type="button"
        className="w-fit cursor-zoom-in rounded-item focus-visible:outline-2 focus-visible:outline-accent-strong"
        onClick={(e) => {
          e.stopPropagation();
          setTerbuka(true);
        }}
        aria-label={nama}
      >
        {/* Tinggi tetap supaya ruangnya sudah tersedia sebelum gambar termuat:
            tanpa itu tiap gambar yang selesai dimuat mendorong isi ke bawah
            dan percakapan tidak lagi berhenti di pesan terbaru. */}
        <img
          src={url}
          alt={nama}
          className="h-48 w-auto max-w-full rounded-item object-contain"
          loading="lazy"
          onLoad={(e) => {
            const { naturalWidth, naturalHeight } = e.currentTarget;
            if (naturalWidth && naturalHeight) setUkuran({ lebar: naturalWidth, rasio: naturalWidth / naturalHeight });
          }}
        />
      </button>
      <ImageFullScreenModal
        aspectRatio={ukuran.rasio}
        downloadSrc={url}
        isFullScreenEnabled={terbuka}
        isTouchDevice={layarSentuh()}
        src={url}
        width={ukuran.lebar ? `${ukuran.lebar}px` : ""}
        toggleFullScreenMode={setTerbuka}
      />
    </>
  );
}

/** Lampiran satu pesan.
 *
 * Gambar dan video ditampilkan langsung; sisanya jadi tautan bernama. Berkas
 * yang tidak bisa dipratinjau tetap harus kelihatan namanya, karena "lampiran"
 * tanpa keterangan apa pun membuat orang harus mengunduhnya dulu untuk tahu itu
 * apa.
 */
export function DaftarLampiran({ lampiran, terang }: Props) {
  const { t } = useTranslation();
  if (lampiran.length === 0) return null;

  const warnaTeks = terang ? "text-on-color/80" : "text-tertiary";
  const warnaKotak = terang ? "border-white/30" : "border-subtle";

  return (
    <div className="mt-1.5 flex flex-col gap-1.5">
      {lampiran.map((l) => {
        const url = `${API_BASE_URL}${l.url}`;
        if (l.tipe.startsWith("image/")) return <GambarLampiran key={l.id} url={url} nama={l.nama} />;
        if (l.tipe.startsWith("video/"))
          return (
            // oxlint-disable-next-line jsx-a11y/media-has-caption -- user-uploaded chat videos have no caption track
            <video
              key={l.id}
              src={url}
              controls
              className="h-48 w-auto max-w-full rounded-item bg-black"
              preload="metadata"
            />
          );
        return (
          <a
            key={l.id}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className={`flex items-center gap-2 rounded-item border px-2.5 py-2 ${warnaKotak}`}
          >
            <FileText className="size-4 shrink-0" />
            <span className="min-w-0 flex-1">
              <span className="block truncate text-12 font-medium">{l.nama || t("chat_ui.file")}</span>
              <span className={`text-12 ${warnaTeks}`}>{ukuranTerbaca(l.ukuran)}</span>
            </span>
          </a>
        );
      })}
    </div>
  );
}
