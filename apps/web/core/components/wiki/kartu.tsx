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
import { Logo } from "@plane/propel/emoji-icon-picker";
import type { TLogoProps } from "@plane/types";
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
  terbuka?: boolean;
};

type TKartuMateri = TKartuDasar & {
  /** MIME berkasnya, penentu ikon dan label. */
  tipe: string;
  label: string;
  ukuran: string;
  /** Menu aksi, kalau orangnya boleh mengelola materi ini. */
  aksi?: React.ReactNode;
};

const SAMPUL = "relative flex h-[132px] items-center justify-center overflow-hidden";
const KARTU =
  "group relative flex flex-col overflow-hidden rounded-lg border border-subtle bg-layer-2 transition-shadow duration-200 hover:border-strong hover:shadow-raised-200 focus-visible:border-strong";

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
export function KartuFolder({ to, judul, keterangan, logoProps, jumlahAnak, satuanAnak, terbuka }: TKartuFolder) {
  return (
    <Link to={to} className={KARTU}>
      <div className={SAMPUL} style={{ backgroundImage: gradienUntuk(judul) }}>
        {logoProps?.in_use ? (
          <span className="grid size-16 place-items-center rounded-2xl bg-white/20 text-white backdrop-blur-[1px]">
            <Logo logo={logoProps} size={34} type="lucide" />
          </span>
        ) : (
          <span className="text-white/95">
            <BookOpen className="size-12" strokeWidth={1.5} />
          </span>
        )}
        {terbuka && (
          <span className="absolute top-3 right-3 inline-flex items-center gap-1 rounded-full bg-white/20 px-2 py-0.5 text-11 font-medium text-white backdrop-blur-[1px]">
            <Users className="size-3" /> Terbuka
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col p-4">
        <h3 className="text-15 truncate font-semibold text-primary">{judul}</h3>
        <p className="mt-1 line-clamp-1 text-12 text-tertiary">{keterangan || "Belum ada keterangan"}</p>

        <div className="mt-4 flex items-center justify-between border-t border-subtle pt-3">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-accent-subtle px-2.5 py-1 text-11 font-medium text-accent-primary">
            <BookOpen className="size-3.5" />
            {jumlahAnak} {satuanAnak}
          </span>
          <span className="inline-flex items-center gap-1 text-12 font-medium text-secondary transition-colors group-hover:text-accent-primary">
            Lihat <ArrowRight className="size-3.5" />
          </span>
        </div>
      </div>
    </Link>
  );
}

/**
 * Kartu Materi: satu berkas yang sudah diunggah seseorang.
 *
 * Ia menyebut tipe dan ukurannya di muka, dan itu bukan hiasan. Orang di
 * jaringan kantor berhak tahu bahwa yang akan dibuka itu video 180 MB sebelum
 * menekannya, bukan sesudah.
 */
export function KartuMateri({ to, judul, keterangan, tipe, label, ukuran, aksi }: TKartuMateri) {
  return (
    <div className={KARTU}>
      <Link to={to} className="flex flex-1 flex-col">
        <div className={SAMPUL} style={{ backgroundImage: gradienUntuk(judul) }}>
          <span className="text-white/95">
            <IkonBerkas tipe={tipe} />
          </span>
        </div>

        <div className="flex flex-1 flex-col p-4">
          <h3 className="text-15 truncate font-semibold text-primary">{judul}</h3>
          <p className="mt-1 line-clamp-1 text-12 text-tertiary">{keterangan}</p>

          <div className="mt-4 flex items-center justify-between border-t border-subtle pt-3">
            <span className="rounded-md bg-layer-3 px-2 py-1 text-11 font-medium tracking-wide text-tertiary">
              {label} · {ukuran}
            </span>
            <span className="rounded-md border border-accent-strong px-3 py-1 text-12 font-medium text-accent-primary transition-colors group-hover:bg-accent-primary group-hover:text-on-color">
              Buka
            </span>
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
    <div className="overflow-hidden rounded-lg border border-subtle bg-layer-2">
      <div className="h-[132px] animate-pulse bg-layer-3" />
      <div className="space-y-2 p-4">
        <div className="h-4 w-2/3 animate-pulse rounded bg-layer-3" />
        <div className="h-3 w-1/2 animate-pulse rounded bg-layer-3" />
        <div className="mt-4 h-6 w-full animate-pulse rounded bg-layer-3" />
      </div>
    </div>
  );
}

/** Grid yang dipakai ketiga tingkat, supaya lebarnya konsisten di seluruh Wiki. */
export function GridKartu({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">{children}</div>;
}
