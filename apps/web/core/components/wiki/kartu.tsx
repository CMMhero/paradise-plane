/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kartu pustaka Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import {
  ArrowRight,
  BookOpen,
  FileSpreadsheet,
  FileText,
  Image as ImageIcon,
  Music,
  Presentation,
  Users,
  Video,
} from "lucide-react";
import { Link } from "react-router";
import { useTranslation } from "@plane/i18n";
import { getButtonStyling } from "@plane/propel/button";
import { Logo } from "@plane/propel/emoji-icon-picker";
import type { TLogoProps } from "@plane/types";
import { cn } from "@plane/utils";
// components
import type { TTintHue } from "@/components/common/tint";
import { TINT_CHIP_CLASS } from "@/components/common/tint";
// local imports
import { gradienUntuk } from "./gradien";

type TKartuDasar = {
  /** Tujuan klik. Sengaja `Link`, bukan onClick: klik tengah dan salin tautan tetap bekerja. */
  to: string;
  judul: string;
  keterangan?: string;
  logoProps?: TLogoProps;
};

type TKartuFolder = TKartuDasar & {
  jumlahAnak: number;
  satuanAnak: string;
  /**
   * Halaman departemen yang boleh dilihat (KEP-97). Hanya untuk folder divisi
   * dan departemen; folder lain tidak punya halaman, jadi chipnya tidak tampil.
   */
  halaman?: { jumlah: number; satuan: string };
  terbuka?: boolean;
  /** Tombol ubah/hapus cepat, kalau orangnya boleh mengelola folder ini. */
  aksi?: React.ReactNode;
};

type TKartuMateri = TKartuDasar & {
  /** MIME berkasnya, penentu ikon dan label. */
  tipe: string;
  label: string;
  ukuran: string;
  /** Menu aksi, kalau orangnya boleh mengelola materi ini. */
  aksi?: React.ReactNode;
  /** Diisi bila kartu ini boleh diseret ke folder lain (hak ubah materi). */
  onSeretMulai?: (e: React.DragEvent<HTMLElement>) => void;
};

const SAMPUL = "relative flex h-[132px] items-center justify-center overflow-hidden";
const KARTU =
  "group relative flex flex-col overflow-hidden rounded-card border border-subtle bg-layer-2 transition-shadow duration-200 hover:border-strong hover:shadow-raised-200 focus-visible:border-strong";

/** Rona chip jenis berkas: lembar kerja hijau, presentasi oranye, dst., supaya jenisnya terbaca sekilas. */
function ronaBerkas(tipe: string): TTintHue {
  if (tipe.startsWith("image/")) return "purple";
  if (tipe.startsWith("video/")) return "pink";
  if (tipe.startsWith("audio/")) return "yellow";
  if (tipe.includes("spreadsheetml") || tipe === "application/vnd.ms-excel") return "emerald";
  if (tipe.includes("presentationml") || tipe === "application/vnd.ms-powerpoint") return "orange";
  if (tipe === "application/pdf") return "crimson";
  return "indigo";
}

/** Ikon yang menjawab "ini berkas apa" dari jauh, sebelum judulnya terbaca. */
function IkonBerkas({ tipe }: { tipe: string }) {
  const kelas = "size-12";
  if (tipe.startsWith("image/")) return <ImageIcon className={kelas} strokeWidth={1.5} />;
  if (tipe.startsWith("video/")) return <Video className={kelas} strokeWidth={1.5} />;
  if (tipe.startsWith("audio/")) return <Music className={kelas} strokeWidth={1.5} />;
  if (tipe.includes("spreadsheetml") || tipe === "application/vnd.ms-excel")
    return <FileSpreadsheet className={kelas} strokeWidth={1.5} />;
  if (tipe.includes("presentationml") || tipe === "application/vnd.ms-powerpoint")
    return <Presentation className={kelas} strokeWidth={1.5} />;
  return <FileText className={kelas} strokeWidth={1.5} />;
}

/**
 * Kartu Divisi atau Topik: sesuatu yang BERISI hal lain.
 *
 * Ia selalu memakai kata kerja "Lihat" dan selalu menyebut berapa banyak
 * isinya, termasuk ketika isinya nol. Folder kosong yang jujur mengaku kosong
 * jauh lebih berguna daripada folder yang terlihat sama saja lalu mengecewakan
 * setelah diklik.
 */
