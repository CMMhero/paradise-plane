/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: lampiran Obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { FileText } from "lucide-react";
import { API_BASE_URL } from "@plane/constants";
import type { TLampiran } from "@/services/chat.service";

/** Ubah byte jadi angka yang bisa dibaca orang. */
export const ukuranTerbaca = (byte: number): string => {
  if (byte >= 1024 * 1024) return `${(byte / (1024 * 1024)).toFixed(1)} MB`;
  if (byte >= 1024) return `${Math.round(byte / 1024)} KB`;
  return `${byte} B`;
};

type Props = { lampiran: TLampiran[]; terang?: boolean };

/** Lampiran satu pesan.
 *
 * Gambar dan video ditampilkan langsung; sisanya jadi tautan bernama. Berkas
 * yang tidak bisa dipratinjau tetap harus kelihatan namanya, karena "lampiran"
 * tanpa keterangan apa pun membuat orang harus mengunduhnya dulu untuk tahu itu
 * apa.
 */
export function DaftarLampiran({ lampiran, terang }: Props) {
  if (lampiran.length === 0) return null;

  const warnaTeks = terang ? "text-white/80" : "text-tertiary";
  const warnaKotak = terang ? "border-white/30" : "border-subtle";

  return (
    <div className="mt-1.5 flex flex-col gap-1.5">
      {lampiran.map((l) => {
        const url = `${API_BASE_URL}${l.url}`;
        if (l.tipe.startsWith("image/"))
          return (
            <a key={l.id} href={url} target="_blank" rel="noopener noreferrer">
              <img src={url} alt={l.nama} className="max-h-64 max-w-full rounded-md" loading="lazy" />
            </a>
          );
        if (l.tipe.startsWith("video/"))
          // eslint-disable-next-line jsx-a11y/media-has-caption
          return <video key={l.id} src={url} controls className="max-h-64 max-w-full rounded-md" preload="metadata" />;
        return (
          <a
            key={l.id}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className={`flex items-center gap-2 rounded-md border px-2.5 py-2 ${warnaKotak}`}
          >
            <FileText className="size-4 shrink-0" />
            <span className="min-w-0 flex-1">
              <span className="text-xs block truncate font-medium">{l.nama || "Berkas"}</span>
              <span className={`text-xs ${warnaTeks}`}>{ukuranTerbaca(l.ukuran)}</span>
            </span>
          </a>
        );
      })}
    </div>
  );
}
