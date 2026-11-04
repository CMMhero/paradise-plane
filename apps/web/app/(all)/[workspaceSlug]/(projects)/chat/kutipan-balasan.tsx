/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kutipan pesan yang dibalas
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { X } from "lucide-react";
import { cn } from "@plane/utils";

type Props = {
  nama: string;
  /** Teks kutipan, sudah diterjemahkan ("Lampiran", "Pesan dihapus") bila perlu. */
  isi: string;
  /** Di atas gelembung berwarna aksen (pesan saya): pakai warna terang. */
  terang?: boolean;
  /** Cetak miring, untuk pesan asli yang sudah dihapus. */
  miring?: boolean;
  /** Klik kutipan (lompat ke pesan asli). Tanpa ini kutipan bukan tombol. */
  onBuka?: () => void;
  /** Tombol batal di sudut kanan, dipakai kotak tulis. */
  onBatal?: () => void;
  labelBatal?: string;
  className?: string;
};

/**
 * Satu-satunya rupa kutipan balasan, dipakai gelembung pesan dan kotak tulis
 * supaya keduanya tidak bisa berbeda.
 *
 * Garis aksen adalah anak absolut yang dipotong `overflow-hidden` pada kotak
 * bersudut bulat, jadi ia hanya mengikuti sudut luar kotak dan ujung dalamnya
 * lurus. Jangan beri garis itu `rounded-*` sendiri.
 */
export function KutipanBalasan(props: Props) {
  const { nama, isi, terang = false, miring = false, onBuka, onBatal, labelBatal } = props;
  const latar = terang ? "bg-black/15" : "bg-accent-subtle";
  const latarHover = terang ? "hover:bg-black/25" : "hover:bg-accent-subtle-hover";

  const isiKutipan = (
    <>
      <span className={cn("block truncate text-12 font-semibold", terang ? "text-on-color" : "text-accent-primary")}>
        {nama}
      </span>
      <span className={cn("line-clamp-2 text-12", terang ? "text-on-color/70" : "text-tertiary", miring && "italic")}>
        {isi}
      </span>
    </>
  );
  const gayaIsi = cn("block w-full py-1 pl-3 text-left", onBatal ? "pr-8" : "pr-2");

  return (
    <div
      className={cn(
        "relative block w-full overflow-hidden rounded-item transition-colors",
        latar,
        onBuka && latarHover,
        props.className
      )}
    >
      <span aria-hidden className={cn("absolute inset-y-0 left-0 w-1", terang ? "bg-white/80" : "bg-accent-primary")} />
      {onBuka ? (
        <button type="button" onClick={onBuka} className={gayaIsi}>
          {isiKutipan}
        </button>
      ) : (
        <div className={gayaIsi}>{isiKutipan}</div>
      )}
      {onBatal ? (
        <button
          type="button"
          onClick={onBatal}
          aria-label={labelBatal}
          className="absolute top-1 right-1 rounded-button p-1 text-tertiary hover:text-primary"
        >
          <X className="size-3.5" />
        </button>
      ) : null}
    </div>
  );
}