export function KartuFolder({
  to,
  judul,
  keterangan,
  logoProps,
  jumlahAnak,
  satuanAnak,
  halaman,
  terbuka,
  aksi,
}: TKartuFolder) {
  const { t } = useTranslation();
  return (
    <div className={KARTU}>
      <Link to={to} className="flex flex-1 flex-col">
        <div className={SAMPUL} style={{ backgroundImage: gradienUntuk(judul) }}>
          {logoProps?.in_use ? (
            <span className="grid size-16 place-items-center rounded-card bg-white/20 text-white backdrop-blur-[1px]">
              <Logo logo={logoProps} size={34} type="lucide" />
            </span>
          ) : (
            <span className="text-white/95">
              <BookOpen className="size-12" strokeWidth={1.5} />
            </span>
          )}
          {terbuka && (
            <span className="absolute top-3 left-3 inline-flex items-center gap-1 rounded-control bg-white/20 px-2 py-0.5 text-11 font-medium text-white backdrop-blur-[1px]">
              <Users className="size-3" /> {t("wiki_ui.card.open")}
            </span>
          )}
        </div>

        <div className="flex flex-1 flex-col p-4">
          <h3 className="truncate text-14 font-semibold text-primary">{judul}</h3>
          <p className="mt-1 line-clamp-1 text-12 text-tertiary">{keterangan || t("wiki_ui.card.no_description")}</p>

          <div className="mt-4 flex flex-col gap-3 border-t border-subtle pt-3">
            <span className="flex w-full items-center gap-1.5">
              <span className="inline-flex min-w-0 flex-1 items-center justify-center gap-1.5 rounded-control bg-accent-subtle px-2.5 py-1.5 text-11 font-medium text-accent-primary">
                <BookOpen className="size-3.5 shrink-0" />
                <span className="truncate">
                  {jumlahAnak} {satuanAnak}
                </span>
              </span>
              {halaman && (
                <span className="inline-flex min-w-0 flex-1 items-center justify-center gap-1.5 rounded-control bg-layer-3 px-2.5 py-1.5 text-11 font-medium text-secondary">
                  <FileText className="size-3.5 shrink-0" />
                  <span className="truncate">
                    {halaman.jumlah} {halaman.satuan}
                  </span>
                </span>
              )}
            </span>
            <span className="inline-flex items-center gap-1 text-12 font-medium text-secondary transition-colors group-hover:text-accent-primary">
              {t("wiki_ui.card.view")} <ArrowRight className="size-3.5" />
            </span>
          </div>
        </div>
      </Link>

      {/* Di luar <Link> supaya menekan tombolnya tidak ikut membuka foldernya. */}
      {/* Kanan atas, sama dengan kartu materi, supaya aksinya selalu di tempat yang sama. */}
      {aksi && <div className="absolute top-2 right-2 flex gap-1">{aksi}</div>}
    </div>
  );
}

/**
 * Kartu Materi: satu berkas yang sudah diunggah seseorang.
 *
 * Ia menyebut tipe dan ukurannya di muka, dan itu bukan hiasan. Orang di
 * jaringan kantor berhak tahu bahwa yang akan dibuka itu video 180 MB sebelum
 * menekannya, bukan sesudah.
 */
export function KartuMateri({ to, judul, keterangan, tipe, label, ukuran, aksi, onSeretMulai }: TKartuMateri) {
  const { t } = useTranslation();
  return (
    <div className={cn(KARTU, onSeretMulai && "cursor-grab active:cursor-grabbing")} draggable={!!onSeretMulai} onDragStart={onSeretMulai}>
      {/* Tautan tidak ikut diseret sendiri: yang berpindah kartunya, bukan alamatnya. */}
      <Link to={to} draggable={onSeretMulai ? false : undefined} className="flex flex-1 flex-col">
        <div className={SAMPUL} style={{ backgroundImage: gradienUntuk(judul) }}>
          <span className="text-white/95">
            <IkonBerkas tipe={tipe} />
          </span>
        </div>

        <div className="flex flex-1 flex-col p-4">
          <h3 className="truncate text-14 font-semibold text-primary">{judul}</h3>
          <p className="mt-1 line-clamp-1 text-12 text-tertiary">{keterangan}</p>

          <div className="mt-4 flex items-center justify-between border-t border-subtle pt-3">
            <span
              className={cn(
                "rounded-control px-2 py-1 text-11 font-medium tracking-wide",
                TINT_CHIP_CLASS[ronaBerkas(tipe)]
              )}
            >
              {label} · {ukuran}
            </span>
            <span className={getButtonStyling("secondary", "base")}>{t("wiki_ui.card.open_material")}</span>
          </div>
        </div>
      </Link>

      {/* Di luar <Link> supaya menekan tombolnya tidak ikut membuka materinya. */}
      {aksi && <div className="absolute top-2 right-2 flex gap-1">{aksi}</div>}
    </div>
  );
}

/** Kerangka kartu selagi datanya dimuat. Ukurannya sengaja sama persis supaya tidak ada lompatan tata letak. */
export function KartuKerangka() {
  return (
    <div className="overflow-hidden rounded-card border border-subtle bg-layer-2">
      <div className="h-[132px] animate-pulse bg-layer-3" />
      <div className="space-y-2 p-4">
        <div className="h-4 w-2/3 animate-pulse rounded-item bg-layer-3" />
        <div className="h-3 w-1/2 animate-pulse rounded-item bg-layer-3" />
        <div className="mt-4 h-6 w-full animate-pulse rounded-item bg-layer-3" />
      </div>
    </div>
  );
}

/** Grid yang dipakai ketiga tingkat, supaya lebarnya konsisten di seluruh Wiki. */
export function GridKartu({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">{children}</div>;
}
