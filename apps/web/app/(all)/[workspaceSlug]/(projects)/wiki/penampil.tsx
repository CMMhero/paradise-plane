/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: bingkai penampil Materi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useState } from "react";
import { Maximize2, Minimize2, RotateCcw, ZoomIn, ZoomOut } from "lucide-react";
import { cn } from "@plane/utils";
// services
import type { TPratinjauMateri } from "@/services/wiki_material.service";

const ZOOM_MIN = 0.25;
const ZOOM_MAKS = 5;
const ZOOM_LANGKAH = 0.25;

/**
 * Satu bingkai untuk semua tipe materi, berikut layar penuh dan zoom.
 *
 * Layar penuhnya sengaja overlay di dalam aplikasi, BUKAN Fullscreen API
 * peramban. Alasannya bukan selera: dengan overlay, bilah alat kita ikut
 * terbawa, jadi orang tetap punya tombol "kembali normal" yang terlihat.
 * Fullscreen API menyembunyikan seluruh chrome peramban dan menyisakan orang
 * dengan satu-satunya jalan keluar berupa tombol Escape yang tidak tertulis di
 * mana pun.
 *
 * Zoom hanya ditawarkan untuk gambar, dan itu jujur: PDF (termasuk hasil
 * konversi Word, Excel, dan PowerPoint) dirender oleh penampil bawaan peramban
 * di dalam iframe, yang PUNYA kontrol zoom sendiri dan tidak bisa kita setir
 * dari luar. Menampilkan tombol zoom yang tidak berbuat apa-apa lebih buruk
 * daripada tidak menampilkannya.
 */
export function PenampilMateri({ pratinjau }: { pratinjau: TPratinjauMateri }) {
  const { kind, url, title } = pratinjau;
  const [layarPenuh, setLayarPenuh] = useState(false);
  const [zoom, setZoom] = useState(1);

  const bisaZoom = kind === "image";

  const keluar = useCallback(() => {
    setLayarPenuh(false);
    setZoom(1);
  }, []);

  // Escape harus bekerja, karena itu yang pertama dicoba orang untuk keluar
  // dari layar penuh, sebelum mencari tombol.
  useEffect(() => {
    if (!layarPenuh) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") keluar();
    };
    window.addEventListener("keydown", onKey);
    // Halaman di belakang jangan ikut bergulir saat overlay terbuka.
    const sebelumnya = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = sebelumnya;
    };
  }, [layarPenuh, keluar]);

  if (!url) return null;

  const tinggi = layarPenuh ? "h-[calc(100vh-3.5rem)]" : "h-[calc(100vh-16rem)]";

  const isi = () => {
    if (kind === "image")
      return (
        <div className={cn("flex w-full items-center justify-center overflow-auto", tinggi)}>
          <img
            src={url}
            alt={title}
            style={{ transform: `scale(${zoom})`, transformOrigin: "center center" }}
            className="max-h-full w-auto max-w-full rounded-lg object-contain transition-transform duration-150"
          />
        </div>
      );

    if (kind === "video")
      return (
        // oxlint-disable-next-line jsx-a11y/media-has-caption
        <video src={url} controls preload="metadata" className={cn("w-full rounded-lg bg-black", tinggi)} />
      );

    if (kind === "audio")
      return (
        <div className="grid place-items-center py-16">
          {/* oxlint-disable-next-line jsx-a11y/media-has-caption */}
          <audio src={url} controls className="w-full max-w-xl" />
        </div>
      );

    return (
      <iframe
        src={url}
        title={title}
        // PDF SENGAJA tanpa sandbox: Chrome menolak memuat penampil PDF
        // bawaannya di dalam iframe ber-sandbox, apa pun kombinasi tokennya.
        // Berkas teks justru dikunci penuh, karena isinya unggahan orang.
        sandbox={kind === "pdf" ? undefined : ""}
        className={cn("w-full rounded-lg border border-subtle bg-layer-1", tinggi)}
      />
    );
  };

  const bilah = (
    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
      <div className="flex items-center gap-1">
        {bisaZoom ? (
          <>
            <button
              type="button"
              aria-label="Perkecil"
              onClick={() => setZoom((z) => Math.max(ZOOM_MIN, z - ZOOM_LANGKAH))}
              className="grid size-8 place-items-center rounded-md border border-subtle text-secondary transition-colors hover:border-strong hover:text-primary"
            >
              <ZoomOut className="size-4" />
            </button>
            <span className="min-w-14 text-center text-12 text-tertiary tabular-nums">{Math.round(zoom * 100)}%</span>
            <button
              type="button"
              aria-label="Perbesar"
              onClick={() => setZoom((z) => Math.min(ZOOM_MAKS, z + ZOOM_LANGKAH))}
              className="grid size-8 place-items-center rounded-md border border-subtle text-secondary transition-colors hover:border-strong hover:text-primary"
            >
              <ZoomIn className="size-4" />
            </button>
            <button
              type="button"
              aria-label="Kembalikan ukuran asli"
              onClick={() => setZoom(1)}
              className="grid size-8 place-items-center rounded-md border border-subtle text-secondary transition-colors hover:border-strong hover:text-primary"
            >
              <RotateCcw className="size-4" />
            </button>
          </>
        ) : (
          <span className="text-11 text-tertiary">
            {kind === "pdf"
              ? "Zoom dan cari ada di dalam penampil PDF-nya sendiri."
              : kind === "video" || kind === "audio"
                ? "Kontrol putar ada di pemutarnya."
                : ""}
          </span>
        )}
      </div>

      <button
        type="button"
        onClick={() => (layarPenuh ? keluar() : setLayarPenuh(true))}
        className="inline-flex items-center gap-1.5 rounded-md border border-subtle px-3 py-1.5 text-12 font-medium text-secondary transition-colors hover:border-strong hover:text-primary"
      >
        {layarPenuh ? (
          <>
            <Minimize2 className="size-3.5" />
            Kembali normal
          </>
        ) : (
          <>
            <Maximize2 className="size-3.5" />
            Layar penuh
          </>
        )}
      </button>
    </div>
  );

  if (layarPenuh)
    return (
      <div className="fixed inset-0 z-50 flex flex-col bg-canvas p-4">
        <div className="mb-1 truncate text-13 font-medium text-primary">{title}</div>
        {bilah}
        <div className="flex-1 overflow-auto">{isi()}</div>
      </div>
    );

  return (
    <div>
      {bilah}
      {isi()}
    </div>
  );
}
