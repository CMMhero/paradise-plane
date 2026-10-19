/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kartu pop-up pemberitahuan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Bell, Hash, MessageSquare, X } from "lucide-react";
import { Avatar } from "@plane/ui";
import { cn, getFileURL } from "@plane/utils";

export type TPopup = {
  /** Unik per kemunculan, bukan per pengirim: dua pesan dari orang yang sama
   * adalah dua kartu. */
  id: string;
  jenis: "pesan" | "kanal" | "tugas";
  judul: string;
  isi: string;
  namaOrang?: string | undefined;
  avatarUrl?: string | undefined;
  tautan: string;
};

/** Selama ini kartunya bertahan. Cukup untuk membaca dua baris tanpa terburu,
 * masih di bawah ambang orang mulai merasa layarnya dikuasai sesuatu. */
const UMUR = 7000;
/** Sama dengan durasi transisi di bawah. Kartunya baru dibuang SESUDAH animasi
 * keluarnya selesai; membuangnya lebih cepat membuat kartu berikutnya melompat
 * naik sementara yang lama masih separuh terlihat. */
const DURASI = 300;

const IKON = {
  pesan: MessageSquare,
  kanal: Hash,
  tugas: Bell,
} as const;

/**
 * Satu kartu pemberitahuan yang masuk dari kanan, lalu pergi sendiri.
 *
 * Yang dianimasikan hanya `transform` dan `opacity`. Keduanya dikerjakan
 * compositor, jadi kartu yang muncul saat orang sedang menggulung papan berisi
 * ratusan tugas tidak ikut membuat gulirannya tersendat.
 *
 * Hitungan mundurnya berhenti saat kursor ada di atas kartu, lalu dimulai LAGI
 * DARI AWAL begitu kursor pergi. Pemberitahuan yang justru kabur tepat ketika
 * orang mengarahkan kursor untuk membacanya adalah bentuk kecil dari mengejek.
 */
const KartuPopup = ({
  data,
  onTutup,
  onBuka,
}: {
  data: TPopup;
  onTutup: (id: string) => void;
  onBuka: (tautan: string) => void;
}) => {
  const [terlihat, setTerlihat] = useState(false);
  const [berjalan, setBerjalan] = useState(false);
  const jam = useRef<ReturnType<typeof setTimeout> | null>(null);

  const tutup = useCallback(() => {
    setTerlihat(false);
    setTimeout(() => onTutup(data.id), DURASI);
  }, [data.id, onTutup]);

  useEffect(() => {
    // Dua bingkai, bukan satu: satu bingkai untuk menempelkan elemen dengan
    // keadaan awalnya, satu lagi untuk mengubahnya. Tanpa jeda itu peramban
    // menggabungkan keduanya dan kartunya muncul begitu saja tanpa bergerak.
    const bingkai = requestAnimationFrame(() =>
      requestAnimationFrame(() => {
        setTerlihat(true);
        setBerjalan(true);
      })
    );
    return () => cancelAnimationFrame(bingkai);
  }, []);

  useEffect(() => {
    if (!berjalan) return;
    jam.current = setTimeout(tutup, UMUR);
    return () => {
      if (jam.current) clearTimeout(jam.current);
    };
  }, [berjalan, tutup]);

  const Ikon = IKON[data.jenis];
  // Avatar dipakai untuk SEMUA jenis, termasuk tugas: wajah pemberi tugas lebih
  // cepat dikenali daripada lonceng, dan lencana di sudutlah yang membedakan
  // pesan dari tugas.
  const punyaAvatar = Boolean(data.namaOrang);

  return (
    <div
      role="status"
      onMouseEnter={() => setBerjalan(false)}
      onMouseLeave={() => setBerjalan(true)}
      className={cn(
        "group pointer-events-auto relative w-[22rem] max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl",
        "border border-subtle bg-surface-1 shadow-overlay-200",
        "transition-[transform,opacity] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]",
        "motion-reduce:translate-x-0 motion-reduce:transition-opacity",
        terlihat ? "translate-x-0 opacity-100" : "translate-x-[110%] opacity-0"
      )}
    >
      <button
        type="button"
        onClick={() => {
          onBuka(data.tautan);
          tutup();
        }}
        className="flex w-full items-start gap-3 p-3 text-left transition-colors hover:bg-layer-1 focus-visible:bg-layer-1 focus-visible:outline-none"
      >
        <span className="relative mt-0.5 shrink-0">
          {punyaAvatar ? (
            <Avatar name={data.namaOrang} src={getFileURL(data.avatarUrl ?? "")} size={36} shape="circle" />
          ) : (
            <span className="grid size-9 place-items-center rounded-full bg-accent-primary/10">
              <Ikon className="size-4 text-accent-primary" />
            </span>
          )}
          {/* Lencana kecil di sudut avatar: dari jauh orang tahu ini pesan atau
              tugas tanpa membaca satu kata pun. */}
          <span className="absolute -right-0.5 -bottom-0.5 grid size-4 place-items-center rounded-full bg-surface-1">
            <Ikon className="size-2.5 text-accent-primary" />
          </span>
        </span>

        <span className="min-w-0 flex-1">
          <span className="text-sm block truncate leading-5 font-semibold text-primary">{data.judul}</span>
          <span className="text-xs mt-0.5 line-clamp-2 block leading-4 text-tertiary">{data.isi}</span>
        </span>
      </button>

      <button
        type="button"
        aria-label="Tutup pemberitahuan"
        onClick={tutup}
        className="absolute top-2 right-2 grid size-6 place-items-center rounded-md text-tertiary opacity-0 transition-opacity group-hover:opacity-100 hover:bg-layer-2 hover:text-primary focus-visible:opacity-100"
      >
        <X className="size-3.5" />
      </button>

      {/* Sisa waktunya terlihat, jadi kartu yang menghilang tidak terasa seperti
          gangguan yang tiba-tiba dicabut. Menyusut lewat scaleX supaya tetap
          urusan compositor, bukan tata letak. */}
      <span className="block h-0.5 w-full bg-layer-2">
        <span
          className={cn(
            "block h-full origin-left bg-accent-primary transition-transform ease-linear",
            berjalan ? "scale-x-0" : "scale-x-100"
          )}
          style={{ transitionDuration: berjalan ? `${UMUR}ms` : "150ms" }}
        />
      </span>
    </div>
  );
};

/**
 * Tumpukan kartu di pojok kanan atas.
 *
 * Pojok KANAN ATAS, bukan kanan bawah, karena kanan bawah sudah ditempati toast
 * bawaan aplikasi (`right-3 bottom-3` di propel). Dua hal berbeda yang muncul di
 * titik yang sama akan saling menimpa pada saat paling buruk: ketika keduanya
 * memang sedang ingin memberi tahu sesuatu.
 */
export const TumpukanPopup = ({
  daftar,
  onTutup,
  onBuka,
}: {
  daftar: TPopup[];
  onTutup: (id: string) => void;
  onBuka: (tautan: string) => void;
}) => {
  if (daftar.length === 0) return null;

  return (
    <div className="pointer-events-none fixed top-[4.5rem] right-4 z-[90] flex flex-col items-end gap-2">
      {daftar.map((p) => (
        <KartuPopup key={p.id} data={p} onTutup={onTutup} onBuka={onBuka} />
      ))}
    </div>
  );
};
