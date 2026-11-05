/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kartu pratinjau tautan (KEP-88)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { LinkIcon } from "@plane/propel/icons";
import { cn } from "@plane/utils";
import { PratinjauTautanService } from "@/services/pratinjau-tautan.service";
import type { TPratinjauTautan } from "@/services/pratinjau-tautan.service";
import { alamatDariHtml, alamatDariTeks } from "./alamat";

const layanan = new PratinjauTautanService();
/** Server meng-cache 24 jam; di peramban cukup satu ambil per sesi per alamat. */
const SATU_JAM_MS = 60 * 60 * 1000;

/** Isi kartu untuk satu alamat. `undefined` selama memuat atau bila gagal. */
export function usePratinjauTautan(url: string | undefined): TPratinjauTautan | undefined {
  const { workspaceSlug } = useParams<{ workspaceSlug?: string }>();
  const { data } = useSWR(
    url && workspaceSlug ? ["pratinjau-tautan", workspaceSlug, url] : null,
    () => layanan.ambil(workspaceSlug!, url!),
    { revalidateOnFocus: false, revalidateIfStale: false, dedupingInterval: SATU_JAM_MS, shouldRetryOnError: false }
  );
  return data;
}

type KartuProps = {
  url: string;
  /** Di atas gelembung chat berwarna aksen: teks putih, garis tembus. */
  terang?: boolean;
  className?: string;
};

/**
 * Kartu ala Open Graph: gambar, nama situs, judul, ringkasan.
 *
 * Tidak menampilkan apa pun selama memuat atau bila situs tidak punya metadata,
 * supaya tautan mati tidak meninggalkan kotak kosong. Gambar dimuat langsung oleh
 * peramban dari situs asalnya; kalau gagal (hotlink ditolak), gambarnya saja yang
 * disembunyikan.
 */
export function KartuPratinjauTautan({ url, terang, className }: KartuProps) {
  const kartu = usePratinjauTautan(url);
  const [gambarGagal, setGambarGagal] = useState(false);
  const [ikonGagal, setIkonGagal] = useState(false);
  if (!kartu || kartu.kosong) return null;

  const gambar = kartu.image && !gambarGagal ? kartu.image : null;
  const ikon = kartu.favicon && !ikonGagal ? kartu.favicon : null;

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      onClick={(e) => e.stopPropagation()}
      className={cn(
        "group flex max-w-md overflow-hidden rounded-item border transition-colors",
        terang ? "border-white/30 bg-white/10 hover:bg-white/15" : "border-subtle bg-layer-1 hover:bg-layer-1-hover",
        className
      )}
    >
      {gambar && (
        <img
          src={gambar}
          alt=""
          loading="lazy"
          referrerPolicy="no-referrer"
          onError={() => setGambarGagal(true)}
          className="h-auto w-24 shrink-0 self-stretch object-cover sm:w-28"
        />
      )}
      <span className="flex min-w-0 flex-1 flex-col gap-0.5 px-3 py-2">
        <span className={cn("flex items-center gap-1.5 text-11", terang ? "text-on-color/80" : "text-tertiary")}>
          {ikon ? (
            <img
              src={ikon}
              alt=""
              loading="lazy"
              referrerPolicy="no-referrer"
              onError={() => setIkonGagal(true)}
              className="size-3.5 shrink-0 rounded-sm"
            />
          ) : (
            <LinkIcon className="size-3.5 shrink-0" />
          )}
          <span className="truncate">{kartu.site_name}</span>
        </span>
        {kartu.title && (
          <span className={cn("line-clamp-2 text-13 font-medium", terang ? "text-on-color" : "text-primary")}>
            {kartu.title}
          </span>
        )}
        {kartu.description && (
          <span className={cn("line-clamp-2 text-12", terang ? "text-on-color/80" : "text-secondary")}>
            {kartu.description}
          </span>
        )}
      </span>
    </a>
  );
}

function DaftarKartu({ daftar, terang, className }: { daftar: string[]; terang?: boolean; className?: string }) {
  if (daftar.length === 0) return null;
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      {daftar.map((url) => (
        <KartuPratinjauTautan key={url} url={url} terang={terang} />
      ))}
    </div>
  );
}

/** Kartu untuk tautan di HTML editor (deskripsi work item, komentar). */
export function PratinjauTautanHtml({ html, className }: { html: string | null | undefined; className?: string }) {
  return <DaftarKartu daftar={alamatDariHtml(html)} className={className} />;
}

/** Jeda ketik sebelum kotak tulis mencari pratinjau, supaya tiap huruf tidak jadi permintaan. */
const JEDA_DRAF_MS = 600;

/**
 * Pratinjau di atas kotak tulis selagi mengetik: memperlihatkan kartu yang akan
 * ikut terkirim. Alamat baru dicari setelah orang berhenti mengetik sebentar.
 */
export function PratinjauTautanDraf({ teks, className }: { teks: string; className?: string }) {
  const [alamat, setAlamat] = useState<string | undefined>(undefined);
  useEffect(() => {
    const jeda = setTimeout(() => setAlamat(alamatDariTeks(teks, 1)[0]), JEDA_DRAF_MS);
    return () => clearTimeout(jeda);
  }, [teks]);
  if (!alamat || !teks.includes(alamat)) return null;
  return <KartuPratinjauTautan key={alamat} url={alamat} className={className} />;
}

/** Kartu untuk tautan di teks biasa (chat). Chat cukup satu kartu, seperti aplikasi pesan. */
export function PratinjauTautanTeks({
  teks,
  maks = 1,
  terang,
  className,
}: {
  teks: string;
  maks?: number;
  terang?: boolean;
  className?: string;
}) {
  return <DaftarKartu daftar={alamatDariTeks(teks, maks)} terang={terang} className={className} />;
}
